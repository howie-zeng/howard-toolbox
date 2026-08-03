# claude-code-routines/jenkins_monitor/models.py
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

WORK_RESULTS = frozenset({"SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"})
FAILING_RESULTS = frozenset({"FAILURE", "ABORTED"})


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
    upstream: str | None = None
    upstream_strict: bool = False
    orchestrator: bool = False
    child_job: str | None = None
    unstable_is_failure: bool = False
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
