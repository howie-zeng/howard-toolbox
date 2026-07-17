## Daily RESI/CLO Summary

**Date:** 2026-06-04 — covers the last ~24h (2026-06-03 morning ET → 2026-06-04 ~08:00 ET).
**Sources:** Outlook — `Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, `HECM`. Times shown in US Eastern (ET = UTC−4). Out-of-scope automated risk runs, Resi SSS file generation, and Compliance Engine messages were excluded per standing scope.

### Executive Summary
- **CLO evening spread-file pipeline broke (~17:24 ET 6/3) then self-recovered ~8 min later.** `quant-dailyclospreadfile #1097` failed → "FAILURE: CLO CAD File 06/03/26 — not saving spreads/dms due to previous errors", which failed `quant-CLODaily-AfternoonWorkflow #884`. The spread file went back to normal at `#1098` (17:32 ET). Worth a 1-minute confirm that the 6/3 CLO spreads/DMs/CAD file actually saved — no explicit success email was seen.
- **LMSim vector job `quant-DailySimHistVector` is still failing** (#1560 morning 6/3, #1561 overnight). The overnight run finished at 99.93% (6,729/6,734) with **5 vectors "unfinished"** — SCOT 2016-1 (all 3), SEMT 2024-1 (1/4), WFMBS 2022-2 (1/4). Build is marked FAILURE due to unfinished (0 hard failures).
- **Two Galileo integration tests have failed two mornings running:** `quant-trimaran-galileo-integration-test` (#111 6/3, #112 6/4 — Build FAILURE, Tests NOT_RUN) and `quant-galileo-integration-test` (#475/#476 — Tests FAILED on a SUCCESS build). SWIB galileo test passes both days.
- **RESI monthly tracking ran clean** — ResiTracking pipeline #29–#32 all SUCCESS, and **no new per-cohort RESI Tracking/Unload FAILED emails for 6/3** in the RESI folder (the NONQM/JUMBO2_0/CAS/HELOC_PSEUDO failures were 6/2 and earlier). Appears resolved for this cycle.
- CLO daily report suite delivered normally on 6/4 (surveillance, IO/PO & break-even yields, MVOC, loan-price changes, RV lists US+Europe, Spread-Model LO MAE for GAM v3.0, curve comparison v2/v2r/delev). CRT Daily Workflow + CRT Monitor Report delivered.

### Failed / Concerning Jobs

- **Job/source:** `quant-dailyclospreadfile` / "CLO CAD File 06/03/26" / `quant-CLODaily-AfternoonWorkflow #884` (CLO) — **recovered, verify output**
  - **What failed:** `quant-dailyclospreadfile #1097` failed ~17:24 ET 6/3 → qrprod "FAILURE: CLO CAD File 06/03/26 — Not saving spreads/dms due to previous errors" → cascaded to fail AfternoonWorkflow #884. Its other sub-steps (markit-process #2074, CLODaily-LoanxLoader #1801, CLODaily-IntexPricingScan #1787) all SUCCEEDED; only `dailyclospreadfileTrigger #698` failed.
  - **Evidence:** `quant-dailyclospreadfile #1098` "Jenkins build is back to normal" 17:32 ET 6/3 (~8 min later). Next-morning `quant-CLODaily-Workflow-pipeline #256` SUCCESS (01:04 ET 6/4); full CLO 6/4 report suite delivered.
  - **Suggested next action:** Confirm 6/3 CLO spreads/DMs + CAD file were regenerated/saved after #1098 recovered (no standalone "CAD success" email observed). Likely fine but worth a quick check.

- **Job/source:** `quant-DailySimHistVector` (RESI / LMSim vectors) — **still failing**
  - **What failed:** Build marked FAILURE on #1560 (morning 6/3) and #1561 (~21:47 ET 6/3). Latest log: "LMSim Vector Run Failed: 0 failed, 5 unfinished / 6734 total … Job Status: JobStatus.STOPPED." Unfinished deals: SCOT 2016-1 (3/3 unfinished → produced none), SEMT 2024-1 (1/4), WFMBS 2022-2 (1/4). The earlier #1560 had far more unfinished (e.g., JUMBO 2022 rate cohorts with dozens unfinished).
  - **Evidence:** Jenkins build-failure emails; no "back to normal" yet.
  - **Suggested next action:** Re-run the unfinished vectors (esp. SCOT 2016-1); root-cause why vectors finish "unfinished" rather than failed (worker/queue timeout vs. hard error).

- **Job/source:** Galileo integration morning checks — **failing 2 days running**
  - **What failed:** `quant-trimaran-galileo-integration-test` #111 (6/3) & #112 (6/4): Build FAILURE, Tests NOT_RUN. `quant-galileo-integration-test` #475 (6/3) & #476 (6/4): Tests FAILED on a SUCCESS build.
  - **Evidence:** Playwright reports at `S:\QR\Reports\MorningChecks\trimaran-…` and `S:\QR\Reports\MorningChecks\libremax-report.html`.
  - **Suggested next action:** Open the morning-check reports. Trimaran test isn't running at all (NOT_RUN) — check the test harness/launch (login/session) for trimaran-galileo; review which assertions fail in the main galileo run.

- **Job/source (context — likely out of core scope):** `quant-Daily-CMBS-Model-Intex-CSV #633` FAILED ~00:08 ET 6/4. CMBS (commercial), not RESI/CLO — flagging only in case it shares the Intex loader path.

- **Recovered transient overnight failures (no action):** `quant-dpa-hyeneedmail` #1642/#1643 → back to normal #1644 (21:15 ET 6/3); `quant-DailySaveVolSurface` #2736 → back to normal #2737 (20:35 ET 6/3); `quant-deploy-lmqr` #22354 → back to normal #22355 (11:34 ET 6/3, user-triggered deploy by A. Damiani).

### RESI Updates
- **Completed:** ResiTracking monthly pipeline #29–#32 all SUCCESS (6/3). CRT Daily Workflow #20–#23 SUCCESS. CRT Monitor Report 20260603 delivered (model 20.12.10e, vector date 4/10/2026, HPA V100). LM Deal List — All Deals Mapped (6/3 23:26).
- **In progress:** `quant-DailySimHistVector` still finishing with a handful of "unfinished" vectors (see above) — improving (5 unfinished overnight vs. many in the morning run) but still marked FAILURE.
- **Risks / follow-ups:** No new per-cohort RESI Tracking/Unload FAILED emails for 6/3 (prior NONQM/JUMBO2_0/CAS/HELOC_PSEUDO failures were 6/2 and earlier) — looks resolved this cycle; worth confirming pseudo cohorts are fully tracked. Unfinished LMSim vectors above.

### CLO Updates
- **Completed (6/4 AM):** CLODaily-Workflow-pipeline #256, CLO-restart-spread-model-celery #43, Surveillance Report 20260603, IO/PO Yields 20260604, Break-Even Yield 20260603, Large MVOC Movement 2026-06-03, Loan Price Changes 6/4, RV lists US+Europe, Spread Model LO MAE (GAM v3.0 / Spread-Model-LO, 2026-01-01→06-02), Spread Model Curve Comparison v2/v2r/delev (6/1 vs 6/2).
- **In progress:** n/a.
- **Risks / follow-ups:** 6/3 evening spread-file/CAD failure (recovered) — verify saved output (Failed Jobs item #1).

### Email / AUTO Folder Signals
- Direct Outlook access was available. Reviewed `Inbox/auto` (~218 msgs in window), `Jenkins Automation` (91 msgs), `CLO` (21 msgs), plus `RESI`, `Tracking`, `HECM` folders.
- **Notable in-scope messages:** "FAILURE: CLO CAD File 06/03/26" (qrprod, 17:24 ET 6/3); CLO RV / surveillance / IO-PO / break-even / MVOC / loan-price suite (qrprod, 6/4 AM); CLO Spread Model LO MAE + curve-comparison v2/v2r/delev (qrprod, 6/3); CRT Monitor Report 20260603 (qrprod).
- **HECM:** no new messages in the window.
- Standard AUTO risk/hedge/scenario reports (Portfolio Sensitivities, Hedge & Summary, Scenario Returns, Credit Smiles, Risk Monitor, Axe Sheet, Rate Hedge) were present but are out of scope (risk-run/desk reporting) and excluded.

### Todo
1. **Confirm 6/3 CLO spreads/DMs + CAD file saved** after `quant-dailyclospreadfile #1098` recovered (~17:32 ET 6/3). [CLO, quick]
2. **Re-run / investigate `quant-DailySimHistVector` unfinished vectors** — SCOT 2016-1 (produced none), SEMT 2024-1, WFMBS 2022-2; root-cause the "unfinished" (worker/queue) state. [RESI / LMSim]
3. **Triage the two Galileo morning-check failures** — trimaran NOT_RUN (×2), galileo Tests FAILED (×2). Open reports under `S:\QR\Reports\MorningChecks\`. [Models / QA]
4. *(Optional)* Note `quant-Daily-CMBS-Model-Intex-CSV #633` failure in case it shares Intex-loader infra with CLO/RESI. [context]
