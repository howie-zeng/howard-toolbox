# claude-code-routines/jenkins_monitor/registry.py
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from .models import JobSpec

VALID_TIERS = frozenset({"fix", "notify"})
VALID_TRIGGERS = frozenset({"cron", "pollscm", "upstream", "manual"})


class RegistryError(ValueError):
    """The registry file is malformed. Raised with the offending job and field."""


def _float_field(name: str, field: str, value, default: float | None) -> float | None:
    """Parse a numeric registry field, or raise RegistryError naming job and field.

    Without this, `float(entry.get("grace_hours", 6.0))` raised a bare ValueError on
    `grace_hours: abc`, which `cli.py` does not catch - so one typo killed the entire
    unattended run instead of being reported as the config bug it is.
    """
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RegistryError(f"{name}: {field} must be a number, got {value!r}") from exc


def _validate_tz(name: str, tzname) -> None:
    """Reject a timezone that does not resolve.

    `cadence.previous_fire_time` calls ZoneInfo(tzname), which raises
    ZoneInfoNotFoundError (a KeyError) - not CadenceError - so cli.py's per-job isolation
    did not catch it and a single typo ('America/New_Yrok') aborted the whole run.
    """
    if tzname is None:
        return
    if not isinstance(tzname, str):
        raise RegistryError(f"{name}: tz must be a string, got {tzname!r}")
    try:
        ZoneInfo(tzname)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RegistryError(f"{name}: tz {tzname!r} is not a resolvable IANA timezone: {exc}") from exc


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

        _validate_tz(name, entry.get("tz"))
        grace_hours = _float_field(name, "grace_hours", entry.get("grace_hours"), 6.0)
        max_silence_days = _float_field(name, "max_silence_days", entry.get("max_silence_days"), None)

        orchestrator = bool(entry.get("orchestrator", False))
        if orchestrator and not entry.get("child_job"):
            # diagnose.py only drills into children when BOTH are set, so `orchestrator`
            # alone silently disables drill-down and then tries to pull a traceback out of
            # a wrapper console that never has one.
            raise RegistryError(f"{name}: orchestrator: true requires 'child_job' (drill-down target)")

        markers = entry.get("success_markers", ())
        if isinstance(markers, str):
            # tuple("Done NQM") would iterate the string into single-character "markers",
            # each of which is trivially present in any console - so nothing is ever
            # reported missing and a partial failure looks complete.
            raise RegistryError(f"{name}: success_markers must be a list, got a bare string {markers!r}")

        specs[name] = JobSpec(
            job=name,
            tier=tier,
            family=entry["family"],
            trigger_type=trigger,
            cron=entry.get("cron"),
            tz=entry.get("tz"),
            grace_hours=grace_hours,
            max_silence_days=max_silence_days,
            upstream=entry.get("upstream"),
            upstream_strict=bool(entry.get("upstream_strict", False)),
            orchestrator=orchestrator,
            child_job=entry.get("child_job"),
            unstable_is_failure=bool(entry.get("unstable_is_failure", True)),
            success_markers=tuple(markers),
            console_informative=bool(entry.get("console_informative", True)),
            nas_log_glob=entry.get("nas_log_glob"),
            entrypoint=entry.get("entrypoint"),
            repo=entry.get("repo"),
        )
    return specs
