## Daily RESI/CLO Summary

_Coverage window: ~2026-06-29 09:15 → 2026-06-30 (Tuesday run). Risk runs, Resi SSS generation, and Compliance Engine messages are excluded per scope._

> **Data-source caveat (read first):** As with the 2026-06-29 run, this scheduled session could **not** reach Howard's RESI/CLO automation feed. The Outlook MCP connector that interactive runs use is **not connected** in this headless/scheduled session. The fallback (`win32com` COM automation) **works** and the **primary Inbox is live and current** (newest item 2026-06-29 19:07 ET) — but the qrprod/qrtest/Jenkins automation folders are **not present in the COM-visible primary store**, and the only COM-visible copies (in the **Online Archive**) are **frozen at ~2025-06-29 — exactly 12 months stale, zero items dated in 2026**. So **no last-24h RESI/CLO job statuses could be verified.** "No failures below" would be misleading; the correct read is "source unavailable." See _Email / AUTO Folder Signals_ for the diagnostic.

### Executive Summary

- **RESI/CLO automation job status is again UNVERIFIABLE this run** (same access gap as 2026-06-29). Treat overnight job status as "unknown," not "all clear."
- **NEW — actionable vendor change (in scope):** dv01 announced **two breaking changes to dv01 Data Direct**, the feed behind Howard's CRT/Figure LMSim vectors. (1) **BigQuery per-dataset views are being removed** — queries that reference per-deal view names (e.g. `..._allya_2017_1`) must migrate to the asset-class view with a `WHERE account_name = '…'` clause. (2) **Point-of-Sale datasets will stop being rewritten with full history starting July 2026** (mixed write-dates; older data no longer overwritten). dv01 explicitly flagged that "some data ingestion processes set up in specific ways may be affected." **Howard's BigQuery ingestion likely needs an audit/migration before these land.** Jay Shaver (internal) is already in the thread.
- **Mailbox is otherwise healthy/live** — last-24h primary Inbox traffic is normal human + vendor + external research mail.
- **Stale open items from 2026-06-12 remain unverified** (18 days): `quant-DailySimHistVector` was RED on 06-12; the Monthly ResiTracking pseudo-cohort fixes (PR #12760) looked resolved. Neither has been re-checked since the data source went dark.

### Failed / Concerning Jobs

**No RESI/CLO job status could be retrieved from accessible sources** — the automation feed (Jenkins / qrprod / qrtest) was not reachable this run. This is an access gap, **not** confirmation that jobs ran clean. A wide scan of the live primary Inbox (since 2026-06-20, 144 messages) found **zero** qrprod/qrtest/Jenkins-sender mail and **zero** failure-subject mail — confirming the automated feed does not land in the COM-reachable store at all.

- **No new infrastructure failure** appeared in today's 24h window. (The Sun 2026-06-28 06:11 ET `[P1] lm-sql01` SQL Server blip flagged yesterday is **outside** today's window and was already reported — no recurrence since.)

If the source is restored, prioritize confirming the weekend + last-24h status of `quant-DailySimHistVector`, `quant-ResiTraceFile`, `quant-CRTDaily-Workflow`, `quant-RMBSLoader`, `quant-CLODaily-Workflow-pipeline`, and `quant-CLO-restart-spread-model-celery`.

### RESI Updates

