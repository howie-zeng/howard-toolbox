## Daily RESI/CLO Summary

_Coverage window: ~2026-06-26 12:00 → 2026-06-29 09:15 ET (Monday run — includes the weekend). Risk runs, Resi SSS generation, and Compliance Engine messages are excluded per scope._

> **Data-source caveat (read first):** This scheduled run could **not** reach Howard's RESI/CLO automation feed. The Outlook MCP connector that prior daily runs used is **not connected** in this headless/scheduled session. The fallback path (Python `win32com` COM automation) **does** work and the mailbox is live — but the dedicated automation folders (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) are **not present in the COM-visible primary mailbox**, and the locally-cached **Online Archive** copies of those folders are **frozen at ~2025-06-29 (zero items dated in 2026)**. As a result, **no last-24h RESI/CLO job statuses could be verified.** "No failures reported below" would be misleading — the correct statement is that the source was unavailable. See _Email / AUTO Folder Signals_ for the full diagnostic.

### Executive Summary

- **The RESI/CLO automation data source was unavailable this run — this report cannot confirm overnight/weekend job status.** Treat "unknown," not "all clear."
- **Root cause:** the Graph/EWS-based Outlook MCP connector (used by prior runs) is offline in this scheduled session. COM automation works and reads the live **primary Inbox** fine (human mail through this morning, 2026-06-29 09:11 ET), but the qrprod/qrtest/Jenkins automation feed is filed into folders that COM cannot see here; the Online Archive copies of those folders contain nothing newer than ~2025-06-29.
- **Mailbox is otherwise healthy/live** — last-48h primary Inbox traffic is normal human + external research mail (trades/hedge summaries, JPM securitized-products research, Datadog digests).
- **One infrastructure signal worth a glance:** a brief **P1 "Can't connect: MS SQL Server database on host lm-sql01"** alert fired **Sun 2026-06-28 06:11 ET and recovered ~06:36 ET** (Datadog). Not a RESI/CLO job itself, but a weekend DB blip can break overnight loaders — worth confirming no run was caught in it once access is restored.
- **Continuity note:** the last saved summary is **2026-06-12** (17-day gap). Open items from that run (below) have **not been re-verified since** and should be re-checked once the data source is fixed.

### Failed / Concerning Jobs

**No RESI/CLO job status could be retrieved from accessible sources** — the automation feed (Jenkins / qrprod / qrtest) was not reachable this run. This is an access gap, **not** confirmation that jobs ran clean.

The only failure-type signal in the accessible (primary) mailbox is infrastructure, not a RESI/CLO model/report job:

- **Job/source:** Datadog monitor → `alert@dtdg.co` (primary Inbox)
- **What looks suspicious:** `[P1] Can't connect: MS SQL Server database on host:lm-sql01` — Triggered 2026-06-28 06:11 ET; "Recovered" 06:15; "No data" 06:34; "Recovered" 06:36. A ~25-minute SQL Server connectivity blip Sunday morning.
- **Evidence:** four Datadog P1 emails 2026-06-28 06:11–06:36 ET in primary Inbox.
- **Suggested next action:** Once the automation feed is reachable again, confirm no overnight RESI/CLO loader/vector job (e.g., `quant-RMBSLoader`, `quant-DailySimHistVector`, CLO loaders) failed during that window. Likely out of Howard's direct scope (infra), flagged only as context.

### RESI Updates

