# claude-code-routines/jenkins_monitor/registry.py
from __future__ import annotations

from pathlib import Path

import yaml

from .models import JobSpec

VALID_TIERS = frozenset({"fix", "notify"})
VALID_TRIGGERS = frozenset({"cron", "pollscm", "upstream", "manual"})


class RegistryError(ValueError):
    """The registry file is malformed. Raised with the offending job and field."""


def load_registry(path: str | Path) -> dict[str, JobSpec]:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(raw, dict) or "jobs" not in raw:
        raise RegistryError(f"{path}: top-level 'jobs:' key is required")

    jobs = raw["jobs"]
    if not isinstance(jobs, list):
        raise RegistryError(f"{path}: 'jobs' must be a list of job entries, got {type(jobs).__name__}")

    specs: dict[str, JobSpec] = {}
    for entry in jobs:
        if not isinstance(entry, dict):
            raise RegistryError(f"{path}: each job entry must be a mapping, got {type(entry).__name__}: {entry!r}")
        name = entry.get("job")
        if not name:
            raise RegistryError(f"{path}: an entry is missing required field 'job'")
        if name in specs:
            raise RegistryError(f"{name}: duplicate registry entry")

        for req in ("tier", "family", "trigger_type"):
            if not entry.get(req):
                raise RegistryError(f"{name}: missing required field '{req}'")

        tier = entry["tier"]
        if tier not in VALID_TIERS:
            raise RegistryError(f"{name}: tier {tier!r} not in {sorted(VALID_TIERS)}")

        trigger = entry["trigger_type"]
        if trigger not in VALID_TRIGGERS:
            raise RegistryError(f"{name}: trigger_type {trigger!r} not in {sorted(VALID_TRIGGERS)}")
        if trigger == "cron" and not (entry.get("cron") and entry.get("tz")):
            raise RegistryError(f"{name}: trigger_type 'cron' requires both 'cron' and 'tz'")
        if trigger == "upstream" and not entry.get("upstream"):
            raise RegistryError(f"{name}: trigger_type 'upstream' requires 'upstream'")

        specs[name] = JobSpec(
            job=name,
            tier=tier,
            family=entry["family"],
            trigger_type=trigger,
            cron=entry.get("cron"),
            tz=entry.get("tz"),
            grace_hours=float(entry.get("grace_hours", 6.0)),
            upstream=entry.get("upstream"),
            upstream_strict=bool(entry.get("upstream_strict", False)),
            orchestrator=bool(entry.get("orchestrator", False)),
            child_job=entry.get("child_job"),
            unstable_is_failure=bool(entry.get("unstable_is_failure", False)),
            success_markers=tuple(entry.get("success_markers", ())),
            console_informative=bool(entry.get("console_informative", True)),
            nas_log_glob=entry.get("nas_log_glob"),
            entrypoint=entry.get("entrypoint"),
            repo=entry.get("repo"),
        )
    return specs
