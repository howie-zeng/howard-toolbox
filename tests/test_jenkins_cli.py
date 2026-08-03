# tests/test_jenkins_cli.py
"""The thin CLI: fact sheet shape, access gaps, and verdict persistence.

No test here reaches the network. A live Jenkins with real credentials exists in this
environment, so every client is a local fake.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import cli, client  # noqa: E402
from jenkins_monitor.client import ms_to_dt  # noqa: E402
from jenkins_monitor.models import BuildInfo  # noqa: E402

REGISTRY = _ROUTINES / "jenkins-jobs.yaml"

# 2026-08-02T18:20:00Z, i.e. recent relative to nothing in particular - these tests assert
# shape and provenance, never freshness verdicts, because freshness is the agent's judgment.
_TS = 1785694800000


def _stamp() -> str:
    return dt.datetime.now(dt.UTC).astimezone().strftime("%Y%m%d")


def _one_job_registry(tmp_path, name="test-job", extra=""):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        f"jobs:\n  - job: {name}\n    tier: fix\n    family: test\n    trigger_type: manual\n{extra}",
        encoding="utf-8",
    )
    return reg


class _FakeClient:
    """Minimal stand-in for JenkinsClient. Every method is local."""

    def __init__(self, blobs=None, builds=None, consoles=None, builds_raise=None):
        self._blobs = blobs or {}
        self._builds = builds or {}
        self._consoles = consoles or {}
        self._builds_raise = builds_raise or {}

    def all_jobs(self):
        return self._blobs

    def recent_builds(self, job, limit=25):
        if job in self._builds_raise:
            raise self._builds_raise[job]
        return self._builds.get(job, [])

    def console(self, job, number):
        return self._consoles[(job, number)]


# --------------------------------------------------------------------- last_real_build


def test_last_real_build_skips_not_built_seed_refreshes():
    """The one computation that must stay in code: a NOT_BUILT seed run is not evidence the
    job ran. One job's lastBuild looked 4 hours old while its last real build was 27 days
    old, which read as healthy."""
    builds = [
        BuildInfo(100, "NOT_BUILT", ms_to_dt(_TS)),
        BuildInfo(99, "NOT_BUILT", ms_to_dt(_TS - 3600_000)),
        BuildInfo(98, "FAILURE", ms_to_dt(_TS - 86_400_000)),
        BuildInfo(97, "SUCCESS", ms_to_dt(_TS - 172_800_000)),
    ]
    real = cli.last_real_build(builds)
    assert real is not None
    assert real.number == 98
    assert real.result == "FAILURE"


def test_last_real_build_is_none_when_every_build_is_a_seed_refresh():
    builds = [BuildInfo(2, "NOT_BUILT", ms_to_dt(_TS)), BuildInfo(1, "NOT_BUILT", ms_to_dt(_TS))]
    assert cli.last_real_build(builds) is None


def test_last_real_build_ignores_an_in_progress_build_with_no_result():
    builds = [BuildInfo(5, None, ms_to_dt(_TS), building=True), BuildInfo(4, "SUCCESS", ms_to_dt(_TS))]
    assert cli.last_real_build(builds).number == 4


def test_consecutive_failing_real_builds_counts_past_seed_runs_and_stops_at_success():
    builds = [
        BuildInfo(10, "NOT_BUILT", ms_to_dt(_TS)),
        BuildInfo(9, "FAILURE", ms_to_dt(_TS)),
        BuildInfo(8, "NOT_BUILT", ms_to_dt(_TS)),
        BuildInfo(7, "ABORTED", ms_to_dt(_TS)),
        BuildInfo(6, "SUCCESS", ms_to_dt(_TS)),
        BuildInfo(5, "FAILURE", ms_to_dt(_TS)),
    ]
    assert cli.consecutive_failing_real_builds(builds) == 2


def test_child_results_parses_numbers_and_results_from_a_wrapper_console():
    text = (
        "Starting building: quant-tracking-report-recache #410\n"
        "Build quant-tracking-report-recache #410 completed: SUCCESS\n"
        "Build quant-tracking-report-recache #411 completed: FAILURE\n"
        "Build quant-tracking-report-recache #412 completed: NOT_BUILT\n"
    )
    assert cli.child_results(text) == {410: "SUCCESS", 411: "FAILURE", 412: "NOT_BUILT"}


# --------------------------------------------------------------------- facts JSON shape


def test_facts_emits_expected_fields_for_every_registry_job(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    blobs = {
        "quant-DailySimDataUpdateLP": {
            "lastBuild": {"number": 95, "result": "NOT_BUILT", "timestamp": _TS},
            "lastSuccessfulBuild": {"number": 93, "timestamp": _TS - 86_400_000},
            "lastFailedBuild": {"number": 90, "timestamp": _TS - 400_000_000},
        }
    }
    builds = {
        "quant-DailySimDataUpdateLP": [
            BuildInfo(95, "NOT_BUILT", ms_to_dt(_TS)),
            BuildInfo(93, "SUCCESS", ms_to_dt(_TS - 86_400_000)),
        ]
    }
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs, builds))
    rc = cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)])
    assert rc == 0

    payload = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))
    assert payload["job_count"] == 25
    assert len(payload["jobs"]) == 25

    lp = next(j for j in payload["jobs"] if j["job"] == "quant-DailySimDataUpdateLP")
    for field in (
        "job",
        "tier",
        "trigger_type",
        "cron",
        "tz",
        "upstream",
        "grace_hours",
        "max_silence_days",
        "success_markers",
        "console_informative",
        "nas_log_glob",
        "orchestrator",
        "child_job",
        "yesterday_verdict",
        "last_real_build",
        "latest_build",
        "last_success",
        "last_failure",
        "consecutive_failing_real_builds",
        "fetch_error",
    ):
        assert field in lp, f"the fact sheet dropped {field}"

    # The declared trigger is published verbatim - job names lie about cadence, so the agent
    # must never have to guess it.
    assert lp["cron"] == "20 14 * * *"
    assert lp["tz"] == "America/New_York"
    assert len(lp["success_markers"]) == 8

    # latest_build is a NOT_BUILT seed run and is FLAGGED as one, while last_real_build skips
    # back to the build that actually ran. Conflating the two was a bug in both directions.
    assert lp["latest_build"]["number"] == 95
    assert lp["latest_build"]["not_built_seed_run"] is True
    assert lp["latest_build"]["did_work"] is False
    assert lp["last_real_build"]["number"] == 93
    assert lp["last_real_build"]["result"] == "SUCCESS"
    assert lp["last_real_build"]["age"] and lp["last_real_build"]["age_hours"] > 0
    assert lp["last_success"]["number"] == 93
    assert lp["last_failure"]["number"] == 90
    assert lp["consecutive_failing_real_builds"] == 0
    assert lp["fetch_error"] is None


def test_facts_reports_friday_only_intex_cron_not_a_daily_one(tmp_path, monkeypatch):
    """Rule 3: the fact sheet is the only cadence source the agent gets, so it must carry
    the real cron for the job whose name says 'Daily' and whose trigger is Friday-only."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)]) == 0
    payload = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))
    intex = next(j for j in payload["jobs"] if j["job"] == "quant-DailySimDataUpdateIntex")
    assert intex["cron"] == "0 16 * * 5"


