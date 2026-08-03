# claude-code-routines/jenkins_monitor/classify.py
from __future__ import annotations

import datetime as dt

from . import cadence
from .client import build_from_blob
from .models import BuildInfo, JobSpec, JobStatus, State


def last_real_build(builds: list[BuildInfo]) -> BuildInfo | None:
    """Newest build that actually did work, skipping NOT_BUILT seed refreshes."""
    for b in builds:
        if b.did_work:
            return b
    return None


def consecutive_failures(builds: list[BuildInfo]) -> int:
    """How many real builds in a row, newest-first, ended non-SUCCESS."""
    count = 0
    for b in builds:
        if not b.did_work:
            continue
        if b.result == "SUCCESS":
            break
        count += 1
    return count


def classify_job(
    spec: JobSpec,
    job_blob: dict,
    builds: list[BuildInfo],
    now: dt.datetime,
    upstream_real_ts: dt.datetime | None = None,
) -> JobStatus:
    latest = build_from_blob(job_blob.get("lastBuild"))
    last_success = build_from_blob(job_blob.get("lastSuccessfulBuild"))
    last_failure = build_from_blob(job_blob.get("lastFailedBuild"))
    real = last_real_build(builds)
    fails = consecutive_failures(builds)

    def _status(state: str, detail: str) -> JobStatus:
        return JobStatus(
            job=spec.job,
            state=state,
            latest=latest,
            last_real=real,
            last_success=last_success,
            last_failure=last_failure,
            detail=detail,
            consecutive_failures=fails,
        )

    if latest is not None and latest.building:
        return _status(State.BUILDING, f"build #{latest.number} in progress; deferred")

    if real is None:
        n = len(builds)
        return _status(
            State.NEVER_DID_WORK,
            f"{n} build(s) recorded, all NOT_BUILT seed refreshes; never did work",
        )

    # Red takes precedence: a newer failure than the newest success.
    s_num = last_success.number if last_success else 0
    f_num = last_failure.number if last_failure else 0
    if f_num > s_num:
        return _status(
            State.RED,
            f"#{f_num} FAILURE is newer than last success #{s_num}"
            + (f"; {fails} consecutive failing builds" if fails > 1 else ""),
        )

    if real.result == "UNSTABLE" and spec.unstable_is_failure:
        return _status(State.UNSTABLE, f"#{real.number} UNSTABLE (partial failure for this job)")

    stale, why = cadence.staleness(spec, real.timestamp, now, upstream_ts=upstream_real_ts)
    if stale:
        return _status(State.STALE, why)

    if latest is not None and not latest.did_work:
        return _status(
            State.SEED_ONLY,
            f"latest build #{latest.number} is a NOT_BUILT seed refresh; "
            f"last real build #{real.number} was {real.result}",
        )

    return _status(State.GREEN, f"#{real.number} {real.result}; {why}")
