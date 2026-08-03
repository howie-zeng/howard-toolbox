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
        return f"{f.previous_state} → {current}"
    return current


def _line(f: Finding) -> str:
    st = f.status
    parts = [f"**`{st.job}`** — {_state_label(f)}: {st.detail}"]
    if f.transition == "ONGOING" and st.state in _UNCONFIRMED_ONGOING_STATES:
        parts.append("_(recovery not yet confirmed)_")
    d = f.diagnosis
    if d:
        if d.error_class and d.error_class != "unknown":
            parts.append(f"`{d.error_class}`")
        if d.source_hint:
            parts.append(f"at `{d.source_hint}`")
        if d.affected:
            parts.append(f"affected: {', '.join(d.affected)}")
        if d.child_builds:
            parts.append(f"child builds: {', '.join(f'#{n}' for n in d.child_builds)}")
        if d.confidence == "low":
            parts.append("_(low confidence — needs manual look)_")
    return "- " + " — ".join(parts)


def render(
    findings: list[Finding],
    *,
    token_ok: bool,
    total_jobs: int,
    fix_count: int = 0,
    notify_count: int = 0,
    capped: Sequence[str] = (),
) -> str:
    out: list[str] = ["### Jenkins Job Monitor", ""]

    if not token_ok:
        out += [
            f"- **Status: UNREACHABLE for all {total_jobs} jobs.** No Jenkins API credentials in "
            "the environment, so job status could not be read. This is an access gap, **not** a "
            "statement that the jobs are healthy.",
            "- Fix: mint a token at `http://jenkins.libremax.com/me/security/` and set "
            "`JENKINS_USER` / `JENKINS_API_TOKEN` at Windows **User** scope.",
            "",
        ]
        return "\n".join(out)

    scope = f"- Scope: {total_jobs} jobs"
    if fix_count or notify_count:
        scope += f" ({fix_count} auto-fix tier, {notify_count} notify-only)"
    out.append(scope + ". Token: OK.")

    # Grouped and ordered strictly by transition (NEW, then ONGOING, then RECOVERED) -
    # never by raw current state. A job that was RED and is now BUILDING is an
    # unresolved ONGOING problem, not a benign "BUILDING" item, and must not be
    # interleaved with truly benign entries by sorting on current state alone.
    buckets: dict[str, list[Finding]] = {"NEW": [], "ONGOING": [], "RECOVERED": []}
    for f in findings:
        buckets.setdefault(f.transition, []).append(f)
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
        out += [
            "",
            f"**Diagnosed but fix not attempted (slot cap):** {', '.join(capped)}. "
            "These are real findings that did not get an agent this run — not all clear.",
        ]

    if any(f.status.state in (State.SEED_ONLY, State.NEVER_DID_WORK) for f in findings):
        out += [
            "",
            "_Notes: `SEED_ONLY` means the latest build was a benign no-work `REFRESH=true` seed "
            "run triggered by a push to the JenkinsJobs repo — staleness is judged from the last "
            "real build instead. `NEVER_DID_WORK` means every recorded build was a seed refresh, "
            "so the job has never actually run — worth investigating whether its upstream ever "
            "invokes it._",
        ]

    out.append("")
    return "\n".join(out)
