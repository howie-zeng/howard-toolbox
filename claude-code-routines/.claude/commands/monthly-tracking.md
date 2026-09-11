---
description: Draft the Monthly Tracking Review email from the RESI tracking workbooks
argument-hint: "[YYYY-MM] (default: current month)"
---

Run the Monthly Tracking Review routine for month **$1** (if empty, use the current month).

Follow `claude-code-routines/monthly-tracking-review.md` exactly. It is the source of truth
for which row the ratios come from, the data-gap checks, the screenshot range, and the format.

Do not skip these, they are the steps that have actually gone wrong before:

1. Read `claude-code-routines/memory/monthly-tracking-review-scope.md` first.
1. List the month's files in `Dialed` and check every workbook maps to a cohort before
   trusting an "N of N cohorts present" verdict. A renamed product keeps matching an old
   pattern and silently swaps cohorts -- that is how FIGRE vanished from the 2026-09 run.
2. Run `facts` and check **every** month's `Proj` for zeros before quoting any ratio — a zero
   Proj is an absent projection and understates every window containing it.
3. Report dial status only when the `Undialed` twin confirms it; otherwise say nothing.
4. Name any cohort with no file for the month as having no tracking, rather than quoting last
   month's figures.
5. Delivery is `email.md` + `python emailer/run.py --md-file ...` so Howard can Ctrl+V.
   Never send. Do not leave extra Outlook drafts.
6. Verify the HTML that actually landed on the clipboard — every image inlined, no `$amount`
   LaTeX accidents — then report what is in it and what you left out.
7. Prefer no dial: highlight a new model converging to 1; propose removing a dial when
   undialed is already near 1. If the undialed model is actually off, we still dial.
   Never equate undialed CPR with undialed CtoP.
