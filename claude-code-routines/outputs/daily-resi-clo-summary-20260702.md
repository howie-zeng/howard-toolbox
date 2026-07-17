# Daily RESI/CLO Summary — 2026-07-02

## Daily RESI/CLO Summary

### Executive Summary
- **Access gap this run (same as expected in scheduled/headless mode):** the Outlook MCP connector — the only path to the live qrprod/qrtest/Jenkins automation feed — is **not connected**. The primary Outlook `Inbox` was reachable via COM and **is current** (newest item 2026-07-02 07:51 UTC), so it was reviewed, but `Inbox/auto` (0 items), `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, and `HECM` are **unreachable this run** (not present in any COM-visible store). **I cannot confirm last-24h status of the RESI/CLO pipelines — this is NOT an "all clear."**
- **No new in-scope failures in the reachable Inbox:** unlike 06-30/07-01, there is **no GitHub Actions CI-failure email** and **no automation/job-failure email** in the primary Inbox over the last 24h. Quiet day for reachable in-scope signal.
- **No new human RESI/CLO threads today:** the NQM pseudo-pool design thread (Glenn Perillo) and the dv01 BigQuery-view thread have not moved in the last 24h — but both remain **open follow-ups** (see below).
- **Time-sensitive carry-over:** the **dv01 Data Direct per-deal BigQuery view removal (~2026-07-13, ~11 days out)** is still pending migration; and the **LMSimData `nqm_hz` Pre-Merge Checks failure** (from 06-30) needs a confirmed green before merge — no email today confirms either is resolved.
- **CLO:** no live CLO signal reachable this run (CLO folder unreachable; nothing CLO-specific in the primary Inbox). Status unknown.

### Failed / Concerning Jobs

- **Job/source:** RESI/CLO automation pipelines (SimHistVector, ResiTraceFile, CRTDaily-Workflow, Monthly-ResiTracking, WeekendCRTTrackingVectors, RMBSLoader, CLODaily-Workflow, CLO spread-model, colordb, etc.)
  - **What looks suspicious:** **Status unverifiable this run.** The automation feed (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) is unreachable — MCP connector absent, and the COM-visible stores do not expose these folders (the Online Archive store contains only standard/PnL folders, no automation folders; `Inbox/auto` = 0 items).
  - **Evidence:** Store/folder probe (2026-07-02 08:11 EDT) — 3 COM stores visible (`Public Folders`, primary `hzeng@LIBREMAX.com`, `Online Archive`); primary `Inbox/auto` = 0 items; Online Archive tree has no `Jenkins Automation`/`CLO`/`RESI`/`Tracking`/`HECM`. Prior context: `quant-DailySimHistVector` and `quant-ResiTraceFile` were RED in early June 2026 (SimHistVector ending short ~99.9%; ResiTraceFile `KeyError: 'TRACE'` on empty results); current status **unknown**.
  - **Suggested next action:** Restore the Outlook MCP connector for scheduled runs (top todo), or check `Jenkins Automation` + `Inbox/auto` + `RESI` folders interactively to confirm today's job status and whether SimHistVector/ResiTraceFile recovered.

- **No new failed/concerning jobs were found in the reachable primary Inbox** over the last 24h. (This is a genuine "nothing new in the reachable source," not a clearance of the pipelines above.)

### RESI Updates
- **Completed:** None confirmed via reachable sources (automation feed dark).
- **In progress (open follow-ups from prior days — no new email today):**
  - NQM tracking update to include **FCLS and REO** loans (branch `nqm_hz`). As of 06-30 the LMSimData **Pre-Merge Checks** run on `nqm_hz` (commit `5993ba1`) was **failing** (2 annotations); no email today confirms a green re-run or merge.
  - Pseudo-pool redesign for NQM (then JUMBO) so delinquent-status tracking isn't constrained by the prepay/current-loan age filter. Glenn Perillo agreed (06-30) and asked to **see the quantified FCLS/REO coverage impact once complete** — still pending on Howard.
- **Risks / follow-ups:**
  - **dv01 BigQuery view removal (~2026-07-13):** dv01 is removing individual per-deal job views (e.g., `auto_aggregated_loan_age_data_<deal>`), leaving only asset-class-level views; queries must switch to `... WHERE account_name = '<DEAL>'`. Any RESI pipeline/query relying on per-deal dv01 Data Direct views will break at the cutoff unless migrated. ~11 days out.
  - **New RESI context (reachable Inbox, informational):** JPM "Non-Agency RMBS Deal Comp Sheets: July 2026" (John Sim, 07-01 14:45Z) and "Fixed Income Cross Product Relative Value Monitor" (Peter DeGroot, 07-02 07:51Z, notes securitized-product sectors remain attractive vs. corporates). Useful market context for Non-QM/RMBS work; no action.

### CLO Updates
- **Completed / In progress:** No CLO signal reachable this run — the `CLO` folder is not accessible via COM and nothing CLO-specific (spread-model MAE, curve comparison v2/v2r/delev, RV lists, surveillance, MVOC, break-even yields) appeared in the reachable primary Inbox.
- **Risks / follow-ups:** CLO pipeline status (`CLODaily-Workflow`, `CLO-restart-spread-model-celery`, `CLO-Loan-Px-Diff-Email`, colordb) **unknown**. Verify via the connector/interactive Outlook.

### Email / AUTO Folder Signals
> Access note: The `AUTO` automation feed was **NOT reviewable** this run (MCP connector absent; primary `Inbox/auto` empty; automation folders not present in any COM-visible store). The items below come from the **primary Outlook `Inbox`** (reachable via COM), which is current through 2026-07-02 07:51 UTC. Times shown in UTC.

- **No in-scope RESI/CLO job, CI, or human-thread emails arrived in the last 24h.** Notably, no GitHub Actions failure notification today (contrast with 06-30's `nqm_hz` Pre-Merge failure).
- **Context / market research (not action items):**
  - Peter DeGroot — "Fixed Income Cross Product Relative Value Monitor…" — 2026-07-02 07:51Z. Securitized-product sectors flagged attractive vs. U.S. corporates. *(RESI/CLO market context.)*
  - John Sim — "Non-Agency RMBS Deal Comp Sheets: July 2026" — 2026-07-01 14:45Z. *(Non-QM/RMBS context.)*
- **Observed but not flagged (not Howard's model work):**
  - Udayaditya Vanaja Renukaprasad — 6× "Fw: … Credit Smile 20260701" (Value/EV/LH/LH204/OC-DEF/Master funds), 07-02 06:16–06:18Z. *(Fund credit-smile / risk-PnL analytics, not RESI/CLO model jobs.)*
  - Thrive / Udaya Puvvadi — "CS4541378 - Alert: Connectivity Failure | LibreMax Capital LLC" thread, opened 07-01 13:38Z, **marked Resolved 07-01 23:51Z**. *(IT/network MSP ticket; not a RESI/CLO job.)*
  - Computershare — "Automated Reports - KNOCK-2025-1" (07-01 19:06Z); Craig Sedaka — "Re: Blotter Overview 2026-07-01" (17:56Z); Datadog daily digest; EquiLend/LifeMart external. *(Custody/trading/monitoring/promo — noted, not flagged.)*

### Todo
1. **Restore Outlook MCP connectivity for scheduled runs** (or run this summary interactively) — today's automation-feed status (`Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`) is **unknown, not clear**. This is the recurring blocker to verifying last-24h RESI/CLO job health.
2. **Confirm the LMSimData `nqm_hz` Pre-Merge Checks are green** (commit `5993ba1` was failing 06-30 with 2 annotations) and merge the FCLS/REO tracking change once passing.
3. **Redesign & regenerate the NQM (then JUMBO) pseudo pools** so delinquent-status tracking isn't constrained by the prepay/current-loan age filter; **quantify the FCLS/REO coverage impact for Glenn** as he requested (still pending on you).
4. **Migrate dv01 Data Direct BigQuery queries** off per-deal job views to the asset-class views + `WHERE account_name = '…'` pattern before dv01's ~2026-07-13 cutoff (~11 days); confirm which RESI pipelines/queries are affected.
5. **Confirm SimHistVector / ResiTraceFile recovery** — both were RED in early June; verify current status once the feed is reachable (ResiTraceFile still needs the empty-`TRACE`-result `KeyError` code fix if not yet merged).
6. **Check CLO pipeline status** (`CLODaily-Workflow`, spread-model celery, Loan-Px-Diff, colordb) once the `CLO` folder is reachable — no CLO signal was visible this run.

---
*Sources: Outlook primary `Inbox` via win32com COM (reachable, current to 2026-07-02 07:51 UTC; 3,947 items). Automation folders (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, `HECM`) were unreachable this run — MCP connector absent in scheduled/headless mode; COM-visible stores (`Public Folders`, primary, `Online Archive`) do not expose the automation folders and `Inbox/auto` = 0 items. Out-of-scope items (LIBREMAX/SWIB Risk Runs, Daily Resi SSS File Generation, Compliance Engine) excluded per task scope.*
