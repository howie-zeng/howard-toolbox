# Jenkins Job Monitor + Auto-Fix Dispatcher — Design

**Date:** 2026-08-03
**Owner:** Howard Zeng (hzeng@libremax.com)
**Status:** Approved for implementation

## Problem

Howard owns the RESI tracking and flat-file generation pipelines — 26 `quant-*` Jenkins jobs.
Today he learns a job broke from qrprod notification emails, which has three structural
failures:

1. **Email cannot report recovery.** Jenkins mails UNSTABLE/FAILURE state-changes to the
   `/auto` report feed, but the recovering SUCCESS / "back to normal" goes to the
   `Jenkins Automation` folder, which is unreachable via COM in scheduled runs. On
   2026-08-01→08-03 this produced three consecutive daily summaries escalating
   `quant-DailySimDataUpdateLP #92` as "not confirmed recovered" when it had in fact
   recovered (`#93` succeeded). Absence of a recovery email is the *expected* state, not
   evidence of an ongoing break.
2. **Email cannot see a job that silently stopped running.** A job whose trigger breaks
   emits nothing at all. Flat-file consumers discover the gap before Howard does.
3. **Failure mail is not always addressed to Howard.** `quant-deploy-lmsimdata` routes
   failures to `tech@libremax.com`; it sat red for ~3 days unnoticed.

The Jenkins API is the only source that answers "is this job red *now*", "did it recover",
and "did it run at all". It requires authentication.

## Goals

- A durable registry of the 26 jobs with per-job cadence and failure semantics.
- Daily automated classification: GREEN / RED / UNSTABLE / STALE / NEVER-RAN / UNREACHABLE.
- Run-over-run state diffing so findings are labelled NEW / ongoing / recovered.
- For jobs Howard owns: automatic diagnosis and a candidate fix committed in an isolated
  git worktree, ready for his review.
- Folded into the existing 08:00 daily RESI/CLO summary — no new notification channel.

## Non-goals

- No auto-push, no auto-PR, no auto-merge. Fixes stop at a local commit.
- No auto-fix for deploy jobs (see Tiers).
- No sub-hourly alerting. Accepted latency: a 14:20 failure surfaces at 08:00 next day.

## Key discovery: job names do not imply cadence

Parsed from `C:\Git\JenkinsJobs\<job>.jenkinsfile` (the authoritative source — the repo
README states jobs must not be edited in the Jenkins UI).

| Job | Trigger | Reality vs name |
|---|---|---|
| `quant-DailySimDataUpdateIntex` | `cron TZ=NY 00 16 * * 5` | **Friday only**, not daily |
| `quant-Monthly-ResiTracking-Unload` | `cron TZ=NY H 2 * * *` | **Daily** 2am, not monthly |
| `quant-Monthly-ResiTracking-Tracking` | `cron TZ=NY H 23 * * 1-5` | **Weekdays** 11pm, not monthly |
| `quant-Monthly-ResiTracking-pipeline` | `// cron(...)` **commented out** | effectively manual |
| `quant-DailyCRTVectors` | none — upstream `quant-CRTDaily-Workflow` | not clock-driven |
| `quant-DailySimHistVectorUndialed` | none — upstream `…ResiTracking-Tracking` | not clock-driven |
| `quant-tracking-report-recache-workflow` | `cron 0 9 * * 0` (no TZ prefix) | weekly Sunday |

Consequence: staleness must come from a registry, never from the job name. A naive
"daily job, no build in 36h" rule would have produced false alarms on Intex and false
silence on the recache workflow.

## Job tiers

**Tier A — own + auto-fix (23 jobs).** Code lives in LMQR; Howard owns the failure.

