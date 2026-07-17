## Daily RESI/CLO Summary

*Window: 2026-06-01 ~12:00 → 2026-06-02 ~12:00 (last 24h). Source: Outlook (Jenkins Automation, CLO, Inbox/auto folders). Out-of-scope risk runs / Resi SSS / Compliance Engine excluded per scope.*

### Executive Summary
- **NQM pseudo-deal tracking vectors are broken and still red.** `quant-PseudoDeal-Tracking` failed on builds #82/#83/#84 (06-02 ~07:11 ET) with no recovery. Root cause: the SIM2 LMSim vector Ray job timed out after 25,200s (7h) leaving 1 of 3,695 deals unfinished (99.97% succeeded), which marked the whole run failed. This is your area (NQM TRACKING run, `as_of_date=20260601`).
- **CLO daily pipeline fully recovered.** An early `quant-CLODaily-Workflow-pipeline` failure (#235, 06-01 15:34 ET) and an aborted #241 were followed by clean SUCCESS runs (#242, #243). All CLO reports (RV lists, surveillance, IO/PO & break-even yields, loan price changes, MVOC, spread-model MAE, curve comparison v2/v2r/delev) delivered normally.
- **Galileo integration tests are failing.** `quant-trimaran-galileo-integration-test` #110 = Build FAILURE (tests NOT_RUN), and `quant-galileo-integration-test` #474 = Playwright tests FAILED (build itself SUCCESS). Both are on your pipeline list and worth a look.
- **New-issue CRT vectors recovered** — `quant-DailyNewIssueCRTVectors` #697 is "back to normal," so an earlier failure self-cleared.
- A few RESI feeder jobs failed without a visible recovery: `quant-ResiTraceFile` #1253 and `quant-Daily-CMBS-Model-Intex-CSV` #631.

### Failed / Concerning Jobs

**1. quant-PseudoDeal-Tracking (NQM tracking vectors) — STILL BROKEN**
- What failed: Builds #82, #83, #84 all FAILURE (latest 06-02 07:16 ET / 11:16 UTC). Triggered upstream by `quant-Monthly-ResiTracking-Tracking`.
- Evidence: `lm_sim_pub_main.py … -deal_type NONQM_PSEUDO -as_of_date 20260601 -force_rerun -purpose TRACKING` → Ray job `raysubmit_MBZKhNkP11zS2aGP` "timed out after 25200s with status RUNNING," stopped; result "0 failed, 1 unfinished / 3695 total" → "LMSim Vector Process Completed with Failures," exit=1. Also many `lmsimvectors.crt_deal - ERROR: bad filename` lines and `__main__ - ERROR: no collat for deal: NQM DOCTYPE_NEW-Other` / `NQM DOCTYPE_NEW-Tax`. Log: `\\libremax-nas\QR_sanbox\QR\logs\sim\20260602_070437_sim2_raysubmit_MBZKhNkP11zS2aGP.log`.
- Suggested next action: Re-run the single unfinished NQM deal (the "NQM WAC [8-8.25)" bucket showed 1 unfinished) or raise the 7h Ray timeout; investigate the two new NQM DOCTYPE deals with "no collat" (DOCTYPE_NEW-Other, DOCTYPE_NEW-Tax) — likely missing collateral mapping for newly added doc-type buckets.

**2. quant-trimaran-galileo-integration-test #110 — Build FAILURE (tests NOT_RUN)**
- Evidence: 06-02 07:55 ET; "Test Status: NOT_RUN, Build Status: FAILURE." Report at `S:\QR\Reports\MorningChecks\trimara…`. No later recovery seen.
- Suggested next action: Check why tests didn't run (build/setup step failed before Playwright); re-trigger after fix.

**3. quant-galileo-integration-test #474 — Playwright tests FAILED**
- Evidence: 06-02 07:17 ET; "Test Status: FAILED" though "Build Status: SUCCESS." Report `S:\QR\Reports\MorningChecks\libremax-report.html`.
- Suggested next action: Open the Playwright report and confirm whether failures are real regressions vs. flaky/data-availability at run time.

**4. quant-CRTDaily-Workflow #10 — ABORTED**
- Evidence: 06-02 01:21 ET, "finished with status ABORTED." Note #9 (06-01 17:01) and #11 (06-01 17:26) both SUCCESS, so the daily workflow has good runs around it; #10 is the latest event chronologically.
- Suggested next action: Low priority — confirm the abort was an intentional/duplicate trigger and not a stuck stage; verify CRT daily outputs for 20260601 landed.

**5. quant-ResiTraceFile #1253 — Build failed (no recovery seen)**
- Evidence: 06-01 17:13 ET, triggered by `quant-ResiTraceFileTrigger` #433. No "back to normal" within the window.
- Suggested next action: Check whether the Resi trace flat-file for 06-01 was produced; re-run if missing.

**6. quant-Daily-CMBS-Model-Intex-CSV #631 — Build failed (no recovery seen)**
- Evidence: 06-02 00:17 ET. CMBS Intex CSV loader (borderline scope).
- Suggested next action: Confirm whether this is owned by you or the CMBS desk; verify the Intex CSV for 06-01.

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-pipeline` #20/#21 SUCCESS (06-01 17:01/17:26 ET). `quant-DailyNewIssueCRTVectors` recovered (#697 back to normal, 06-02 02:12 ET). CRT Monitor Report 20260601 delivered (qrprod, model v20.12.10e, vector date 4/10/2026). `resi-load-lender-statement-and-accural-report` recovered (#76121 back to normal).
- **In progress / red:** NQM pseudo-deal tracking vectors (`quant-PseudoDeal-Tracking`) still failing — see Failed Jobs #1. `quant-ResiTraceFile` #1253 failed.
- **Risks / follow-ups:** Two new NQM doc-type buckets (DOCTYPE_NEW-Other, DOCTYPE_NEW-Tax) have no collateral mapping; the SIM2 Ray run is bumping the 7h timeout window. Both will keep the monthly Resi tracking run red until addressed.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline` #242 & #243 SUCCESS (06-01 19:30 / 06-02 01:21 ET) after earlier trouble. `quant-CLO-restart-spread-model-celery` #29/#30 SUCCESS. `quant-CLODaily-LoanxLoader` #1795 back to normal. Full CLO report suite delivered: US+Europe RV Lists & Offers, CLO Surveillance 20260601, IO/PO Yields 20260602, Break-Even Yield 20260601, Loan Price Changes 06/02, Large MVOC Movement 2026-06-01, Spread Model LO MAE (GAM v3.0, 2026-01-01→05-29), Spread Model Curve Comparison v2/v2r/delev (05-28 vs 05-29).
- **In progress:** None outstanding — CLO daily chain is green as of 06-02 05:21 UTC.
- **Risks / follow-ups:** The earlier `quant-CLODaily-Workflow-pipeline` #235 FAILURE + #241 ABORTED self-recovered; no action needed, but worth confirming #235's failure cause didn't skip any downstream loader output.

### Email / AUTO Folder Signals
- **Jenkins Automation** (primary signal source): 139 messages in window. All in-scope failures/recoveries captured above. Sender for all build notices: `jenkins@libremax.com` → `LibreMax-Quants@libremax.com`.
- **Inbox/auto** (191 messages): routine `qrprod@libremax.com` end-of-day report feed — Portfolio Sensitivities, Volatility, Credit Smiles (Master/LH/EV/Value/OC-DEF/PC), Axe Sheets, Hedge & Summary, Risk Monitor, Rate Hedge, Scenario Returns, Form PF Compliance PASS, Companion Fund Holdings. All delivered normally; no failure signals. (Out-of-scope risk-run / SSS / Compliance items not surfaced per scope rules.)
- **CLO folder** (19 messages): all CLO RV/surveillance/yield/spread-model reports delivered, no failures.
- No direct-from-person emails requiring a reply were found in the in-scope folders during the window.

### Todo
1. **Fix the NQM pseudo-deal tracking run** (`quant-PseudoDeal-Tracking`): re-run the 1 unfinished NQM deal and/or raise the 7h SIM2 Ray timeout so build #82+ goes green. *(highest urgency — currently red)*
2. **Add collateral mapping** for the two new NQM doc-type buckets `DOCTYPE_NEW-Other` and `DOCTYPE_NEW-Tax` ("no collat for deal" errors).
3. **Triage the Galileo integration tests**: `quant-trimaran-galileo-integration-test` #110 (FAILURE / tests NOT_RUN) and `quant-galileo-integration-test` #474 (Playwright FAILED) — open the MorningChecks reports and re-trigger after fixing.
4. **Verify RESI trace flat-file** for 06-01 (`quant-ResiTraceFile` #1253 failed); re-run if the file is missing.
5. **Confirm `quant-CRTDaily-Workflow` #10 abort** was benign and CRT daily outputs for 20260601 are complete.
6. **Check ownership/output** of `quant-Daily-CMBS-Model-Intex-CSV` #631 (CMBS Intex CSV) — confirm whether yours and whether the 06-01 CSV landed.