def test_a_failed_history_fetch_is_an_explicit_error_never_no_builds(tmp_path, monkeypatch):
    """An empty build list is indistinguishable from 'this job has only seed builds', which
    previously produced a false healthy verdict that then fabricated a recovery the next
    day. A failed fetch must be reported as unknown."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path)
    blobs = {"test-job": {"lastBuild": {"number": 7, "result": "FAILURE", "timestamp": _TS}}}
    fake = _FakeClient(blobs, builds_raise={"test-job": cli.client.JenkinsUnreachable("HTTP 500")})
    monkeypatch.setattr(cli.client, "from_env", lambda: fake)

    rc = cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)])
    assert rc == 0, "a broken fetch is data about an access gap, not a tool failure"

    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["fetch_error"] and "HTTP 500" in job["fetch_error"]
    assert job["last_real_build"] is None
    assert job["consecutive_failing_real_builds"] is None


def test_a_job_missing_from_the_controller_is_a_fetch_error(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path)
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs={}))
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["fetch_error"] is not None
    assert job["last_real_build"] is None


def test_fetch_error_is_stated_loudly_in_the_markdown_too(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path)
    fake = _FakeClient({"test-job": {}}, builds_raise={"test-job": cli.client.JenkinsUnreachable("HTTP 500")})
    monkeypatch.setattr(cli.client, "from_env", lambda: fake)
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    out = capsys.readouterr().out
    assert "FETCH ERROR" in out
    assert "UNKNOWN today, not healthy" in out


# --------------------------------------------------------------------- prior snapshot header


def test_no_prior_snapshot_says_comparisons_are_unavailable(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)]) == 0

    out = capsys.readouterr().out
    assert "Prior snapshot: NONE FOUND" in out
    assert "UNAVAILABLE" in out
    payload = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))
    assert payload["prior_snapshot"]["available"] is False
    assert all(j["yesterday_verdict"] is None for j in payload["jobs"])


def test_prior_snapshot_supplies_yesterday_verdict_per_job(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path)
    (tmp_path / "jenkins-status-20250101.json").write_text('{"test-job": "RED"}', encoding="utf-8")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0

    out = capsys.readouterr().out
    assert "NONE FOUND" not in out
    payload = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))
    assert payload["prior_snapshot"]["available"] is True
    assert payload["prior_snapshot"]["date"] == "20250101"
    assert payload["jobs"][0]["yesterday_verdict"] == "RED"


def test_an_unreadable_prior_snapshot_counts_as_no_prior_snapshot(tmp_path, monkeypatch, capsys):
    """`available` keys on having loaded verdicts, not on a file existing: a corrupt snapshot
    leaves the comparison just as unavailable, and claiming otherwise presents meaningless
    labels as real."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path)
    (tmp_path / "jenkins-status-20250101.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    assert "Prior snapshot: NONE FOUND" in capsys.readouterr().out


# --------------------------------------------------------------------- orchestrator children


def test_orchestrator_failure_lists_child_builds_from_the_wrapper_console(tmp_path, monkeypatch):
    """Rule 8: the wrapper reports one flat FAILURE while its children split pass/fail, so
    without these numbers the child failures are invisible."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path, name="wrapper", extra="    orchestrator: true\n    child_job: kid\n")
    blobs = {"wrapper": {"lastBuild": {"number": 293, "result": "FAILURE", "timestamp": _TS}}}
    builds = {"wrapper": [BuildInfo(293, "FAILURE", ms_to_dt(_TS))]}
    consoles = {
        ("wrapper", 293): (
            "Build kid #410 completed: SUCCESS\nBuild kid #411 completed: FAILURE\nBuild kid #412 completed: FAILURE\n"
        )
    }
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs, builds, consoles))
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0

    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["child_builds"] == [
        {"number": 410, "result": "SUCCESS"},
        {"number": 411, "result": "FAILURE"},
        {"number": 412, "result": "FAILURE"},
    ]


def test_orchestrator_children_are_read_from_the_last_real_build_not_a_seed_run(tmp_path, monkeypatch):
    """Reading the wrapper's NOT_BUILT seed build made every stage report 'skipped due to
    when conditional', so all deal types looked failed when one was."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path, name="wrapper", extra="    orchestrator: true\n    child_job: kid\n")
    blobs = {"wrapper": {"lastBuild": {"number": 300, "result": "NOT_BUILT", "timestamp": _TS}}}
    builds = {
        "wrapper": [
            BuildInfo(300, "NOT_BUILT", ms_to_dt(_TS)),
            BuildInfo(293, "FAILURE", ms_to_dt(_TS - 86_400_000)),
        ]
    }
    consoles = {("wrapper", 293): "Build kid #411 completed: FAILURE\n"}
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs, builds, consoles))
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["child_builds"] == [{"number": 411, "result": "FAILURE"}]


