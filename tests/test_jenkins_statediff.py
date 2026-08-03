# tests/test_jenkins_statediff.py
"""Cross-day memory. The only thing this module does is persist the agent's verdicts.

Transition labelling used to live here and is now the agent's judgment
(JENKINS_MONITOR_PROMPT.md rule 6). What remains must round-trip exactly, write atomically,
and never hand tomorrow a half-written or bogus snapshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import statediff  # noqa: E402


def test_snapshot_round_trip(tmp_path):
    p = tmp_path / "jenkins-status-20260803.json"
    statediff.save_snapshot({"a": "RED", "b": "GREEN"}, p)
    assert statediff.load_snapshot(p) == {"a": "RED", "b": "GREEN"}


def test_save_snapshot_creates_missing_parent_directories(tmp_path):
    p = tmp_path / "nested" / "deeper" / "jenkins-status-20260803.json"
    statediff.save_snapshot({"a": "RED"}, p)
    assert statediff.load_snapshot(p) == {"a": "RED"}


def test_save_snapshot_leaves_no_temp_file_behind(tmp_path):
    """The write goes via a .tmp and an atomic replace: a half-written snapshot would
    corrupt tomorrow's comparison, and a leftover .tmp would accumulate on the NAS share."""
    p = tmp_path / "jenkins-status-20260803.json"
    statediff.save_snapshot({"a": "RED"}, p)
    assert list(tmp_path.glob("*.tmp")) == []
    assert p.exists()


def test_save_snapshot_overwrites_an_existing_snapshot_atomically(tmp_path):
    p = tmp_path / "jenkins-status-20260803.json"
    statediff.save_snapshot({"a": "RED", "b": "RED"}, p)
    statediff.save_snapshot({"a": "GREEN"}, p)
    # A full replace, not a merge: today's verdicts are today's, and a stale key silently
    # surviving would be a verdict nobody made.
    assert statediff.load_snapshot(p) == {"a": "GREEN"}


def test_snapshot_is_utf8_and_sorted_for_readable_diffs(tmp_path):
    p = tmp_path / "jenkins-status-20260803.json"
    statediff.save_snapshot({"z-job": "RED", "a-job": "GREEN"}, p)
    text = p.read_bytes().decode("utf-8")
    assert text.index('"a-job"') < text.index('"z-job"')
    assert json.loads(text) == {"z-job": "RED", "a-job": "GREEN"}


def test_load_snapshot_missing_returns_empty(tmp_path):
    assert statediff.load_snapshot(tmp_path / "nope.json") == {}


def test_load_snapshot_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert statediff.load_snapshot(p) == {}


def test_load_snapshot_top_level_list_returns_empty(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert statediff.load_snapshot(p) == {}


def test_load_snapshot_top_level_string_returns_empty(tmp_path):
    p = tmp_path / "string.json"
    p.write_text('"just a string"', encoding="utf-8")
    assert statediff.load_snapshot(p) == {}


def test_latest_snapshot_path_picks_newest_before_today(tmp_path):
    for stamp in ("20260731", "20260801", "20260803"):
        (tmp_path / f"jenkins-status-{stamp}.json").write_text("{}", encoding="utf-8")
    got = statediff.latest_snapshot_path(tmp_path, before="20260803")
    assert got.name == "jenkins-status-20260801.json"


def test_latest_snapshot_path_none_when_no_earlier_file(tmp_path):
    (tmp_path / "jenkins-status-20260803.json").write_text("{}", encoding="utf-8")
    assert statediff.latest_snapshot_path(tmp_path, before="20260803") is None


def test_latest_snapshot_path_ignores_nine_digit_datestamp(tmp_path):
    # A 9-digit run must not be matched as a shifted 8-digit datestamp.
    (tmp_path / "jenkins-status-202608031.json").write_text("{}", encoding="utf-8")
    assert statediff.latest_snapshot_path(tmp_path, before="99999999") is None


def test_latest_snapshot_path_ignores_unrelated_json_files(tmp_path):
    (tmp_path / "jenkins-facts-20260801.json").write_text("{}", encoding="utf-8")
    assert statediff.latest_snapshot_path(tmp_path, before="20260803") is None
