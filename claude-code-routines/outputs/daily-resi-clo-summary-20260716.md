## Daily RESI/CLO Summary

_Coverage window: 2026-07-15 ~08:12 EDT → 2026-07-16 ~04:23 EDT (new material since the 07-15 summary). Machine clock (2026-07-16 08:11) matched the scheduled-task date — no date drift, and 07-15 is the newest prior summary on file, so no multi-day gap._

_**Source & sync note (better coverage than recent runs):** the Outlook MCP connector is again absent in this scheduled run, so the fallback was Python `win32com` COM. **This run the primary `Inbox/auto` feed is back online and synced live to 07-16 04:07 EDT (1,903 items)** — the full overnight qrprod/qrtest automation batch is visible, unlike recent runs where `/auto` read empty. The top-level primary Inbox synced to 07-16 04:23. **The Jenkins build feed remains unreachable** — the `Jenkins Automation`/`CLO`/`RESI`/`Tracking`/`HECM` folders exist only in the Online Archive store and are frozen ~1 year stale (Jenkins newest item 2025-07-14), so individual `quant-*` build outcomes could not be verified. See access note._

### Executive Summary
- **Overnight RESI/CLO automation ran clean — no in-scope failures.** With `/auto` back online, the 07-16 overnight report feed is fully visible and every in-scope pipeline that reports there succeeded: CRT Monitor Report, Daily ColorDB parser, CLO Loan Pricing, CLO Surveillance, Trimaran surveillance, Intex loaders, LMM OAS Pipeline, QL Forward Curves, and the Galileo listing/risk refresh. The many "N bonds failed" emails in the feed are all **LIBREMAX/SWIB Risk Runs — out of scope** (not Howard's).
- **Jenkins build feed still can't be verified (not an "all-clear").** The `quant-*` build jobs — including the known-red `quant-DailySimHistVector` and `quant-ResiTraceFile`, plus the CRT/RMBS/CLO daily pipelines and CLO spread-model MAE/curve-comparison jobs — report in the archive-only `Jenkins Automation` folder, which is stale ~1 year. Their downstream report outputs succeeded (indirect good sign), but the builds themselves warrant a manual spot-check in the Outlook client.
- **`nqm_hz` CI-failure break holds (7th day clear):** zero new `LMSimData` Pre-Merge Checks failure emails through 07-16 04:23. GitHub emails **failures only**, so this is still **not a confirmed green** — verify the branch/PR state directly before merging the NQM fix.
- **dv01 BigQuery cutover is now 4 days out — hard deadline Mon 2026-07-20.** dv01 will remove the per-dataset/job BigQuery views; queries must move to the asset-class-level views with a `WHERE <dataset_name>` filter. Any RESI pipeline still on single-dataset views breaks Monday unless migrated first. No new email on this in the window; the clock is running.
- **No new email traffic on the open CLO/NQM threads this window** — Yiming's long-term USD BBB/BB spread-model review, EUR spread-model release, NQM Modeling sign-off, and the new-issue SSS ownership asks (CPS 2026-C / AXIS 2026-1A / RPM 2026-4A) are all still open and carry forward.

### Failed / Concerning Jobs
- **No failed or concerning in-scope jobs found from accessible sources across 2026-07-15 → 2026-07-16.** All in-scope automation reporting in `/auto` completed (SUCCESS / [OK] / "completed successfully"). Every bond-level failure in the feed belongs to the out-of-scope **LIBREMAX Risk Run / SWIB Risk Run** notifications (e.g. "68 successful, 1 failed", "33 successful, 33 failed", CRT/CLO/HECM/RMBS-STATIC/COMMERCIAL/CON-ABS bonds) and is intentionally ignored per scope.

_Access caveat (this is **not** proof the pipelines were green): the **Jenkins `quant-*` build feed is unreachable** this run. The RESI/CRT builds (`quant-CRTDaily-Workflow`, `quant-DailyNewIssueCRTVectors`, `quant-DailySimHistVector` +`-freestyle`, `quant-ResiTraceFile`, `quant-RMBSLoader`, `quant-Monthly-ResiTracking-*`), per-cohort `RESI Tracking/Unload FAILED`, and the CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC build jobs are **not verifiable from the accessible feeds.** `quant-DailySimHistVector` and `quant-ResiTraceFile` are known to run red (SimHistVector tail-of-deals; ResiTraceFile `KeyError: 'TRACE'` empty-result bug) — spot-check them manually._

### RESI Updates
- **Completed (07-16 overnight, from the `/auto` feed):**
  - **CRT Monitor Report 20260715** generated 07-16 02:05 (Model Version 20.12.10e, Model Vector Date 4/10/2026, HPA V100) — the daily CRT surveillance report ran fine.
  - **Intex Transaction Loader — SUCCESS** (07-15 20:09) and **intex database checker [OK]** (07-15 20:30); Intex/ABS data loaders and Intex feed localization ran through the day.
  - **LMM OAS Pipeline — Success** (07-15 12:57) and **QL Forward Curves — Success** (07-15 05:12 / 08:13 / 12:48; relates to `quant-dpa-ForwardCurveGeneration`).
- **In progress:**
  - **NQM model update (`nqm_hz` in `LMSimData`).** Pre-Merge Checks failure-email streak still clear (no failures 07-10 → 07-16 04:23). Green is **not confirmed** (failures-only email) — verify the branch/PR state before landing.
  - **NQM dial / framework work (carry-over, awaiting Modeling sign-off).** No new email this window on the permanent (non-decaying) deep-delinquent dials, the dialed-NQM-CDR-vs-base comparison, or the plan to add FCLS→REO transitions / switch to STACR deep-delinquent models. Still pending sign-off.
- **Risks / follow-ups:**
  - **dv01 Data Direct — BigQuery per-dataset views removed Mon 2026-07-20 (hard deadline, 4 days out).** Confirm all of Howard's / the quants' RESI dv01 BigQuery pulls are migrated to the asset-class-level views with a `WHERE <dataset_name>` filter (asset-class views are already live), or ask Jay Shaver to request an extension.
  - Confirm `nqm_hz` is actually green, then land the NQM fix (stopped failure emails ≠ proof).
  - Get Modeling sign-off on the two deliberate-but-material NQM decisions (permanent non-decaying dials; NQM CDR above base) before shipping the FCLS-REO / STACR deep-delinquent framework change.
  - **New-issue SSS ownership** — still open: Samantha Grossman's `CPS 2026-C` / `AXIS 2026-1A` (07-14) and the earlier `RPM 2026-4A` (07-09). Confirm whether any new-deal onboarding falls to Howard.
  - **Spot-check `quant-DailySimHistVector` and `quant-ResiTraceFile` in the Outlook client** — both known red and unverifiable from the accessible feeds this run.

### CLO Updates
- **Completed (07-15 → 07-16, from the `/auto` feed):**
  - **CLO Loan Pricing** ran (07-15 13:25 and 18:48; relates to `quant-CLO-Loan-Px-Diff-Email`).
  - **CLO Surveillance** ran (07-15 19:13).
  - **Daily ColorDB Parser Stats + Daily SWIB ColorDB Parser Stats** generated 07-15 13:50 — **CLO color parse rate 81%** (137 parsed / 33 failed), which is healthy; overall cross-sector rates were RMBS 42% / ABS 46% / CMBS 62% (routine daily stats — many inbound dealer emails are non-parseable color, so moderate rates are normal, not a job failure). This is Howard's BWIC/color-ingestion lane.
  - **Trimaran Distressed Loans Report** (07-15 06:02: 83 distressed loans, $660.7M par, 10.7% distressed rate) and **Trimaran Deal Metrics Surveillance** (07-15 05:31) generated.
  - **Listing File Generation & Galileo Portfolio Risk Refresh — completed successfully** (07-16 03:05; relates to `quant-trimaran-galileo-integration-test`).
- **In progress / carry-over (no new email this window):**
  - **Yiming Zhang's long-term USD BBB/BB DM spread models** — the active 07-14 thread (non-delevered-only rows, Desk Tier as a feature, dropping EquityNAV/PercentLe90 from BB, adding VIX; Glenn's ask to expose categorical coefficients). No further traffic 07-15 → 07-16 in the reachable feeds — **still awaiting Howard's review/reply.**
  - **Release the EUR spread models** — Yiming's 07-08 handoff ("go ahead, non-delev changes are benign"). No release confirmation in the reachable Inbox. Settle directly.
