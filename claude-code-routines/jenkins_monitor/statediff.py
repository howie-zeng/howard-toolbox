# claude-code-routines/jenkins_monitor/statediff.py
"""Cross-day memory: the one thing a daily agent genuinely cannot do for itself.

A snapshot is a flat `{job: state_string}` mapping of the AGENT's verdicts for one day.
Nothing here judges anything; it only persists what the agent concluded so tomorrow's run
can tell "still broken" from "recovered". Without it, an agent reasoning fresh each morning
escalated the same job for three consecutive days after it had already recovered.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

_SNAPSHOT_RE = re.compile(r"^jenkins-status-(\d{8})\.json$")


def save_snapshot(verdicts: Mapping[str, str], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {str(job): str(state) for job, state in verdicts.items()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)  # atomic - a half-written snapshot would corrupt tomorrow's comparison


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
