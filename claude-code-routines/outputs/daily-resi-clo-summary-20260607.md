## Daily RESI/CLO Summary — 2026-06-07 (Sunday)

_Source: Howard's Outlook (hzeng@libremax.com). Window reviewed: ~last 36h (Sat 6/6 + overnight into Sun 6/7), with Fri 6/5 evening carryover for weekend jobs. Folders checked: `Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`, `HECM`. Times are ET unless noted. Out-of-scope per standing instructions: LIBREMAX/SWIB risk runs, Resi SSS file generation, Compliance Engine — excluded below._

### Executive Summary
- **Daily RESI + CLO production pipelines ran clean over the weekend.** `quant-CLODaily-Workflow-pipeline` (#270 Sat, #271 Sun) and `quant-Monthly-ResiTracking` Tracking #40 / Unload #48–#49 all reported **SUCCESS**, and CLO surveillance, loan pricing, Intex loaders, and Credit Smiles all completed.
- **Good news on Resi tracking:** the `RESI` folder shows **no per-cohort Tracking/Unload failures this cycle** — the NONQM/JUMBO/CAS/HELOC `_PSEUDO` failures seen on/before 6/2 did **not** recur, so the SUCCESS at the pipeline level is genuine this time.
- **Three of Howard's RESI/CRT jobs remain RED for multiple days, no recovery:** (1) `quant-DailySimHistVector` (LMSim sim-history vectors) — failed again Sat night (#13 / freestyle #1564); (2) `quant-ResiTraceFile` (#1257, KeyError `'TRACE'`); (3) the **weekend CRT vector pipelines** (`WeekendCRTVectorsWorkflow #167`, `WeekendCRTTrackingVectors #36`) failed Fri evening and have not re-run/recovered. These are the carryover items needing Howard's attention Monday.
- Two lower-confidence/borderline failures to glance at: `quant-HECMYTRisk #12` (HECM) and `quant-MPL-platform-data-update #291` — ownership unclear; noted for awareness.

### Failed / Concerning Jobs

**1. `quant-DailySimHistVector` — LMSim sim-history vectors (RESI) — STILL FAILING (multi-day)**
- What failed: Both the pipeline job (`#12` Fri night 6/5, `#13` Sat night 6/6 ~21:03 ET) and the freestyle job (`#1563` 6/5, `#1564` 6/6 ~21:03 ET) finished **Build FAILURE**. No SUCCESS / "back to normal" at any point in the window.
- Evidence: `jenkins@libremax.com` → LibreMax-Quants, in `Jenkins Automation`. Truncated console output shows it is processing HELOC/CES/CRT SIM vectors (e.g. `AOMT 2025-HB2 | HELOC | V1_0_V4_HE | SIM2`, `FIGRE 2024-HE1 | HELOC | V2_0_7_HE`). Prior daily summaries (6/4, 6/5, 6/6) flagged this same job; the 6/4 note recorded an overnight run finishing at **99.93% (6,729/6,734)** with ~5 vectors short — i.e. a small tail of deals failing, not a total outage.
- Suggested next action: This is the top carryover. Check the latest console log for `quant-DailySimHistVector/13` to identify which 5-ish deals/vectors are failing and whether the Ray job is dying at the tail. Decide whether to backfill the missing vectors manually.

**2. `quant-ResiTraceFile #1257` — RESI trace file export — STILL FAILING (multi-day)**
- What failed: **Build FAILURE** Fri 6/5 ~17:13 ET (triggered by `quant-ResiTraceFileTrigger`). Now failed across #1254–#1257 (6/3, 6/4, 6/5), no recovery. Did not re-run over the weekend (business-day trigger).
- Evidence: `jenkins@libremax.com`, `Jenkins Automation`. Prior summary diagnosed the root cause: `KeyError: 'TRACE'` — a code bug where the export step doesn't handle the case when Sentrace returns **no RESI traces** (empty result). Characterized as a real code bug requiring a fix, not transient.
- Suggested next action: Patch the export step to guard against an empty/`'TRACE'`-missing Sentrace result. Will fail again Monday when the trigger fires unless fixed.

**3. `quant-WeekendCRTVectorsWorkflow #167` + `quant-WeekendCRTTrackingVectors #36` — weekend CRT vectors — FAILED, no recovery**
- What failed: Both **Build FAILURE** Fri 6/5 ~19:02 ET; console shows `20260605 19:02:33:ERROR:` in the WeekendCRTTrackingVectors run. No subsequent re-run or "back to normal" observed over the weekend.
- Evidence: `jenkins@libremax.com`, `Jenkins Automation`. The 6/6 summary tied these to the same underlying disruption that took down DailySimHistVector ("hundreds of CRT/NQM/CES/HELOC deals came back with vectors and the Ray job ended").
- Suggested next action: Confirm whether weekend CRT tracking vectors actually need a successful run before Monday's business-day CRT pipeline, or whether Monday's `quant-DailyNewIssueCRTVectors` / `quant-CRTDaily-Workflow` will supersede them. Re-trigger if the weekend vectors are needed.

**Lower-confidence / borderline (ownership unclear — noted, not owned):**
- `quant-HECMYTRisk #12` — Build FAILURE Fri 6/5 ~22:40 ET; no recovery seen. HECM is a product Howard tracks, but this is a risk-flavored job — confirm whether it's his.
- `quant-MPL-platform-data-update #291` — Build FAILURE Sun 6/7 ~00:23 ET (`upgrade_platform_monthly`). Looks like platform/marketplace-lending data, likely not Howard's RESI/CLO model work — flagged for awareness only.

_Recovered during the window (no action needed): `quant-ListingReport #1597` (after #1596), `quant-CreditSmile-Workflow #715` (after #714 / morningparalleljobs #133), `quant-Daily-CMBS-Model-Intex-CSV #635`, `quant-ABS-Data-Loader-Weekend #229`. `quant-MorningReports-pipeline` flapped (#225 FAIL → #226 OK → #227 FAIL) but is a broad shared report pipeline, not specifically Howard's._

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-Tracking #40` SUCCESS (Fri night), `Unload #48` (Sat) and `#49` (Sun) SUCCESS. **No** per-cohort `RESI Tracking/Unload FAILED` emails this cycle in the `RESI` folder — the earlier NONQM/JUMBO2_0/CAS/HELOC `_PSEUDO` failures (≤6/2) did not recur. `LM Deal List - All Deals Mapped` last delivered Fri 6/5.
- **In progress:** None new over the weekend (Tracking-report folder quiet since 6/2; new-issue CRT vectors are business-day jobs, none expected on the weekend).
- **Risks / follow-ups:** LMSim vector job (`DailySimHistVector`) and `ResiTraceFile` both still red (see Failed Jobs #1, #2) — these are the RESI items to clear Monday. Weekend CRT vectors (#3) also unresolved.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline #270` (Sat 00:42 ET) and `#271` (Sun 00:12 ET) SUCCESS. CLO Surveillance, CLO Loan Pricing, Intex data loader/localization, Loan index computation, ABS data loader, and `SUCCESS: Intex Transaction Loader on 2026-06-06` (0 failed / 21 successful) all OK. `CLO Loan Price Changes 06/05` and `CLO Large MVOC Movement Report for 2026-06-05` generated. Credit Smile reports (Master/LH/LH204/OC-DEF/Value/EV) produced 6/6.
- **In progress:** Nothing pending.
- **Risks / follow-ups:** None. No CLO model/spread-model/walk-forward failures observed in the window.

### Email / AUTO Folder Signals
- Direct Outlook access was available; this summary is built primarily from it.
- `Jenkins Automation` (~13k items): see Failed/Recovered jobs above — the RESI/CRT failures are the signal; CLO + Resi daily pipelines green.
- `Inbox/auto` (~36k items, qrtest/qrprod): CLO surveillance/pricing/Intex/loan-index/ABS loaders all reported OK overnight; Credit Smiles, Axe Sheets, Scenario Returns, and MVOC/loan-price reports generated normally. **Compliance Engine** `[ERROR] lost connection` / started / stopped messages (6/7 ~00:00 ET) — **out of scope**, excluded. **LIBREMAX Risk Run / Nightly risk check** notifications (incl. CRT/RMBS/CLO bond results and a FAILURE→back-to-normal flap) — **out of scope**, excluded.
- `CLO` folder: only the 06/05 Loan Price Changes and Large MVOC Movement reports — both normal.
- `RESI` folder: clean this cycle (see RESI Updates). `Tracking` folder: no new QR Model Tracking Report since 6/2. `HECM` folder: no new messages since 6/5.

### Todo
1. **(RESI, top priority)** Triage `quant-DailySimHistVector` — pull console log for build `#13`/freestyle `#1564`, identify the ~5 failing deals/vectors and why the Ray job ends short; backfill or fix so Monday's run is green.
2. **(RESI)** Fix the `quant-ResiTraceFile` `KeyError: 'TRACE'` bug (handle empty Sentrace result in the export step) before the Monday business-day trigger fires.
3. **(CRT/RESI)** Decide if the failed weekend CRT vector pipelines (`WeekendCRTVectorsWorkflow #167` / `WeekendCRTTrackingVectors #36`) need a re-run, or whether Monday's `quant-DailyNewIssueCRTVectors` / `quant-CRTDaily-Workflow` covers it.
4. **(Awareness)** Glance at `quant-HECMYTRisk #12` and `quant-MPL-platform-data-update #291` failures to confirm they aren't yours; reassign/ignore as appropriate.
5. **(No action)** Confirm nothing else — daily CLO + Resi tracking pipelines are healthy; the earlier pseudo-cohort tracking failures have cleared.