- **Risks / follow-ups:**
  - **Review Yiming's revised USD BBB/BB analysis and weigh in** — Howard's spread-model lane; the thread went quiet but the design choices are still open.
  - CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC **build outcomes not verifiable** (Jenkins feed unreachable) — the downstream CLO pricing/surveillance/ColorDB reports did run, but confirm the model-fit builds in the Outlook client.

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM, with forced Send/Receive. Confirmed this run:
- **The primary store `hzeng@LIBREMAX.com` `Inbox/auto` feed is back online and current** — 1,903 items, newest 07-16 04:07 EDT. This carries the full qrprod/qrtest overnight automation batch (portfolio/risk reports, CRT Monitor, ColorDB, CLO pricing/surveillance, Trimaran, Intex, forward curves, OAS). **This is a coverage improvement over the last several runs, where `/auto` read 0 items.**
- **The top-level primary Inbox** synced to 07-16 04:23 (count 5,067). It carries human mail + GitHub CI notifications; the 07-15 20:00 → 07-16 04:23 window held only 2 items, both out of scope (a Thrive IT disk-space alert; Bryan Gonnella's "risk differences are reasonable" reply). Early-morning (post-04:23) human mail may not have synced yet.
- **The archive automation folders remain stale ~1 year** — `Jenkins Automation` 1,505 items (newest 2025-07-14), `HECM` newest 2025-07-02, `Tracking` newest 2025-07-10. These are a rolling-retention snapshot, **not the live feed** — the Jenkins `quant-*` build outcomes cannot be verified from them.
- **Net:** the qrprod/qrtest report feed is verified clean for the window; the Jenkins `quant-*` build feed is unverified.

Relevant / notable messages this window:
- **07-16 04:07 — qrtest/qrprod overnight batch (`/auto`):** CRT Monitor 20260715, ColorDB + SWIB ColorDB parser stats, CLO Loan Pricing, CLO Surveillance, Trimaran surveillance, Intex loaders (SUCCESS/[OK]), LMM OAS Pipeline (Success), QL Forward Curves (Success), Galileo listing/risk refresh (completed successfully). **All in-scope items succeeded; detailed above.**
- **07-16 04:23 — Bryan Gonnella:** `RE: Large Risk Differences 07/15/26` — "Risk Differences are reasonable." Out-of-scope risk-run reconciliation; no action for Howard.
- Noise / out-of-scope (ignored): all `LIBREMAX Risk Run` / `SWIB Risk Run` bond-failure emails; `Daily Resi SSS File Generation completed` (07-16 02:06); `Compliance Engine 3.0 started/stopped` + `PASS - Form PF Compliance`; desk/ops reports (Free Cash, Trades Summary, Hedge, Axe Sheet, Credit Smile, VaR, Portfolio Volatility/Sensitivities); CMBS surveillance; a Thrive IT alert; `[ACTION NEEDED] Tag Mapping Checker – 2 Unmapped Position(s)` (07-15 15:47, ops data-mapping, not RESI/CLO model work); and external research (JPM, Scott Gimpel Non-QM originator analysis).

### Todo
1. **Beat the dv01 BigQuery cutover (Mon 2026-07-20 — now 4 days out).** Confirm every RESI dv01 BigQuery pull is migrated off single-dataset views to the asset-class views with a `WHERE <dataset_name>` filter (asset-class views are already live), or ask Jay Shaver to request an extension. **Highest priority — hard external deadline.**
2. **Manually spot-check the Jenkins `quant-*` build feed for 07-15 → 07-16 via the Outlook client** — not reachable this run: `quant-DailySimHistVector` (+`-freestyle`) and `quant-ResiTraceFile` (both known red), the CRT/RMBS/CLO daily pipelines, per-cohort `RESI Tracking/Unload FAILED`, and CLO spread-model MAE / curve-comparison / MVOC. Their downstream reports ran clean, but confirm the builds.
3. **Review Yiming's long-term USD BBB/BB CLO spread-model analysis and reply.** Howard's lane; thread went quiet 07-15 → 07-16 but the design choices are open (non-delevered-only rows, Desk Tier feature, dropping EquityNAV/PercentLe90 from BB, adding VIX, exposing categorical coefficients per Glenn).
4. **Confirm `nqm_hz` Pre-Merge Checks is actually green and land the NQM model fix.** Failure emails clear 07-10 → 07-16, but GitHub emails failures only — verify the branch/PR state directly. Unblocks the NQM dial / FCLS-REO / STACR framework merge.
5. **Get Modeling sign-off on the two NQM decisions** (permanent non-decaying deep-delinquent dials; NQM CDR above base), then ship the FCLS-REO / STACR deep-delinquent framework change once the branch is green.
6. **Close out the EUR spread-model release with Yiming** (07-08 handoff, non-delev benign) — still no release confirmation in the reachable Inbox.
7. **Confirm ownership of the new-issue SSS asks** — `CPS 2026-C` / `AXIS 2026-1A` (Samantha Grossman, 07-14) and the still-open `RPM 2026-4A` (07-09). Quick check on whether any RESI/CLO model or vector setup falls to Howard.
8. **Restore the Outlook MCP connector for scheduled runs** so the live `Jenkins Automation` / `CLO` / `RESI` / `Tracking` build feeds are covered directly — this run the `/auto` report feed came back (good), but the Jenkins `quant-*` build outcomes still can't be verified via COM. Recurring blocker.
