# claude-code-routines/jenkins_monitor/report.py
from __future__ import annotations

from collections.abc import Sequence

from .models import Finding, State

_ORDER = {
    State.RED: 0,
    State.UNSTABLE: 1,
    State.STALE: 2,
    State.NEVER_DID_WORK: 3,
    State.UNREACHABLE: 4,
    State.SEED_ONLY: 5,
    State.BUILDING: 6,
    State.GREEN: 7,
}

#: An ONGOING finding whose *current* state is one of these has not been shown to
#: be fixed - it is a build in progress or a no-work seed run, not a confirmed
#: recovery. Called out explicitly so this never reads as a quiet all-clear.
_UNCONFIRMED_ONGOING_STATES = frozenset({State.BUILDING, State.SEED_ONLY})


def _state_label(f: Finding) -> str:
    """`<previous> -> <current>` when the previous state is known and differs, else bare current state."""
    current = f.status.state
    if f.previous_state and f.previous_state != current:
        return f"{f.previous_state} -> {current}"
    return current


def _line(f: Finding) -> str:
    st = f.status
    parts = [f"**`{st.job}`** - {_state_label(f)}: {st.detail}"]
    if f.transition == "ONGOING" and st.state in _UNCONFIRMED_ONGOING_STATES:
        parts.append("_(recovery not yet confirmed)_")
    d = f.diagnosis
    if d:
        # Name the build the diagnosis was actually read from. The diagnoser deliberately
        # inspects the last build that DID WORK, which is often not `lastBuild` (a
        # NOT_BUILT seed refresh can be newer); printing it makes any future mismatch
        # between the reported state and the inspected build visible to a reader instead
        # of silently authoritative.
        if d.build_number is not None:
            parts.append(f"diagnosed from build #{d.build_number}")
        if d.error_class and d.error_class != "unknown":
            parts.append(f"`{d.error_class}`")
        if d.source_hint:
            parts.append(f"at `{d.source_hint}`")
        if d.affected:
            parts.append(f"affected: {', '.join(d.affected)}")
        if d.child_builds:
            parts.append(f"child builds: {', '.join(f'#{n}' for n in d.child_builds)}")
        if d.confidence == "low":
            parts.append("_(low confidence - needs manual look)_")
    return "- " + " - ".join(parts)


def render(
    findings: list[Finding],
    *,
    token_ok: bool,
    total_jobs: int,
    fix_count: int = 0,
    notify_count: int = 0,
    capped: Sequence[str] = (),
    reason: str = "",
    prior_snapshot_available: bool = True,
) -> str:
    out: list[str] = ["### Jenkins Job Monitor", ""]

    if not token_ok:
        # `reason` is threaded through because this branch is reached for BOTH a missing
        # credential and a controller outage. Hardcoding the credential wording made the
        # persisted .md claim "No Jenkins API credentials in the environment" during a
        # Jenkins outage - a wrong diagnosis stated with full confidence.
        out += [
            f"- **Status: UNREACHABLE for all {total_jobs} jobs.** Job status could not be read, "
            "so nothing here is a statement that the jobs are healthy - it is an access or "
            "infrastructure gap.",
            f"- Cause: {reason}"
            if reason
            else "- Cause: not recorded by the caller (this itself is a bug worth reporting).",
            "- If the cause is a missing/expired credential: mint a token at "
            "`http://jenkins.libremax.com/me/security/` and set `JENKINS_USER` / "
            "`JENKINS_API_TOKEN` at Windows **User** scope.",
            "",
        ]
        return "\n".join(out)

    scope = f"- Scope: {total_jobs} jobs"
    if fix_count or notify_count:
        scope += f" ({fix_count} auto-fix tier, {notify_count} notify-only)"
    out.append(scope + ". Token: OK.")

    if not prior_snapshot_available:
        # Without a usable prior snapshot every current failure is labelled NEW and no
        # RECOVERED can ever be emitted. Presenting that silently would misrepresent a
        # long-standing failure as brand new and hide every recovery.
        out.append(
            "- **No prior snapshot available** (first run, or the previous snapshot was missing or "
            "unreadable): the NEW / ONGOING / RECOVERED labels below are not meaningful this run. "
            "Every current finding is shown as NEW, and a recovery cannot be detected at all."
        )

    # Grouped and ordered strictly by transition (NEW, then ONGOING, then RECOVERED) -
    # never by raw current state. A job that was RED and is now BUILDING is an
    # unresolved ONGOING problem, not a benign "BUILDING" item, and must not be
    # interleaved with truly benign entries by sorting on current state alone.
    buckets: dict[str, list[Finding]] = {"NEW": [], "ONGOING": [], "RECOVERED": []}
    for f in findings:
        if f.transition not in buckets:
            raise ValueError(
                f"job {f.status.job!r} has unexpected transition {f.transition!r}; "
                "expected one of NEW, ONGOING, RECOVERED - refusing to silently drop the finding"
            )
        buckets[f.transition].append(f)
    for items in buckets.values():
        items.sort(key=lambda f: (_ORDER.get(f.status.state, 9), f.status.job))

    if buckets["NEW"]:
        out += ["", "**NEW failures / findings since the last run:**"]
        out += [_line(f) for f in buckets["NEW"]]
    else:
        out.append("- **No new failures since the last run.**")

    if buckets["ONGOING"]:
        out += ["", "**Ongoing (already reported in a previous run):**"]
        out += [_line(f) for f in buckets["ONGOING"]]

    if buckets["RECOVERED"]:
        out += ["", "**Recovered since the last run:**"]
        out += [_line(f) for f in buckets["RECOVERED"]]

    if capped:
        # Every eligible finding is diagnosed; the cap only limits how many are NOMINATED
        # for a fix agent. The old wording said "Diagnosed but fix not attempted" for jobs
        # that had in fact been neither diagnosed nor nominated - a claim of work not done.
        out += [
            "",
            f"**Diagnosed, fix agent not nominated (fix-slot cap):** {', '.join(capped)}. "
            "The diagnosis for each is on its line above; the cap limits only how many jobs "
            "get an agent dispatched this run - these are real findings, not all clear.",
        ]

    if any(f.status.state in (State.SEED_ONLY, State.NEVER_DID_WORK) for f in findings):
        out += [
            "",
            "_Notes: `SEED_ONLY` means the latest build was a benign no-work `REFRESH=true` seed "
            "run triggered by a push to the JenkinsJobs repo - staleness is judged from the last "
            "real build instead. `NEVER_DID_WORK` means every recorded build was a seed refresh, "
            "so the job has never actually run - worth investigating whether its upstream ever "
            "invokes it._",
        ]

    out.append("")
    return "\n".join(out)