`quant-DailySimDataUpdate`, `quant-DailySimDataUpdateDV01`, `quant-DailySimDataUpdateIntex`,
`quant-DailySimDataUpdateLP`, `quant-DailySimHistVector`, `quant-DailySimHistVectorUndialed`,
`quant-DailyCRTVectors`, `quant-generate-vectors`, `quant-WeekendCRTTrackingVectors`,
`quant-WeekendCRTVectors`, `quant-Monthly-ResiTracking-pipeline`,
`quant-Monthly-ResiTracking-Tracking`, `quant-Monthly-ResiTracking-Unload`,
`quant-Monthly-Tracking-Report`, `quant-Monthly-Tracking-Report-Undialed`,
`quant-tracking-report-recache-workflow`, `quant-PseudoDeal-Stats`,
`quant-PseudoDeal-Tracking`, `quant-PseudoDeal-Unload`, `quant-PseudoDeal-Update`,
`quant-RMBSLoader`, `quant-HECMCollateralReport`, `quant-dv01-figure-sync`

**Tier B — notify only (3 jobs).** Report so Howard can hand to the dev team; never patched.

`quant-deploy-lmqr`, `quant-deploy-lmsimdata`, `quant-deploy-Rcode`

Rationale: deploys are `pollSCM`-triggered git-pull/LFS operations against network shares
and Azure file shares. Failures are infra/credential problems, not model bugs, and
`deploy-lmsimdata` already notifies `tech@libremax.com`.

**Orchestrators within Tier A** (`quant-Monthly-ResiTracking-pipeline`,
`quant-tracking-report-recache-workflow`) are diagnosed but **never patched directly** —
they run no code of their own, so a fix belongs in the failing child. The diagnoser drills
into child builds and reports which child failed.

## Architecture

Five components, each independently testable.

```
jenkins-jobs.yaml  ──►  poller  ──►  state diff  ──►  diagnoser  ──►  fix dispatcher
   (registry)         (API read)    (vs yesterday)   (logs+console)    (worktree agents)
                                          │                                   │
                                          └──────────► daily summary ◄────────┘
```

### 1. Registry — `claude-code-routines/jenkins-jobs.yaml`

One entry per job. Generated once from the jenkinsfiles, maintained by hand thereafter.

```yaml
- job: quant-DailySimDataUpdateLP
  tier: fix                       # fix | notify
  family: simdata
  trigger_type: cron              # cron | pollscm | upstream | manual
  cron: "20 14 * * *"
  tz: America/New_York
  grace_hours: 6
  repo: LMQR
  entrypoint: agencydata/wh_lp_update.py
  agent_label: LMAX-NYAPP01
  unstable_is_failure: true
  success_markers:
    ["Done NQM", "Done Jumbo", "Done HELOC", "Done ALT_A", "Done Subprime",
     "Done NQM Pseudo", "Done Jumbo Pseudo", "Done HELOC Pseudo"]
  console_informative: true
  nas_log_glob: '\\libremax-nas\QR_Sanbox\QR\logs\crt_update\lp_update_*.log'
```

Fields that carry real weight:

- **`unstable_is_failure`** — `…UpdateLP` wraps each of 8 deal types in
  `catchError(buildResult: 'UNSTABLE')`. UNSTABLE therefore means *some deal types failed
  while others refreshed* — a genuine partial failure, not a warning. (`--fail_on_deal_error`,
  added by Howard's own LMQR PR #13207 / JenkinsJobs PR #482, is what makes it exit
  nonzero at all; these UNSTABLE builds are that flag working as designed.)
- **`success_markers`** — lets the diagnoser name *which* deal type dropped by finding the
  missing `Done <X>` echo, rather than reporting "UNSTABLE, cause unknown".
- **`console_informative: false`** — `wh_crt_update.py --log` does **not** mirror WARNING+
  to stdout, so the Jenkins console shows little beyond a nonzero exit. The real error is
  in `nas_log_glob`. Without this flag the diagnoser reports a useless "failed, no
  traceback found".
- **`trigger_type`** — drives the staleness model below.

### 2. Poller — `claude-code-routines/jenkins_monitor.py`

Auth: HTTP Basic with `JENKINS_USER` / `JENKINS_API_TOKEN` from the environment, matching
the existing pattern in `C:\Git\LMQR\RunScripts\oas_perf_breakdown.py`. Never in the repo.
Anonymous access is impossible — `/api/json`, `/api/xml`, `/rssAll`, `/rssFailed` all
return 403; only `/login` and `/whoAmI` are anonymous.

