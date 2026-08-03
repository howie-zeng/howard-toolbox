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


class _FlakyClient(_FakeClient):
    """Like _FakeClient, but specific (job, number) lookups raise instead of returning.

    Models a genuine transport/programming failure on a single build so tests can
    drive the diagnoser's graceful-degradation paths without a real network call.
    """

    def __init__(self, consoles=None, details=None, raise_console_for=(), raise_detail_for=()):
        super().__init__(consoles, details)
        self._raise_console_for = set(raise_console_for)
        self._raise_detail_for = set(raise_detail_for)

    def console(self, job, number):
        if (job, number) in self._raise_console_for:
            raise RuntimeError(f"HTTP 500 fetching console for {job} #{number}")
        return super().console(job, number)

    def build_detail(self, job, number):
        if (job, number) in self._raise_detail_for:
            raise RuntimeError(f"HTTP 500 fetching build detail for {job} #{number}")
        return super().build_detail(job, number)


def test_extract_python_error_finds_last_keyerror():
    text = (FIXTURES / "console_keyerror.txt").read_text(encoding="utf-8")
    err_class, block = diagnose.extract_python_error(text)
    assert err_class == "KeyError"
    assert "Transition" in block
    assert "crt_deal.py" in block


def test_extract_python_error_returns_empty_when_no_traceback():
    assert diagnose.extract_python_error("all fine\nFinished: SUCCESS") == ("", "")


def test_extract_python_error_recognizes_bare_keyboard_interrupt():
    """A timeout-killed or manually aborted process commonly ends its traceback this way."""
    text = (
        "Traceback (most recent call last):\n"
        '  File "S:\\QR\\GitHub\\job.py", line 42, in <module>\n'
        "    long_running_call()\n"
        "KeyboardInterrupt\n"
    )
    err_class, block = diagnose.extract_python_error(text)
    assert err_class == "KeyboardInterrupt"
    assert block.splitlines()[-1] == "KeyboardInterrupt"


def test_extract_python_error_bounds_unterminated_traceback():
    """No line ever matches _ERROR_LINE - block must not grow to end-of-file."""
    body = "\n".join(f"    print('runaway line {i}')" for i in range(500))
    text = "Traceback (most recent call last):\n" + body
    err_class, block = diagnose.extract_python_error(text)
    assert err_class == ""
    block_lines = block.splitlines()
    assert len(block_lines) <= diagnose._MAX_TRACEBACK_LINES
    assert len(block_lines) < len(text.splitlines())


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


def test_diagnose_orchestrator_build_detail_failure_leaves_a_trace_and_uses_fallback_label():
    """A build_detail failure for one child must not lose the other children's deal
    types, must fall back to '#<num>' for the failing one, and must surface some
    indication that the fetch failed rather than vanishing silently."""
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
    client = _FlakyClient(
        consoles={
            (spec.job, 293): (FIXTURES / "console_wrapper_293.txt").read_text(encoding="utf-8"),
            ("quant-tracking-report-recache", 75): child_console,
            ("quant-tracking-report-recache", 76): child_console,
            ("quant-tracking-report-recache", 78): child_console,
        },
        details={
            ("quant-tracking-report-recache", 76): ("FAILURE", {"deal_type": "NONQM_PSEUDO"}),
            ("quant-tracking-report-recache", 78): ("FAILURE", {"deal_type": "HELOC_PSEUDO"}),
        },
        raise_detail_for={("quant-tracking-report-recache", 75)},
    )
    d = diagnose.diagnose_job(client, spec, status)
    assert d.error_class == "KeyError"
    assert d.child_builds == (75, 76, 78)
    assert set(d.affected) == {"#75", "NONQM_PSEUDO", "HELOC_PSEUDO"}
    assert "could not read build detail for #75" in d.error_text


def test_diagnose_job_console_failure_degrades_to_low_confidence():
    """Top-level client.console raising must return a low-confidence diagnosis, not raise."""
    spec = JobSpec(job="quant-x", tier="fix", family="f", trigger_type="manual")
    status = JobStatus(job=spec.job, state=State.RED, latest=BuildInfo(10, "FAILURE", None), detail="d")
    client = _FlakyClient(raise_console_for={(spec.job, 10)})
    d = diagnose.diagnose_job(client, spec, status)
    assert d.confidence == "low"
    assert d.error_class == ""
    assert "#10" in d.error_text


