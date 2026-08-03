# claude-code-routines/jenkins_monitor/cli.py
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import sys
from dataclasses import replace
from pathlib import Path

from . import classify, client, diagnose, registry, report, statediff
from .cadence import CadenceError
from .models import FIXABLE_STATES, JobStatus, State

#: How many findings may be NOMINATED for a fix agent in one run. This is a limit on
#: agent dispatch (an agent storm is expensive and agents can conflict), NOT on
#: diagnosis: reading a console is a cheap read-only GET, so every eligible finding is
#: diagnosed regardless of this cap.
MAX_FIX_SLOTS = 3

#: Transitions worth diagnosing. ONGOING is included: a job red for three days used to
#: carry a diagnosis on day 1 only, so the digest degraded to a bare state line exactly
#: as the problem got older.
DIAGNOSED_TRANSITIONS = ("NEW", "ONGOING")


def _make_client():
    return client.from_env()


def _upstream_real_ts(name, specs, blobs, cache, api):
    """Timestamp of the upstream job's last real build, for upstream staleness."""
    if name in cache:
        return cache[name]
    ts = None
    if name in blobs:
        try:
            real = classify.last_real_build(api.recent_builds(name))
            ts = real.timestamp if real else None
        except Exception:  # noqa: BLE001 - upstream is advisory only
            ts = None
    cache[name] = ts
    return ts


