## Daily RESI/CLO Summary

_Coverage window: ~2026-06-11 12:00 → 2026-06-12 08:00 ET. Source: Howard's Outlook (`Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`, `HECM` folders). Times shown in ET (UTC−4). Risk runs, Resi SSS generation, and Compliance Engine messages are excluded per scope._

### Executive Summary

- **One in-scope job is still red and needs attention:** `quant-DailySimHistVector #18` (LMSim daily sim-history vectors over CRT/NQM/CES/HELOC/Figure) **FAILED** overnight (06-11 20:54 ET) and has not recovered. This matches the known multi-day failure pattern (Ray job dying on a tail of deals).
- **Morning-checks integration tests are red for a 2nd straight day:** `quant-trimaran-galileo-integration-test` (#117 → #118, Build FAILURE / Tests NOT_RUN) and `quant-galileo-integration-test` (#481 → #482, Tests FAILED though build succeeds).
- **Good news — two of Howard's pipelines recovered:** `quant-ResiTraceFile` is **back to normal** (#1261, 06-11 17:13 ET) after its prior `KeyError: 'TRACE'` failures, and the CLO spread-model / color-clean jobs all recovered yesterday afternoon.
- **Core RESI + CLO daily production ran clean:** CRT daily workflow, CLO daily workflow + spread-model celery, and the Monthly ResiTracking pipeline (Tracking #47 / Unload #56) all succeeded. No new per-cohort pseudo-deal failures in the `RESI` folder (the early-June NONQM/JUMBO/CAS/HELOC_PSEUDO failures appear resolved).
- All daily CLO reports (RV lists US+Europe, surveillance, IO/PO & break-even yields, loan price changes, MVOC, spread-model LO MAE, curve comparison v2/v2r/delev) were delivered.

### Failed / Concerning Jobs

**1. quant-DailySimHistVector #18 — STILL RED (Howard's, high priority)**
- Job/source: `Jenkins Automation` → `jenkins@libremax.com`
- What failed: Build FAILURE; LMSim daily sim-history vectors over CRT/NQM/CES/HELOC/Figure deals. No later SUCCESS or "back to normal" — still broken as of latest data.
- Evidence: "quant-DailySimHistVector #18 (quant-DailySimHistVector) finished with status FAILURE" — received 2026-06-12 00:54 UTC (06-11 20:54 ET). Console: `http://jenkins.libremax.com/job/quant-DailySimHistVector/18/`
- Suggested next action: Open the console log; this is the recurring tail-of-deals / Ray-worker-death pattern (job ends short of 100%). Identify the failing deal(s) and either fix the data or make the runner tolerate the dead Ray worker.

**2. quant-trimaran-galileo-integration-test #118 — RED 2 days (Howard's, medium-high)**
- Job/source: `Jenkins Automation` → Playwright Test Report
- What failed: Build Status FAILURE, Test Status NOT_RUN (tests never executed). Same result the prior day (#117).
- Evidence: "quant-trimaran-galileo-integration-test #118 [Tests: NOT_RUN] … Build Status: FAILURE" — 2026-06-12 11:55 UTC (07:55 ET); #117 identical at 06-11 07:55 ET. Report: `S:\QR\Reports\MorningChecks\trimaran...`
- Suggested next action: Tests aren't even starting — likely an environment/setup break in the Trimaran-Galileo harness rather than a test assertion. Check the build step before Playwright launches.

**3. quant-galileo-integration-test #482 — Tests failing 2 days (medium)**
- Job/source: `Jenkins Automation` → Playwright Test Report (MorningChecks)
- What failed: Build SUCCESS but Test Status FAILED (#481 06-11, #482 06-12). The SWIB equivalent (`quant-swib-galileo-integration-test #226`) PASSED, so the failure is specific to the main Galileo check.
- Evidence: "quant-galileo-integration-test #482 [Tests: FAILED] … Build Status: SUCCESS" — 2026-06-12 11:17 UTC (07:17 ET). Report: `S:\QR\Reports\MorningChecks\libremax-report.html`
- Suggested next action: Review the Playwright report to see which assertion(s) are failing; confirm whether it's a real Galileo regression or stale expected values.

**4. quant-HECMYTRisk #17 — FAILURE (HECM; verify ownership)**
- Job/source: `Jenkins Automation` → `jenkins@libremax.com`
- What failed: Build FAILURE (06-11 23:01 ET). Note `quant-HECMMonitor #18` SUCCEEDED ~1.5h later, so the HECM monitor pipeline itself is fine.
- Evidence: "quant-HECMYTRisk #17 (quant-HECMYTRisk) finished with status FAILURE" — 2026-06-12 03:01 UTC. Console: `http://jenkins.libremax.com/job/quant-HECMYTRisk/17/`
- Suggested next action: Confirm whether HECM year-to risk is Howard's; if so, check the console. (Listed because HECM is one of Howard's monitored areas; not the excluded LIBREMAX/SWIB scenario risk runs.)

_For awareness, likely another desk (CMBS, not RESI/CLO):_ `quant-Daily-CMBS-Model-Intex-CSV #639` (FAILURE, 06-12 00:07 ET) and `quant-CMBSLoader #1172` (FAILURE, 06-11 10:39 ET). Flagged only because they touch the Intex loader; do not appear to be Howard's RESI/CLO responsibility.

### RESI Updates

- **Completed / healthy:**
  - `quant-CRTDaily-Workflow #36` — SUCCESS (06-11 14:14 ET).
  - `quant-Monthly-ResiTracking-pipeline #45` — SUCCESS, with sub-jobs `…-Tracking #47` (SUCCESS, 06-11 23:10 ET) and `…-Unload #56` (SUCCESS, 06-12 02:07 ET). **Cross-checked the `RESI` folder: no new per-cohort `FAILED` emails** — the early-June NONQM/JUMBO2_0/CAS/HELOC_PSEUDO failures (tied to LMQR PR #12760) appear resolved this cycle.
  - `quant-ResiTraceFile` — **back to normal (#1261, 06-11 17:13 ET)**, recovering from the prior `KeyError: 'TRACE'` empty-result failures.
  - `quant-ResiPortCreatioin` — back to normal (#1278, 06-11 07:33 ET).
  - `CRT Monitor Report 20260611` delivered (model v20.12.10e, vector date 4/10/2026).
- **In progress / scheduled:** Daily CRT/Figure vector and RESI trace jobs continue on their normal overnight cadence.
- **Risks / follow-ups:**
  - `quant-DailySimHistVector` still failing (see Failed Jobs #1) — the main open RESI item.
  - `Tracking` folder: latest "QR Model Tracking Report" is 2026-06-08; nothing new in the last 24h (expected — monthly cadence).

### CLO Updates

- **Completed / healthy:**
  - `quant-CLODaily-Workflow-pipeline #277` — SUCCESS (06-12 00:51 ET).
  - `quant-CLO-restart-spread-model-celery #62` — SUCCESS (06-12 04:50 ET).
  - Daily CLO reports all delivered: CLO RV Lists & Offers (US+Europe), CLO Surveillance Report 20260611, CLO IO/PO Yields, CLO Break-Even Yield, CLO Loan Price Changes, CLO Large MVOC Movement Report.
  - Model monitoring delivered: **CLO Spread Model LO MAE Report** (GAM v3.0 / Spread-Model-LO, 2026-01-01→2026-06-10) and **Spread Model Curve Comparison v2/v2r/delev** (06-09 vs 06-10).
- **Recovered yesterday afternoon (were red, now green):**
  - `quant-CLO-Spread-Model-LO-Report-T0-Workflow #448` (back to normal 06-11 09:24 ET) and its EUR variant `#135` (back to normal 06-11 12:26 ET).
  - `quant-CLO-Model-ColorClean-EOD #17128` (back to normal 06-11 09:08 ET) after a run of ~20 consecutive failures earlier that morning (#17106–#17127, upstream `quant-CLO-Intraday-Workflow`).
- **In progress / scheduled:** Normal CLO daily + intraday cadence resumed.
- **Risks / follow-ups:** None currently open — all CLO model/report jobs are green as of the latest run. Worth a glance at the ColorClean failure cluster root cause in case it recurs.

### Email / AUTO Folder Signals

Direct Outlook access **was available** — all findings above are from live mailbox queries.

- **`Jenkins Automation` (~97 messages in window):** primary source for build status; failures/recoveries detailed above. Sender `jenkins@libremax.com`.
- **`Inbox/auto` (qrprod/qrtest feed):** daily report deliveries — Master Fund Portfolio Sensitivities/Volatility 20260611, Hedge & Summary Reports, CRT Monitor Report 20260611, Credit Smiles (LH/EV/Value/Master/OC-DEF), Risk Monitor, Form PF Compliance (PASS), Axe Sheets, Rate Hedge updates. All informational/completions; nothing failed.
- **`CLO` folder:** 19 messages in window — all the daily CLO RV/surveillance/yield/price/MVOC/spread-model reports listed under CLO Updates. All delivered.
- **`RESI` folder:** latest items are routine "LM Deal List – All Deals Mapped" (06-11 23:26 ET). Most recent `FAILED` per-cohort emails date to 2026-06-02 — none in the last 24h.
- **`Tracking` folder:** no new messages in window (last report 06-08).
- **`HECM` folder:** no new messages in window (the HECMYTRisk failure reported via `Jenkins Automation`, not this folder).

### Todo

1. **Fix `quant-DailySimHistVector`** (open & recurring). Pull console log for build #18, identify the deal(s) on which the Ray job dies, and either patch the data or make the runner resilient to the dead worker so the run reaches 100%.
2. **Triage the Galileo morning checks** (red 2 days):
   - `quant-trimaran-galileo-integration-test` — Build FAILURE / Tests NOT_RUN → fix the pre-test setup so Playwright actually runs.
   - `quant-galileo-integration-test` — Tests FAILED on a passing build → review `libremax-report.html` for the failing assertions (SWIB equivalent passes, so it's Galileo-specific).
3. **Confirm `quant-HECMYTRisk #17`** ownership; if it's yours, check the console (HECMMonitor itself is green).
4. **(Optional)** Note the `quant-CLO-Model-ColorClean-EOD` failure cluster from 06-11 morning (now recovered) and the CMBS Intex/loader failures — pass the CMBS ones to the owning desk if not yours.
5. **(No action)** Confirm the Monthly ResiTracking pseudo-cohort fix is holding — this cycle ran clean with no per-cohort failures.
