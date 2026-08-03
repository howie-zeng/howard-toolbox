# claude-code-routines/jenkins_monitor/cli.py
"""Three thin subcommands. All judgment lives in JENKINS_MONITOR_PROMPT.md.

`facts`          - the morning fact sheet: cached registry data plus freshly fetched build
                   history, as readable markdown on stdout and JSON on disk.
`console`        - print a build's console text so the agent can read a traceback.
`save-verdicts`  - persist the agent's verdicts so tomorrow's run has a memory.

Nothing here decides whether a job is broken, reads a traceback, or chooses what to report.
The only computation is factual and non-obvious: skipping NOT_BUILT seed builds to find the
last build that really ran, and parsing child build results out of a wrapper's console.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import re
import sys
from pathlib import Path

from . import client, registry, statediff
from .models import BuildInfo, JobSpec

#: How an orchestrator's wrapper console reports each child build. Parsing this is factual,
#: and it is the only way the child failures are visible at all: the wrapper reports one flat
#: FAILURE while its children split pass/fail.
_CHILD_RESULT = re.compile(r"Build (?P<job>[\w.-]+) #(?P<num>\d+) completed: (?P<result>[A-Z_]+)")

DEFAULT_TAIL = 400


# --------------------------------------------------------------------------- facts helpers


def last_real_build(builds: list[BuildInfo]) -> BuildInfo | None:
    """Newest build that actually did work, skipping NOT_BUILT seed refreshes.

    This stays in code because it is the one thing that silently masks staleness: a push to
    the JenkinsJobs repo re-runs every pipeline with REFRESH=true, and those builds finish
    NOT_BUILT having done nothing. One job's `lastBuild` looked 4 hours old while its last
    real build was 27 days old.
    """
    for b in builds:
        if b.did_work:
            return b
    return None


def consecutive_failing_real_builds(builds: list[BuildInfo]) -> int:
    """How many real builds in a row, newest-first, ended non-SUCCESS."""
    count = 0
    for b in builds:
        if not b.did_work:
            continue
        if b.result == "SUCCESS":
            break
        count += 1
    return count


def child_results(text: str) -> dict[int, str]:
    """Map child build number -> result from an orchestrator's console."""
    return {int(m.group("num")): m.group("result") for m in _CHILD_RESULT.finditer(text)}