def _persist(path: Path, write, what: str) -> str | None:
    """Run a write, returning a stdout-worthy warning instead of aborting the run.

    The outputs directory lives on a NAS share: a read-only or full volume raises OSError
    long after all jobs were classified and the red ones diagnosed. Losing the report over
    that is the worst possible trade, since the daily routine consumes stdout - so the
    report is printed BEFORE anything is persisted, and a persistence failure is reported
    as a line of output rather than as a traceback and a non-zero exit.
    """
    try:
        write()
    except OSError as exc:
        return (
            f"\n**WARNING: could not write the {what} to `{path}` ({exc}).** The report above is "
            "complete, but this run was not persisted: tomorrow's NEW / ONGOING / RECOVERED labels "
            "will be computed against an older snapshot (or none), so today's findings may be "
            "relabelled NEW tomorrow and a recovery may go undetected."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    # This CLI is the process boundary for stdout. sys.stdout.encoding is cp1252 in the
    # production environment; a non-ASCII character anywhere in a rendered report would
    # otherwise crash print() with no report emitted at all. Guarded because not every
    # stdout replacement (some test/capture shims) supports reconfigure().
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(prog="jenkins_monitor")
    ap.add_argument("--outputs", required=True, help="directory for snapshot + report")
    ap.add_argument("--registry", default=None, help="path to jenkins-jobs.yaml")
    ap.add_argument("--no-diagnose", action="store_true", help="skip console fetching")
    args = ap.parse_args(argv)

    outputs = Path(args.outputs)
    outputs.mkdir(parents=True, exist_ok=True)
    reg_path = Path(args.registry) if args.registry else Path(__file__).parent.parent / "jenkins-jobs.yaml"

    try:
        specs = registry.load_registry(reg_path)
    except registry.RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 2

    # Computed once from the live registry so the report's scope line can never go
    # stale relative to specs - it is recomputed every run, never hardcoded.
    fix_count = sum(1 for s in specs.values() if s.tier == "fix")
    notify_count = len(specs) - fix_count

    now = dt.datetime.now(dt.UTC)
    stamp = now.astimezone().strftime("%Y%m%d")
    report_path = outputs / f"jenkins-monitor-{stamp}.md"

    def _emit_unreachable(exc: Exception) -> int:
        # `reason` is threaded into the rendered text so the persisted .md states the
        # ACTUAL cause. Both a missing credential and a controller outage land here, and
        # the old fixed wording claimed "No Jenkins API credentials in the environment"
        # during an outage.
        text = report.render(
            [],
            token_ok=False,
            total_jobs=len(specs),
            fix_count=fix_count,
            notify_count=notify_count,
            reason=str(exc),
        )
        print(text)
        warning = _persist(report_path, lambda: report_path.write_text(text, encoding="utf-8"), "report file")
        if warning:
            print(warning)
        return 0

    try:
        api = _make_client()
    except client.AuthMissing as exc:
        return _emit_unreachable(exc)

    try:
        blobs = api.all_jobs()
    except client.JenkinsUnreachable as exc:
        return _emit_unreachable(exc)

    statuses: list[JobStatus] = []
    cache: dict[str, dt.datetime | None] = {}
    for name, spec in specs.items():
        blob = blobs.get(name)
        if blob is None:
            statuses.append(JobStatus(job=name, state=State.UNREACHABLE, detail="not found on controller"))
            continue
        try:
            builds = api.recent_builds(name)
        except client.JenkinsUnreachable as exc:
            # NOT `builds = []`. An empty build list is indistinguishable from "this job
            # has only seed builds", which classified a genuinely red manual-trigger job as
            # GREEN and every other job as NEVER_DID_WORK - the latter then persisted into
            # the snapshot and fabricated a RECOVERED the next day for a job that never
            # broke. A failed read is an unknown state and must be reported as one.
            statuses.append(JobStatus(job=name, state=State.UNREACHABLE, detail=f"could not read build history: {exc}"))
            continue
        up_ts = (
            _upstream_real_ts(spec.upstream, specs, blobs, cache, api)
            if spec.trigger_type == "upstream" and spec.upstream
            else None
        )
        try:
            statuses.append(classify.classify_job(spec, blob, builds, now, upstream_real_ts=up_ts))
        except CadenceError as exc:
            # classify_job deliberately lets a malformed cadence propagate - correct for a
            # pure classifier, since a bad registry entry is a config bug. But this CLI is
            # the unattended daily entry point: one bad entry must degrade to a single
            # isolated finding, not take down the report for the other jobs.
            statuses.append(JobStatus(job=name, state=State.UNREACHABLE, detail=f"cadence error: {exc}"))

    prev_path = statediff.latest_snapshot_path(outputs, before=stamp)
    previous = statediff.load_snapshot(prev_path) if prev_path else {}
    findings = statediff.label(statuses, previous)

    capped: list[str] = []
    if not args.no_diagnose:
        eligible = [
            f
            for f in findings
            if f.transition in DIAGNOSED_TRANSITIONS
            and f.status.state in FIXABLE_STATES
            and specs[f.status.job].tier == "fix"
        ]
        eligible.sort(key=lambda f: -f.status.consecutive_failures)
        # ALL eligible findings are diagnosed - console fetching is a read-only GET and
        # carries none of the cost that motivates the fix-slot cap.
        diagnoses = {f.status.job: diagnose.diagnose_job(api, specs[f.status.job], f.status) for f in eligible}
        # dataclasses.replace, not a hand-built Finding: reconstructing by hand silently
        # dropped Finding.notes, and would drop any field added later.
        findings = [replace(f, diagnosis=diagnoses[f.status.job]) if f.status.job in diagnoses else f for f in findings]
        capped = [f.status.job for f in eligible[MAX_FIX_SLOTS:]]

    text = report.render(
        findings,
        token_ok=True,
        total_jobs=len(specs),
        fix_count=fix_count,
        notify_count=notify_count,
        capped=capped,
        prior_snapshot_available=bool(previous),
    )

    # Print BEFORE persisting, and report a persistence failure instead of raising. The
    # snapshot used to be written first, so an OSError between the two writes committed
    # today's states while losing today's report - and tomorrow relabelled today's NEW
    # reds as ONGOING with nobody ever having seen them.
    print(text)
    snapshot_path = outputs / f"jenkins-status-{stamp}.json"
    for warning in (
        _persist(report_path, lambda: report_path.write_text(text, encoding="utf-8"), "report file"),
        _persist(snapshot_path, lambda: statediff.save_snapshot(statuses, snapshot_path), "state snapshot"),
    ):
        if warning:
            print(warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
