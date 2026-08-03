# tests/test_jenkins_cli.py
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import cli  # noqa: E402

REGISTRY = _ROUTINES / "jenkins-jobs.yaml"


def test_missing_token_exits_zero_and_reports_gap(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.delenv("JENKINS_USER", raising=False)
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "UNREACHABLE" in out


def test_bad_registry_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("jobs:\n  - tier: fix\n", encoding="utf-8")
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(bad)])
    assert rc == 2


def test_writes_snapshot_and_report_files(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Client:
        def all_jobs(self):
            return {
                "quant-DailySimDataUpdateLP": {
                    "lastBuild": {"number": 93, "result": "SUCCESS", "timestamp": 1785690000000},
                    "lastSuccessfulBuild": {"number": 93, "timestamp": 1785690000000},
                }
            }

        def recent_builds(self, job, limit=25):
            from jenkins_monitor.client import ms_to_dt
            from jenkins_monitor.models import BuildInfo

            return [BuildInfo(93, "SUCCESS", ms_to_dt(1785690000000))]

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY), "--no-diagnose"])
    assert rc == 0
    snaps = list(tmp_path.glob("jenkins-status-*.json"))
    assert len(snaps) == 1
    data = json.loads(snaps[0].read_text(encoding="utf-8"))
    assert "quant-DailySimDataUpdateLP" in data
    assert list(tmp_path.glob("jenkins-monitor-*.md"))


def test_report_scope_line_reflects_actual_tier_counts(tmp_path, monkeypatch):
    """report.render must get real fix/notify counts computed from the registry,
    not stale defaults - otherwise the scope line silently goes wrong the moment a
    job is added to or archived from the registry."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Client:
        def all_jobs(self):
            return {}

        def recent_builds(self, job, limit=25):
            return []

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())

    captured = {}
    real_render = cli.report.render

    def _spy_render(findings, **kwargs):
        captured.update(kwargs)
        return real_render(findings, **kwargs)

    monkeypatch.setattr(cli.report, "render", _spy_render)
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY), "--no-diagnose"])
    assert rc == 0

    from jenkins_monitor import registry as registry_mod

    specs = registry_mod.load_registry(REGISTRY)
    expected_fix = sum(1 for s in specs.values() if s.tier == "fix")
    assert captured["fix_count"] == expected_fix
    assert captured["notify_count"] == len(specs) - expected_fix


def test_bad_cadence_entry_does_not_crash_whole_run(tmp_path, monkeypatch):
    """classify.classify_job deliberately lets CadenceError propagate for a pure
    classifier - but the CLI is the unattended daily entry point, so one malformed
    registry entry (an unparseable cron expression) must degrade to a single
    isolated UNREACHABLE finding, not take down the report for every other job."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
jobs:
  - job: good-job
    tier: fix
    family: test
    trigger_type: cron
    cron: "0 12 * * *"
    tz: America/New_York
    grace_hours: 6
  - job: bad-cadence-job
    tier: fix
    family: test
    trigger_type: cron
    cron: "0 99 * * *"
    tz: America/New_York
    grace_hours: 6