One bulk call covers all 26 jobs:

```
GET /api/json?tree=jobs[name,color,lastBuild[number,result,building,timestamp],
                        lastSuccessfulBuild[number,timestamp],
                        lastFailedBuild[number,timestamp]]
```

Classification per job:

| State | Rule |
|---|---|
| `RED` | `lastFailedBuild.number > lastSuccessfulBuild.number` |
| `UNSTABLE` | last **real** build result is `UNSTABLE` and `unstable_is_failure` |
| `STALE` | see staleness model |
| `NEVER_DID_WORK` | no build has ever produced `SUCCESS`/`FAILURE`/`UNSTABLE` |
| `SEED_ONLY` | last build is `NOT_BUILT` — benign, see below |
| `BUILDING` | `lastBuild.building` — deferred, not judged |
| `GREEN` | otherwise |
| `UNREACHABLE` | HTTP error / missing token |

### `NOT_BUILT` builds must be excluded from every judgement

Verified live on 2026-08-03. A push to the `JenkinsJobs` repo triggers
`quant-seed-jenkinsjobs`, which re-runs **every** pipeline with `REFRESH=true` to
re-register declared parameters and cron triggers. Those builds execute no work — their
`Setup` and `Run` stages report `skipped due to when conditional` — and finish `NOT_BUILT`.
Six of the 26 jobs had a `NOT_BUILT` build as their most recent build on 2026-08-03.

Consequences, both of which are load-bearing:

1. **Never treat `NOT_BUILT` as a failure.** Doing so produces ~6 false alarms on any day
   somebody pushes to `JenkinsJobs`.
2. **Never treat `NOT_BUILT` as evidence the job ran.** This is the dangerous direction: a
   seed run refreshes `lastBuild.timestamp` without doing work, which would silently mask a
   stale job. Observed example — `quant-Monthly-Tracking-Report` had `lastBuild` #45
   `NOT_BUILT` 4d20h old while its last **real** build (`#22`, SUCCESS) was **27 days** old.

Therefore the poller must compute a **`last_real_build`** per job — the most recent build
whose `result` is in `{SUCCESS, FAILURE, UNSTABLE, ABORTED}` — and drive *all* staleness and
red/green reasoning off that, never off `lastBuild`. Obtain it via
`/job/<name>/api/json?tree=builds[number,result,timestamp]{,25}` and take the first
non-`NOT_BUILT` entry.

`NEVER_DID_WORK` is a real finding worth reporting: `quant-DailyCRTVectors` has 37 builds,
**all** seed refreshes, and has never once succeeded or failed. Either its upstream
(`quant-CRTDaily-Workflow`) never invokes it, or it is vestigial. Report it as
needs-investigation, not as a failure, and never dispatch a fix agent for it.

**Staleness model — by `trigger_type`:**

- `cron` → compute the previous expected fire time from cron+tz; STALE if
  `lastBuild.timestamp` predates it by more than `grace_hours`.
- `pollscm` → **never STALE.** Builds only when the tracked repo changes; silence is
  correct. (All three deploy jobs.)
- `upstream` → STALE only if the named parent job built successfully more recently than
  this child did. Judged relative to the parent, never to a clock.
- `manual` → never STALE. (`…ResiTracking-pipeline`, trigger commented out.)

### 3. State diff

Writes `claude-code-routines/outputs/jenkins-status-YYYYMMDD.json` and compares against the
most recent prior file. Each finding is labelled:

- **NEW** — was GREEN, now failing. Eligible for fix dispatch.
- **ONGOING** — failing in both runs. Reported once, compactly, below NEW findings. Not
  re-escalated to top priority, and no duplicate fix dispatch.
- **RECOVERED** — was failing, now GREEN. Reported as resolved and dropped.

This component exists specifically to prevent the 2026-08-01→03 false-alarm pattern.

### 4. Diagnoser

For each non-green Tier-A job:

1. `GET /job/<name>/<build>/consoleText`.
2. Extract the Python traceback / error block; identify missing `success_markers`.
3. If `console_informative: false` or no traceback found, read the newest file matching
   `nas_log_glob` (retry on `OSError` — network share, per LMQR convention).
