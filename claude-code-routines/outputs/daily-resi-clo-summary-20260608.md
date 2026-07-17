## Daily RESI/CLO Summary — 2026-06-08 (Monday)

_Source: Howard's Outlook (hzeng@libremax.com). Window reviewed: Sun 6/7 + overnight into Mon 6/8 (~last 24h). Folders checked: `Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`. Times are ET (UTC−4) unless noted. Out-of-scope per standing instructions: LIBREMAX/SWIB risk runs, Resi SSS file generation, Compliance Engine — excluded below._

### Executive Summary
- **NEW, top priority:** `quant-DailyNewIssueCRTVectors` failed twice overnight (#700 timer + #701 Naginator retry, ~02:12 / 03:14 ET Mon) with a **hard native crash** — exit code `-1073740791` (`0xC0000409`, STACK_BUFFER_OVERRUN) in the SIM2 engine (`LMSim2App.dll` v2.0.22-beta5) on the new-issue HELOC deal **FIGRE 2026-HE5**. Both runs died at the identical point → deterministic, not transient. **Monday's new-issue CRT/Figure vectors did not generate.**
- This is the **same SIM2-on-HELOC instability family** that has been red for days: `quant-DailySimHistVector` and the weekend CRT vector pipelines all crash in the SIM2 engine over HELOC/CES/CRT collateral. The `0xC0000409` crash on FIGRE 2026-HE5 strongly points at a native engine bug (the v2.0.22-beta5 build) rather than data/config.
- **Daily RESI + CLO production pipelines otherwise ran clean:** `quant-CLODaily-Workflow-pipeline #272` SUCCESS, `quant-Monthly-ResiTracking-Unload #50` SUCCESS, `quant-CLO-restart-spread-model-celery #57` SUCCESS, plus CreditSmile/HECMMonitor/MorningReports all green. CLO surveillance, IO/PO & break-even yields, loan-price, MVOC, and European RV lists all delivered.
- **Resi tracking is genuinely healthy:** the `RESI` folder shows **no new per-cohort Tracking/Unload failures** — the only FAILED emails there are still the 6/2 `_PSEUDO` ones (already cleared). `Unload #50` SUCCESS is real, not a masked pipeline pass.
- **Carryover still open:** `quant-ResiTraceFile` (`KeyError: 'TRACE'`) hasn't re-fired yet Monday (business-day evening trigger) — will fail again unless patched. `quant-DailySimHistVector` did not run Sunday night; next run Mon night.

### Failed / Concerning Jobs

**1. `quant-DailyNewIssueCRTVectors #700 + #701` — new-issue CRT/Figure LMSim vectors (RESI/CRT) — NEW, FAILED, no recovery [TOP PRIORITY]**
- What failed: `#700` (started by timer, 02:10 ET) and the Naginator retry `#701` (03:12 ET) both finished **Build FAILURE** on Mon 6/8. The SIM2 native engine crashed with `Python failed with exit code -1073740791` = `0xC0000409` (Windows STATUS_STACK_BUFFER_OVERRUN / fast-fail) — a hard process abort, not a Python traceback.
- Where it died: while running the only new-issue deal in the batch, **FIGRE 2026-HE5** (HELOC, model `V2_0_7_HE`, SIM2 engine `\\...\sim_releases\v2.0.22-beta5\windows\LMSim2App.dll`), immediately after `Loading HPA from Redis` / `HPA Manager Load` (asofdate 20260605, collat 20260501). Both runs crash at the exact same step → deterministic on this deal+engine.
- Evidence: `jenkins@libremax.com` → LibreMax-Quants, `Jenkins Automation`. Console: `lm_sim_pub_main.py -as_of_date 20260608 -mode batch-local -request_mode forward_proj -purpose PROD -scenarios_batch weekend -deal_type new_deal`; `Running new issue deals: ['FIGRE 2026-HE5']`; then `Build step 'PowerShell' marked build as failure`.
- Suggested next action: Reproduce FIGRE 2026-HE5 under SIM2 v2.0.22-beta5 in isolation; this is almost certainly the same native crash hitting DailySimHistVector and the weekend CRT vectors. Decide whether to (a) roll the SIM2 engine back to the last stable release for the daily vector jobs, or (b) get a fix/hotfix for the v2.0.22-beta5 HELOC path. Backfill FIGRE 2026-HE5 vectors once the engine is stable.

**2. `quant-ResiTraceFile` — RESI trace-file export (RESI) — carryover, code bug unpatched**
- Status this window: did **not** re-fire (business-day trigger runs ~evening; hadn't run yet as of ~08:00 ET Mon). No new build in the window.
- Evidence/diagnosis (from prior summaries): fails with `KeyError: 'TRACE'` when Sentrace returns no RESI traces — the export step doesn't handle an empty result. Last failed run #1257 (Fri 6/5). Real code bug, not transient.
- Suggested next action: Patch the export step to guard against an empty / `'TRACE'`-missing Sentrace result **before** the Monday-evening trigger fires, or it fails again.

**3. `quant-DailySimHistVector` — LMSim sim-history vectors (RESI) — carryover, no new run**
- Status this window: no Sunday-night run (last failure was `#13` / freestyle `#1564`, Sat 6/6 ~21:03 ET). Next scheduled run is Mon 6/8 night. Same SIM2-engine family as item #1 (HELOC/CES/CRT SIM vectors).
- Suggested next action: Whatever fixes the SIM2 crash for #1 should clear this too; re-check after tonight's run.

**Lower-confidence / borderline (ownership unclear — noted, not owned):**
- `quant-trimaran-galileo-integration-test #114` — **Build FAILURE, Tests NOT_RUN** (Mon 07:55 ET). MorningChecks integration test (report at `S:\QR\Reports\MorningChecks\trimaran-report.html`); build failed before tests ran. In Howard's pipeline list, so worth a glance.
- `quant-galileo-integration-test #478` — Build SUCCESS but **Tests FAILED** (Mon 07:21 ET); the SWIB variant (`#222`) PASSED. Morning smoke test — confirm which Galileo checks regressed.
- `quant-npl-strats #12` — Build FAILURE (Mon 05:15 ET). NPL-strategy job; not in Howard's known RESI/CLO set — flagged for awareness only.
- `quant-MPL-platform-data-update #291` — Build FAILURE (Sun 6/7 00:23 ET, `upgrade_platform_monthly`). Already flagged 6/7; platform/marketplace-lending data, likely not Howard's.

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-Unload #50` SUCCESS (Mon 02:06 ET, to hzeng@). `RESI` folder clean — **no new per-cohort Tracking/Unload failures**; only the stale 6/2 `_PSEUDO` items remain, so the pipeline-level SUCCESS is genuine. `Tracking` folder quiet since 6/2 (last QR Model Tracking Report 6/2). `CRT Monitor Report 20260605` delivered normally (auto).
- **In progress:** New-issue CRT vectors blocked by the SIM2 crash (FIGRE 2026-HE5, see Failed #1). `LM Deal List - All Deals Mapped` last delivered Fri 6/5 (Monday's expected this evening).
- **Risks / follow-ups:** SIM2 native crash on HELOC collateral is the unifying RESI/CRT risk (items #1, #3). `ResiTraceFile` code bug (#2) still unpatched. Clear both Monday.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline #272` SUCCESS (Mon 00:16 ET), `quant-CLO-restart-spread-model-celery #57` SUCCESS (04:55 ET), `quant-stage3-eod-tplus0 #50` SUCCESS. CLO reports delivered: European Lists & Offers 06/08, Surveillance 20260605, IO/PO Yields 20260608, Break-Even Yield 20260605, Loan Price Changes 06/08, Large MVOC Movement 2026-06-05.
- **In progress:** Nothing pending.
- **Risks / follow-ups:** None. No CLO model / spread-model / walk-forward / color-ingestion failures in the window.

### Email / AUTO Folder Signals
- Direct Outlook access was available; this summary is built primarily from it.
- `Jenkins Automation` (~13k items): the new `DailyNewIssueCRTVectors` crash (#700/#701) is the signal; CLO daily + Resi-tracking-unload + CreditSmile/HECMMonitor/MorningReports(#228, recovered from weekend flapping)/morningparalleljobs(#134) all green.
- `Inbox/auto` (~36k items, qrprod/qrtest): full routine report suite delivered Monday AM — Credit Smiles (Master/LH/LH204/OC-DEF/Value/EV), Axe Sheets, Scenario Returns, Risk/Hedge reports, CRT Monitor Report 20260605, Companion Fund Holdings — all normal; no failure/error subjects. **Compliance Engine** and **LIBREMAX/SWIB Risk Run** messages present but **out of scope** — excluded.
- `CLO` folder: European RV lists, surveillance, IO/PO & break-even yields, loan-price, MVOC — all delivered, normal.
- `RESI` folder: clean (see RESI Updates). `Tracking` folder: no new report since 6/2.

### Todo
1. **(RESI/CRT, top priority)** Triage the SIM2 native crash (`0xC0000409`) on **FIGRE 2026-HE5** that killed `quant-DailyNewIssueCRTVectors #700/#701`. Repro under SIM2 v2.0.22-beta5; decide roll-back-to-stable vs. hotfix; backfill the new-issue vectors once green.
2. **(RESI)** Confirm the same SIM2 crash is what's failing `quant-DailySimHistVector` (HELOC/CES/CRT) and the weekend CRT vector pipelines — fix once, clear all three.
3. **(RESI)** Patch `quant-ResiTraceFile` `KeyError: 'TRACE'` (guard empty Sentrace result) before tonight's business-day trigger.
4. **(Awareness)** Glance at `quant-trimaran-galileo-integration-test #114` (build failure) and `quant-galileo-integration-test #478` (tests failed) MorningChecks; confirm `quant-npl-strats #12` / `quant-MPL-platform-data-update #291` aren't yours.
5. **(No action)** Daily CLO + Resi-tracking pipelines are healthy; pseudo-cohort tracking failures remain cleared.
