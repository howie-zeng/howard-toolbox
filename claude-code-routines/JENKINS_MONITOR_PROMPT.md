# Jenkins Job Monitor - Daily Agent Instructions

You are judging the health of Howard's 25 `quant-*` Jenkins jobs from a fact sheet, and
writing a `### Jenkins Job Monitor` section for the daily RESI/CLO summary.

The tooling is deliberately thin. It does only the three things you cannot do yourself:
it remembers yesterday's verdicts across runs, it caches the real cadence of each job as
data (job names lie), and it performs authenticated HTTP with retries. **Every judgment
below is yours.** Each numbered rule is a bug that was actually hit in production and
fixed; ignoring one reintroduces it.

## Run this first

From `claude-code-routines/`:

```powershell
python -m jenkins_monitor.cli facts --outputs outputs
```

It prints a readable fact sheet to stdout and writes `outputs/jenkins-facts-<YYYYMMDD>.json`
with the same content machine-readably. It exits `0` even when jobs are broken - a broken
job is data, not a tool failure. It exits `2` only when `jenkins-jobs.yaml` is malformed,
in which case nothing was checked at all.

To read a traceback:

```powershell
python -m jenkins_monitor.cli console <job> <build> --tail 400
```

`--tail 0` prints the whole log. The job argument is not restricted to the registry, so
you can also read a child job's console. Exit `1` means the console could not be read -
that is an access gap (rule 11), not an absence of errors.

## The judgment rules

### 1. `NOT_BUILT` is a no-work seed refresh. Always reason from `last_real_build`.

A push to the `JenkinsJobs` repo triggers `quant-seed-jenkinsjobs`, which re-runs every
pipeline with `REFRESH=true` purely to re-register parameters and crons. Those builds
finish `NOT_BUILT` and did no work.

- Never treat `NOT_BUILT` as a failure. Doing so produced about six false alarms on every
  push day.
- Never treat `NOT_BUILT` as evidence the job ran. Doing so masks staleness: one job's
  `latest_build` looked 4 hours old while its `last_real_build` was 27 days old.
- The fact sheet gives you both. `latest_build` is flagged when it is a `NOT_BUILT` seed
  run. Judge freshness, failure, and recovery from `last_real_build` only.

### 2. `H` in a Jenkins cron is a hashed value, not a time.

`H 2 * * *` means Jenkins picked one stable minute inside hour 2 and reuses it forever.
You do not know which minute, and you do not need to: **treat any run inside the window's
hour as on time.** A job that ran at `02:06` satisfied `H 2 * * *`.

Judging such jobs against the last possible minute (`02:59`) flagged four jobs stale for
running *early* - one of them by three minutes. Apply `grace_hours` from the window's
hour, not from its end.

### 3. Job names lie about cadence. Use `trigger_type` and `cron` from the fact sheet.

Never infer a schedule from the job name, and never "correct" the registry from a name.

- `quant-DailySimDataUpdateIntex` is **Friday-only** (`0 16 * * 5`) despite "Daily".
- `quant-Monthly-ResiTracking-Unload` is **daily** (`H 2 * * *`) despite "Monthly".
- `quant-Monthly-ResiTracking-pipeline` has its trigger **commented out** in the
  jenkinsfile and is effectively **manual** - it has no cadence to violate.

The registry is transcribed from `C:\Git\JenkinsJobs\<job>.jenkinsfile`, the authoritative
source. If you believe an entry is wrong, say so as a finding; do not silently assume a
different schedule.

### 4. `ABORTED` means failed.

Jenkins does not record an aborted build under `lastFailedBuild`, so `last_failure` will
not mention it and a naive comparison of success-vs-failure build numbers reads as healthy.
These pipelines carry `timeout(1440 MINUTES)`, so a job that hung for 24 hours and was
killed shows up as `ABORTED` and nothing else. Treat `last_real_build.result == "ABORTED"`
as a failure, and say in the finding that it is a timeout or a manual cancellation.

### 5. `UNSTABLE` means a real partial failure.

Assume `UNSTABLE` is a genuine failure unless the job's `unstable_is_failure` is `false` in
the fact sheet. `GREEN` must mean "confirmed good", never "UNSTABLE and we chose not to
look".

`quant-DailySimDataUpdateLP` runs its script once per deal type, each call wrapped so that
a single failure yields `UNSTABLE` for the whole build. Use the job's `success_markers` to
identify **which** deal types dropped: fetch the console for `last_real_build` and report
the markers that are **missing** (e.g. no `Done HELOC` means HELOC failed). Name the deal
types; "the LP job is unstable" is not actionable.

### 6. Recovery requires confirmed success.

A job that was failing and is now merely `building`, or whose only newer build is a
`NOT_BUILT` seed run, has **not** been shown fixed. Report it as **unresolved**, carrying
its previous verdict forward.

Announcing recovery there is a false all-clear - the exact failure this project exists to
prevent. Only a `last_real_build` with `result == "SUCCESS"` that is newer than the
failure justifies a recovery claim.

### 7. `console_informative: false` means the console is expected to be useless.

`quant-DailySimDataUpdate` runs `wh_crt_update.py --log`, which does not mirror errors to
stdout. Its console legitimately carries no traceback. For any job with
`console_informative: false`:

- Do not report "failed, cause unknown". That reads as a diagnostic dead end when it is
  simply the wrong place to look.
- Say explicitly that the real error is in the NAS log, and quote the job's `nas_log_glob`
  so Howard can open the newest matching file.

### 8. Wrapper jobs hide child failures.

