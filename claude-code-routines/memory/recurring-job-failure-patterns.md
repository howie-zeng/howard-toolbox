---
name: recurring-job-failure-patterns
description: "Known recurring/self-recovering RESI/CLO job failures so the daily summary doesn't over-alarm — and which are real bugs vs timing"
metadata:
  node_type: memory
  type: reference
  originSessionId: daily-resiclo-summary-2026-06-11
---

Recurring failure signatures seen in the daily RESI/CLO summary (Jenkins Automation / qrprod). Distinguish self-recovering timing failures from real code bugs so the summary flags the right ones. See [[mailbox-folder-map]] and [[daily-resi-clo-summary-scope]].

**Self-recovering (note, don't over-alarm — confirm recovery, don't treat as broken):**
- `quant-CLO-Model-ColorClean-EOD` — fires repeatedly each morning with `ValueError: No objects to concatenate` (`clo_color_clean.py` → `utils.py:stack_dataframes` → `pd.concat`) when the raw CLO color listing is still empty. Naginator auto-retries, producing 10–15 near-identical FAILURE emails in ~1h. On 2026-06-10 it failed #17037–#17061 then went "back to normal" (#17062 ~09:08 ET) once the intraday color feed (`quant-CLO-Intraday-Workflow`) populated. Treat a morning loop as **timing**; only escalate if it's still red past ~midday ET.
- `quant-CLO-Surveillance` / `quant-Daily-CLO-Report` — occasional `MissingRateData … [Errno 22] Invalid argument: '…\LMSimData\init_config\LMUtil.json'` = transient Azure file-share read; recovers same/next run.
- `quant-ResiPortCreatioin`, `quant-DailySaveVolSurface` — flap and self-recover ("back to normal" follows). VolSurface is not RESI/CLO core.

**Real bugs (escalate — won't self-heal):**
- `quant-ResiTraceFile` — `KeyError: 'TRACE'` at `ReadTraceResi_Sentrace.py:308` (`export_df["TRACE"] = export_df["TRACE"].str.lstrip("$")`) whenever Sentrace returns **no** RESI traces for the date. Empty-result/missing-column case is unhandled in `export_to_file()`. Howard's fix.
- `quant-DailySimHistVector` — LMSim sim-history vectors (CRT/NQM/CES/HELOC/Figure); ends short (~99.9%) on a tail of deals or the Ray job dies → FAILURE/ABORTED. Has run red on consecutive nights (e.g. 06-09 #15 FAILURE, 06-10 #16 ABORTED).
- `quant-CLO-Spread-Model-LO-Report-T0-Workflow` (+ `-EUR`) — GAM v3.0 Spread-Model-LO T0 report has shown sustained FAILURE with no recovery in-window; pull console log.

**Ownership-uncertain:** `quant-HECMYTRisk` (HECM yield-table risk) has failed on consecutive nights while `quant-HECMMonitor` succeeds; HECM is in Howard's folder map so worth flagging, but confirm it's his.

**`quant-historic-cashflows` fails EVERY Saturday and Sunday - a weekend as-of-date defect,
not a break (learned 2026-08-23):** the job runs daily at 22:00 ET including weekends and its
console shows `resolveDate: ASOFDATE=<date> (businessDayOnly=false)`, so it never rolls back to
the last business day. The ratings market has no data for a weekend date, so
`loadRatingsDataDF` raises `Exception: market date in the future` at
`lmdata/scenhistmarket.py:1783` (called from `lmintex/histcashflow.py:190`). Confirmed by the
build history: #45 failed Sat 08-15, #46 Sun 08-16, #47-#51 all SUCCESS Mon-Fri, #53 failed Sat
08-22. **How to apply:** on a weekend run, report it as the known recurring weekend defect that
self-recovers Monday - do NOT diagnose it fresh or escalate it as new. The real fix is
`businessDayOnly=true` or a weekday-only cron. Ownership uncertain (LMQR `lmintex`, not one of
Howard's 22).

**The "Weekend" CRT vector chain is FRIDAY-ONLY and WEEKLY - a failure costs a whole week
(learned 2026-08-23):** `quant-WeekendCRTVectorsWorkflow` and its children
`quant-WeekendCRTTrackingVectors` / `quant-WeekendCRTVectors` fire once a week at **Fri 18:31
ET** (they generate vectors *for* the weekend; they do not run *during* it). So a Friday failure
does not retry Saturday or Sunday - the next attempt is the following Friday. Seen: workflow #43
SUCCESS Fri 08-07, #46 FAILURE Fri 08-14, #47 FAILURE Fri 08-21 = two consecutive *weekly*
failures and two weekends of missing tracking vectors, while the sibling
`quant-WeekendCRTVectors` passed both times (so the fault is specific to the Tracking child).
**How to apply:** never describe this chain as "no new build since yesterday" as though it were
idle - state the weekly cadence and name the next firing as the fix deadline. Do not wait for a
weekend re-run that will not come.
