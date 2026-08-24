---
description: Draft the Monthly Tracking Review email from the RESI tracking workbooks
argument-hint: "[YYYY-MM] (default: current month)"
---

Run the Monthly Tracking Review routine for month **$1** (if empty, use the current month).

Follow `claude-code-routines/monthly-tracking-review.md` exactly. It is the source of truth
for which row the ratios come from, the data-gap checks, the screenshot range, and the format.

Do not skip these, they are the steps that have actually gone wrong before:

1. Read `claude-code-routines/memory/monthly-tracking-review-scope.md` first.
2. Run `facts` and check **every** month's `Proj` for zeros before quoting any ratio — a zero
   Proj is an absent projection and understates every window containing it.
3. Report dial status only when the `Undialed` twin confirms it; otherwise say nothing.
4. Name any cohort with no file for the month as having no tracking, rather than quoting last
   month's figures.
5. Stop at an Outlook **draft**. Never send.
6. Verify the draft that actually landed — attachments present, every image referenced inline
   by content-id — then report what is in it and what you left out.