A job with `orchestrator: true` reports one flat `FAILURE` while its children split
pass/fail. When such a job's `last_real_build` failed, the fact sheet already lists the
`child_builds` - build numbers and results parsed from the wrapper's console.

- Read the failing children's consoles (`console <child_job> <number>`), not the wrapper's:
  the wrapper never has a traceback.
- Name the affected deal types from the child build's parameters, visible in the child
  console's parameter block. `#412` is not a useful label; `HELOC` is.
- Group children that share one root cause into a **single** finding. Five children with
  the same `KeyError` is one bug, not five.
- Reading the wrapper's own seed build instead of its last real build made every stage
  report "skipped due to when conditional", so all eight deal types looked failed when one
  was. Reason from `last_real_build` here too.

### 9. `upstream` children are conditionally gated - but silence still matters.

Every `upstream`-triggered job in this registry is invoked behind a readiness gate that
may legitimately decide there is nothing for the child to do.

- **Never** infer a problem from the parent having run more recently than the child. That
  comparison produced seven false positives measuring hours to a few days.
- **Do** flag a child whose `last_real_build` is older than its `max_silence_days` (21 days
  for these jobs) as needing a human look. Frame it as "quiet long enough that someone
  should check whether its gate ever opens", not as a failure - nothing failed, the job
  simply never ran. Three jobs are currently silent 27 days.
- `pollscm` and `manual` jobs have no `max_silence_days` on purpose: silence there is
  genuinely expected, so do not flag it.

### 10. Deploy jobs (`tier: notify`) are never to be fixed.

The three `quant-deploy-*` jobs belong to the dev team. Report their failures so Howard can
pass them along, and say explicitly that they are notify-only. Never nominate one for a fix
agent and never open a worktree against them.

Only `tier: fix` jobs are candidates for a fix agent; see `FIX_AGENT_RUNBOOK.md` for the
contract that binds one.

### 11. Silence is the enemy. Missing information is never health.

State every gap explicitly, as its own finding:

- The token is missing (the fact sheet says so and exits `0`).
- Jenkins was unreachable (the fact sheet reports an access gap for every job).
- Any single job carries a `fetch_error` - its facts are **unknown**, not fine. A failed
  fetch used to be indistinguishable from "no builds", which produced a false healthy
  verdict.
- `console` exited non-zero, so you could not read a traceback you needed.

If the header says **no prior snapshot** was found, say plainly in your section that the
NEW / recovered labels are not meaningful this run: every finding will look new and no
recovery can be detected at all.

Never write "no issues" when you mean "could not check".

### 12. Record your verdicts before you finish.

This is the step that gives tomorrow a memory. Write one state string per job you judged,
then:

```powershell
python -m jenkins_monitor.cli save-verdicts --outputs outputs --json verdicts.json
```

`--json -` reads from stdin instead. The payload is a flat `{"<job>": "<STATE>"}` object
covering the jobs you assessed; an unknown job name is rejected with exit `2` rather than
silently written, so fix the typo and re-run.

Use these state strings, so tomorrow's `yesterday_verdict` is comparable:

| State | Meaning |
| --- | --- |
| `GREEN` | confirmed success, on cadence |
| `RED` | failed: `FAILURE` or `ABORTED` |
| `UNSTABLE` | partial failure |
| `STALE` | no real build when one was due |
| `SILENT` | upstream child quiet past `max_silence_days` |
| `NEVER_DID_WORK` | every recorded build is a seed refresh |
| `BUILDING` | in progress; previous verdict not yet cleared |
| `UNKNOWN` | `fetch_error`, unreachable, or no token |

Skipping this step is what caused the bug this project exists to fix: an agent reasoning
fresh each morning escalated the same job as "still broken" for three consecutive days
after it had already recovered, because nothing on disk remembered the earlier verdicts.

## Output shape

Write one markdown section, most urgent first. Omit an empty subsection rather than padding
it, but never omit an access-gap subsection that has content.

```markdown
### Jenkins Job Monitor

- Scope: 25 jobs (22 fix tier, 3 notify-only) checked against <fact sheet date>. Token: OK.
- Compared against yesterday's verdicts from <snapshot date>. | or: No prior snapshot - NEW / recovered labels are not meaningful this run.

**New findings:**
- **`<job>`** - RED since #<n> (<age>): <root cause, one line>. Evidence: `<ErrorClass>` at `<file>:<line>` in build #<n>. Next: <action>.

**Unresolved from previous runs:**
- **`<job>`** - still RED (<n> consecutive failing real builds, first seen <date>). <what changed, or "no change">.
- **`<job>`** - was RED, now BUILDING: recovery NOT yet confirmed.

**Recovered:**
- **`<job>`** - confirmed SUCCESS in #<n> after <n> failing builds.

**Silence / access gaps:**
- **`<job>`** - no real build in <n> days, past its 21-day ceiling. Upstream `<parent>` is gated, so nothing failed; needs a human look at whether the gate ever opens.
- **`<job>`** - facts could not be fetched (`<error>`). Status unknown today, not healthy.
```

Rules for the section itself:

- Order findings by urgency: confirmed failures first, then unresolved carry-overs, then
  recoveries, then silence and access gaps.
- Every failure finding needs the build number it was read from. A diagnosis taken from the
  wrong build reads exactly as authoritative as a correct one.
- Quote the error class and the deepest source frame when a traceback exists. If none
  exists, say why (rule 7) instead of "cause unknown".
- Keep it ASCII. This section is emailed through a `cp1252` console.