""",
        encoding="utf-8",
    )

    blob = {
        "lastBuild": {"number": 5, "result": "SUCCESS", "timestamp": 1785690000000},
        "lastSuccessfulBuild": {"number": 5, "timestamp": 1785690000000},
    }

    class _Client:
        def all_jobs(self):
            return {"good-job": blob, "bad-cadence-job": blob}

        def recent_builds(self, job, limit=25):
            from jenkins_monitor.client import ms_to_dt
            from jenkins_monitor.models import BuildInfo

            return [BuildInfo(5, "SUCCESS", ms_to_dt(1785690000000))]

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(reg), "--no-diagnose"])
    assert rc == 0

    snaps = list(tmp_path.glob("jenkins-status-*.json"))
    assert len(snaps) == 1
    data = json.loads(snaps[0].read_text(encoding="utf-8"))
    # Both jobs made it into the snapshot - the bad one downgraded, the good one untouched.
    assert set(data) == {"good-job", "bad-cadence-job"}
    assert data["bad-cadence-job"] == "UNREACHABLE"

    report_text = tmp_path.glob("jenkins-monitor-*.md")
    text = next(iter(report_text)).read_text(encoding="utf-8")
    assert "bad-cadence-job" in text
    assert "good-job" in data  # present in snapshot regardless of its own classified state


def test_main_survives_non_ascii_report_on_strict_cp1252_stdout(tmp_path, monkeypatch):
    """sys.stdout.encoding is cp1252 in the production environment. Task 7 stripped
    non-ASCII from report.py, but the CLI is the process boundary and must not be one
    edit away from a crash that produces no report at all. Reproduce a strict cp1252
    stdout and confirm main() still completes when the rendered text is non-ASCII."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Client:
        def all_jobs(self):
            return {}

        def recent_builds(self, job, limit=25):
            return []

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    monkeypatch.setattr(cli.report, "render", lambda *a, **k: "status caf\u00e9 done \u2713")

    buffer = io.BytesIO()
    fake_stdout = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY), "--no-diagnose"])
    fake_stdout.flush()

    assert rc == 0
    written = buffer.getvalue().decode("utf-8")
    assert "caf" in written


def test_file_writes_use_utf8_even_with_non_ascii_content(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Client:
        def all_jobs(self):
            return {}

        def recent_builds(self, job, limit=25):
            return []

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    monkeypatch.setattr(cli.report, "render", lambda *a, **k: "status caf\u00e9 done \u2713")

    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY), "--no-diagnose"])
    assert rc == 0
    md = next(iter(tmp_path.glob("jenkins-monitor-*.md")))
    assert "caf\u00e9" in md.read_text(encoding="utf-8")


def _stamp() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).astimezone().strftime("%Y%m%d")


def _red_registry(tmp_path, count, trigger="manual"):
    lines = ["jobs:"]
    for i in range(count):
        lines += [
            f"  - job: red-job-{i}",
            "    tier: fix",
            "    family: test",
            f"    trigger_type: {trigger}",
        ]
    reg = tmp_path / "reg.yaml"
    reg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return reg


def _red_blob(number=293, success=276):
    return {
        "lastBuild": {"number": number, "result": "FAILURE", "timestamp": 1785690000000},
        "lastSuccessfulBuild": {"number": success, "timestamp": 1785600000000},
        "lastFailedBuild": {"number": number, "timestamp": 1785690000000},
    }


# --- Final review, CRITICAL 1 part 1: `except JenkinsUnreachable: builds = []` made a
# --- failed per-job fetch indistinguishable from "this job has only seed builds". A
# --- genuinely red manual-trigger job was reported GREEN with a fabricated detail, and
# --- every other job became NEVER_DID_WORK - which was then written to the snapshot and
# --- produced a fabricated RECOVERED the next day for a job that never broke.


def test_failed_build_history_fetch_is_unreachable_not_green(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)

    from jenkins_monitor import client as client_mod

    class _Client:
        def all_jobs(self):
            return {"red-job-0": _red_blob()}

        def recent_builds(self, job, limit=25):
            raise client_mod.JenkinsUnreachable("GET /job/red-job-0/api/json returned HTTP 500")

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(reg), "--no-diagnose"])
    assert rc == 0

    data = json.loads(next(iter(tmp_path.glob("jenkins-status-*.json"))).read_text(encoding="utf-8"))
    assert data["red-job-0"] == "UNREACHABLE", (
        "a failed per-job fetch is an unknown state; GREEN or NEVER_DID_WORK here is a "
        "fabricated verdict, and NEVER_DID_WORK in the snapshot fabricates a RECOVERED tomorrow"
    )
    text = next(iter(tmp_path.glob("jenkins-monitor-*.md"))).read_text(encoding="utf-8")
    assert "could not read build history" in text


