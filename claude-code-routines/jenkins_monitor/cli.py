# claude-code-routines/jenkins_monitor/cli.py
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import sys
from pathlib import Path

from . import classify, client, diagnose, registry, report, statediff
from .cadence import CadenceError
from .models import FIXABLE_STATES, JobStatus, State

MAX_FIX_SLOTS = 3


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

    try:
        api = _make_client()
    except client.AuthMissing as exc:
        text = report.render([], token_ok=False, total_jobs=len(specs), fix_count=fix_count, notify_count=notify_count)
        print(text)
        print(f"\n(reason: {exc})")
        (outputs / f"jenkins-monitor-{stamp}.md").write_text(text, encoding="utf-8")
        return 0

    try:
        blobs = api.all_jobs()
    except client.JenkinsUnreachable as exc:
        text = report.render([], token_ok=False, total_jobs=len(specs), fix_count=fix_count, notify_count=notify_count)
        print(text)
        print(f"\n(reason: {exc})")
        (outputs / f"jenkins-monitor-{stamp}.md").write_text(text, encoding="utf-8")
        return 0

    statuses: list[JobStatus] = []
    cache: dict[str, dt.datetime | None] = {}
    for name, spec in specs.items():
        blob = blobs.get(name)
        if blob is None:
            statuses.append(JobStatus(job=name, state=State.UNREACHABLE, detail="not found on controller"))
            continue
        try:
            builds = api.recent_builds(name)
        except client.JenkinsUnreachable:
            builds = []
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
            if f.transition == "NEW" and f.status.state in FIXABLE_STATES and specs[f.status.job].tier == "fix"
        ]
        eligible.sort(key=lambda f: -f.status.consecutive_failures)
        top = eligible[:MAX_FIX_SLOTS]
        enriched = []
        for f in findings:
            if f in top:
                d = diagnose.diagnose_job(api, specs[f.status.job], f.status)
                enriched.append(
                    type(f)(status=f.status, transition=f.transition, diagnosis=d, previous_state=f.previous_state)
                )
            else:
                enriched.append(f)
        findings = enriched
        capped = [f.status.job for f in eligible[MAX_FIX_SLOTS:]]

    statediff.save_snapshot(statuses, outputs / f"jenkins-status-{stamp}.json")
    text = report.render(
        findings,
        token_ok=True,
        total_jobs=len(specs),
        fix_count=fix_count,
        notify_count=notify_count,
        capped=capped,
    )
    (outputs / f"jenkins-monitor-{stamp}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