def _fmt_age(delta: dt.timedelta) -> str:
    total = int(delta.total_seconds())
    sign = "-" if total < 0 else ""
    days, rem = divmod(abs(total), 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{sign}{days}d {hours}h"
    if hours:
        return f"{sign}{hours}h {minutes}m"
    return f"{sign}{minutes}m"


def _build_dict(b: BuildInfo | None, now: dt.datetime) -> dict | None:
    if b is None:
        return None
    age = None if b.timestamp is None else now - b.timestamp
    return {
        "number": b.number,
        "result": b.result,
        "building": b.building,
        "timestamp": b.timestamp.isoformat() if b.timestamp else None,
        "age": _fmt_age(age) if age is not None else None,
        "age_hours": round(age.total_seconds() / 3600, 2) if age is not None else None,
        "did_work": b.did_work,
        # Flagged rather than hidden: a NOT_BUILT latest build is neither a failure nor
        # evidence the job ran, and conflating it with either was a real bug in both
        # directions (about six false alarms per push day, or masked staleness).
        "not_built_seed_run": b.result == "NOT_BUILT",
    }


def _stamp_dict(b: BuildInfo | None, now: dt.datetime) -> dict | None:
    """Number + age only: the bulk blob carries no result for these two pointers."""
    if b is None:
        return None
    age = None if b.timestamp is None else now - b.timestamp
    return {
        "number": b.number,
        "timestamp": b.timestamp.isoformat() if b.timestamp else None,
        "age": _fmt_age(age) if age is not None else None,
        "age_hours": round(age.total_seconds() / 3600, 2) if age is not None else None,
    }


def _spec_facts(spec: JobSpec, yesterday_verdict: str | None) -> dict:
    """The registry half of a job's facts: cached data, no network involved."""
    return {
        "job": spec.job,
        "tier": spec.tier,
        "family": spec.family,
        "trigger_type": spec.trigger_type,
        "cron": spec.cron,
        "tz": spec.tz,
        "upstream": spec.upstream,
        "grace_hours": spec.grace_hours,
        "max_silence_days": spec.max_silence_days,
        "unstable_is_failure": spec.unstable_is_failure,
        "success_markers": list(spec.success_markers),
        "console_informative": spec.console_informative,
        "nas_log_glob": spec.nas_log_glob,
        "orchestrator": spec.orchestrator,
        "child_job": spec.child_job,
        "entrypoint": spec.entrypoint,
        "repo": spec.repo,
        "yesterday_verdict": yesterday_verdict,
        "latest_build": None,
        "last_real_build": None,
        "last_success": None,
        "last_failure": None,
        "consecutive_failing_real_builds": None,
        "child_builds": None,
        "fetch_error": None,
    }


def _orchestrator_children(api, spec: JobSpec, build_number: int) -> tuple[list[dict] | None, str | None]:
    """Child build numbers and results from the wrapper's console, or an error string."""
    try:
        console_text = api.console(spec.job, build_number)
    except Exception as exc:  # noqa: BLE001 - one unreadable wrapper console must not lose the sheet
        return None, f"could not read orchestrator console for #{build_number}: {exc}"
    results = child_results(console_text)
    if not results:
        return [], f"#{build_number} failed but its console names no child builds of {spec.child_job}"
    return [{"number": n, "result": results[n]} for n in sorted(results)], None


def _collect_job_facts(api, spec: JobSpec, blob: dict | None, now: dt.datetime, yesterday: str | None) -> dict:
    facts = _spec_facts(spec, yesterday)

    if blob is None:
        # NOT "no builds". A job the bulk call did not return is an unknown, and an unknown
        # that reads as an absence of failures is the false healthy verdict this tool exists
        # to prevent.
        facts["fetch_error"] = "job not present in the controller's job list"
        return facts

    facts["latest_build"] = _build_dict(client.build_from_blob(blob.get("lastBuild")), now)
    facts["last_success"] = _stamp_dict(client.build_from_blob(blob.get("lastSuccessfulBuild")), now)
    facts["last_failure"] = _stamp_dict(client.build_from_blob(blob.get("lastFailedBuild")), now)

    try:
        builds = api.recent_builds(spec.job)
    except client.JenkinsUnreachable as exc:
        # NOT `builds = []`. An empty build list is indistinguishable from "this job has only
        # seed builds", which previously produced a false healthy verdict and then persisted
        # into the snapshot to fabricate a recovery the next day.
        facts["fetch_error"] = f"could not read build history: {exc}"
        return facts

    real = last_real_build(builds)
    facts["last_real_build"] = _build_dict(real, now)
    facts["consecutive_failing_real_builds"] = consecutive_failing_real_builds(builds)

    if spec.orchestrator and spec.child_job and real is not None and real.result not in (None, "SUCCESS"):
        children, err = _orchestrator_children(api, spec, real.number)
        facts["child_builds"] = children
        if err:
            facts["fetch_error"] = err
    return facts


# --------------------------------------------------------------------------- facts render


def _fmt_build(label: str, d: dict | None) -> str:
    if d is None:
        return f"- {label}: none recorded"
    bits = [f"#{d['number']}", d.get("result") or ("BUILDING" if d.get("building") else "no result")]
    if d.get("timestamp"):
        bits.append(f"at {d['timestamp']}")
    if d.get("age"):
        bits.append(f"(age {d['age']})")
    line = f"- {label}: " + " ".join(bits)
    if d.get("not_built_seed_run"):
        line += "  [NOT_BUILT seed run - did no work; not a failure and not evidence the job ran]"
    return line


def _fmt_stamp(label: str, d: dict | None) -> str:
    if d is None:
        return f"{label}: none"
    return f"{label}: #{d['number']} (age {d['age']})"


def _render_job(f: dict, access_gap: str | None = None) -> list[str]:
    out = [f"#### {f['job']}  [tier: {f['tier']}, family: {f['family']}]"]

    trigger = [f"- trigger_type: {f['trigger_type']}"]
    if f["cron"]:
        trigger.append(f'declared cron: "{f["cron"]}"  tz: {f["tz"]}  grace_hours: {f["grace_hours"]:g}')
    if f["upstream"]:
        trigger.append(f"upstream parent: {f['upstream']}")
    out.append("  ".join(trigger))

    if f["fetch_error"]:
        # Restated per job even under a fleet-wide gap. A reader scanning one job's block must
        # not be able to mistake empty fields for "nothing wrong here".
        detail = "see the access gap above" if f["fetch_error"] == access_gap else f["fetch_error"]
        out.append(f"- **FETCH ERROR ({detail}) -- this job's status is UNKNOWN today, not healthy.**")

    out.append(_fmt_build("last_real_build", f["last_real_build"]))
    out.append(_fmt_build("latest_build", f["latest_build"]))
    out.append(f"- {_fmt_stamp('last_success', f['last_success'])}  {_fmt_stamp('last_failure', f['last_failure'])}")
    fails = f["consecutive_failing_real_builds"]
    out.append(f"- consecutive_failing_real_builds: {fails if fails is not None else 'unknown (not fetched)'}")
    out.append(f"- yesterday_verdict: {f['yesterday_verdict'] if f['yesterday_verdict'] else 'none'}")

    reg = [
        f"max_silence_days: {f['max_silence_days'] if f['max_silence_days'] is not None else 'none'}",
        f"unstable_is_failure: {str(f['unstable_is_failure']).lower()}",
        f"console_informative: {str(f['console_informative']).lower()}",
    ]
    out.append("- " + "  ".join(reg))
    if f["nas_log_glob"]:
        out.append(f"- nas_log_glob: {f['nas_log_glob']}")
    if f["success_markers"]:
        out.append(f"- success_markers: {', '.join(f['success_markers'])}")
    if f["orchestrator"]:
        out.append(f"- orchestrator: true  child_job: {f['child_job']}")
    if f["child_builds"] is not None:
        if f["child_builds"]:
            listed = ", ".join(f"#{c['number']} {c['result']}" for c in f["child_builds"])
            out.append(f"- child_builds (from the wrapper console): {listed}")
        else:
            out.append("- child_builds: none found in the wrapper console")
    out.append("")
    return out


def _render_facts(payload: dict) -> str:
    out = ["### Jenkins Job Monitor - fact sheet", ""]
    out.append(f"- Generated: {payload['generated_at']} (UTC). Facts JSON: `{payload['facts_json']}`")
    out.append(
        f"- Scope: {payload['job_count']} jobs "
        f"({payload['fix_count']} fix tier, {payload['notify_count']} notify-only). "
        f"Registry: `{payload['registry']}`"
    )

    snap = payload["prior_snapshot"]
    if snap["available"]:
        out.append(
            f"- Prior snapshot: `{snap['path']}` ({snap['date']}). "
            "The `yesterday_verdict` on each job below comes from it, so new / unresolved / "
            "recovered comparisons are meaningful this run."
        )
    else:
        out.append(
            "- **Prior snapshot: NONE FOUND.** No earlier run left verdicts on disk, so "
            "yesterday-comparisons are UNAVAILABLE this run: every `yesterday_verdict` below is "
            "null, every finding will look new, and no recovery can be detected at all. Say so "
            "in the report rather than presenting the labels as if they were meaningful."
        )

    if payload["access_gap"]:
        out += [
            "",
            f"- **ACCESS GAP: Jenkins could not be read at all. {payload['access_gap']}**",
            "- Nothing below is a statement that these jobs are healthy. This is an access or "
            "infrastructure gap and must be reported as one.",
            "- If a credential is missing or expired: mint a token at "
            "`http://jenkins.libremax.com/me/security/` and set `JENKINS_USER` / "
            "`JENKINS_API_TOKEN` at Windows **User** scope.",
        ]

    errored = [f["job"] for f in payload["jobs"] if f["fetch_error"]]
    if errored and not payload["access_gap"]:
        out.append(
            f"- **{len(errored)} job(s) could not be fetched (status UNKNOWN, not healthy):** {', '.join(errored)}"
        )

    out += [
        "",
        "Judgment rules: `claude-code-routines/JENKINS_MONITOR_PROMPT.md`. Read them before concluding anything.",
        "",
    ]
    for f in payload["jobs"]:
        out += _render_job(f, payload["access_gap"])
    return "\n".join(out)


# --------------------------------------------------------------------------- subcommands


def _registry_path(arg: str | None) -> Path:
    return Path(arg) if arg else Path(__file__).parent.parent / "jenkins-jobs.yaml"


def _load_specs(arg: str | None) -> dict[str, JobSpec] | None:
    try:
        return registry.load_registry(_registry_path(arg))
    except registry.RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return None


def cmd_facts(args) -> int:
    specs = _load_specs(args.registry)
    if specs is None:
        return 2

    outputs = Path(args.outputs)
    # Non-fatal: the outputs directory lives on a NAS share, and being unable to create it
    # must cost at most the persisted JSON, never the fact sheet the caller reads from stdout.
    with contextlib.suppress(OSError):
        outputs.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.UTC)
    stamp = now.astimezone().strftime("%Y%m%d")

    prev_path = statediff.latest_snapshot_path(outputs, before=stamp)
    previous = statediff.load_snapshot(prev_path) if prev_path else {}
    # latest_snapshot_path only returns names matching jenkins-status-<8 digits>.json.
    prev_stamp = prev_path.stem.rsplit("-", 1)[1] if prev_path else ""

    facts_json = outputs / f"jenkins-facts-{stamp}.json"
    fix_count = sum(1 for s in specs.values() if s.tier == "fix")
    payload = {
        "generated_at": now.isoformat(),
        "registry": str(_registry_path(args.registry)),
        "facts_json": str(facts_json),
        "job_count": len(specs),
        "fix_count": fix_count,
        "notify_count": len(specs) - fix_count,
        "prior_snapshot": {
            # `available` is keyed on actually having loaded verdicts, not merely on a file
            # existing: an unreadable or empty snapshot leaves the comparison just as
            # unavailable, and saying otherwise would present meaningless labels as real.
            "available": bool(previous),
            "path": str(prev_path) if prev_path else None,
            "date": prev_stamp or None,
        },
        "access_gap": None,
        "jobs": [],
    }

    api = None
    blobs: dict[str, dict] = {}
    try:
        api = client.from_env()
        blobs = api.all_jobs()
    except (client.AuthMissing, client.JenkinsUnreachable) as exc:
        # Both land here, and the cause is threaded through verbatim: hardcoded wording once
        # claimed "no credentials in the environment" during a controller outage - a wrong
        # diagnosis stated with full confidence.
        payload["access_gap"] = str(exc)

    for name, spec in specs.items():
        if payload["access_gap"]:
            facts = _spec_facts(spec, previous.get(name))
            facts["fetch_error"] = payload["access_gap"]
        else:
            facts = _collect_job_facts(api, spec, blobs.get(name), now, previous.get(name))
        payload["jobs"].append(facts)

    text = _render_facts(payload)
    # Printed BEFORE persisting. The outputs directory lives on a NAS share, so an OSError
    # here would otherwise cost the caller the whole fact sheet it consumes from stdout.
    print(text)
    try:
        facts_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"\n**WARNING: could not write `{facts_json}` ({exc}).** The fact sheet above is complete.")
    return 0


