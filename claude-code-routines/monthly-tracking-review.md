# Monthly Tracking Review

## Name

Monthly Tracking Review

## Description

On-demand. Read the month's RESI tracking workbooks, judge how each cohort is tracking,
and leave an Outlook **draft** of the Monthly Tracking Review for Howard to review and send.

## When to run

Run this **only when asked**. It is deliberately not scheduled:

- The workbooks do not land on a fixed day (July 2026 was dated `20260701`, August `20260803`),
  so a cron would fire on days when the files are not there.
- The review needs judgment every month. On the 2026-08 run, NQM was missing entirely and
  HELOC carried a zero-projection gap that made a healthy cohort look broken. An unattended
  run would have either mailed a false claim to the whole modeling team or stalled.

A monthly review a day late costs nothing. A wrong one costs a lot.

## Instructions

Before doing anything, read:

- `claude-code-routines/memory/monthly-tracking-review-scope.md`

The data lives in `R:\QR\Resi_shared\tracking\Dialed`. `Undialed` holds a parallel set with
identical filenames — it is the dial-verification twin, not a second data source. Never open
either for write; the helper copies to a scratch directory before touching Excel.

Cohorts, in the order they appear in the email: **STACR, CAS, NQM, JUMBO, HELOC**.

### Step 0 — readiness

Start with the pre-flight check, `claude-code-routines/monthly-tracking-readiness.md`:

```powershell
python monthly_tracking_review.py readiness --month YYYY-MM
```

Exit `4` means a cohort is missing or gapped. That does **not** block the review — it tells you
what the narrative has to address, and what to chase. Follow that routine's guidance for
diagnosing a missing cohort before continuing here.

### Step 1 — get the fact sheet

```powershell
python monthly_tracking_review.py facts --month YYYY-MM
```

This reports, per cohort: the as-of date, dial status, the 3M/6M/12M tracking-error ratios
from the `CtP` and `CPR` sheets, the per-month Actual/Proj pairs, and any missing cohort.

Ratios come from the **WAC `ALL AVG` row** — the second `ALL AVG` row in column C. That is
the row that reproduces the numbers quoted in prior reviews; the AGE row is also reported so
you can cross-check, and it will differ.

### Step 2 — check for data gaps before quoting any ratio

`Ratio = sum(Proj) / sum(Actual)` over the window. A month whose **Proj is zero or blank is
an absent projection, not a slow model**, and it drags down every window that contains it.

The tool prints `[DATA GAP]` lines and refuses to build a draft unless you pass `--ack-gaps`.
Do not pass that flag until the narrative actually explains the gap. On 2026-08, HELOC's
June projection was zero, which showed a 3-month CtoP of 0.72 against a true 1.04 — the
draft would have told the team a healthy cohort had deteriorated.

When a gap exists: report the affected ratio, state that it is understated, give the
recomputed figure excluding the gap month, and add repopulating that month to Next Steps.

### Step 3 — establish dial status honestly

The tool reports `no dial applied` when the `Undialed` twin is numerically identical,
`dial applied` when it differs, and `unverified` when no twin exists for that date.

If it says **unverified, say nothing about dials for that cohort**. Do not carry forward the
previous month's claim — on 2026-08 there were no August `Undialed` files at all, so July's
"no dial currently applied" could not be confirmed.

### Step 4 — write the narrative

Write an HTML fragment holding the `Summary` and `Next Steps` sections. Save it to
`claude-code-routines/outputs/monthly-tracking-review-YYYYMM.html` so the run is reproducible
without recomputing.

Use the July 2026 structure:

```html
<p><b>Summary</b></p>
<p>One or two sentences: the overall verdict and the single most important exception.</p>
<ul>
  <li><b>COHORT:</b> how CtoP is tracking, with the ratios; dial status if verified;
      whether action is needed.</li>
  ...one bullet per cohort, in email order...
</ul>
<p><b>Next Steps</b></p>
<p>What is being fixed or watched, and what you are deliberately not acting on yet.</p>
```

Label the windows **correctly**: `6M Error` is the six-month tracking error. The July 2026
email called it a "12-month average," which was a mistake Howard confirmed — do not copy it.
Because of that, a cohort's figure will not line up with what July's email said for the same
metric; if the discrepancy is visible, say so in one sentence rather than letting the team
puzzle over it.

For a cohort with no file that month, state plainly that there is no tracking for it and that
an update will follow once the tracking is regenerated. Do not quote last month's numbers as
if they were current.

Distinguish a genuine model turn from a data artifact. A real turn shows in the Actual/Proj
pairs — on 2026-08, JUMBO had been projecting faster than actual early in the year and
reversed, with no missing months. An artifact is a zero Proj.

### Step 5 — leave a draft, never send

```powershell
python monthly_tracking_review.py draft --month YYYY-MM `
  --narrative claude-code-routines/outputs/monthly-tracking-review-YYYYMM.html `
  --draft
```

This renders each cohort's `CtP` screenshot — `A1:AE<2nd ALL AVG row>`, the AGE and WAC
blocks, matching how Howard has always captured it — attaches the workbooks, inlines the
images, and saves to Outlook Drafts. Add `--ack-gaps` only per Step 2.

**Stop at the draft.** `--send` exists but this routine never uses it: the email goes to the
whole modeling team and Howard signs it. Report that the draft is ready and what is in it.

### Step 6 — verify, then report

Confirm what actually landed rather than trusting the success message: subject, recipient,
that every workbook is attached, and that every image is referenced inline by its content-id.
A `cid` attached but not referenced renders as a broken image for every recipient.

Then tell Howard: which cohorts are in, which are missing, any data gaps and how the
narrative handled them, anything left out and why.

## Rules

- Never send. Draft only.
- Never write to `R:\QR\Resi_shared\tracking`. Copy, then read.
- Do not invent a ratio, a dial status, or a cohort's condition. If a source is missing or a
  projection is absent, say so — an understated ratio reported at face value is worse than a
  stated gap.
- Quote the row and sheet the numbers come from, so Howard can check them.
- The screenshots are the evidence: if a rendered image is blank, the run failed. The helper
  raises on a blank render; do not work around it.
- Keep the tone Howard's — conclusion first, measured about acting on one month of data.
