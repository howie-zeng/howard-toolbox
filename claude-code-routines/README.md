# Claude Code Routines

Local Claude Code routines for Howard Toolbox. Some are scheduled; the Monthly Tracking
Review is deliberately on-demand.

Full runbook for the two monthly routines — data layout, methodology, failure modes, and open
items — is in `MONTHLY_TRACKING_REVIEW.md`. Read that before changing either routine or the
helper.

## Monthly Tracking Readiness (on demand)

Routine prompt:

- `monthly-tracking-readiness.md`

Slash command:

- `/tracking-readiness [YYYY-MM]`

Pre-flight check for the review below: which of STACR, CAS, NQM, JUMBO and HELOC have landed
for the month, and whether the ones that landed are usable. Reports only — no drafting, no
email. Exit `0` when everything is present and clean, `4` when something is missing or gapped.

```powershell
python claude-code-routines/monthly_tracking_review.py readiness --month 2026-08
```

Two failure modes, needing different follow-up: a **missing** cohort (its tracking pipeline
never produced the workbook — check the `quant-Monthly-ResiTracking-*` Jenkins jobs, and note
that a failure there may have emailed nobody) versus a **data gap** (the workbook exists but a
month's projection is zero, which understates every tracking-error window containing it).

## Monthly Tracking Review (on demand)

Routine prompt:

- `monthly-tracking-review.md`

Slash command:

- `/monthly-tracking [YYYY-MM]`

Routine-specific memory:

- `memory/monthly-tracking-review-scope.md`

Helper and outputs:

- `monthly_tracking_review.py`
- `outputs/monthly-tracking-review-YYYYMM.html` (the narrative, so a run is reproducible)

Reads the month's cohort workbooks from `R:\QR\Resi_shared\tracking\Dialed`, judges how STACR,
CAS, NQM, JUMBO and HELOC are tracking, renders the `CtP` screenshots, and leaves an Outlook
**draft**. It never sends — the email goes to the whole modeling team and Howard signs it.

Not scheduled on purpose: the workbooks do not land on a fixed day, and the review needs
judgment every month (a missing cohort, or a zero projection that makes a healthy cohort look
broken).

Fact sheet only, no draft:

```powershell
python claude-code-routines/monthly_tracking_review.py facts --month 2026-08
```

Render the charts and assemble the draft:

```powershell
python claude-code-routines/monthly_tracking_review.py draft --month 2026-08 `
  --narrative claude-code-routines/outputs/monthly-tracking-review-202608.html `
  --draft
```

`draft` refuses to run when a monthly projection is missing or zero, because that understates
every tracking-error window containing it. Pass `--ack-gaps` only once the narrative explains
the gap and gives the recomputed figure.

## Daily RESI/CLO Email Summary

Routine prompt:

- `daily-email-summary.md`

Routine-specific memory:

- `memory/`

Outputs:

- `outputs/daily-resi-clo-summary-YYYYMMDD.md`

The routine should review Outlook email first, especially `Inbox/auto`,
`Jenkins Automation`, `CLO`, `HECM`, `RESI`, and `Tracking`, then save a
summary and email it to Howard.

## Email Helper

Dry-run render:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --body-file claude-code-routines/outputs/test-daily-resi-clo-summary.md `
  --to hzeng@libremax.com `
  --subject "Daily RESI/CLO Summary - Test" `
  --dry-run
```

Create an Outlook draft:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --body-file claude-code-routines/outputs/test-daily-resi-clo-summary.md `
  --to hzeng@libremax.com `
  --subject "Daily RESI/CLO Summary - Test" `
  --draft
```

Send today's summary using the default output filename:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --date 2026-06-01 `
  --to hzeng@libremax.com `
  --send `
  --fallback-draft
```
