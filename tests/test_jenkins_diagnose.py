# tests/test_jenkins_diagnose.py
from __future__ import annotations

import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import diagnose  # noqa: E402
from jenkins_monitor.models import BuildInfo, JobSpec, JobStatus, State  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "jenkins"


class _FakeClient:
    def __init__(self, consoles=None, details=None):
        self._consoles = consoles or {}
        self._details = details or {}

    def console(self, job, number):
        return self._consoles[(job, number)]

    def build_detail(self, job, number):
        return self._details[(job, number)]


def test_extract_python_error_finds_last_keyerror():
    text = (FIXTURES / "console_keyerror.txt").read_text(encoding="utf-8")
    err_class, block = diagnose.extract_python_error(text)
    assert err_class == "KeyError"
    assert "Transition" in block
    assert "crt_deal.py" in block


def test_extract_python_error_returns_empty_when_no_traceback():
    assert diagnose.extract_python_error("all fine\nFinished: SUCCESS") == ("", "")


def test_missing_markers_reports_absent_only():
    text = "Done NQM\nDone Jumbo\n"
    got = diagnose.missing_markers(text, ("Done NQM", "Done Jumbo", "Done HELOC"))
    assert got == ("Done HELOC",)


def test_child_results_parsed_from_wrapper_console():
    text = (FIXTURES / "console_wrapper_293.txt").read_text(encoding="utf-8")
    got = diagnose.child_results(text)
    assert got[75] == "FAILURE"
    assert got[77] == "SUCCESS"
    assert sorted(k for k, v in got.items() if v == "FAILURE") == [75, 76, 78]


def test_diagnose_orchestrator_drills_into_failing_children_and_names_deal_types():
    spec = JobSpec(
        job="quant-tracking-report-recache-workflow",
        tier="fix",
        family="resitracking",
        trigger_type="manual",
        orchestrator=True,
        child_job="quant-tracking-report-recache",
    )
    status = JobStatus(job=spec.job, state=State.RED, latest=BuildInfo(293, "FAILURE", None), detail="d")
    child_console = (FIXTURES / "console_keyerror.txt").read_text(encoding="utf-8")
    client = _FakeClient(
        consoles={
            (spec.job, 293): (FIXTURES / "console_wrapper_293.txt").read_text(encoding="utf-8"),
            ("quant-tracking-report-recache", 75): child_console,
            ("quant-tracking-report-recache", 76): child_console,
            ("quant-tracking-report-recache", 78): child_console,
        },
        details={
            ("quant-tracking-report-recache", 75): ("FAILURE", {"deal_type": "JUMBO2_0_PSEUDO"}),
            ("quant-tracking-report-recache", 76): ("FAILURE", {"deal_type": "NONQM_PSEUDO"}),
            ("quant-tracking-report-recache", 78): ("FAILURE", {"deal_type": "HELOC_PSEUDO"}),
        },
    )
    d = diagnose.diagnose_job(client, spec, status)
    assert d.error_class == "KeyError"
    assert d.child_builds == (75, 76, 78)
    assert set(d.affected) == {"JUMBO2_0_PSEUDO", "NONQM_PSEUDO", "HELOC_PSEUDO"}
    assert "crt_deal.py" in d.source_hint


def test_diagnose_unstable_job_reports_missing_markers_as_affected():
    spec = JobSpec(
        job="quant-DailySimDataUpdateLP",
        tier="fix",
        family="simdata",
        trigger_type="manual",
        unstable_is_failure=True,
        success_markers=("Done NQM", "Done Jumbo", "Done HELOC"),
    )
    status = JobStatus(job=spec.job, state=State.UNSTABLE, latest=BuildInfo(92, "UNSTABLE", None), detail="d")
    client = _FakeClient(consoles={(spec.job, 92): (FIXTURES / "console_lp_unstable.txt").read_text(encoding="utf-8")})
    d = diagnose.diagnose_job(client, spec, status)
    assert "Done HELOC" in d.affected


def test_diagnose_flags_low_confidence_when_console_uninformative():
    spec = JobSpec(
        job="quant-DailySimDataUpdate",
        tier="fix",
        family="simdata",
        trigger_type="manual",
        console_informative=False,
        nas_log_glob=r"\\nas\logs\crt_update\wh_crt_update_*.log",
    )
    status = JobStatus(job=spec.job, state=State.RED, latest=BuildInfo(96, "FAILURE", None), detail="d")
    client = _FakeClient(consoles={(spec.job, 96): "ERROR: script returned exit code 1\n"})
    d = diagnose.diagnose_job(client, spec, status)
    assert d.confidence == "low"
    assert "wh_crt_update" in d.source_hint
