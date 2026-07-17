## Daily RESI/CLO Summary

_Coverage window: 2026-07-16 05:00 → 2026-07-17 08:11 EDT (business date 20260716). Generated 2026-07-17 08:11 EDT._

### Executive Summary
- **No failed or concerning in-scope RESI/CLO jobs** in the accessible source. Every in-scope qrprod/qrtest report job for business date 20260716 reported Success/OK (CRT Monitor, LMM OAS Pipeline, QL Forward Curves, CLO Loan Pricing, CLO Surveillance, ColorDB parser, Trimaran surveillance, Intex loaders, Listing/Galileo risk refresh).
- **Visibility gap (recurring):** the Outlook MCP connector is not connected in this scheduled/headless run, so only the live `Inbox/auto` **report** feed (qrprod/qrtest) is readable via COM. The **Jenkins build feed** (`quant-*` pipelines) and the per-cohort **RESI Tracking/Unload** emails live in the Online Archive store, which is frozen ~1 year stale (newest 2025-07-14). **Jenkins build outcomes and pseudo-cohort tracking results could NOT be verified this run** — this is not an "all clear" on those.
- Two trading-ops flags appeared in the report feed — `[ACTION NEEDED] Tag Mapping Checker – 2 Unmapped Position(s)` and `ISSUE: Blotter trades missing tags` (both 07-16). These are position-tagging/blotter ops items, **not Howard's RESI/CLO models**; noted for awareness only.
- CLO spread-model MAE / curve-comparison (v2/v2r/delev) emails normally land in the `CLO` archive folder, which is unreachable this run — spread-model status is part of the unverifiable gap, not a confirmed problem.

### Failed / Concerning Jobs
No failed or concerning **in-scope** jobs found from accessible sources.

- Caveat: "accessible sources" = the live `Inbox/auto` report feed only. Jenkins `quant-*` build outcomes and per-cohort RESI Tracking/Unload results were **not verifiable** (archive store ~1 year stale; MCP connector absent). Absence of a failure here does not confirm those pipelines are green.

### RESI Updates
- **Completed (report feed, business date 20260716, all Success/OK):**
  - `CRT Monitor Report 20260716` — qrprod, 07-17 02:05
  - `Success: LMM OAS Pipeline 20260716` — qrprod, 07-16 12:58
  - `Success: QL Forward Curves for 20260716` — qrprod (×3: 05:12, 08:13, 12:47) — dpa forward-curve generation
  - `Swaptions Update: 20260716` — qrtest, 07-16 13:35
  - `Loan index computation` — qrtest, 07-16 19:58
  - `Update Proxy KRD File 20260716 Success` — qrtest, 07-16 16:24
  - `New Bonds Added Update for 07/16/2026` — qrprod
- **In progress / not observed:** New-issue CRT/Figure LMSim vectors (`quant-DailyNewIssueCRTVectors`), `quant-DailySimHistVector`, `quant-ResiTraceFile`, and the monthly Resi-tracking pseudo cohorts report to the Jenkins/RESI archive folders — **not observable this run.**
- **Risks / follow-ups:** Per prior runs, `quant-DailySimHistVector` and `quant-ResiTraceFile` (the `KeyError: 'TRACE'` empty-result bug) had a history of running RED in early June. Status **cannot be confirmed today** — needs the MCP connector or a direct Jenkins check.

### CLO Updates
- **Completed (report feed, business date 20260716, all Success/OK):**
  - `CLO Loan Pricing` — qrtest (07-16 13:25 and 18:49)
  - `CLO Surveillance` — qrtest, 07-16 19:13
  - `Daily ColorDB Parser Stats 2026-07-16` + `Daily SWIB ColorDB Parser Stats 2026-07-16` — qrprod, 07-16 13:50
  - `Trimaran Deal Metrics Surveillance 2026-07-16` — qrprod, 07-16 05:32
  - `Trimaran Distressed Loans Report 20260716` — qrprod, 07-16 06:02
  - `Listing File Generation & Galileo Portfolio Risk Refresh completed successfully for 20260716` — qrtest, 07-17 03:08
  - Intex chain: `SUCCESS: Intex Transaction Loader on 2026-07-16` (20:10), `[OK] intex database checker` (20:30), `Intex data loader` / `ABS data loader` / `Intex data feed localization` (all OK)
- **In progress / not observed:** CLO spread-model runs (GAM v3.0 LO MAE, curve comparison v2/v2r/delev), IO/PO & break-even yields, MVOC — these report to the `CLO` archive folder, **unreachable this run.**
- **Risks / follow-ups:** CLO spread-model daily status could not be verified. If a spread-model MAE/curve-comparison email needs review, check the live folder via the MCP connector or Jenkins directly.

### Email / AUTO Folder Signals
- **Primary source: `Inbox/auto`** (COM, live — 117 items in window; newest 07-17 04:08 after a forced Send/Receive). The full business-date-20260716 overnight batch is present and in-scope report jobs are all Success/OK (see RESI/CLO sections).
- **Non-Howard ops flags noted for awareness** (in `/auto`, qrprod, 07-16): `[ACTION NEEDED] Tag Mapping Checker – 2 Unmapped Position(s)` (15:46) and `ISSUE: Blotter trades missing tags on 07/16/2026` (13:41). Position-tagging / blotter ops — not RESI/CLO model work.
- **Top-level `Inbox`** (COM, live to 07-17 04:11) — 5 items in window, none are in-scope job failures: Tyler Ascione / Bryan Gonnella "Large Risk Differences" replies (risk-run trading threads), John Sim "RMBS Credit Commentary: Picking up ARMs" (research note), Craig Sedaka "Blotter Overview" reply, and an external `[EXTERNAL] Automated Reports - KNOCK-2025-1` custody notice. No GitHub Actions CI-failure notifications this window.
- **Out of scope (excluded per scope memory):** all `LIBREMAX Risk Run` / `SWIB Risk Run` scenario-set notifications, `Daily Resi SSS File Generation completed for 20260716`, and `Compliance Engine 3.0 started/stopped`.
- **Access limitation stated plainly:** the Outlook MCP connector (the only live path to the Jenkins build feed and RESI/CLO custom folders) is not connected in this headless run. COM reaches the live primary Inbox and `Inbox/auto` report feed only; the Online Archive automation folders are frozen ~1 year stale (Jenkins Automation newest 2025-07-14, Tracking 2025-07-10, HECM 2025-07-02; CLO/RESI not present).

### Todo
1. **Restore the Outlook MCP connector for scheduled/headless runs** — the top priority; without it, Jenkins `quant-*` build outcomes and per-cohort RESI Tracking/Unload status cannot be verified in the daily summary (recurring gap).
2. **Manually confirm Jenkins build feed for 20260716** (if any doubt): `quant-DailySimHistVector`, `quant-ResiTraceFile`, `quant-DailyNewIssueCRTVectors`, `quant-CRTDaily-Workflow`, `quant-CLODaily-Workflow-pipeline` — check the live `Jenkins Automation` folder or the Jenkins UI directly, since COM only shows a year-old snapshot.
3. **Spot-check CLO spread-model output** (GAM v3.0 LO MAE / curve comparison v2/v2r/delev) for 07-16 in the live `CLO` folder — not observable this run.
4. No action needed on the report-feed jobs — all in-scope qrprod/qrtest reports for 20260716 completed successfully.
