---
description: Check whether the month's RESI tracking data is complete enough to review
argument-hint: "[YYYY-MM] (default: current month)"
---

Run the Monthly Tracking Readiness check for month **$1** (if empty, use the current month).

Follow `claude-code-routines/monthly-tracking-readiness.md`.

Report only — no drafting and no email. First list the month's files in `Dialed` and check each one maps to a cohort: a renamed product keeps matching its old pattern and silently swaps cohorts, so an "N of N present" verdict proves nothing on its own. Distinguish the two failure modes: a **missing**
cohort (pipeline never produced it, so check the `quant-Monthly-ResiTracking-*` Jenkins jobs
and remember a failure there may have emailed nobody) versus a **data gap** (workbook exists
but a month's projection is zero, which understates every window containing it). For a gap,
check whether a prior month's workbook had the value — if so it was lost, not never computed.