def test_a_successful_orchestrator_is_not_drilled_into(tmp_path, monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    reg = _one_job_registry(tmp_path, name="wrapper", extra="    orchestrator: true\n    child_job: kid\n")
    blobs = {"wrapper": {"lastBuild": {"number": 293, "result": "SUCCESS", "timestamp": _TS}}}
    builds = {"wrapper": [BuildInfo(293, "SUCCESS", ms_to_dt(_TS))]}
    # No console registered: a drill-down attempt would raise KeyError from the fake.
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs, builds, consoles={}))
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["child_builds"] is None


# --------------------------------------------------------------------- access gaps


def test_missing_token_prints_the_gap_loudly_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "")
    rc = cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "ACCESS GAP" in out
    assert "JENKINS_API_TOKEN" in out
    assert "Nothing below is a statement that these jobs are healthy" in out

    payload = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))
    assert payload["access_gap"] is not None
    assert all(j["fetch_error"] for j in payload["jobs"]), "no job may read as healthy when nothing was fetched"


def test_unreachable_controller_reports_the_real_cause_not_a_credential_guess(tmp_path, monkeypatch, capsys):
    """Hardcoded wording once claimed 'no credentials in the environment' during a controller
    outage - a wrong diagnosis stated with full confidence."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Down:
        def all_jobs(self):
            raise cli.client.JenkinsUnreachable("GET http://jenkins.example/api/json returned HTTP 503")

    monkeypatch.setattr(cli.client, "from_env", lambda: _Down())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)]) == 0
    out = capsys.readouterr().out
    assert "503" in out
    assert "missing/empty environment variable" not in out


def test_malformed_registry_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("jobs:\n  - tier: fix\n", encoding="utf-8")
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(bad)]) == 2


def test_facts_still_reaches_stdout_when_the_json_cannot_be_written(tmp_path, monkeypatch, capsys):
    """The outputs directory lives on a NAS share. An OSError must not cost the caller the
    fact sheet it consumes from stdout."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    (tmp_path / f"jenkins-facts-{_stamp()}.json").mkdir()  # a real filesystem failure
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    rc = cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "### Jenkins Job Monitor" in out
    assert "could not write" in out.lower()


