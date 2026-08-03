# claude-code-routines/jenkins_monitor/diagnose.py
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol

from .models import Diagnosis, JobSpec, JobStatus

_TRACEBACK_START = "Traceback (most recent call last):"

#: Exception names that terminate a traceback without ending in Error/Exception/Exit.
#: KeyboardInterrupt and StopIteration are the ones seen in practice: these pipelines run
#: under `timeout(1440 MINUTES)`, and a timeout-killed or manually aborted Python process
#: commonly prints a bare KeyboardInterrupt as the last line of its traceback. SystemExit
#: and GeneratorExit are included for completeness, though the generic suffix branch below
#: already matches them.
_BARE_ERROR_NAMES = ("KeyboardInterrupt", "StopIteration", "SystemExit", "GeneratorExit")
_ERROR_LINE = re.compile(
    r"^(?P<cls>[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Exit)|" + "|".join(_BARE_ERROR_NAMES) + r")\b\s*:?(?P<msg>.*)$"
)
_FILE_LINE = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')
_CHILD_RESULT = re.compile(r"Build (?P<job>[\w.-]+) #(?P<num>\d+) completed: (?P<result>[A-Z_]+)")

#: Hard cap on how many lines extract_python_error will collect into one traceback block.
#: Without this, a traceback whose last line never matches _ERROR_LINE (a corrupted/truncated
#: console, or an exception name outside the patterns above) would make `block` grow to
#: end-of-file - a nameless, unbounded dump instead of a bounded excerpt.
_MAX_TRACEBACK_LINES = 60


def extract_python_error(text: str) -> tuple[str, str]:
    """Return (error_class, traceback_block) for the LAST traceback in the log.

    The last one is the operative failure; earlier ones are often retried or
    caught. Returns ("", "") when no traceback is present. The collected block
    is capped at _MAX_TRACEBACK_LINES even if no terminating error line is found.
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
        if len(block) >= _MAX_TRACEBACK_LINES:
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


def missing_markers(text: str, markers: Sequence[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(m for m in markers if m not in text)


def child_results(text: str) -> dict[int, str]:
    """Map child build number -> result from an orchestrator's console."""
    out: dict[int, str] = {}
    for m in _CHILD_RESULT.finditer(text):
        out[int(m.group("num"))] = m.group("result")
    return out


class DiagnosticClient(Protocol):
    """The subset of JenkinsClient's interface diagnose.py depends on.

    Kept minimal and separate from client.JenkinsClient so tests can supply a
    lightweight fake without importing the real (network-backed) client.
    """

    def console(self, job: str, number: int) -> str: ...

    def build_detail(self, job: str, number: int) -> tuple[str | None, dict[str, str]]: ...


def diagnose_job(client: DiagnosticClient, spec: JobSpec, status: JobStatus) -> Diagnosis:
    build_no = status.latest.number if status.latest else None
    if build_no is None:
        return Diagnosis(job=spec.job, error_class="", error_text="no build to diagnose", confidence="low")

    try:
        console = client.console(spec.job, build_no)
    except Exception as exc:  # degrade, never abort the whole run
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


def _diagnose_orchestrator(client: DiagnosticClient, spec: JobSpec, build_no: int, console: str) -> Diagnosis:
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
    notes: list[str] = []
    for num in failing:
        # Only the network call is guarded - a bug in the label extraction below (e.g.
        # `params` shaped unexpectedly) must propagate, not be mistaken for a fetch failure.
        try:
            _result, params = client.build_detail(spec.child_job, num)
        except Exception as exc:
            affected.append(f"#{num}")
            notes.append(f"could not read build detail for #{num}: {exc}")
        else:
            label = params.get("deal_type") or params.get("dealtype") or f"#{num}"
            affected.append(str(label))

        if err_class:
            continue
        try:
            child_console = client.console(spec.child_job, num)
        except Exception as exc:  # a missing child console must not lose the diagnosis, but leave a trace
            notes.append(f"could not read console for #{num}: {exc}")
            continue
        err_class, block = extract_python_error(child_console)
        hint = source_hint(block)

    total = len(results)
    error_text = (
        f"{len(failing)} of {total} child builds of {spec.child_job} failed "
        f"(wrapper reported one flat FAILURE).\n\n{block}"
    )
    if notes:
        error_text += "\n\n" + "\n".join(notes)
    return Diagnosis(
        job=spec.job,
        error_class=err_class or "unknown",
        error_text=error_text,
        source_hint=hint,
        affected=tuple(affected),
        child_builds=tuple(failing),
        source="child-console",
        confidence="high" if err_class else "low",
    )