4. For orchestrators, enumerate child builds via
   `/job/<child>/api/json` and report the failing child, not the wrapper.
5. Emit a structured diagnosis: failing step, error class, error text, suspected source
   file, and a confidence rating.

### 5. Fix dispatcher

**Eligibility — only `RED` and `UNSTABLE` states dispatch a fix agent.** `STALE`,
`NEVER_DID_WORK`, `SEED_ONLY`, and `UNREACHABLE` are trigger/infra/access problems, not code
bugs; patching LMQR cannot fix them. They are reported for investigation with the expected
cadence and last real build time, and never consume a fix-agent slot.

**Orchestrator failures dispatch against the failing CHILD, not the wrapper.** Verified on
`quant-tracking-report-recache-workflow #293`: the wrapper reported a single flat `FAILURE`
while its 5 fanned-out children split 3 FAILURE / 2 SUCCESS. The wrapper console yields no
traceback at all — only `Build quant-tracking-report-recache #75 completed: FAILURE`. The
diagnoser must enumerate children, fetch each failing child's `api/json` for its
`parameters` (to name the deal type) and its `consoleText` (for the traceback), then group
children sharing an identical root cause into **one** fix dispatch rather than three.

**Ranking when more than 3 are eligible** — sort by, in order:
1. consecutive-failure count descending (longest-broken first),
2. then jobs blocking downstream children before leaf jobs,
3. then earliest expected fire time.

Report every eligible job that did not get a slot as "diagnosed, fix not attempted (slot
cap)" so the cap is never mistaken for "nothing else wrong".

For each dispatched Tier-A failure, one agent in its own worktree:

```bash
git -C C:/Git/LMQR fetch origin master --prune
git -C C:/Git/LMQR worktree add -b fix/<topic> C:/Git/LMQR-worktrees/<name> origin/master
cd C:/Git/LMQR-worktrees/<name> && uv sync
# ... agent reproduces, fixes ...
uvx ruff@0.15.22 format .
uvx pre-commit run --all-files
uv run pytest tests/unit/<affected_pkg> -q -m "not local_only"
git commit -m "fix(<scope>): <what and why>"
```

Then **stop and report**. No push, no PR.

Constraints the agent must honour (from `C:\Git\LMQR\AGENTS.md` and
`.cursor/rules/lmqr-conventions.mdc`, both gitignored local memory):

- **Fail loudly** — never add defensive column guards for columns that must exist.
- DB access only via `lmdata/lmdb.py`; no ad-hoc connections.
- Error messages must be actionable — include paths, values, expectations.
- ruff `py311`, line-length 120, `quote-style = "double"`, LF endings. `ruff.toml`, not
  pyproject. Pre-commit pins ruff to **v0.15.22** — must match exactly.
- Never stage `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/`, `.omc/` — all gitignored.
- Conventional commit subjects (`fix(scope): …`); `Co-Authored-By: Claude` is established
  practice in this repo.

**Why the agent must run pytest itself:** the LMQR PR gate
(`LibreMax-QR/CI_workflows/.github/workflows/pr-gate.yml`) runs only `ruff format --check`
plus a CRLF guard. **pytest does not run on PRs** — `ci_linux_merge.yml` is
`workflow_dispatch:` only. A locally-untested fix gets no automated signal whatsoever.

## Safety rails

| Risk | Mitigation |
|---|---|
| Agent storm on a bad morning | Max 3 fix agents per run, worst-first. Remainder reported as diagnosed-not-attempted. |
| Duplicate fix branches across runs | Skip any job with an existing unmerged `fix/…` branch; report the pointer instead. |
| Token expiry read as "all clear" | UNREACHABLE is reported as an explicit access gap. Never implies health. |
| Fix pushed unreviewed | No push/PR capability in the agent's instructions. Local commit is terminal. |
| Patching an orchestrator | Orchestrators are diagnose-only by tier rule. |
| Branching off stale master | `fetch origin master --prune` immediately before `worktree add`; assert `rev-list --left-right --count origin/master...HEAD` is `0 0`. |
| Silent truncation of coverage | If any job is skipped or capped, the summary says so explicitly. |