# --------------------------------------------------------------------- console


def test_console_tails_the_requested_number_of_lines(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    text = "\n".join(f"line {i}" for i in range(100))
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(consoles={("kid", 7): text}))
    assert cli.main(["console", "kid", "7", "--tail", "5"]) == 0
    out = capsys.readouterr().out
    assert "line 99" in out
    assert "line 50" not in out
    assert "last 5 of 100 lines" in out


def test_console_tail_zero_prints_everything(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    text = "\n".join(f"line {i}" for i in range(1000))
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(consoles={("kid", 7): text}))
    assert cli.main(["console", "kid", "7", "--tail", "0"]) == 0
    out = capsys.readouterr().out
    assert "line 0" in out
    assert "line 999" in out


def test_console_accepts_a_child_job_that_is_not_in_the_registry(tmp_path, monkeypatch, capsys):
    """A wrapper's child is deliberately not a registry entry, and it is where the traceback
    lives. Restricting `console` to the registry would make rule 8 unfollowable."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    fake = _FakeClient(consoles={("quant-tracking-report-recache", 411): "Traceback...\nKeyError: 'Transition'"})
    monkeypatch.setattr(cli.client, "from_env", lambda: fake)
    assert cli.main(["console", "quant-tracking-report-recache", "411"]) == 0
    assert "KeyError" in capsys.readouterr().out


def test_console_failure_is_reported_as_a_gap_not_as_an_absence_of_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")

    class _Down:
        def console(self, job, number):
            raise cli.client.JenkinsUnreachable("HTTP 404")

    monkeypatch.setattr(cli.client, "from_env", lambda: _Down())
    rc = cli.main(["console", "kid", "7"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "could not read console" in out
    assert "not evidence the build had no errors" in out


def test_console_without_a_token_states_the_gap_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "")
    assert cli.main(["console", "kid", "7"]) == 0
    assert "ACCESS GAP" in capsys.readouterr().out


# --------------------------------------------------------------------- save-verdicts


def test_save_verdicts_writes_todays_snapshot_from_a_file(tmp_path, capsys):
    payload = tmp_path / "verdicts.json"
    payload.write_text(
        json.dumps({"quant-DailySimDataUpdateLP": "UNSTABLE", "quant-RMBSLoader": "GREEN"}),
        encoding="utf-8",
    )
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(REGISTRY)])
    assert rc == 0
    written = json.loads((tmp_path / f"jenkins-status-{_stamp()}.json").read_text(encoding="utf-8"))
    assert written == {"quant-DailySimDataUpdateLP": "UNSTABLE", "quant-RMBSLoader": "GREEN"}


def test_save_verdicts_reads_stdin_when_json_is_a_dash(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"quant-RMBSLoader": "RED"}'))
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", "-", "--registry", str(REGISTRY)])
    assert rc == 0
    written = json.loads((tmp_path / f"jenkins-status-{_stamp()}.json").read_text(encoding="utf-8"))
    assert written == {"quant-RMBSLoader": "RED"}


def test_save_verdicts_rejects_an_unknown_job_rather_than_writing_it(tmp_path, capsys):
    """A typo'd key would sit in the snapshot forever as a verdict for a job that does not
    exist, while the real job silently kept a null yesterday_verdict - the memory would look
    present and be absent."""
    payload = tmp_path / "verdicts.json"
    payload.write_text(json.dumps({"quant-RMBSLoader": "GREEN", "quant-Typo-Job": "RED"}), encoding="utf-8")
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(REGISTRY)])
    assert rc == 2
    assert "quant-Typo-Job" in capsys.readouterr().err
    assert not list(tmp_path.glob("jenkins-status-*.json")), "nothing may be written when a key is unknown"


def test_save_verdicts_rejects_malformed_json(tmp_path):
    payload = tmp_path / "verdicts.json"
    payload.write_text("{not json", encoding="utf-8")
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(REGISTRY)])
    assert rc == 2
    assert not list(tmp_path.glob("jenkins-status-*.json"))


def test_save_verdicts_rejects_a_top_level_list(tmp_path):
    payload = tmp_path / "verdicts.json"
    payload.write_text('["quant-RMBSLoader"]', encoding="utf-8")
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(REGISTRY)])
    assert rc == 2


def test_save_verdicts_round_trips_into_tomorrows_yesterday_verdict(tmp_path, monkeypatch):
    """The whole point of the snapshot: an agent has no memory between daily runs, and
    reasoning fresh each morning escalated the same job for three consecutive days after it
    had already recovered."""
    reg = _one_job_registry(tmp_path)
    payload = tmp_path / "verdicts.json"
    payload.write_text('{"test-job": "RED"}', encoding="utf-8")
    assert cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(reg)]) == 0

    # Rename to yesterday so `facts` sees it as strictly older than today's stamp.
    written = tmp_path / f"jenkins-status-{_stamp()}.json"
    written.rename(tmp_path / "jenkins-status-20250101.json")

    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(reg)]) == 0
    job = json.loads((tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8"))["jobs"][0]
    assert job["yesterday_verdict"] == "RED"


# --------------------------------------------------------------------- encoding


def test_facts_survives_a_strict_cp1252_stdout(tmp_path, monkeypatch):
    """sys.stdout.encoding is cp1252 in the production environment. The CLI is the process
    boundary and must not be one edit away from a crash that produces no fact sheet at all."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient())
    # Escaped, not literal: this repo forbids non-ASCII bytes in Python sources.
    monkeypatch.setattr(cli, "_render_facts", lambda payload: "status caf\u00e9 done \u2713")

    buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252", errors="strict"))
    rc = cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)])
    sys.stdout.flush()

    assert rc == 0
    assert "caf" in buffer.getvalue().decode("utf-8")


