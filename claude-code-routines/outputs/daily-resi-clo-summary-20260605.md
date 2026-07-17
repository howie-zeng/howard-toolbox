## Daily RESI/CLO Summary

**Date:** 2026-06-05 — covers the last ~24h (2026-06-04 ~08:00 ET → 2026-06-05 ~08:00 ET).
**Sources:** Outlook — `Inbox/auto`, `Jenkins Automation` (104 msgs in window), `CLO`, `RESI`, `Tracking`, `HECM`. Times in US Eastern (ET = UTC−4). Out-of-scope automated risk runs, Resi SSS file generation, and Compliance Engine messages were excluded per standing scope.

### Executive Summary
- **Galileo integration tests are still failing for a 3rd straight morning.** `quant-trimaran-galileo-integration-test #113` = Build FAILURE / Tests **NOT_RUN** (07:55 ET 6/5) and `quant-galileo-integration-test #477` = Tests **FAILED** on a SUCCESS build (07:15 ET 6/5). The SWIB variant (`#221`) passed again. Same pattern as 6/3 (#111/#475) and 6/4 (#112/#476) — needs triage, not transient.
- **`quant-ResiTraceFile` (RESI trace file) has now failed two days running** — `#1255` (6/3 17:13 ET) and `#1256` (6/4 17:13 ET), with no "back to normal" since. It recovered between (`#1254` 6/2), so it is flapping. This is a daily timer-triggered RESI job and wasn't flagged yesterday — worth a look.
- **LMSim vectors still red:** `quant-DailySimHistVector-freestyle #1562` finished Build FAILURE again (6/4 21:00 ET), continuing the multi-day pattern (#1560/#1561 prior) of a small number of "unfinished" vectors marking the whole build failed.
- **Yesterday's CLO spread-file concern is resolved.** `quant-CLODaily-AfternoonWorkflow #885` went **back to normal** (6/4 17:22 ET), and the full CLO daily suite delivered cleanly overnight into 6/5. CLO/CRT daily pipelines, monthly Resi-tracking, and morning report pipelines all SUCCESS.
- **No new per-cohort RESI Tracking/Unload failures** in the `RESI` folder for 6/3–6/4 (latest were 6/2: NONQM/JUMBO2_0/CAS/HELOC_PSEUDO) — the pseudo-cohort tracking issue still looks resolved this cycle.

### Failed / Concerning Jobs

- **Job/source:** `quant-trimaran-galileo-integration-test` + `quant-galileo-integration-test` (Models / QA morning checks) — **failing 3 days running**
  - **What failed:** trimaran `#113` = Build FAILURE, Tests **NOT_RUN** (07:55 ET 6/5); main galileo `#477` = Tests **FAILED** on a SUCCESS build (07:15 ET 6/5). SWIB galileo `#221` PASSED (06:56 ET 6/5).
  - **Evidence:** Playwright reports at `S:\QR\Reports\MorningChecks\trimaran-…` and `S:\QR\Reports\MorningChecks\libremax-report.html`. Identical failure on 6/3 (#111/#475) and 6/4 (#112/#476).
  - **Suggested next action:** Trimaran test still never launches (NOT_RUN ×3) — check the harness/login/session for trimaran-galileo. For the main galileo run, open the report and see which assertions fail. 3 consecutive days = not transient.

- **Job/source:** `quant-ResiTraceFile` (RESI trace file generation) — **failed 2 days running**
  - **What failed:** `#1255` FAILED 6/3 17:13 ET and `#1256` FAILED 6/4 17:13 ET (timer-triggered via `quant-ResiTraceFileTrigger`). No recovery email since. It recovered at `#1254` (6/2) after a 6/1 failure, so it's flapping rather than newly broken.
  - **Evidence:** Jenkins "Build failed in Jenkins: quant-ResiTraceFile #1255/#1256" emails; no later "back to normal".
  - **Suggested next action:** Open the `#1256` console; confirm whether the resi trace file for 6/4 was produced. Recurs at the same time daily — likely a data-availability/timing dependency.

- **Job/source:** `quant-DailySimHistVector-freestyle #1562` (RESI / LMSim vectors) — **still failing**
  - **What failed:** Build marked FAILURE again on the 6/4 evening run (21:00 ET). The freestyle job emails the full vector console log each run; the build is failed by a small number of "unfinished" vectors (0 hard failures in recent runs), same as #1560/#1561.
  - **Evidence:** "Build failed in Jenkins: quant-DailySimHistVector-freestyle #1562" (6/4 21:00 ET). No "back to normal".
  - **Suggested next action:** Open the `#1562` console to get the exact unfinished deal list and re-run those vectors; root-cause why vectors land "unfinished" (worker/queue timeout) rather than hard-fail.

- **Job/source (context — out of core RESI/CLO scope):** `quant-Daily-CMBS-Model-Intex-CSV #634` FAILED 00:18 ET 6/5 (2nd day; #633 failed 6/4). CMBS (commercial), flagged only in case it shares the Intex-loader path with CLO/RESI.

- **Recovered transient overnight failures (no action):**
  - `quant-CLODaily-AfternoonWorkflow #885` → back to normal 6/4 17:22 ET (resolves yesterday's CLO spread-file follow-up).
  - `quant-colordb-run-risk-results #121224` FAILED 17:15 ET → `#121225` back to normal 17:21 ET 6/4 (~6 min).
  - `quant-DailySaveVolSurface #2739` FAILED (6/4 20:07 ET) → `#2740` back to normal (6/4 23:49 ET).
  - `quant-dpa-updateproxykrd #1546/#1547` FAILED (6/4 20:23 / 22:14 ET) → `#1548` back to normal (6/4 23:21 ET).

- **New/experimental jobs (likely dev/test noise, not production):** `quant-cashflows` low-numbered builds churned on 6/4 (#2 FAILURE 15:09 ET, #4 FAILURE 15:41 ET, #7/#8/#10 ABORTED through 18:06 ET); `quant-uv-smoke-test #2` FAILURE (16:10 ET) then #4/#5 SUCCESS; `quant-HECMMonitor #5` ABORTED (16:38 ET). Low build numbers + repeated manual aborts suggest a pipeline being stood up/iterated, not a broken production job. Mention only.

### RESI Updates
- **Completed (6/4):** `quant-Monthly-ResiTracking-pipeline` ran clean (#34–#38 all SUCCESS, ~15:08–18:04 ET — multiple re-runs, all green); `quant-CRTDaily-Workflow #26–#29` SUCCESS; **CRT Monitor Report 20260604** delivered (06:05 ET 6/5 — model 20.12.10e, vector date 4/10/2026, HPA V100); **LM Deal List — All Deals Mapped** (6/4 23:26). `quant-DailyNewIssueCRTVectors` healthy — no failure email since its #697 recovery (6/2), i.e. silent successes since.
- **In progress:** `quant-DailySimHistVector` still finishing each run with a handful of "unfinished" vectors (build FAILURE) — see Failed Jobs.
- **Risks / follow-ups:** `quant-ResiTraceFile` failing 6/3–6/4 (see above). No new per-cohort RESI Tracking/Unload FAILED emails for 6/3–6/4 (latest were 6/2) — pseudo-cohort tracking still looks resolved; worth a confirm.

### CLO Updates
- **Completed (6/4 EOD → 6/5 AM):** `quant-CLODaily-Workflow-pipeline #259–#263` SUCCESS (latest #263 01:10 ET 6/5); `quant-CLODaily-AfternoonWorkflow #885` back to normal (6/4 17:22 ET); `quant-CLO-restart-spread-model-celery #45–#50` SUCCESS. Daily CLO report suite delivered: Surveillance 20260604 (07:17 ET), IO/PO Yields 20260605 (07:05 ET), Break-Even Yield 20260604 (06:24 ET), Loan Price Changes 06/05/26 (05:03 ET), Large MVOC 2026-06-04 (04:46 ET), and RV Lists/Offers (US+Europe 6/4; Europe 06/05 07:41 ET).
- **In progress:** CLO Spread Model LO MAE (GAM v3.0) and Curve Comparison (v2/v2r/delev) for the 6/5 cycle had **not yet arrived** at the ~08:00 ET snapshot — these historically land ~09:00–09:40 ET, so expected later this morning (the 6/4-cycle versions delivered normally). Not a failure; flagging only so it can be eyeballed.
- **Risks / follow-ups:** None outstanding; 6/3 evening spread-file/CAD issue is resolved.

### Email / AUTO Folder Signals
- Direct Outlook access was available. Reviewed `Inbox/auto` (161 msgs in window), `Jenkins Automation` (104 msgs, paged), `CLO` (19 msgs), and the `RESI`, `Tracking`, `HECM` folders.
- **In-scope highlights:** CRT Monitor Report 20260604 (qrprod, 06:05 ET 6/5); full CLO daily suite (qrprod, 6/5 AM); CLO RV / European Lists (qrprod). Jenkins failure/recovery emails as detailed above.
- **`auto` folder is dominated by out-of-scope desk/risk reporting** (Portfolio Sensitivities, Hedge & Summary, Scenario Returns, Credit Smiles, Risk Monitor, Axe Sheet, Rate Hedge, EOD Positions, Form PF Compliance PASS, Companion Holdings) — present and normal, excluded per scope.
- **`HECM` folder:** no new messages in the window (the only HECM signal was `quant-HECMMonitor #5` ABORTED in Jenkins — see experimental jobs).
- **`Tracking` folder:** newest item is a QR Model Tracking Report from 6/2; nothing new 6/3–6/5 (report cadence, not a gap).

### Todo
1. **Triage the Galileo morning-check failures (3rd day).** Trimaran test NOT_RUN ×3 → fix harness/login for trimaran-galileo; review failing assertions in `quant-galileo-integration-test #477`. Reports under `S:\QR\Reports\MorningChecks\`. [Models / QA — highest priority, persistent]
2. **Check `quant-ResiTraceFile #1256`** (failed 6/3 + 6/4) — open console, confirm the 6/4 resi trace file was produced; it recurs at the same daily time, likely a timing/data dependency. [RESI]
3. **Re-run / investigate `quant-DailySimHistVector #1562` unfinished vectors** — open the console for the exact deal list; root-cause the "unfinished" (worker/queue) state. [RESI / LMSim]
4. *(Quick confirm)* Eyeball that the CLO **Spread Model LO MAE + Curve Comparison** for the 6/5 cycle land this morning (~09:00–09:40 ET) as usual. [CLO]
5. *(Optional / context)* Note `quant-Daily-CMBS-Model-Intex-CSV #634` failing 2 days in case it shares Intex-loader infra with CLO/RESI. [context]
