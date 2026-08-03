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
