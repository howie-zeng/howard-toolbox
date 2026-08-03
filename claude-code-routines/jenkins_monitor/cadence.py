# claude-code-routines/jenkins_monitor/cadence.py
"""Jenkins-cron subset evaluator.

Deliberately not croniter: croniter is not installed here and cannot parse
Jenkins' 'H' (hashed value) syntax, which four of the monitored jobs use.
Unsupported syntax raises rather than silently mis-evaluating - a wrong fire
time produces either a false stale alarm or false silence.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .models import JobSpec

_MAX_LOOKBACK_DAYS = 400


class CadenceError(ValueError):
    """The cron expression uses syntax this evaluator does not support."""


def _parse_field(raw: str, lo: int, hi: int, field: str) -> set[int]:
    """Expand one cron field to a set of ints.

    Supports: '*', 'H', an int, 'a-b' ranges, and comma-separated lists of those.
    'H' expands to the FULL range - callers pick the latest match, so a hashed
    minute is treated as "any time in the window", never as a precise instant.
    """
    raw = raw.strip()
    if raw in ("*", "H"):
        return set(range(lo, hi + 1))

    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part == "H":
            out.update(range(lo, hi + 1))
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                start, end = int(a), int(b)
            except ValueError as exc:
                raise CadenceError(f"{field}: unsupported range {part!r}") from exc
            if not (lo <= start <= hi and lo <= end <= hi and start <= end):
                raise CadenceError(f"{field}: range {part!r} outside {lo}-{hi}")
            out.update(range(start, end + 1))
            continue
        try:
            val = int(part)
        except ValueError as exc:
            raise CadenceError(f"{field}: unsupported token {part!r}") from exc
        if not lo <= val <= hi:
            raise CadenceError(f"{field}: value {val} outside {lo}-{hi}")
        out.add(val)
    if not out:
        raise CadenceError(f"{field}: expanded to nothing from {raw!r}")
    return out


def _jenkins_dow(day: dt.date) -> int:
    """Jenkins/cron day-of-week: Sunday=0 .. Saturday=6."""
    return day.isoweekday() % 7


def previous_fire_time(cron: str, tzname: str, now: dt.datetime) -> dt.datetime:
    """Latest moment this cron was scheduled to fire at or before `now` (UTC)."""
    fields = cron.split()
    if len(fields) != 5:
        raise CadenceError(f"expected 5 cron fields, got {len(fields)}: {cron!r}")
    minute_f, hour_f, dom_f, month_f, dow_f = fields

    minutes = _parse_field(minute_f, 0, 59, "minute")
    hours = _parse_field(hour_f, 0, 23, "hour")
    doms = _parse_field(dom_f, 1, 31, "day-of-month")
    months = _parse_field(month_f, 1, 12, "month")
    dows_raw = _parse_field(dow_f, 0, 7, "day-of-week")
    dows = {0 if d == 7 else d for d in dows_raw}  # 7 and 0 both mean Sunday

    dom_restricted = dom_f.strip() not in ("*", "H")
    dow_restricted = dow_f.strip() not in ("*", "H")

    tz = ZoneInfo(tzname)
    local_now = now.astimezone(tz)
    day = local_now.date()
    latest_hour, latest_min = max(hours), max(minutes)

    for _ in range(_MAX_LOOKBACK_DAYS):
        if day.month in months and _day_matches(day, doms, dows, dom_restricted, dow_restricted):
            for hh in sorted(hours, reverse=True):
                if day == local_now.date() and hh > local_now.hour:
                    continue
                for mm in sorted(minutes, reverse=True):
                    cand = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
                    if cand <= local_now:
                        return cand.astimezone(dt.UTC)
        day -= dt.timedelta(days=1)

    raise CadenceError(
        f"no fire time found within {_MAX_LOOKBACK_DAYS} days for {cron!r} (latest slot h={latest_hour} m={latest_min})"
    )


def _day_matches(day: dt.date, doms: set[int], dows: set[int], dom_restricted: bool, dow_restricted: bool) -> bool:
    """Standard cron DOM/DOW semantics: OR when both restricted, else AND."""
    dom_ok = day.day in doms
    dow_ok = _jenkins_dow(day) in dows
    if dom_restricted and dow_restricted:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def staleness(
    spec: JobSpec,
    last_real_ts: dt.datetime | None,
    now: dt.datetime,
    upstream_ts: dt.datetime | None = None,
) -> tuple[bool, str]:
    """Decide whether a job has silently stopped doing work.

    `last_real_ts` MUST be the timestamp of the last build that actually did work
    (i.e. a build whose result is in WORK_RESULTS), not the timestamp of Jenkins'
    `lastBuild`. Passing `lastBuild`'s timestamp would let a no-work `NOT_BUILT`
    seed/refresh build "refresh" the apparent last-run time and mask a job that
    has actually gone stale - the seed build ran, but it did no real work.
    """
    if spec.trigger_type == "pollscm":
        return False, "SCM-polled: builds only on repo change, silence is expected"
    if spec.trigger_type == "manual":
        return False, "manual/disabled trigger: no expected cadence"

    if spec.trigger_type == "upstream":
        if upstream_ts is None or last_real_ts is None:
            return False, f"upstream-triggered by {spec.upstream}: no comparison available"
        if upstream_ts > last_real_ts:
            gap = upstream_ts - last_real_ts
            return True, (f"upstream {spec.upstream} did work {_fmt(gap)} more recently than this job")
        return False, f"up to date relative to upstream {spec.upstream}"

    if spec.trigger_type != "cron":
        raise CadenceError(f"{spec.job}: unrecognized trigger_type {spec.trigger_type!r}")
    if spec.cron is None:
        raise CadenceError(f"{spec.job}: trigger_type 'cron' requires a cron expression, got cron=None")

    expected = previous_fire_time(spec.cron, spec.tz, now)
    if last_real_ts is None:
        return True, f"never did work; expected a run by {expected.isoformat()}"
    deadline = expected + dt.timedelta(hours=spec.grace_hours)
    if last_real_ts < expected and now > deadline:
        return True, (
            f"expected a run at {expected.isoformat()} "
            f"(+{spec.grace_hours:g}h grace); last real build was {last_real_ts.isoformat()}"
        )
    return False, f"last real build {last_real_ts.isoformat()} satisfies {expected.isoformat()}"


def _fmt(delta: dt.timedelta) -> str:
    total = int(delta.total_seconds())
    days, rem = divmod(total, 86400)
    hours = rem // 3600
    return f"{days}d{hours}h" if days else f"{hours}h"
