# tests/test_jenkins_classify.py
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import classify  # noqa: E402
from jenkins_monitor.models import BuildInfo, JobSpec, State  # noqa: E402

UTC = dt.UTC
NOW = dt.datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def _b(num, result, hours_ago, building=False):
    return BuildInfo(num, result, NOW - dt.timedelta(hours=hours_ago), building)


CRON_SPEC = JobSpec(
    job="j",
    tier="fix",
    family="f",
    trigger_type="cron",
    cron="20 15 * * *",
    tz="America/New_York",
    grace_hours=6,
)
MANUAL_SPEC = JobSpec(job="m", tier="fix", family="f", trigger_type="manual")


def test_last_real_build_skips_not_built_seed_runs():
    builds = [_b(45, "NOT_BUILT", 4), _b(44, "NOT_BUILT", 10), _b(43, "SUCCESS", 100)]
    got = classify.last_real_build(builds)
    assert got.number == 43


def test_last_real_build_none_when_only_seed_runs():
    assert classify.last_real_build([_b(2, "NOT_BUILT", 1), _b(1, "NOT_BUILT", 5)]) is None


def test_consecutive_failures_counts_leading_non_success_real_builds():
    builds = [_b(5, "FAILURE", 1), _b(4, "NOT_BUILT", 2), _b(3, "FAILURE", 3), _b(2, "SUCCESS", 4)]
    assert classify.consecutive_failures(builds) == 2


def test_consecutive_failures_zero_when_latest_real_is_success():
    assert classify.consecutive_failures([_b(2, "SUCCESS", 1), _b(1, "FAILURE", 2)]) == 0


def test_red_when_last_failed_number_exceeds_last_success():
    blob = {
        "lastBuild": {"number": 293, "result": "FAILURE", "timestamp": 1},
        "lastSuccessfulBuild": {"number": 276, "timestamp": 1},
        "lastFailedBuild": {"number": 293, "timestamp": 1},
    }
    st = classify.classify_job(MANUAL_SPEC, blob, [_b(293, "FAILURE", 25)], NOW)
    assert st.state == State.RED


def test_seed_only_when_latest_is_not_built_but_history_is_green():
    blob = {"lastBuild": {"number": 45, "result": "NOT_BUILT", "timestamp": 1}}
    builds = [_b(45, "NOT_BUILT", 4), _b(44, "SUCCESS", 30)]
    st = classify.classify_job(MANUAL_SPEC, blob, builds, NOW)
    assert st.state == State.SEED_ONLY
    assert st.last_real.number == 44


def test_never_did_work_when_all_builds_are_seed_runs():
    blob = {"lastBuild": {"number": 37, "result": "NOT_BUILT", "timestamp": 1}}
    st = classify.classify_job(MANUAL_SPEC, blob, [_b(37, "NOT_BUILT", 100)], NOW)
    assert st.state == State.NEVER_DID_WORK


def test_building_is_deferred_not_judged():
    blob = {"lastBuild": {"number": 677, "result": None, "timestamp": 1, "building": True}}
    st = classify.classify_job(MANUAL_SPEC, blob, [_b(677, None, 0, building=True)], NOW)
    assert st.state == State.BUILDING


def test_unstable_is_failure_only_when_spec_says_so():
    blob = {"lastBuild": {"number": 92, "result": "UNSTABLE", "timestamp": 1}}
    builds = [_b(92, "UNSTABLE", 2)]
    lenient = JobSpec(job="j", tier="fix", family="f", trigger_type="manual")
    strict = JobSpec(job="j", tier="fix", family="f", trigger_type="manual", unstable_is_failure=True)
    assert classify.classify_job(lenient, blob, builds, NOW).state == State.GREEN
    assert classify.classify_job(strict, blob, builds, NOW).state == State.UNSTABLE


def test_stale_detected_when_last_real_build_is_old():
    blob = {
        "lastBuild": {"number": 10, "result": "SUCCESS", "timestamp": 1},
        "lastSuccessfulBuild": {"number": 10, "timestamp": 1},
    }
    st = classify.classify_job(CRON_SPEC, blob, [_b(10, "SUCCESS", 24 * 4)], NOW)
    assert st.state == State.STALE


def test_seed_run_does_not_mask_staleness():
    """Regression: a NOT_BUILT seed run 4h ago must not make a 27-day-old job look fresh."""
    seed_ts_ms = int((NOW - dt.timedelta(hours=4)).timestamp() * 1000)
    blob = {"lastBuild": {"number": 45, "result": "NOT_BUILT", "timestamp": seed_ts_ms}}
    builds = [_b(45, "NOT_BUILT", 4), _b(44, "SUCCESS", 24 * 27)]
    st = classify.classify_job(CRON_SPEC, blob, builds, NOW)
    assert st.state == State.STALE


def test_aborted_last_real_build_is_red_not_green():
    """Regression: ABORTED (e.g. timeout(1440 MINUTES)) must not fall through to GREEN.

    Jenkins does not populate lastFailedBuild for an aborted build, so without an explicit
    check the job would slip past the RED and UNSTABLE branches and report healthy.
    """
    blob = {"lastBuild": {"number": 50, "result": "ABORTED", "timestamp": 1}}
    builds = [_b(50, "ABORTED", 1)]
    st = classify.classify_job(MANUAL_SPEC, blob, builds, NOW)
    assert st.state == State.RED
    assert st.state != State.GREEN


def test_aborted_does_not_shadow_newer_genuine_failure():
    """The newest real build is ABORTED (#61), but Jenkins' own lastFailedBuild (#60) is
    still newer than lastSuccessfulBuild (#58) - a genuine failure. The pre-existing
    lastFailedBuild-vs-lastSuccessfulBuild RED check must fire first and report with the
    FAILURE-based detail, not get rerouted to the ABORTED wording."""
    blob = {
        "lastBuild": {"number": 61, "result": "ABORTED", "timestamp": 1},
        "lastSuccessfulBuild": {"number": 58, "timestamp": 1},
        "lastFailedBuild": {"number": 60, "timestamp": 1},
    }
    builds = [_b(61, "ABORTED", 1), _b(60, "FAILURE", 2), _b(59, "SUCCESS", 3)]
    st = classify.classify_job(MANUAL_SPEC, blob, builds, NOW)
    assert st.state == State.RED
    assert "FAILURE" in st.detail
    assert "#60" in st.detail
    assert "ABORTED" not in st.detail


def test_green_when_recent_success():
    blob = {
        "lastBuild": {"number": 95, "result": "SUCCESS", "timestamp": 1},
        "lastSuccessfulBuild": {"number": 95, "timestamp": 1},
    }
    st = classify.classify_job(CRON_SPEC, blob, [_b(95, "SUCCESS", 3)], NOW)
    assert st.state == State.GREEN