def test_failed_build_history_fetch_is_reported_never_dropped_as_green(tmp_path, monkeypatch):
    """The job must still appear as a finding. The old code produced GREEN for a
    manual-trigger job, and statediff drops GREEN-was-GREEN entirely - so a red job
    vanished from the report instead of being reported."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)

    from jenkins_monitor import client as client_mod

    class _Client:
        def all_jobs(self):
            return {"red-job-0": _red_blob()}

        def recent_builds(self, job, limit=25):
            raise client_mod.JenkinsUnreachable("boom")

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    captured = {}
    real_render = cli.report.render

    def _spy(findings, **kwargs):
        captured["findings"] = findings
        return real_render(findings, **kwargs)

    monkeypatch.setattr(cli.report, "render", _spy)
    assert cli.main(["--outputs", str(tmp_path), "--registry", str(reg), "--no-diagnose"]) == 0
    assert [f.status.job for f in captured["findings"]] == ["red-job-0"]
    assert captured["findings"][0].status.state != "GREEN"


# --- Final review, IMPORTANT 2: both file writes preceded print(text). The outputs
# --- directory lives on a NAS share, so an OSError from the snapshot write - after all 25
# --- jobs were classified and the red one diagnosed - lost the entire report, which the
# --- daily routine consumes from stdout. The snapshot was also written first, so a failure
# --- in between committed today's states while losing today's report.


def test_report_reaches_stdout_even_when_outputs_cannot_be_written(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)

    # Both target paths already exist as DIRECTORIES, so write_text and the snapshot's
    # atomic replace both raise OSError - a real filesystem failure, not a monkeypatch.
    stamp = _stamp()
    (tmp_path / f"jenkins-monitor-{stamp}.md").mkdir()
    (tmp_path / f"jenkins-status-{stamp}.json").mkdir()

    class _Client:
        def all_jobs(self):
            return {"red-job-0": _red_blob()}

        def recent_builds(self, job, limit=25):
            from jenkins_monitor.client import ms_to_dt
            from jenkins_monitor.models import BuildInfo

            return [BuildInfo(293, "FAILURE", ms_to_dt(1785690000000))]

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(reg), "--no-diagnose"])

    out = capsys.readouterr().out
    assert rc == 0, "a persistence failure must not cost the caller its exit code"
    assert "### Jenkins Job Monitor" in out, "the report must reach stdout even if nothing can be persisted"
    assert "red-job-0" in out
    assert "could not write" in out.lower()
    assert "NEW / ONGOING / RECOVERED" in out, "the warning must say tomorrow's labels are affected"


# --- Final review, IMPORTANT 4: the cap throttled DIAGNOSIS, and the report then claimed
# --- the capped jobs had been diagnosed. Console fetching is a read-only GET with none of
# --- the cost that motivates the cap, so every eligible finding is diagnosed and the cap
# --- limits only fix-agent nomination. ONGOING findings are diagnosed too - a job red for
# --- three days used to carry detail on day 1 only.


def _diagnosing_client(jobs):
    class _Client:
        def all_jobs(self):
            return {name: _red_blob() for name in jobs}

        def recent_builds(self, job, limit=25):
            from jenkins_monitor.client import ms_to_dt
            from jenkins_monitor.models import BuildInfo

            return [BuildInfo(293, "FAILURE", ms_to_dt(1785690000000))]

        def console(self, job, number):
            return "Traceback (most recent call last):\n  File \"x.py\", line 1, in <module>\nKeyError: 'Transition'\n"

        def build_detail(self, job, number):
            return "FAILURE", {}

    return _Client()


def test_all_eligible_findings_are_diagnosed_not_just_the_first_three(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 5)
    names = [f"red-job-{i}" for i in range(5)]
    monkeypatch.setattr(cli, "_make_client", lambda: _diagnosing_client(names))

    captured = {}
    real_render = cli.report.render

    def _spy(findings, **kwargs):
        captured["findings"] = findings
        captured["capped"] = kwargs.get("capped")
        return real_render(findings, **kwargs)

    monkeypatch.setattr(cli.report, "render", _spy)
    assert cli.main(["--outputs", str(tmp_path), "--registry", str(reg)]) == 0

    findings = captured["findings"]
    assert len(findings) == 5
    undiagnosed = [f.status.job for f in findings if f.diagnosis is None]
    assert undiagnosed == [], f"the fix-slot cap must not throttle diagnosis: {undiagnosed}"
    assert all(f.diagnosis.error_class == "KeyError" for f in findings)
    assert len(captured["capped"]) == 2, "the cap still limits how many are nominated for a fix agent"


def test_ongoing_findings_are_diagnosed_too(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)
    # A prior snapshot with the same RED state makes this finding ONGOING, not NEW.
    (tmp_path / "jenkins-status-20250101.json").write_text('{"red-job-0": "RED"}', encoding="utf-8")
    monkeypatch.setattr(cli, "_make_client", lambda: _diagnosing_client(["red-job-0"]))

    captured = {}
    real_render = cli.report.render

    def _spy(findings, **kwargs):
        captured["findings"] = findings
        return real_render(findings, **kwargs)

    monkeypatch.setattr(cli.report, "render", _spy)
    assert cli.main(["--outputs", str(tmp_path), "--registry", str(reg)]) == 0

    finding = captured["findings"][0]
    assert finding.transition == "ONGOING"
    assert finding.diagnosis is not None, (
        "a job red for three days must keep carrying its diagnosis, not show detail on day 1 only"
    )


def test_finding_notes_survive_diagnosis_enrichment(tmp_path, monkeypatch):
    """cli.py used to rebuild the Finding by hand and silently dropped Finding.notes."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)
    monkeypatch.setattr(cli, "_make_client", lambda: _diagnosing_client(["red-job-0"]))

    real_label = cli.statediff.label

    def _label_with_notes(statuses, previous):
        from dataclasses import replace as _replace

        return [_replace(f, notes=("keep me",)) for f in real_label(statuses, previous)]

    monkeypatch.setattr(cli.statediff, "label", _label_with_notes)

    captured = {}
    real_render = cli.report.render

    def _spy(findings, **kwargs):
        captured["findings"] = findings
        return real_render(findings, **kwargs)

    monkeypatch.setattr(cli.report, "render", _spy)
    assert cli.main(["--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    finding = captured["findings"][0]
    assert finding.diagnosis is not None
    assert finding.notes == ("keep me",)


def test_unreachable_report_file_states_the_real_cause_not_a_credential_guess(tmp_path, monkeypatch):
    """The persisted .md used to claim missing credentials during a controller outage."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    from jenkins_monitor import client as client_mod

    class _Client:
        def all_jobs(self):
            raise client_mod.JenkinsUnreachable("GET http://jenkins.example/api/json returned HTTP 503")

    monkeypatch.setattr(cli, "_make_client", lambda: _Client())
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(REGISTRY), "--no-diagnose"])
    assert rc == 0
    text = next(iter(tmp_path.glob("jenkins-monitor-*.md"))).read_text(encoding="utf-8")
    assert "503" in text
    assert "No Jenkins API credentials in the environment" not in text


def test_first_run_says_labels_are_not_meaningful_yet(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _red_registry(tmp_path, 1)
    monkeypatch.setattr(cli, "_make_client", lambda: _diagnosing_client(["red-job-0"]))
    rc = cli.main(["--outputs", str(tmp_path), "--registry", str(reg), "--no-diagnose"])
    assert rc == 0
    text = next(iter(tmp_path.glob("jenkins-monitor-*.md"))).read_text(encoding="utf-8")
    assert "no prior snapshot" in text.lower()
