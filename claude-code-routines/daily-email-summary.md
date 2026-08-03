# Daily RESI/CLO Email Summary

## Name

Daily RESI/CLO Email Summary

## Description

Review email/AUTO-folder signals for yesterday's RESI and CLO activity, then produce failed-job and follow-up todos.

## Instructions

Create a concise daily summary for Howard covering RESI and CLO emails from the last 24 hours.

Primary goal: inspect Howard's Outlook email first, especially the `AUTO` folder and any RESI/CLO/job notification folders. If direct Outlook access is unavailable, inspect accessible Outlook exports, `.msg` / `.eml` files, saved mail artifacts, and local report/job notification files. Do **not** start from git commits unless Outlook/email sources are unavailable or need context.

Before searching, read these routine memory files:

- `claude-code-routines/memory/daily-resi-clo-summary-scope.md`
- `claude-code-routines/memory/duplicate-scheduled-run-guard.md`
- `claude-code-routines/memory/mailbox-folder-map.md`
- `claude-code-routines/memory/libremax-tls-interception-ca.md`

Before regenerating or sending, apply the duplicate-run guard: check for a fresh
same-day output file and a same-day email with the expected subject in Outlook
Sent Items. If both exist and no newer in-scope message arrived, stop without
overwriting or resending.

**Out of scope — do NOT flag these (not Howard's responsibility):**

- Automated **risk runs** — the "LIBREMAX Risk Run" / "SWIB Risk Run: '…' scenario set for … " job-failure/success notifications (CRT/RMBS/CLO/etc.). Ignore their bond failures.
- **Resi SSS file generation** — "Daily Resi SSS File Generation" success/failure counts.
- **Compliance Engine** — `Compliance@`/`Compliance_EOD@` started/stopped/failed/[ERROR] messages.

Mention these only if directly relevant context for an in-scope RESI/CLO item; otherwise omit them.

Focus especially on:

- Outlook email, especially folders named `AUTO`, `Auto`, `auto`, `Jenkins`, `RESI`, `CLO`, `QR`, `Models`, `Risk`, or similar if available.
- Exported Outlook/email artifacts such as `.msg`, `.eml`, `.pst` extracts, saved HTML emails, or local mail folders if direct Outlook access is not available.
- Failed or suspicious jobs, including Jenkins, scheduled model runs, tracking runs, vector runs, data unloads, and report-generation jobs.
- Job failure emails, warning emails, completion emails, and overnight batch/run notifications.
- RESI items: CRT, Non-QM, Jumbo, HELOC, HECM, DV01/Figure, LMSim vectors, tracking reports, risk runs, flat-file updates, `CRTStats`, `factor_month`, and `reporting_month`.
- CLO items: EUR/USD model training, V2/V2R/V3, spread model runs, walk-forward backtests, color parsing, BWIC/color ingestion, model fit reports, and production comparison jobs.
- Git commits, uncommitted changes, generated reports, and notebook/script edits only as secondary context after email/AUTO sources have been checked.
- Anything that needs Howard's attention today.

Suggested search order:

1. Look for accessible email/AUTO folders or exported mail files under the workspace and common local paths.
2. If Outlook automation/MCP/tools are available, query Outlook directly for the last 24 hours first. Prioritize the `AUTO` folder, then Inbox and RESI/CLO-related folders.
3. If direct Outlook access is unavailable, review files modified in the last 24 hours under email/AUTO/report/output/log folders.
4. Search subjects/senders/bodies/file names for failure/success keywords: `failed`, `error`, `warning`, `exception`, `traceback`, `Jenkins`, `completed`, `success`, `RESI`, `CLO`, `NQM`, `HELOC`, `CRT`, `DV01`, `Figure`, `LMSim`, `V2R`.
5. Use git commits only as a fallback context source, not as the primary source.

Mailbox folder map (learned 2026-06-01 — check ALL of these, not just Inbox/AUTO):

- **Check every run:** `Inbox/auto` (the "AUTO" feed; ~36k items), **`Jenkins Automation`** (~12.5k items — this is where Howard's RESI/CLO build pipelines report: `quant-DailyNewIssueCRTVectors`, `quant-CRTDaily-Workflow`, `quant-Monthly-ResiTracking-pipeline`, `quant-WeekendCRTTrackingVectors`, `quant-RMBSLoader`, `quant-CLODaily-Workflow-pipeline`, `quant-CLO-restart-spread-model-celery`, `quant-CLO-Loan-Px-Diff-Email`, `quant-colordb-run-risk-results`, `quant-trimaran-galileo-integration-test`, etc.), **`CLO`** (CLO RV lists/offers, spread-model MAE & curve-comparison v2/v2r/delev, surveillance, IO/PO & break-even yields, MVOC), `HECM`, `RESI`, `Tracking` (QR Model Tracking Reports / NQM called deal-months), and `Inbox`.
- **Out-of-scope folders (skip):** `Daily Fund PnL`, `Performance Attribution`, `Resources`, `Archive`, `Conversation History`, `Sync Issues`, `Junk Email`, `Glenn & Kiet`.
- **Folder-access gotcha:** the `outlook_email_search` `folderName` lookup resolves `Inbox`, `CLO`, `HECM`, `Jenkins Automation`, `auto`, but returns NOT_FOUND for some custom folders (`RESI`, `Tracking`). For those, get the folder ID from `read_resource mail:///folders/` (lists all folders) and read it via `read_resource mail:///folders/{id}` to enumerate recent messages.
- In Jenkins, treat `Build FAILURE` / `Build failed in Jenkins` / `ABORTED` / `[Tests: FAILED]` as failures, and `Jenkins build is back to normal` as a recovery (implies a prior failure). A failure with no later "back to normal" or SUCCESS for the same job = still broken.

Before writing the summary, run the Jenkins job monitor and fold its output in as a
`### Jenkins Job Monitor` section:

```powershell
python -m jenkins_monitor.cli --outputs outputs
```

Run it from `claude-code-routines/`. It exits 0 even when jobs are red. If it reports
UNREACHABLE, say so explicitly — that is an access gap, never "all clear". Only `RED` and
`UNSTABLE` jobs in the `fix` tier are candidates for a fix agent; see
`FIX_AGENT_RUNBOOK.md`. Deploy jobs are notify-only — report them for the dev team.

**If the command fails for any reason** — non-zero exit, a Python traceback, no output, or
output you cannot parse — do **not** omit the section. A missing Jenkins Job Monitor section
is indistinguishable from "no Jenkins issues", which is the one wrong conclusion here.
Instead:

- Write the `### Jenkins Job Monitor` section anyway, stating that **the Jenkins monitor did
  not run and job status is unknown for today**, with the exit code and the last few lines
  of output as evidence.
- Add "Jenkins monitor did not run — job status unknown for today" as a **top item** in the
  `### Todo` list, above the other todos.
- Never infer job health from the absence of failure emails when the monitor did not run;
  the monitor exists precisely because failure emails are missed.

Exit codes: `0` = it ran (jobs may still be red — read the report); `2` = malformed job
registry (`jenkins-jobs.yaml`), so nothing was checked; any other non-zero = unexpected
error. Treat `2` and "other" identically for the summary: status unknown, top todo.

Use this output format:

```markdown
## Daily RESI/CLO Summary

### Executive Summary
- 2-5 bullets with the most important takeaways.

### Failed / Concerning Jobs
- Job/source:
- What failed or looks suspicious:
- Evidence:
- Suggested next action:

If none are found, write: `No failed or concerning jobs found from accessible sources.`

### RESI Updates
- Completed:
- In progress:
- Risks / follow-ups:

### CLO Updates
- Completed:
- In progress:
- Risks / follow-ups:

### Email / AUTO Folder Signals
- Summarize relevant Outlook messages first, especially from the `AUTO` folder.
- If direct Outlook access was unavailable, say that clearly and summarize only accessible exported/local email artifacts.
- Include sender, subject, date/time, and why it matters when available.

### Todo
- Actionable checklist for Howard, ordered by urgency.
```

At the end, save the completed summary to:

```text
claude-code-routines/outputs/daily-resi-clo-summary-YYYYMMDD.md
```

Use today's local date for `YYYYMMDD` unless the user or scheduler context provides a different target date.

Then email the saved summary to Howard through Outlook:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --date YYYY-MM-DD `
  --to hzeng@libremax.com `
  --send `
  --fallback-draft
```

If Outlook automation is unavailable or sending fails, create a draft instead:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --date YYYY-MM-DD `
  --to hzeng@libremax.com `
  --draft
```

Report whether the email was sent, drafted, or blocked.

Rules:

- Do not invent job status or email content. If a source is unavailable, state that.
- Outlook email/AUTO review is the primary task. Do not lead with git commit summaries.
- Prefer concrete file paths, job names, commit hashes, PR numbers, and timestamps.
- Keep the summary management-friendly: conclusion first, technical details second.
- Separate true failures from warnings, stale outputs, or missing access.
- Do not include secrets, credentials, tokens, or full email bodies unless needed for context.
- If there are no meaningful updates, say: `No material RESI/CLO updates found from accessible sources.`

