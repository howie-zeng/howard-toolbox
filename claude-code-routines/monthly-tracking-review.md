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

Cohorts, in the order they appear in the email: **STACR, CAS, NQM, JUMBO, FIGRE, HELOC**.

`FIGRE` (`tracking_V2_0_7_FIGRE_*`) is the Figure-platform HELOC book and is what every review
before 2026-09 called "HELOC". `HELOC` (`tracking_V1_0_V5_HE_*`) is the separate non-Figure
HELOC book and is new in 2026-09. When comparing against an earlier month's email, that
email's "HELOC" line is this month's FIGRE line — say so, rather than letting the team read a
relabelling as a model move.

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

The tool compares the **per-month projections** at the quoted WAC `ALL AVG` row, not the
window `Ratio` cells, and reports a per-sheet factor — e.g. `dial applied (CtP x1.1999, CPR
x1.1500)`, or `no dial applied (CtP none, CPR none)`, or `unverified` when no twin exists.
Months where either book's projection is missing or zero are skipped and counted in the note.

**Do not go back to comparing the Ratio cells.** A ratio gap is produced just as easily by a
projection the `Undialed` run never wrote as by a dial. On 2026-09 the old ratio-only check
was wrong in four of six cohorts: STACR and CAS showed a +0.20 gap on the 3M CtP ratio that
was entirely one absent 2026-08 projection, JUMBO's "dial" was 7e-09 of float noise, and
FIGRE's was an `Undialed` book whose projections are all zero. Only HELOC had a real one.

A real dial looks like a **uniform factor across every bucket and every month** (HELOC 2026-09:
×1.1999 on CtP, ×1.15 on CPR, on all 35 rows). A one-month, one-column difference is a
defective run, not a dial — say so instead.

The `Undialed` books are a **separate, later re-run**, typically written ~24 h after their
`Dialed` twins, not a no-dial branch of the same process. That is why their newest month can be
incomplete. Check the write times before drawing a conclusion from a newest-column difference.

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
  <li><b>COHORT:</b> CPR then CtoP, 3M/6M/12M, one takeaway, whether action is needed.</li>
  ...one bullet per cohort, in email order...
</ul>
<p><b>Next Steps</b></p>
<p>What is being fixed or watched, and what you are deliberately not acting on yet.</p>
```

Keep the published email **high-level**. Each bullet is CPR/CtoP ratios plus one takeaway.
Do not walk the full transition chain in the mail. **FCLS is STACR-only** — CAS does not
report FCLS; those workbook rows are derived and must not be quoted.

**Prefer no dial; still dial if the model is off.** A newly released model should be left
undialed and allowed to converge to 1 — highlight that path when it is happening (NQM
V1_8_0 in 2026-09). If a published miss *is* the dial, propose taking it off, quote undialed
CtoP **and** CPR separately (they are not the same number), and put the undialed `CtP`
screenshot next to the dialed one. Copy the Undialed file to a distinct local name first or
the renderer will screenshot the Dialed scratch copy. If the undialed model is actually off
— consistent miss, not a window/restatement/gap — we still dial.

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

### Step 5 — paste HTML, never send

Howard wants a Ctrl+V paste, not an extra Outlook draft from the helper.

Write `claude-code-routines/outputs/mtr-YYYYMM/email.md` (images in that folder), then:

```powershell
python emailer/run.py --md-file "S:\QR\hzeng\howard-toolbox\claude-code-routines\outputs\mtr-YYYYMM\email.md"
```

Never write `$amount` in that markdown — emailer treats `$...$` as LaTeX. No sign-off.
Add `--ack-gaps` only per Step 2 if you also run the helper `draft` path.

The helper can still render `CtP` screenshots (`A1:AE<2nd ALL AVG row>`, AGE + WAC blocks)
and optionally `--draft` to Outlook. As of 2026-09 Howard does not use that draft.

`--skip COHORT` leaves a cohort out of the attachments and the charts, for a workbook that is
known bad enough that sending it would mislead the team (2026-09: `--skip FIGRE`). It does not
excuse you from the narrative — **the bullet still has to name the cohort and say why it is
held back**. A cohort that simply stops appearing is the exact failure this routine exists to
catch.

Excel is driven through a dedicated instance (`DispatchEx`) with a retry on open/activate,
because this box is shared and attaching to someone else's Excel session picks up modal state
the script cannot see. If a run dies mid-render it can leave an orphan `EXCEL.EXE` holding the
scratch copies; the next run is insulated from it, but close it.

**Stop at paste.** `--send` exists but this routine never uses it: the email goes to the
whole modeling team and Howard signs it. Report that the HTML is on the clipboard and what
is in it.

### Step 6 — verify, then report

Confirm what actually landed on the clipboard rather than trusting the success message:
subject/recipient Howard will type, every image inlined (not a broken path), no `$amount`
turned into CodeCogs, and the undialed comparison present if a dial is being removed.

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
- Keep the published email high-level — conclusion first, one takeaway per cohort, measured
  about acting on one month of data. Never quote CAS FCLS.
- Prefer no dial: highlight a new model converging to 1; propose removing a dial when
  undialed is already near 1. If the undialed model is actually off, we still dial. Never
  treat undialed CPR 1.00 as undialed CtoP 1.00.