def test_the_real_fact_sheet_is_cp1252_encodable(tmp_path, monkeypatch):
    """Belt to the reconfigure() brace: the rendered sheet itself must contain nothing a
    cp1252 console cannot represent, so a lost `reconfigure` is not a lost report."""
    monkeypatch.setenv("JENKINS_USER", "u")
    monkeypatch.setenv("JENKINS_API_TOKEN", "t")
    blobs = {"quant-RMBSLoader": {"lastBuild": {"number": 5, "result": "FAILURE", "timestamp": _TS}}}
    builds = {"quant-RMBSLoader": [BuildInfo(5, "FAILURE", ms_to_dt(_TS))]}
    monkeypatch.setattr(cli.client, "from_env", lambda: _FakeClient(blobs, builds))
    assert cli.main(["facts", "--outputs", str(tmp_path), "--registry", str(REGISTRY)]) == 0
    text = (tmp_path / f"jenkins-facts-{_stamp()}.json").read_text(encoding="utf-8")
    text.encode("cp1252")  # raises UnicodeEncodeError if any non-representable char slipped in


def test_files_are_written_as_utf8(tmp_path, monkeypatch):
    payload = tmp_path / "verdicts.json"
    payload.write_text('{"quant-RMBSLoader": "GREEN"}', encoding="utf-8")
    assert (
        cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(payload), "--registry", str(REGISTRY)])
        == 0
    )
    raw = (tmp_path / f"jenkins-status-{_stamp()}.json").read_bytes()
    assert json.loads(raw.decode("utf-8")) == {"quant-RMBSLoader": "GREEN"}


def test_save_verdicts_reports_a_missing_verdict_file_instead_of_a_traceback(tmp_path, capsys):
    """A traceback out of the unattended daily path is indistinguishable from the tool being
    broken, and the caller must be told the memory was NOT written."""
    missing = tmp_path / "nope.json"
    rc = cli.main(["save-verdicts", "--outputs", str(tmp_path), "--json", str(missing), "--registry", str(REGISTRY)])
    assert rc == 2
    assert "could not read the verdict file" in capsys.readouterr().err
    assert not list(tmp_path.glob("jenkins-status-*.json"))