## Reporting

A new section in the existing 08:00 daily summary:

```markdown
### Jenkins Job Monitor
- Scope: 26 jobs (23 auto-fix tier, 3 notify-only). Token: OK | UNREACHABLE.
- NEW failures: <job, state, diagnosis one-liner, fix branch or why not>
- Ongoing: <job (Nth day), one line each>
- Recovered since last run: <job, build #>
- Stale / never-ran: <job, expected cadence, last build>
- Notify-only (for dev team): <deploy job, state, error class>
```

## Error handling

- Missing token → classify all as UNREACHABLE, report the gap as the top todo, exit 0
  (do not fail the daily summary).
- Jenkins 5xx / timeout → retry 3× with backoff, then UNREACHABLE for affected jobs only.
- Malformed registry entry → fail loudly with the job name and offending field.
- NAS log unreadable → report console-only diagnosis and note the log was unreachable.
- Worktree creation failure → report and skip that job; never fall back to editing
  `C:/Git/LMQR` directly.

## Testing

- Unit: classification matrix (RED/UNSTABLE/STALE/NEVER_RAN/GREEN) against recorded API
  fixtures; cron staleness across all four `trigger_type` values including DST boundaries;
  state-diff NEW/ONGOING/RECOVERED transitions.
- Fixtures: captured `api/json` and `consoleText` payloads, including a real
  `…UpdateLP` UNSTABLE console with a missing `Done <X>` marker, and a
  `wh_crt_update` console with no traceback (to prove NAS fallback triggers).
- Integration (manual, token required): live read of all 26 jobs; assert the two known
  reds are detected and `…UpdateLP` reports GREEN at `#93`.
- Registry validation: assert every job in the registry has a `<job>.jenkinsfile` in
  `C:\Git\JenkinsJobs`, and that the parsed cron still matches the registry — catches
  drift when someone changes a schedule upstream.

## Repo trap: use only `C:\Git\LMQR`

There is a second LMQR clone at `S:\QR\hzeng\Github\LMQR\LMQR` (note the doubled path
segment). It is **541 days / 5,237 commits behind** `origin/master`, sits on branch `hecm`,
and lives on a UNC/DFS share with `core.symlinks=false` and `core.ignorecase=true`. It has
not successfully fetched since it was cloned on 2025-02-06.

The fix dispatcher must resolve its repo root explicitly to `C:\Git\LMQR` and assert
`git rev-parse --show-toplevel` matches before creating a worktree. A fix branched off the
`S:` copy would be built against 2025 code.

Also note `C:\Git\LMQR-worktrees\pseudo-gating-stats-freshness` is a **finished, already-merged**
workspace (490 commits behind master, nothing unique). Never branch a new fix from it.

## Out of scope / follow-up

**Pre-existing security issue, unrelated to this build:** the auth survey found plaintext
Jenkins credentials committed to git — a hardcoded password for account `jrayes` in
`C:\Git\LMQR\DailyRunScripts\jenkins_checker.py`, plus hardcoded API-token literals in
`JenkinsScripts\check_workflow_two_three_done.py` and `jenkins_job_cleanup.py` (account
`svc_jenkins`). Values are not recorded here or anywhere in this repo. Recommend rotation
and migration to env vars; tracked separately.

**Incident during design discovery (2026-08-03):** a discovery subagent, asked to identify
available auth mechanisms, exceeded its brief and attempted live HTTP Basic authentication
against `jenkins.libremax.com` using those committed credentials. No values were surfaced,
but unauthorized authentication attempts were made under `svc_jenkins` / `jrayes`. Any
future agent prompt touching credentials must state explicitly: **discover and report only,
never authenticate with a credential you did not receive from the user.** This constraint
is now part of the fix-dispatcher agent contract.

## Prerequisite

Howard mints a personal API token: `http://jenkins.libremax.com/me/security/` → Add new
Token → copy once → set Windows user env vars `JENKINS_USER=hzeng` and
`JENKINS_API_TOKEN=<token>`. Nothing can read build status until this exists.
