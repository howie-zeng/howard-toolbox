# tests/test_jenkins_cadence.py
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import cadence  # noqa: E402
from jenkins_monitor.models import JobSpec  # noqa: E402

NY = ZoneInfo("America/New_York")
UTC = dt.UTC


def _ny(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=NY)


def test_daily_cron_previous_fire_is_today_when_already_passed():
    now = _ny(2026, 8, 3, 18, 0)
    got = cadence.previous_fire_time("20 15 * * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 3, 15, 20)


def test_daily_cron_previous_fire_is_yesterday_when_not_yet_due():
    now = _ny(2026, 8, 3, 9, 0)
    got = cadence.previous_fire_time("20 15 * * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 2, 15, 20)


def test_friday_only_cron_from_a_monday_returns_last_friday():
    """quant-DailySimDataUpdateIntex: '0 16 * * 5' - name says Daily, cron says Friday."""
    now = _ny(2026, 8, 3, 8, 0)  # Monday
    got = cadence.previous_fire_time("0 16 * * 5", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 7, 31, 16, 0)  # Friday


def test_sunday_cron_dow_zero():
    now = _ny(2026, 8, 3, 8, 0)  # Monday
    got = cadence.previous_fire_time("0 9 * * 0", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 2, 9, 0)  # Sunday


def test_dow_seven_also_means_sunday():
    now = _ny(2026, 8, 3, 8, 0)
    assert cadence.previous_fire_time("0 9 * * 7", "America/New_York", now) == (
        cadence.previous_fire_time("0 9 * * 0", "America/New_York", now)
    )


def test_hashed_minute_expands_to_latest_minute_in_hour():
    """'H 2 * * *' fires at some minute in hour 2; use the latest to avoid
    calling the job stale before its window closes."""
    now = _ny(2026, 8, 3, 8, 0)
    got = cadence.previous_fire_time("H 2 * * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 3, 2, 59)


def test_weekday_range_skips_weekend():
    now = _ny(2026, 8, 3, 8, 0)  # Monday morning, before 23:00
    got = cadence.previous_fire_time("H 23 * * 1-5", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 7, 31, 23, 59)  # Friday


def test_day_of_month_range():
    now = _ny(2026, 8, 3, 8, 0)
    got = cadence.previous_fire_time("H 23 20-31 * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 7, 31, 23, 59)


def test_comma_list_dow():
    now = _ny(2026, 8, 3, 8, 0)  # Monday
    got = cadence.previous_fire_time("20 15 * * 1,2,3,4,5,6,7", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 2, 15, 20)


def test_unsupported_syntax_raises():
    with pytest.raises(cadence.CadenceError):
        cadence.previous_fire_time("*/5 * * * * *", "America/New_York", _ny(2026, 8, 3, 8, 0))
    with pytest.raises(cadence.CadenceError):
        cadence.previous_fire_time("0 9 * * MON", "America/New_York", _ny(2026, 8, 3, 8, 0))


def test_dst_spring_forward_does_not_crash():
    now = _ny(2026, 3, 9, 12, 0)
    got = cadence.previous_fire_time("30 2 * * *", "America/New_York", now)
    assert got.tzinfo is not None


# ---- staleness ----------------------------------------------------------------

_CRON_SPEC = JobSpec(
    job="j",
    tier="fix",
    family="f",
    trigger_type="cron",
    cron="20 15 * * *",
    tz="America/New_York",
    grace_hours=6,
)


def test_cron_job_is_stale_when_last_real_predates_expected_fire_plus_grace():
    now = _ny(2026, 8, 3, 8, 0)
    last = _ny(2026, 8, 1, 15, 20)  # two days ago
    stale, why = cadence.staleness(_CRON_SPEC, last, now)
    assert stale is True
    assert "expected" in why.lower()


def test_cron_job_is_not_stale_within_grace():
    now = _ny(2026, 8, 3, 18, 0)
    last = _ny(2026, 8, 3, 15, 25)
    stale, _ = cadence.staleness(_CRON_SPEC, last, now)
    assert stale is False


def test_pollscm_job_is_never_stale():
    spec = JobSpec(job="d", tier="notify", family="deploy", trigger_type="pollscm")
    stale, why = cadence.staleness(spec, _ny(2020, 1, 1, 0, 0), _ny(2026, 8, 3, 8, 0))
    assert stale is False
    assert "scm" in why.lower()


def test_manual_job_is_never_stale():
    spec = JobSpec(job="m", tier="fix", family="f", trigger_type="manual")
    stale, _ = cadence.staleness(spec, None, _ny(2026, 8, 3, 8, 0))
    assert stale is False


def test_upstream_job_stale_only_if_parent_ran_more_recently():
    spec = JobSpec(job="c", tier="fix", family="f", trigger_type="upstream", upstream="p")
    now = _ny(2026, 8, 3, 8, 0)
    stale, _ = cadence.staleness(spec, _ny(2026, 8, 1, 0, 0), now, upstream_ts=_ny(2026, 8, 2, 0, 0))
    assert stale is True
    stale2, _ = cadence.staleness(spec, _ny(2026, 8, 2, 0, 0), now, upstream_ts=_ny(2026, 8, 1, 0, 0))
    assert stale2 is False


def test_cron_job_with_no_real_build_ever_is_stale():
    stale, why = cadence.staleness(_CRON_SPEC, None, _ny(2026, 8, 3, 8, 0))
    assert stale is True
    assert "never" in why.lower()
