# claude-code-routines/jenkins_monitor/models.py
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

WORK_RESULTS = frozenset({"SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"})


class State:
    RED = "RED"
    UNSTABLE = "UNSTABLE"
    STALE = "STALE"
    NEVER_DID_WORK = "NEVER_DID_WORK"
    SEED_ONLY = "SEED_ONLY"
    BUILDING = "BUILDING"
    GREEN = "GREEN"
    UNREACHABLE = "UNREACHABLE"


#: States that justify dispatching a fix agent. Everything else is infra/access.
FIXABLE_STATES = frozenset({State.RED, State.UNSTABLE})


@dataclass(frozen=True)
class JobSpec:
    job: str
    tier: str
    family: str
    trigger_type: str
    cron: str | None = None
    tz: str | None = None
    grace_hours: float = 6.0
    #: Absolute wall-clock ceiling on silence, independent of the cadence comparison. Set
    #: it and a job is STALE once its last REAL build is older than this many days, even
    #: for trigger types whose cadence check is intentionally disabled (non-strict
    #: upstream). None means no ceiling - only correct where silence is genuinely
    #: expected (pollscm: builds on repo change; manual: no trigger at all).
    max_silence_days: float | None = None
    upstream: str | None = None
    upstream_strict: bool = False
    orchestrator: bool = False
    child_job: str | None = None
    #: Defaults to True: an UNSTABLE build is a partial failure, and GREEN must mean
    #: "confirmed good", never "UNSTABLE and we chose not to look". The registry is
    #: hand-maintained against upstream jenkinsfiles that change, so a job that newly
    #: gains `catchError(buildResult: 'UNSTABLE')` must become visible by default rather
    #: than silently invisible. Set it False to opt a specific job out, deliberately.
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


@dataclass(frozen=True)
class JobStatus:
    job: str
    state: str
    latest: BuildInfo | None = None
    last_real: BuildInfo | None = None
    last_success: BuildInfo | None = None
    last_failure: BuildInfo | None = None
    detail: str = ""
    consecutive_failures: int = 0


@dataclass(frozen=True)
class Diagnosis:
    job: str
    error_class: str
    error_text: str
    source_hint: str = ""
    affected: tuple[str, ...] = ()
    child_builds: tuple[int, ...] = ()
    source: str = "console"
    confidence: str = "medium"
    #: The build whose console was actually read. Surfaced in the report so a reader can
    #: see at a glance which build the diagnosis describes - a diagnosis taken from the
    #: wrong build (e.g. a no-work NOT_BUILT seed run instead of the failing build) reads
    #: as authoritative and would otherwise be indistinguishable from a correct one.
    build_number: int | None = None


@dataclass(frozen=True)
class Finding:
    status: JobStatus
    transition: str  # NEW | ONGOING | RECOVERED
    diagnosis: Diagnosis | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    #: The job's state in the previous snapshot, when known. Threaded through so a
    #: renderer can show `RED -> BUILDING` instead of a bare current state - an
    #: ONGOING finding whose current state is BUILDING/SEED_ONLY has NOT been
    #: confirmed recovered, and dropping the previous state invites reading it as
    #: neutral or all-clear.
    previous_state: str | None = None
