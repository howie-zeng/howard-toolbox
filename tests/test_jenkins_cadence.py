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


def test_hashed_minute_uses_window_start_not_latest_minute_in_hour():
    """'H 2 * * *' means Jenkins hashed ONE stable minute somewhere in hour 2 - we
    don't know which, so the safe comparison instant is the window's START (02:00),
    not the latest possible minute (02:59).

    Using the end (the old behaviour) judged a job that ran early in its own hashed
    window - e.g. at 02:19 - as late, because 02:19 < 02:59. The concern that
    motivated picking the end ("don't call a job stale before its window closes") is
    already handled by the separate `now > expected + grace_hours` guard in
    staleness(), which requires real elapsed time before anything is flagged - so
    using the start here does not reintroduce premature staleness. See
    test_hashed_window_start_does_not_cause_premature_staleness below.
    """
    now = _ny(2026, 8, 3, 8, 0)
    got = cadence.previous_fire_time("H 2 * * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 3, 2, 0)


def test_weekday_range_skips_weekend():
    now = _ny(2026, 8, 3, 8, 0)  # Monday morning, before 23:00
    got = cadence.previous_fire_time("H 23 * * 1-5", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 7, 31, 23, 0)  # Friday, window start


def test_day_of_month_range():
    now = _ny(2026, 8, 3, 8, 0)
    got = cadence.previous_fire_time("H 23 20-31 * *", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 7, 31, 23, 0)


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
    """2026-03-08 is the spring-forward day; 02:30 local does not exist that day.
    now must be ON that day or the day-walk returns immediately and never touches the gap."""
    now = _ny(2026, 3, 8, 12, 0)
    got = cadence.previous_fire_time("30 2 * * *", "America/New_York", now)
    assert got.tzinfo is not None
    assert got.astimezone(NY).date() == dt.date(2026, 3, 8)


def test_both_dom_and_dow_restricted_uses_or_semantics():
    """Standard cron: DOM and DOW both restricted -> OR, not AND."""
    now = _ny(2026, 8, 20, 12, 0)  # Thursday
    got = cadence.previous_fire_time("0 9 15 * 1", "America/New_York", now)
    assert got.astimezone(NY) == _ny(2026, 8, 17, 9, 0)  # Monday, nearer than the 15th


# ---- H window-start regression (false positives from the first live run) ------


def test_regression_dv01_figure_sync_early_in_window_is_not_stale():
    """Real false positive from the first live run: quant-dv01-figure-sync, cron
    'H 20 * * *', ran at 20:56 local - inside its own hashed window - and was
    wrongly flagged STALE because the old window-END expected time (20:59) made
    20:56 look 3 minutes late."""
    spec = JobSpec(
        job="quant-dv01-figure-sync",
        tier="fix",
        family="loaders",
        trigger_type="cron",
        cron="H 20 * * *",
        tz="America/New_York",
        grace_hours=6,
    )
    last = _ny(2026, 8, 2, 20, 56)
    now = _ny(2026, 8, 3, 10, 0)  # following mid-morning
    stale, why = cadence.staleness(spec, last, now)
    assert stale is False, why


def test_hashed_window_start_does_not_cause_premature_staleness():
    """Confirms the window-start fix does not flag a job stale just because `now`
    falls inside a hashed window that hasn't produced today's run yet. Yesterday's
    real run is older than today's expected (window-start) instant, but the
    grace-hours deadline - which requires hours to elapse, not just the window to
    open - has not passed, so this must not be stale."""
    spec = JobSpec(
        job="j",
        tier="fix",
        family="f",
        trigger_type="cron",
        cron="H 20 * * *",
        tz="America/New_York",
        grace_hours=6,
    )
    last = _ny(2026, 8, 2, 20, 56)  # yesterday's real run
    now = _ny(2026, 8, 3, 20, 5)  # just past today's window open; today hasn't run yet
    stale, why = cadence.staleness(spec, last, now)
    assert stale is False, why


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


def test_upstream_job_gated_by_default_is_not_stale_even_if_parent_ran_more_recently():
    """Every upstream-triggered job in the registry is invoked by a readiness gate:
    the parent runs unconditionally but only sometimes actually kicks off the child.
    The parent doing work more recently than the child is the NORMAL case, not a
    fault - the default (upstream_strict=False) must not flag it. Real false
    positives from the first live run: quant-DailySimHistVectorUndialed,
    quant-Monthly-Tracking-Report(-Undialed), quant-PseudoDeal-*."""
    spec = JobSpec(job="c", tier="fix", family="f", trigger_type="upstream", upstream="p")
    now = _ny(2026, 8, 3, 8, 0)
    stale, why = cadence.staleness(spec, _ny(2026, 8, 1, 0, 0), now, upstream_ts=_ny(2026, 8, 2, 0, 0))
    assert stale is False
    assert "gate" in why.lower()


def test_upstream_job_strict_is_stale_only_if_parent_ran_more_recently():
    """A future strictly-chained child (no readiness gate) opts in with
    upstream_strict=True and gets the old parent-vs-child comparison back."""
    spec = JobSpec(job="c", tier="fix", family="f", trigger_type="upstream", upstream="p", upstream_strict=True)
    now = _ny(2026, 8, 3, 8, 0)
    stale, _ = cadence.staleness(spec, _ny(2026, 8, 1, 0, 0), now, upstream_ts=_ny(2026, 8, 2, 0, 0))
    assert stale is True
    stale2, _ = cadence.staleness(spec, _ny(2026, 8, 2, 0, 0), now, upstream_ts=_ny(2026, 8, 1, 0, 0))
    assert stale2 is False


def test_cron_job_with_no_real_build_ever_is_stale():
    stale, why = cadence.staleness(_CRON_SPEC, None, _ny(2026, 8, 3, 8, 0))
    assert stale is True
    assert "never" in why.lower()


def test_unrecognized_trigger_type_raises_cadence_error():
    spec = JobSpec(job="x", tier="fix", family="f", trigger_type="bogus")
    with pytest.raises(cadence.CadenceError):
        cadence.staleness(spec, None, _ny(2026, 8, 3, 8, 0))


def test_cron_trigger_type_with_no_cron_raises_cadence_error_not_attribute_error():
    spec = JobSpec(job="y", tier="fix", family="f", trigger_type="cron", tz="America/New_York")
    with pytest.raises(cadence.CadenceError):
        cadence.staleness(spec, None, _ny(2026, 8, 3, 8, 0))


# ---- absolute silence ceiling (final review, CRITICAL 3) -----------------------
# staleness() returned not-stale before any clock comparison for pollscm, manual and
# non-strict upstream jobs - 14 of the 25 registered jobs, i.e. staleness detection was
# switched off for over half the fleet. The observation that motivated this whole package
# (quant-Monthly-Tracking-Report, last REAL build 27 days old) classified GREEN and was
# dropped from the report entirely. max_silence_days is an absolute wall-clock floor that
# is checked before every one of those early returns.

_UPSTREAM_CEILING_SPEC = JobSpec(
    job="quant-Monthly-Tracking-Report",
    tier="fix",
    family="resitracking",
    trigger_type="upstream",
    upstream="quant-Monthly-ResiTracking-Tracking",
    max_silence_days=21,
)


def test_upstream_job_silent_27_days_is_stale_via_absolute_ceiling():
    """The spec's own motivating example. Non-strict upstream, so the parent-recency
    comparison is deliberately disabled - the ceiling is the only thing that can catch it."""
    now = _ny(2026, 8, 3, 8, 0)
    last = now - dt.timedelta(days=27)
    stale, why = cadence.staleness(_UPSTREAM_CEILING_SPEC, last, now, upstream_ts=now)
    assert stale is True, why
    assert "27d" in why, "the reason must name the silence duration"
    assert "ceiling" in why.lower() or "floor" in why.lower()
    assert "not cadence enforcement" in why.lower(), (
        "the reason must say this is an absolute floor, not a cadence violation - otherwise "
        "a reader will look for a schedule this job does not have"
    )


def test_same_upstream_job_silent_three_days_is_not_stale():
    """Deliberately chosen at 21 days so the ceiling cannot reproduce the 7 upstream false
    positives that motivated upstream_strict: false - those were parent-recency
    comparisons measuring hours to a few days, well inside three weeks."""
    now = _ny(2026, 8, 3, 8, 0)
    last = now - dt.timedelta(days=3)
    stale, why = cadence.staleness(_UPSTREAM_CEILING_SPEC, last, now, upstream_ts=now)
    assert stale is False, why
    assert "gate" in why.lower(), "it must fall through to the normal gated-upstream explanation"


def test_upstream_job_just_inside_the_ceiling_is_not_stale():
    now = _ny(2026, 8, 3, 8, 0)
    stale, _ = cadence.staleness(_UPSTREAM_CEILING_SPEC, now - dt.timedelta(days=20, hours=23), now)
    assert stale is False


def test_pollscm_job_without_a_ceiling_is_never_stale_however_old():
    """pollscm builds only on repo change, so silence is genuinely expected - these jobs
    omit max_silence_days on purpose and must stay exempt at any age."""
    spec = JobSpec(job="quant-deploy-lmqr", tier="notify", family="deploy", trigger_type="pollscm")
    assert spec.max_silence_days is None
    stale, why = cadence.staleness(spec, _ny(2015, 1, 1, 0, 0), _ny(2026, 8, 3, 8, 0))
    assert stale is False
    assert "scm" in why.lower()


def test_manual_job_without_a_ceiling_is_never_stale_however_old():
    spec = JobSpec(job="quant-Monthly-ResiTracking-pipeline", tier="fix", family="f", trigger_type="manual")
    assert spec.max_silence_days is None
    stale, _ = cadence.staleness(spec, _ny(2015, 1, 1, 0, 0), _ny(2026, 8, 3, 8, 0))
    assert stale is False


def test_ceiling_applies_to_pollscm_too_when_explicitly_set():
    """The ceiling is checked before the pollscm early return, so a deploy job CAN opt in
    if someone decides repo silence that long is itself worth a look."""
    spec = JobSpec(job="d", tier="notify", family="deploy", trigger_type="pollscm", max_silence_days=21)
    stale, why = cadence.staleness(spec, _ny(2015, 1, 1, 0, 0), _ny(2026, 8, 3, 8, 0))
    assert stale is True, why
