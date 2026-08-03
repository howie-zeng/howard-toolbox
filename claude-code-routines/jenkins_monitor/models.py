# claude-code-routines/jenkins_monitor/models.py
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

#: Build results that mean the build actually executed work. `NOT_BUILT` is absent on
#: purpose: it is what a REFRESH=true seed build finishes as. See BuildInfo.did_work.
WORK_RESULTS = frozenset({"SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"})


@dataclass(frozen=True)
class JobSpec:
    """One registry entry: cached facts about a job that are expensive to re-derive.

    Everything here is DATA the daily agent reads, not a rule the code applies. The cadence
    fields in particular exist because job names lie about their schedule
    (`quant-DailySimDataUpdateIntex` is Friday-only) and re-reading 25 jenkinsfiles every
    morning is slow and error-prone. How to interpret each field is in
    `JENKINS_MONITOR_PROMPT.md`.
    """

    job: str
    tier: str
    family: str
    trigger_type: str
    #: Verbatim from the jenkinsfile. 'H' is Jenkins' hashed value: one stable value
    #: somewhere in the field's range, reused forever - so it denotes a WINDOW, not a time.
    cron: str | None = None
    tz: str | None = None
    grace_hours: float = 6.0
    #: Absolute wall-clock ceiling on silence, in days. Set only on upstream-triggered jobs,
    #: whose parent-recency comparison is meaningless (they sit behind a readiness gate).
    #: None means no ceiling - correct where silence is genuinely expected (pollscm builds
    #: on repo change; manual has no trigger at all).
    max_silence_days: float | None = None
    upstream: str | None = None
    orchestrator: bool = False
    child_job: str | None = None
    #: Defaults to True: an UNSTABLE build is a partial failure, and a green verdict must
    #: mean "confirmed good", never "UNSTABLE and we chose not to look". The registry is
    #: hand-maintained against upstream jenkinsfiles that change, so a job that newly gains
    #: `catchError(buildResult: 'UNSTABLE')` becomes visible by default rather than silently
    #: invisible. Set it False to opt a specific job out, deliberately.
    unstable_is_failure: bool = True
    success_markers: tuple[str, ...] = ()
    console_informative: bool = True
    nas_log_glob: str | None = None
    entrypoint: str | None = None
    repo: str | None = None


@dataclass(frozen=True)
class BuildInfo:
    number: int
    result: str | None
    timestamp: dt.datetime | None
    building: bool = False

    @property
    def did_work(self) -> bool:
        """True only for builds that actually executed work.

        A REFRESH=true seed build finishes NOT_BUILT and must never be treated as
        evidence the job ran - it would mask staleness.
        """
        return self.result in WORK_RESULTS