- **Completed:** Unknown — not retrievable this run.
- **In progress:** Unknown — not retrievable this run.
- **Risks / follow-ups (STALE — last verified 2026-06-12, unverified for 17 days):**
  - `quant-DailySimHistVector` was **RED** on 06-12 (Build FAILURE; recurring Ray-worker-death tail-of-deals pattern). **Status since: unknown.** Re-verify.
  - Monthly ResiTracking pseudo-cohort failures (NONQM/JUMBO2_0/CAS/HELOC_PSEUDO, tied to LMQR PR #12760) appeared **resolved** as of 06-12. Confirm still holding.

### CLO Updates

- **Completed:** Unknown — not retrievable this run.
- **In progress:** Unknown — not retrievable this run.
- **Risks / follow-ups (STALE — last verified 2026-06-12):** all CLO model/report jobs (CLODaily workflow, spread-model celery, Spread Model LO MAE, curve comparison v2/v2r/delev, ColorClean EOD) were **green** as of 06-12. **Status since: unknown.** Re-verify.

### Email / AUTO Folder Signals

**Direct Outlook access was PARTIAL.** Python `win32com` COM automation connected successfully and can read the live mailbox, but the specific RESI/CLO automation folders were not reachable. Diagnostic detail (so this can be fixed):

- **Primary mailbox `hzeng@LIBREMAX.com`:** `Inbox` is live and current (1,231 items; newest 2026-06-29 09:11 ET). Its `auto` subfolder exists but is **empty (0 items)**. There is **no** `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, or `HECM` folder in the primary store. A full recursive scan found recent mail (last 48h) **only** in the primary `Inbox` (12 items, all general/external).
- **Online Archive `hzeng@libremax.com`:** this is where the named folders live in the COM view — `Inbox/auto` (16,168), `Jenkins Automation` (675), `Tracking` (50), `HECM` (7) — **but all are frozen ~1 year ago**: newest items are 2025-06-29 (auto/Jenkins), 2025-06-27 (Tracking), 2025-06-06 (HECM). **Zero items dated in 2026.** Consistent with a 12-month archive-retention policy (the archive holds aged-out mail; current mail should be elsewhere) — but the current-mail destination is not visible to COM in this session.
- **No `CLO` or `RESI` folder is visible in either store** via COM.
- **Conclusion:** the automated `qrprod@` / `qrtest@` / `jenkins@libremax.com` feed is filed server-side into folders that only the Graph/EWS-based Outlook MCP connector can read. That connector is offline in this scheduled run, so the feed was inaccessible. (Confirmed: the primary Inbox's only "Jenkins"/"Build failed" matches are four **human reply threads** from 2025-10-16, not the automated feed.)

**Accessible primary-Inbox items in the window (none are Howard's RESI/CLO jobs):**

- 2026-06-29 05:04 ET — Datadog `[Dashboard Report] Galileo Dashboard – Report | Mon 29 Jun 5:00AM EDT` (scheduled dashboard snapshot; informational. Galileo integration tests were a flagged item on 06-12 — but this dashboard email carries no pass/fail detail).
- 2026-06-28 06:11–06:36 ET — Datadog `[P1]` SQL Server connectivity blip on `lm-sql01` (see Failed/Concerning Jobs).
- 2026-06-26 → 06-29 — routine: JPM securitized-products research, Datadog daily digests, internal trades/hedge summaries & "Free Cash" mail. All out of RESI/CLO model-job scope.
- **Git/local fallback:** no repo commits since 2026-06-01 and no report/notebook files modified in the window — no secondary signal there either.

### Todo

1. **Restore the RESI/CLO automation data source (blocks this whole report).** Reconnect the Outlook MCP connector for scheduled/headless runs, or fix the COM-side sync so the live `auto` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` folders are reachable. Until then, the daily summary cannot verify job status.
2. **Manually spot-check Jenkins for the weekend + last 24h** (it's Monday): `quant-DailySimHistVector`, `quant-CRTDaily-Workflow`, `quant-WeekendCRTTrackingVectors`, `quant-RMBSLoader`, `quant-CLODaily-Workflow-pipeline`, `quant-CLO-restart-spread-model-celery`, and the Monthly ResiTracking pipeline (cross-check the `RESI` folder for per-cohort FAILED emails). `http://jenkins.libremax.com/`
3. **Re-verify the 06-12 open item:** is `quant-DailySimHistVector` still red? It had a recurring Ray-worker tail-of-deals failure and was unresolved for multiple days in early June. 17 days unverified.
4. **Confirm the Sun 06-28 06:11 ET SQL Server (`lm-sql01`) blip** didn't catch any overnight RESI/CLO loader/vector job mid-run.
5. **(Process)** Investigate the 17-day gap in saved summaries (last output 2026-06-12) — confirm the scheduled task and its data connector have been running.