- **Completed:** Unknown — automation feed not retrievable this run.
- **In progress:** Unknown — not retrievable this run.
- **Risks / follow-ups:**
  - **NEW — dv01 Data Direct breaking changes (see Executive Summary / Email Signals).** Directly touches the CRT/Figure LMSim vector ingestion. Audit BigQuery queries for per-dataset view references and assess the Point-of-Sale history change before July.
  - **STALE (last verified 2026-06-12, 18 days unverified):** `quant-DailySimHistVector` was RED on 06-12 (recurring Ray-worker tail-of-deals failure); `quant-ResiTraceFile` had the unhandled `KeyError: 'TRACE'` empty-result bug; Monthly ResiTracking pseudo-cohort failures (NONQM/JUMBO2_0/CAS/HELOC_PSEUDO, PR #12760) appeared resolved. **Status since: unknown — re-verify.**

### CLO Updates

- **Completed:** Unknown — automation feed not retrievable this run.
- **In progress:** Unknown — not retrievable this run.
- **Risks / follow-ups (STALE — last verified 2026-06-12):** all CLO model/report jobs (CLODaily workflow, spread-model celery, Spread Model LO MAE/T0 report, curve comparison v2/v2r/delev, ColorClean EOD) were green/self-recovering as of 06-12. **Status since: unknown — re-verify.** No CLO-specific mail reached the accessible primary Inbox this window.

### Email / AUTO Folder Signals

**Direct Outlook access was PARTIAL.** `win32com` COM connected and reads the live mailbox; the dedicated RESI/CLO automation folders were not reachable. Diagnostic:

- **Primary store `hzeng@LIBREMAX.com`:** `Inbox` live and current (3,745 items; newest 2026-06-29 19:07 ET). Its `auto` subfolder exists but is **empty (0 items)**. No `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, or `HECM` folder in the primary store.
- **Online Archive `hzeng@libremax.com`:** holds the named folders in the COM view — `Inbox/auto` (16,168), `Jenkins Automation` (675), `Tracking` (50), `HECM` (7) — **but all frozen ~12 months ago**: newest items 2025-06-29 (auto/Jenkins), 2025-06-27 (Tracking), 2025-06-06 (HECM). **Zero items dated in 2026.** A 12-month archive-retention artifact; current automation mail is not in any COM-reachable store.
- **Conclusion:** the `qrprod@`/`qrtest@`/`jenkins@libremax.com` feed is filed server-side into folders only the Graph/EWS-based Outlook MCP connector can read. That connector is offline in scheduled runs, so the feed is inaccessible here.

**Accessible primary-Inbox items in the window (relevance noted):**

- **2026-06-29 15:32–16:40 ET — dv01 (`mathew@dv01.co` / `support@dv01.co`), thread "dv01 Data Direct – BigQuery job views update" + "…Point of Sale update."** _IN SCOPE / actionable._ dv01 is removing per-dataset BigQuery views (migrate to `WHERE account_name = '…'`) and, from July, will stop full-history rewrites of Point-of-Sale datasets. Internal reply from **Jay Shaver** in the thread — team already engaging. Affects Howard's CRT/Figure vector ingestion.
- **2026-06-29 18:50 ET — Scott Gimpel (`scott@webbshill.com`), "[EXTERNAL] Non-QM RMBS: Delinquency & Prepay Timeline Analysis – by Loan Size."** _RESI context._ External vendor analysis (Non-QM/Investor-DSCR 2021–2025; higher-balance loans perform worse). Useful Non-QM color; no action required.
- **2026-06-29 09:39 / 10:00 ET — Samantha Grossman / Connor Hunt, "UPST 26-3 sss."** Human thread on the UPST 2026-3 deal SSS file. _Note:_ Resi SSS file generation is out of scope per the routine; flagged only in case Howard owns a deal-specific ask here.
- **2026-06-29 05:04 ET — Datadog "[Dashboard Report] Galileo Dashboard – Report."** Scheduled snapshot, informational; no pass/fail detail. (Galileo/Trimaran integration was a flagged item back on 06-12.)
- Routine/out-of-scope: JPM securitized-products RV research (Peter DeGroot), internal trades/hedge/blotter & "Free Cash" ops mail, KNOCK-2025-1 custody report, Datadog daily digests, Large Risk Differences thread (risk runs out of scope).
- **Git/local fallback:** no repo commits since before 2026-06-28 and no report/notebook files modified in the window — no secondary signal there.

### Todo

1. **dv01 Data Direct migration (NEW — actionable now).** Audit Howard's BigQuery ingestion (CRT/Figure LMSim vector pulls, `quant-DailyNewIssueCRTVectors` / `quant-Lmsimdata-push`) for any reference to **per-dataset views** (`..._<deal>` style) and migrate to the asset-class view + `WHERE account_name = '…'`. Separately, assess the **Point-of-Sale full-history-rewrite change (effective July 2026)** against Howard's POS ingestion and reply to dv01 (`support@dv01.co`) if affected. Coordinate with **Jay Shaver** (already in the thread).
2. **Restore the RESI/CLO automation data source (blocks job verification).** Reconnect the Outlook MCP connector for scheduled/headless runs (or fix COM-side sync so the live `auto` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` folders are reachable). Until then this summary cannot confirm job status.
3. **Manually spot-check Jenkins for the last 24h + weekend:** `quant-DailySimHistVector`, `quant-ResiTraceFile`, `quant-CRTDaily-Workflow`, `quant-RMBSLoader`, `quant-CLODaily-Workflow-pipeline`, `quant-CLO-restart-spread-model-celery`, and the Monthly ResiTracking pipeline (cross-check the `RESI` folder for per-cohort FAILED emails — the pipeline wrapper masks them). `http://jenkins.libremax.com/`
4. **Re-verify the stale 06-12 open items** (now 18 days unverified): is `quant-DailySimHistVector` still red? Did the `quant-ResiTraceFile` `KeyError: 'TRACE'` fix land? Are the pseudo-cohort tracking fixes (PR #12760) still holding?
5. **(Process)** The scheduled task still runs without its data connector — the daily summary has now been access-blind for two consecutive runs (06-29, 06-30). Get the connector fixed so these reports regain value.
