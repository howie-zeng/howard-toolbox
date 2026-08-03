# claude-code-routines/jenkins_monitor/diagnose.py
from __future__ import annotations

import re

from .models import Diagnosis, JobSpec, JobStatus

_TRACEBACK_START = "Traceback (most recent call last):"
_ERROR_LINE = re.compile(r"^(?P<cls>[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Exit))\b\s*:?(?P<msg>.*)$")
_FILE_LINE = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')
_CHILD_RESULT = re.compile(r"Build (?P<job>[\w.-]+) #(?P<num>\d+) completed: (?P<result>[A-Z_]+)")


def extract_python_error(text: str) -> tuple[str, str]:
    """Return (error_class, traceback_block) for the LAST traceback in the log.

    The last one is the operative failure; earlier ones are often retried or
    caught. Returns ("", "") when no traceback is present.
    """
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if _TRACEBACK_START in ln]
    if not starts:
        return "", ""
    start = starts[-1]
    block: list[str] = []
    err_class = ""
    for ln in lines[start:]:
        block.append(ln)
        m = _ERROR_LINE.match(ln.strip())
        if m and len(block) > 1:
            err_class = m.group("cls")
            break
    return err_class, "\n".join(block)


def source_hint(block: str) -> str:
    """Deepest (last) source frame in a traceback: 'path:line in func'."""
    last = None
    for ln in block.splitlines():
        m = _FILE_LINE.match(ln)
        if m:
            last = m
    if not last:
        return ""
    return f"{last.group('path')}:{last.group('line')} in {last.group('func')}"


def missing_markers(text: str, markers) -> tuple[str, ...]:
    return tuple(m for m in markers if m not in text)


def child_results(text: str) -> dict[int, str]:
    """Map child build number -> result from an orchestrator's console."""
    out: dict[int, str] = {}
    for m in _CHILD_RESULT.finditer(text):
        out[int(m.group("num"))] = m.group("result")
    return out


def diagnose_job(client, spec: JobSpec, status: JobStatus) -> Diagnosis:
    build_no = status.latest.number if status.latest else None
    if build_no is None:
        return Diagnosis(job=spec.job, error_class="", error_text="no build to diagnose", confidence="low")

    try:
        console = client.console(spec.job, build_no)
    except Exception as exc:  # noqa: BLE001 - degrade, never abort the whole run
        return Diagnosis(
            job=spec.job,
            error_class="",
            error_text=f"could not read console for #{build_no}: {exc}",
            confidence="low",
        )

    if spec.orchestrator and spec.child_job:
        return _diagnose_orchestrator(client, spec, build_no, console)

    err_class, block = extract_python_error(console)
    affected = missing_markers(console, spec.success_markers)

    if not err_class and not spec.console_informative:
        return Diagnosis(
            job=spec.job,
            error_class="",
            error_text=(
                f"console for #{build_no} carries no traceback, which is expected for this job "
                f"(--log does not mirror errors to stdout). The real error is in the NAS log."
            ),
            source_hint=f"read newest file matching {spec.nas_log_glob}",
            affected=affected,
            source="nas-log-required",
            confidence="low",
        )

    return Diagnosis(
        job=spec.job,
        error_class=err_class or "unknown",
        error_text=block or console[-2000:],
        source_hint=source_hint(block),
        affected=affected,
        source="console",
        confidence="high" if err_class else "low",
    )


def _diagnose_orchestrator(client, spec: JobSpec, build_no: int, console: str) -> Diagnosis:
    """A wrapper's own console has no traceback - drill into failing children."""
    results = child_results(console)
    failing = sorted(n for n, r in results.items() if r != "SUCCESS")
    if not failing:
        return Diagnosis(
            job=spec.job,
            error_class="",
            error_text=f"#{build_no} failed but no failing child build was found in its console",
            confidence="low",
        )

    err_class = ""
    block = ""
    hint = ""
    affected: list[str] = []
    for num in failing:
        try:
            _result, params = client.build_detail(spec.child_job, num)
            label = params.get("deal_type") or params.get("dealtype") or f"#{num}"
            affected.append(str(label))
        except Exception:  # noqa: BLE001, S110 - a missing label must not lose the diagnosis
            affected.append(f"#{num}")
        if err_class:
            continue
        try:
            child_console = client.console(spec.child_job, num)
        except Exception:  # noqa: BLE001, S112
            continue
        err_class, block = extract_python_error(child_console)
        hint = source_hint(block)

    total = len(results)
    return Diagnosis(
        job=spec.job,
        error_class=err_class or "unknown",
        error_text=(
            f"{len(failing)} of {total} child builds of {spec.child_job} failed "
            f"(wrapper reported one flat FAILURE).\n\n{block}"
        ),
        source_hint=hint,
        affected=tuple(affected),
        child_builds=tuple(failing),
        source="child-console",
        confidence="high" if err_class else "low",
    )
