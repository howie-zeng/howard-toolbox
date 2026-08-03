# claude-code-routines/jenkins_monitor/statediff.py
from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Finding, JobStatus, State

_SNAPSHOT_RE = re.compile(r"^jenkins-status-(\d{8})\.json$")

#: States that represent something needing attention.
_ATTENTION = frozenset({State.RED, State.UNSTABLE, State.STALE, State.NEVER_DID_WORK, State.UNREACHABLE})


def save_snapshot(statuses: list[JobStatus], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {s.job: s.state for s in statuses}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)  # atomic - a half-written snapshot would corrupt tomorrow's diff


def load_snapshot(path: Path) -> dict[str, str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def latest_snapshot_path(outputs_dir: Path, before: str) -> Path | None:
    """Newest snapshot strictly older than the `before` datestamp (YYYYMMDD)."""
    candidates = []
    for p in Path(outputs_dir).glob("jenkins-status-*.json"):
        m = _SNAPSHOT_RE.search(p.name)
        if m and m.group(1) < before:
            candidates.append((m.group(1), p))
    if not candidates:
        return None
    return max(candidates)[1]


def label(statuses: list[JobStatus], previous: dict[str, str]) -> list[Finding]:
    """Attach NEW / ONGOING / RECOVERED to each status worth reporting."""
    findings: list[Finding] = []
    for st in statuses:
        prev = previous.get(st.job)
        now_bad = st.state in _ATTENTION

        # Three cases this distinguishes: (1) still failing now - NEW/ONGOING per whether
        # the specific bad state repeats; (2) was failing and is now confirmed GREEN vs.
        # merely not-yet-confirmed (BUILDING/SEED_ONLY) - only the former is RECOVERED;
        # (3) was fine and just turned not-green - NEW/ONGOING per whether it repeats.
        if now_bad:
            transition = "ONGOING" if prev == st.state else "NEW"
        elif prev in _ATTENTION:
            # RECOVERED requires confirmed GREEN. A job that was failing and is now
            # BUILDING or SEED_ONLY has NOT been shown to be fixed - claiming recovery
            # there is a false all-clear, the exact failure class this module exists to
            # eliminate. Report it as unresolved instead.
            transition = "RECOVERED" if st.state == State.GREEN else "ONGOING"
        elif st.state == State.GREEN:
            continue  # green and was green: nothing to say
        else:
            transition = "ONGOING" if prev == st.state else "NEW"

        findings.append(Finding(status=st, transition=transition, previous_state=prev))
    return findings
