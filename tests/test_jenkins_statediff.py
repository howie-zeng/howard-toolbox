# tests/test_jenkins_statediff.py
from __future__ import annotations

import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import statediff  # noqa: E402
from jenkins_monitor.models import JobStatus, State  # noqa: E402


def _st(job, state):
    return JobStatus(job=job, state=state, detail="d")


def test_new_failure_labelled_new():
    findings = statediff.label([_st("a", State.RED)], {"a": State.GREEN})
    assert [f.transition for f in findings] == ["NEW"]


def test_repeat_failure_labelled_ongoing():
    findings = statediff.label([_st("a", State.RED)], {"a": State.RED})
    assert findings[0].transition == "ONGOING"


def test_recovery_labelled_recovered():
    findings = statediff.label([_st("a", State.GREEN)], {"a": State.RED})
    assert findings[0].transition == "RECOVERED"


def test_green_staying_green_is_omitted():
    assert statediff.label([_st("a", State.GREEN)], {"a": State.GREEN}) == []


def test_unknown_previous_state_counts_as_new():
    findings = statediff.label([_st("a", State.RED)], {})
    assert findings[0].transition == "NEW"


def test_state_change_between_two_failing_states_is_new():
    findings = statediff.label([_st("a", State.RED)], {"a": State.STALE})
    assert findings[0].transition == "NEW"


def test_snapshot_round_trip(tmp_path):
    p = tmp_path / "jenkins-status-20260803.json"
    statediff.save_snapshot([_st("a", State.RED), _st("b", State.GREEN)], p)
    assert statediff.load_snapshot(p) == {"a": State.RED, "b": State.GREEN}


def test_load_snapshot_missing_returns_empty(tmp_path):
    assert statediff.load_snapshot(tmp_path / "nope.json") == {}


def test_load_snapshot_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert statediff.load_snapshot(p) == {}


def test_latest_snapshot_path_picks_newest_before_today(tmp_path):
    for stamp in ("20260731", "20260801", "20260803"):
        (tmp_path / f"jenkins-status-{stamp}.json").write_text("{}", encoding="utf-8")
    got = statediff.latest_snapshot_path(tmp_path, before="20260803")
    assert got.name == "jenkins-status-20260801.json"


def test_latest_snapshot_path_none_when_no_earlier_file(tmp_path):
    (tmp_path / "jenkins-status-20260803.json").write_text("{}", encoding="utf-8")
    assert statediff.latest_snapshot_path(tmp_path, before="20260803") is None