def cmd_console(args) -> int:
    try:
        api = client.from_env()
        text = api.console(args.job, args.build)
    except client.AuthMissing as exc:
        print(f"**ACCESS GAP: {exc}** No console could be read; this is not an absence of errors.")
        return 0
    except client.JenkinsUnreachable as exc:
        print(f"**ERROR: could not read console for {args.job} #{args.build}: {exc}**")
        print("Report this as an access gap. It is not evidence the build had no errors.")
        return 1

    lines = text.splitlines()
    if args.tail > 0 and len(lines) > args.tail:
        print(f"[showing the last {args.tail} of {len(lines)} lines; use --tail 0 for all]")
        lines = lines[-args.tail :]
    print("\n".join(lines))
    return 0


def cmd_save_verdicts(args) -> int:
    specs = _load_specs(args.registry)
    if specs is None:
        return 2

    try:
        raw = sys.stdin.read() if args.json == "-" else Path(args.json).read_text(encoding="utf-8")
    except OSError as exc:
        # Reported, not raised. A traceback out of the unattended daily path is indistinguishable
        # from the tool being broken, and the caller must be told the memory was NOT written.
        print(f"could not read the verdict file: {exc}", file=sys.stderr)
        return 2
    try:
        verdicts = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"malformed verdict JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(verdicts, dict):
        print(
            f"malformed verdict JSON: expected an object of job -> state, got {type(verdicts).__name__}",
            file=sys.stderr,
        )
        return 2

    # An unknown job is rejected rather than written. A typo'd key would sit in the snapshot
    # forever as a verdict for a job that does not exist, while the real job silently kept a
    # null `yesterday_verdict` - i.e. the memory would look present and be absent.
    unknown = sorted(k for k in verdicts if k not in specs)
    if unknown:
        print(
            f"malformed verdict JSON: {len(unknown)} job(s) are not in the registry: {', '.join(unknown)}",
            file=sys.stderr,
        )
        return 2

    outputs = Path(args.outputs)
    outputs.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).astimezone().strftime("%Y%m%d")
    path = outputs / f"jenkins-status-{stamp}.json"
    statediff.save_snapshot(verdicts, path)
    print(f"wrote {len(verdicts)} verdict(s) to {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # This CLI is the process boundary for stdout. sys.stdout.encoding is cp1252 in the
    # production environment; a single non-ASCII character in the output would otherwise
    # crash print() with nothing emitted at all. Guarded because not every stdout
    # replacement (some test/capture shims) supports reconfigure().
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # --registry is a shared parent option rather than a top-level one so it can be passed
    # after the subcommand, which is where a caller naturally puts it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry", default=None, help="path to jenkins-jobs.yaml")

    ap = argparse.ArgumentParser(prog="jenkins_monitor")
    sub = ap.add_subparsers(dest="command", required=True)

    p_facts = sub.add_parser("facts", parents=[common], help="print the morning fact sheet and write it as JSON")
    p_facts.add_argument("--outputs", required=True, help="directory for the facts JSON and snapshots")
    p_facts.set_defaults(func=cmd_facts)

    # No --registry: a wrapper's child job is deliberately NOT a registry entry, and the
    # agent must be able to read a child console to find the traceback the wrapper lacks.
    p_console = sub.add_parser("console", help="print a build's console text")
    p_console.add_argument("job")
    p_console.add_argument("build", type=int)
    p_console.add_argument("--tail", type=int, default=DEFAULT_TAIL, help="last N lines; 0 for all")
    p_console.set_defaults(func=cmd_console)

    p_save = sub.add_parser(
        "save-verdicts", parents=[common], help="persist today's verdicts for tomorrow's comparison"
    )
    p_save.add_argument("--outputs", required=True, help="directory for the snapshot")
    p_save.add_argument("--json", required=True, help="path to a {job: state} JSON file, or - for stdin")
    p_save.set_defaults(func=cmd_save_verdicts)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
