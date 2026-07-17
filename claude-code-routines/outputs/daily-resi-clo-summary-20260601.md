## Daily RESI/CLO Summary

*Window covered: 2026-05-30 through 2026-06-01 (Mon AM run, includes the weekend). Source: Howard's Outlook — `Jenkins Automation`, `Inbox/auto`, and `CLO` folders. Out-of-scope categories (LIBREMAX/SWIB risk runs, Daily Resi SSS file generation, Compliance Engine) excluded per standing scope.*

### Executive Summary
- **One job still broken and needs attention: `quant-DailyNewIssueCRTVectors`** — the Monday new-issue run for **FIGRE 2026-HE5** (Figure HELOC, SIM2 engine) crashed twice with a native fault. New-issue CRT/Figure LMSim vectors for that deal were **not produced**.
- Two Galileo integration tests are red: **`quant-trimaran-galileo-integration-test #109` build FAILURE** (tests didn't run) and **`quant-galileo-integration-test #473` tests FAILED** (build itself succeeded).
- Nearly everything else that failed over the weekend **self-recovered by the Monday morning run** — CLO daily workflow, RMBS loader, weekend CRT tracking vectors, ABS data loader, forward curves, morning reports/parallel jobs all ended green.
- **CLO production output is complete and current**: RV lists (US + Europe), Spread Model LO MAE (GAM v3.0), curve comparison (v2/v2r/delev), surveillance, MVOC, IO/PO & break-even yields all delivered for 05/29–06/01.
- One transient infra blip on `quant-tracking-report-recache #896` (Jenkins agent disconnect mid-NQM-recache); the monthly Resi tracking pipeline itself ran clean.

### Failed / Concerning Jobs

**1. quant-DailyNewIssueCRTVectors #695 → #696 — FAILURE (no recovery)**  *(RESI — Howard's pipeline)*
- What failed: New-issue LMSim vector run for **FIGRE 2026-HE5** (deal type HELOC, model `V2_0_7_HE`, SIM2 engine `v2.0.22-beta5`, 15 scenarios). Naginator auto-retried after #695 failed; #696 crashed at the same point.
- Evidence: `#696` received 2026-06-01 07:14 UTC. The Python process aborted with `Python failed with exit code -1073740791` (= 0xC0000409, native stack-buffer-overrun / hard crash in the SIM2 engine), immediately after "Loading HPA from Redis" — i.e. a crash inside the C++ sim DLL, not a data/SQL error. No subsequent SUCCESS or "back to normal" for this job in the window.
- Suggested next action: Re-run the job for as-of 20260601; if it crashes again on FIGRE 2026-HE5, check the SIM2 `v2.0.22-beta5` HELOC engine against the FIGRE2026HE5 collateral/HPA inputs (Redis HPI_MAX_DATE=20260401). This deal's new-issue vectors are missing until resolved.

**2. quant-trimaran-galileo-integration-test #109 — Build FAILURE / Tests NOT_RUN**
- What failed: Build failed before Playwright tests executed. Report: `S:\QR\Reports\MorningChecks\trimaran-report.html`.
- Evidence: received 2026-06-01 11:55 UTC, "Test Status: NOT_RUN, Build Status: FAILURE". No recovery in window.
- Suggested next action: Open the trimaran report / console log to see why the build aborted before the test stage; re-trigger.

**3. quant-galileo-integration-test #473 — Tests FAILED (build SUCCESS)**
- What failed: Build succeeded but the Playwright suite reported failures. Report: `S:\QR\Reports\MorningChecks\libremax-report.html`.
- Evidence: received 2026-06-01 11:17 UTC, "Test Status: FAILED, Build Status: SUCCESS".
- Suggested next action: Review the failing test cases in the report — could be a genuine regression or flaky checks against Galileo.

**4. quant-tracking-report-recache #896 — FAILURE (likely transient infra)**  *(RESI tracking)*
- What failed: NQM pseudo-deal tracking recache. The computation was running normally (only pandas FutureWarnings) when the Jenkins build agent dropped.
- Evidence: received 2026-05-31 13:34 UTC; root error `java.nio.channels.ClosedChannelException` / "Backing channel … is disconnected" (agent 10.0.5.23) — infrastructure, not code. The `quant-Monthly-ResiTracking-pipeline` ran SUCCESS five times on 06-01, so tracking output itself is healthy.
- Suggested next action: Low priority — confirm the recache re-ran cleanly; no action if the Monday tracking reports look complete.

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-pipeline` SUCCESS (#14–#18, 06-01); `quant-CRTDaily-Workflow` SUCCESS (#3–#7, 06-01); `quant-RMBSLoader` recovered (#711 fail → #712 back to normal, 16:13 UTC); `quant-WeekendCRTTrackingVectors` recovered (#33 fail → #35 back to normal, 17:25 UTC); QL Forward Curves "Success" (70 curves, 06-01); Credit Smile (Live) delivered for LH204, EV, LH, Master, Value, OC-DEF funds.
- **In progress:** New-issue vectors for FIGRE 2026-HE5 pending re-run (see Failed #1).
- **Risks / follow-ups:** FIGRE 2026-HE5 new-issue vectors missing until the SIM2 crash is cleared. Weekend-only jobs `quant-WeekendCRTVectors #324` and `quant-WeekendCRTVectorsWorkflow #166` failed Sat 05-30 but were superseded by the clean Monday `quant-CRTDaily-Workflow` run — likely no action, confirm if weekend coverage matters. `quant-MPL-platform-data-update #290` (Marlette/MPL loan data) failed Sun 05-31 — worth a glance if MPL data is needed.

### CLO Updates
- **Completed (all delivered):** CLO RV "US + Europe Lists and Offers" (multiple intraday refreshes 06/01) and "European Lists and Offers"; CLO Spread Model LO MAE Report (GAM v3.0 / Spread-Model-LO, 2026-01-01→05-29); CLO Spread Model Curve Comparison (v2/v2r/delev, 05-28 vs 05-29, 8 models); CLO Relative Value Positions Report (05-29); LibreMax CLO Surveillance Report (20260529); CLO Loan Price Changes (06/01); CLO IO/PO Yields (20260601); CLO Break-Even Yield (20260529); CLO Large MVOC Movement (05-29). `quant-CLO-restart-spread-model-celery` SUCCESS (#21–#26).
- **In progress:** None outstanding.
- **Risks / follow-ups:** `quant-CLODaily-Workflow-pipeline` had a rough start — FAILURE on #227 (Sat) and #228 (Sun), then two ABORTED runs midday Monday (#230, #232, likely manual restarts) — but **ended SUCCESS (#237, 15:27 UTC)**. `quant-CLO-Loan-Px-Diff-Email` recovered (#181 fail → #182 back to normal). No action needed; flag only if the midday aborts were unexpected.

### Email / AUTO Folder Signals
- **`Jenkins Automation`** (primary source, 102 build emails in window): the failure/recovery picture above. Net state Monday close: only DailyNewIssueCRTVectors and the two Galileo integration tests remain red; all other pipelines green.
- **`CLO`** folder: 14 production report emails from `qrprod@libremax.com` (05-30 → 06-01), all delivered with attachments — full CLO report suite is current (see CLO Updates).
- **`Inbox/auto`** folder: `qrprod@libremax.com` production reports flowing normally — Credit Smile (Live) for all funds, QL Forward Curves success, Portfolio Sensitivities, CMBS/CMBX surveillance & distressed-loan reports, CTS Links Q&A. No RESI/CLO failures originate here.
- **Excluded (out of scope, seen but not actioned):** repeated `Compliance Engine 3.0 started/stopped`, `[ERROR] … started`, and `Compliance Engine Process Failed` messages from Compliance@/Compliance_EOD@; LIBREMAX/SWIB risk-run notifications. `quant-colordb-run-risk-results` failed twice Sat then recovered (#120304 back to normal) — risk-run-adjacent, no action.

### Todo
1. **Re-run `quant-DailyNewIssueCRTVectors` for 20260601** and watch FIGRE 2026-HE5. If it crashes again (exit -1073740791), escalate the SIM2 `v2.0.22-beta5` HELOC engine crash — new-issue vectors for this deal are currently missing. *(High)*
2. **Check `quant-trimaran-galileo-integration-test #109`** console/`trimaran-report.html` — find why the build failed before tests ran, then re-trigger. *(Medium)*
3. **Review `quant-galileo-integration-test #473` failing tests** (`libremax-report.html`) — confirm regression vs. flake. *(Medium)*
4. Confirm `quant-tracking-report-recache` re-ran after the agent-disconnect blip; spot-check Monday NQM tracking reports for completeness. *(Low)*
5. Optional: verify weekend CRT vector gaps (`quant-WeekendCRTVectors #324`, `…Workflow #166`) and `quant-MPL-platform-data-update #290` (Marlette) don't leave data holes. *(Low)*
