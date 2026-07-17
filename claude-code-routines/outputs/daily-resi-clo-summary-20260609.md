## Daily RESI/CLO Summary — 2026-06-09 (Tuesday)

_Source: Howard's Outlook (hzeng@libremax.com). Window reviewed: Mon 6/8 ~09:00 ET → Tue 6/9 ~08:10 ET (~last 24h). Folders checked: `Jenkins Automation` (62 msgs in window), `Inbox/auto`, `CLO`, `RESI`, `Tracking`. Times are ET (UTC−4). Out-of-scope per standing instructions: LIBREMAX/SWIB risk runs, Resi SSS file generation, Compliance Engine — excluded below._

### Executive Summary
- **Top-priority carryover CLEARED:** `quant-DailyNewIssueCRTVectors #702` reported **"back to normal"** at 02:11 ET Tue. The SIM2 native crash (`0xC0000409`) on **FIGRE 2026-HE5** that killed #700/#701 Monday has resolved — Monday's missed new-issue CRT/Figure LMSim vectors are generating again.
- **NEW, now the top open item (CLO):** `quant-CLO-Model-ColorClean-EOD` failed **~13 times** this morning (#16978–#16990, 07:02–08:08 ET Tue) with `ValueError: No objects to concatenate` in `clo_color_clean.py` (empty color set fed to `pd.concat`). It is Naginator-looping and still red. This is Howard's CLO color-clean/ingestion code.
- **Two carryover bugs still open:** `quant-ResiTraceFile #1258` failed again (Mon 17:13 ET) with the same **`KeyError: 'TRACE'`** — confirmed root cause: Sentrace returned **no RESI traces** and the export step indexes a missing `TRACE` column (empty-result still unguarded). `quant-DailySimHistVector #14` / `-freestyle #1565` failed Mon ~20:57 ET — **still crashing on HELOC/SIM2** even though the new-issue path recovered, so the SIM2-on-HELOC family is only *partially* fixed.
- **Daily RESI + CLO production otherwise green:** `quant-CLODaily-Workflow-pipeline #273`, `quant-Monthly-ResiTracking-Tracking #43` + `-Unload #52`, `quant-CLO-restart-spread-model-celery #58`, CreditSmile / MorningReports #229 / morningparalleljobs #135 all SUCCESS. The **`RESI` folder is clean** (no new per-cohort failures — only the stale 6/2 `_PSEUDO` items), so the pipeline-level Tracking SUCCESS is genuine, not masked. Tracking report + `LM Deal List` delivered Mon evening; full CLO report suite delivered.
- **Carryover awareness:** the Galileo MorningChecks pattern persists (`quant-trimaran-galileo-integration-test #115` build FAILURE/tests NOT_RUN; `quant-galileo-integration-test #479` tests FAILED; SWIB #223 PASSED), and the weekend CRT vector reruns (`quant-WeekendCRTVectors #326–#329`, `-TrackingVectors #37`, manually triggered by Jay Shaver Mon) are still failing on a collateral-count mismatch.

### Failed / Concerning Jobs

**1. `quant-CLO-Model-ColorClean-EOD #16978–#16990` — CLO EOD color clean (CLO) — NEW, FAILING, no recovery [TOP PRIORITY]**
- What failed: ~13 consecutive Build FAILUREs between 07:02 and 08:08 ET Tue, Naginator auto-retrying after each. Started by upstream `quant-CLO-Intraday-Workflow`. Still red as of 08:08 ET.
- Root cause (console, #16990): `ValueError: No objects to concatenate` — `clo_color_clean.py:168 get_clo_model_color_clean` → `utils.py:349 CleanCLOColorListingDaily` → `utils.py:170 stack_dataframes` → `pd.concat(concat_dfs)` on an **empty list** (no color dataframes to stack). Note the log line `the date passed in was NULL / using todays date = 20260609` — the EOD clean defaulted to today and found no EOD color yet, which may be why the concat input is empty.
- Suggested next action: (a) Decide whether the **EOD** color clean should be firing intraday at all (the NULL-date default → today + empty color suggests a timing/trigger issue); (b) guard `stack_dataframes` / `CleanCLOColorListingDaily` against an empty input so it logs "no color today" instead of raising — same class of empty-result bug as ResiTraceFile. Confirm whether downstream CLO color-based RV/spread outputs for 6/9 are affected (the delivered CLO reports above are off 6/5–6/8 data, so today's are at risk).

**2. `quant-ResiTraceFile #1258` — RESI trace-file export (RESI) — carryover, code bug still unpatched**
- What failed: Build FAILURE Mon 17:13 ET (business-day evening trigger via `quant-ResiTraceFileTrigger #438`), exactly as predicted in the 6/8 summary.
- Root cause (now confirmed from console): `INFO: No traces fetched from Sentrace for the Residential Bonds for the provided time range` → then `export_to_file` runs `export_df["TRACE"] = export_df["TRACE"].str.lstrip("$")` on an empty frame → `KeyError: 'TRACE'` (`ReadTraceResi_Sentrace.py:308`). Pure empty-result handling bug, not data corruption.
- Suggested next action: In `ReadTraceResi_Sentrace.py`, short-circuit `export_to_file` when `resi_traces_df` is empty (or has no `TRACE` column) — write an empty/skip file and exit 0. Will keep failing every business-day evening until patched.

**3. `quant-DailySimHistVector #14` + `-freestyle #1565` — LMSim sim-history vectors (RESI) — carryover, still failing**
- What failed: both Build FAILURE Mon ~20:56–20:57 ET. Console tail again shows HELOC collateral on the SIM2 engine (e.g. `JPMMT 2024-HE2 | HELOC | V1_0_V4_HE | SIM2`). Same SIM2-on-HELOC family as the (now-recovered) new-issue job.
- Note: `DailyNewIssueCRTVectors` recovered (#702) but this sim-history path did **not** — so whatever cleared the new-issue deal (FIGRE 2026-HE5) did not clear the broader HELOC/CES/CRT sim-hist run.
- Suggested next action: Re-check tonight's run; if still red, treat as the remaining tail of the SIM2/HELOC instability and pursue the engine-stability fix (roll back vs. hotfix the v2.0.22-beta5 HELOC path) independently of the new-issue recovery.

**4. `quant-WeekendCRTVectors #326–#329` + `quant-WeekendCRTTrackingVectors #37` — weekend CRT vectors (RESI/CRT) — carryover, no recovery (Jay Shaver driving)**
- What failed: four WeekendCRTVectors builds (#326 10:03, #327 10:29, #328 11:12, #329 13:02 ET) and TrackingVectors #37 (13:22 ET) on Mon, all Build FAILURE. #326 was started by user **Jay Shaver** (manual reruns → someone is already troubleshooting).
- Failure mode is **different** from the SIM2 crash: collateral-count mismatches, e.g. `ERROR: deal=RMLT 2019-2 collatid=QWA expected=15 …`, `deal=STACRCC FICO [575-625) collatid=STACRC…`, `VERUS 2020-1 | NONQM`. Data/config (expected-vs-actual collateral) rather than a native crash.
- Suggested next action: Sync with Jay Shaver — confirm whether this is the same collateral-count issue and whether it blocks the weekend CRT tracking vectors Howard owns.

**Lower-confidence / borderline (ownership unclear — noted, not owned):**
- `quant-trimaran-galileo-integration-test #115` — Build FAILURE, Tests NOT_RUN (07:55 ET Tue). MorningChecks; carryover from #114. Report at `S:\QR\Reports\MorningChecks\trimaran-report.html`.
- `quant-galileo-integration-test #479` — Build SUCCESS but **Tests FAILED** (07:19 ET Tue); SWIB variant `#223` PASSED. Same pattern as 6/8's #478. Confirm which Galileo checks regressed.
- `quant-HECMYTRisk #13` — Build FAILURE (22:39 ET Mon). HECM-area job; `quant-HECMMonitor #14` SUCCEEDED (00:27 ET Tue), so monitor is fine — confirm whether HECM YT-risk is yours.
- `quant-Daily-CMBS-Model-Intex-CSV #636` — Build FAILURE (00:07 ET Tue). CMBS Intex CSV loader — likely not RESI/CLO, flagged for awareness.
- `quant-dpa-nightly-risk-check #2060` — Build FAILURE (20:57 ET Mon, paged). DPA nightly risk check; adjacent to `quant-dpa-ForwardCurveGeneration` — glance to confirm it isn't yours.
- Recovered on their own (no action): `quant-DailySaveVolSurface` #2743 FAIL → #2744 back to normal; `quant-tracking-report-recache` #930 FAIL → #931 back to normal (RESI-tracking recache, self-healed); `quant-npl-strats` #13 FAIL → #14 SUCCESS.

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-Tracking #43` SUCCESS (23:09 ET Mon) and `-Unload #52` SUCCESS (02:07 ET Tue), both to hzeng@. Earlier flapping (`Tracking #42` FAILURE 18:47 ET, `Unload #51` ABORTED 14:54 ET) **retried clean** and produced **no per-cohort RESI-folder failures**. `RESI` folder is clean — only the stale 6/2 `_PSEUDO` FAILED items remain. `QR Model Tracking Report` delivered Mon 17:38 ET; `LM Deal List - All Deals Mapped` delivered Mon 19:26 ET. `CRT Monitor Report 20260608` delivered. **Top carryover cleared:** new-issue CRT/Figure vectors back (`DailyNewIssueCRTVectors #702`).
- **In progress:** SIM2/HELOC sim-history vectors (`DailySimHistVector`) and weekend CRT vectors still failing — see Failed #3, #4.
- **Risks / follow-ups:** `ResiTraceFile` empty-result `KeyError: 'TRACE'` (Failed #2) and the residual SIM2-on-HELOC crash (Failed #3) are the two open RESI code/engine items.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline #273` SUCCESS (00:55 ET Tue), `quant-CLO-restart-spread-model-celery #58` SUCCESS (04:52 ET Tue), `quant-stage3-eod-tplus0 #51` SUCCESS. Reports delivered: CLO Surveillance 20260608, IO/PO Yields 20260609, Break-Even Yield 20260608, Large MVOC 2026-06-08, Loan Price Changes 06/09 (no significant changes), US+Europe Lists & Offers 06/08, Spread Model LO MAE (GAM v3.0, 01-01→06-05), Spread Model Curve Comparison v2/v2r/delev (06-04 vs 06-05), RV Trades/Positions 06-05.
- **In progress:** EOD color clean (`CLO-Model-ColorClean-EOD`) is failing on empty concat — see Failed #1.
- **Risks / follow-ups:** Confirm the ColorClean failure isn't degrading today's (6/9) color-based CLO RV/spread outputs. No spread-model / walk-forward / curve-comparison failures otherwise.

### Email / AUTO Folder Signals
- Direct Outlook access was available; this summary is built primarily from it.
- `Jenkins Automation` (~13.1k items): signals are the ColorClean-EOD failure storm, the ResiTraceFile/DailySimHistVector carryover failures, and the DailyNewIssueCRTVectors #702 recovery; daily CLO + Resi-tracking + CreditSmile/MorningReports/HECMMonitor all green.
- `Inbox/auto` (~36.4k items, qrprod/qrtest): full Tue-AM routine suite delivered — Credit Smiles (Master/LH/LH204/OC-DEF/Value/EV), Axe Sheets, Scenario Returns 06-08-26, Risk/Hedge reports, CRT Monitor 20260608, Companion Fund Holdings, Listing File + Galileo Risk Refresh "completed successfully". One **ops** item (not Howard's): `ISSUE: Null tags found on 06/08/2026` (qrprod→ops, CUSIP 89626YAC6) — reporting-tag fix for ops. **Compliance Engine** and **LIBREMAX/SWIB Risk Run** messages present but out of scope — excluded.
- `CLO` folder: all RV lists, surveillance, IO/PO & break-even yields, loan-price, MVOC, spread-model MAE & curve-comparison delivered normally.
- `RESI` folder: clean (newest = Mon-evening LM Deal List; only stale 6/2 `_PSEUDO` failures). `Tracking` folder: new QR Model Tracking Report Mon 17:38 ET; no new "NQM called deal-months" alert.

### Todo
1. **(CLO, top priority — NEW)** Triage `quant-CLO-Model-ColorClean-EOD` (~13 failures this AM, `ValueError: No objects to concatenate`). Check the NULL-date→today defaulting / intraday-trigger timing, guard the empty-concat path, and verify today's CLO color-based outputs aren't degraded.
2. **(RESI)** Patch `quant-ResiTraceFile` `KeyError: 'TRACE'` — short-circuit `export_to_file` on an empty Sentrace result. It re-fails every business-day evening (last #1258, Mon 17:13 ET).
3. **(RESI)** Confirm the residual SIM2-on-HELOC crash still failing `quant-DailySimHistVector` (#14/#1565) after tonight's run; pursue engine roll-back vs. hotfix. Note the new-issue path already recovered (#702).
4. **(RESI/CRT)** Sync with Jay Shaver on the weekend CRT vector failures (`WeekendCRTVectors #326–#329`, `-TrackingVectors #37`) — collateral-count mismatch, distinct from the SIM2 crash.
5. **(Awareness)** Glance at MorningChecks Galileo (`trimaran #115` build fail, `galileo #479` tests fail); confirm `HECMYTRisk #13`, `Daily-CMBS-Model-Intex-CSV #636`, `dpa-nightly-risk-check #2060` aren't yours.
6. **(No action)** Daily CLO + Resi-tracking pipelines healthy; RESI per-cohort tracking clean (stale 6/2 `_PSEUDO` only); new-issue CRT/Figure vectors recovered.