def test_diagnose_orchestrator_no_failing_child_found_is_honest_low_confidence():
    """Wrapper reported failure but its console names no failing child build - report
    that honestly at low confidence instead of fabricating a cause."""
    spec = JobSpec(
        job="quant-tracking-report-recache-workflow",
        tier="fix",
        family="resitracking",
        trigger_type="manual",
        orchestrator=True,
        child_job="quant-tracking-report-recache",
    )
    status = JobStatus(job=spec.job, state=State.RED, latest=BuildInfo(300, "FAILURE", None), detail="d")
    client = _FakeClient(consoles={(spec.job, 300): "Started by timer\nFinished: FAILURE\n"})
    d = diagnose.diagnose_job(client, spec, status)
    assert d.confidence == "low"
    assert d.error_class == ""
    assert d.child_builds == ()
    assert "no failing child build was found" in d.error_text


# --- Final review, CRITICAL 2: diagnose_job used `status.latest` - the one place in the
# --- package that regressed to Jenkins' lastBuild instead of the last_real_build rule the
# --- whole design rests on. classify_job returns RED/UNSTABLE while `latest` can still be
# --- a no-work NOT_BUILT seed build, because the RED/ABORTED/UNSTABLE checks all precede
# --- the SEED_ONLY check. Reading the seed build's console (every stage "skipped due to
# --- when conditional") made all eight success markers look absent, so the report claimed
# --- all eight deal types failed when one did; for an orchestrator it reported "no failing
# --- child build was found", which reads as "nothing to chase in the children".


def test_diagnose_reads_last_real_build_not_a_newer_seed_build():
    """#92 went UNSTABLE; a JenkinsJobs push then created #93 NOT_BUILT. The diagnosis must
    come from #92."""
    spec = JobSpec(
        job="quant-DailySimDataUpdateLP",
        tier="fix",
        family="simdata",
        trigger_type="cron",
        cron="20 14 * * *",
        tz="America/New_York",
        unstable_is_failure=True,
        success_markers=("Done NQM", "Done Jumbo", "Done HELOC"),
    )
    status = JobStatus(
        job=spec.job,
        state=State.UNSTABLE,
        latest=BuildInfo(93, "NOT_BUILT", None),
        last_real=BuildInfo(92, "UNSTABLE", None),
        detail="d",
    )
    seed_console = "Stage 'NQM' skipped due to when conditional\nFinished: NOT_BUILT\n"
    real_console = "Done NQM\nDone Jumbo\nERROR: HELOC failed\nFinished: UNSTABLE\n"
    client = _FakeClient(consoles={(spec.job, 93): seed_console, (spec.job, 92): real_console})

    d = diagnose.diagnose_job(client, spec, status)

    assert d.build_number == 92, "the diagnosed build must be the last build that did work"
    assert d.affected == ("Done HELOC",), (
        "reading the seed build's console instead would report every marker missing - "
        "claiming all deal types failed when only one did"
    )


def test_diagnose_orchestrator_reads_last_real_build_not_a_newer_seed_build():
    """Same bug, orchestrator shape: the seed build's console names no child builds, so the
    diagnoser reported 'no failing child build was found' for a wrapper that has three."""
    spec = JobSpec(
        job="quant-tracking-report-recache-workflow",
        tier="fix",
        family="resitracking",
        trigger_type="manual",
        orchestrator=True,
        child_job="quant-tracking-report-recache",
    )
    status = JobStatus(
        job=spec.job,
        state=State.RED,
        latest=BuildInfo(294, "NOT_BUILT", None),
        last_real=BuildInfo(293, "FAILURE", None),
        detail="d",
    )
    child_console = (FIXTURES / "console_keyerror.txt").read_text(encoding="utf-8")
    client = _FakeClient(
        consoles={
            (spec.job, 294): "Stage 'recache' skipped due to when conditional\nFinished: NOT_BUILT\n",
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

    assert d.build_number == 293
    assert d.child_builds == (75, 76, 78)
    assert "no failing child build was found" not in d.error_text


def test_diagnose_falls_back_to_latest_when_no_real_build_is_known():
    """last_real is None (e.g. an UNREACHABLE-ish status built without a build list) - the
    diagnoser still tries `latest` rather than giving up."""
    spec = JobSpec(job="quant-x", tier="fix", family="f", trigger_type="manual")
    status = JobStatus(job=spec.job, state=State.RED, latest=BuildInfo(11, "FAILURE", None), detail="d")
    client = _FakeClient(consoles={(spec.job, 11): "Traceback (most recent call last):\nKeyError: 'x'\n"})
    d = diagnose.diagnose_job(client, spec, status)
    assert d.build_number == 11
    assert d.error_class == "KeyError"


def test_diagnose_with_no_build_at_all_reports_it_and_carries_no_build_number():
    spec = JobSpec(job="quant-x", tier="fix", family="f", trigger_type="manual")
    status = JobStatus(job=spec.job, state=State.RED, detail="d")
    d = diagnose.diagnose_job(_FakeClient(), spec, status)
    assert d.build_number is None
    assert "no build to diagnose" in d.error_text
