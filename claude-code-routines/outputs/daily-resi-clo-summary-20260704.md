# Daily RESI/CLO Summary — 2026-07-04

## Daily RESI/CLO Summary

### Executive Summary
- **Access gap this run (recurring in scheduled/headless mode):** the Outlook MCP connector — the only path to the live qrprod/qrtest/Jenkins automation feed — is **not connected**. The primary Outlook `Inbox` was reachable via COM and **is current** (newest item 2026-07-03 15:06 EDT), so it was reviewed, but `Inbox/auto` (0 items), `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, and `HECM` are **unreachable** (their only COM-visible copies live in the `Online Archive` store and are frozen ~1 year stale). **I cannot confirm last-24h status of the RESI/CLO pipelines — this is NOT an "all clear."**
- **Holiday, and quiet:** 2026-07-04 is the **US Independence Day** holiday (Saturday). There are **no messages dated 07-04** in the reachable Inbox, and 07-03 carried **no in-scope RESI/CLO items** — only a recurring external custody report and a Datadog digest. No GitHub Actions CI-failure email and no automation/job-failure email appeared over the last 24h in the primary Inbox.
- **No net-new human RESI/CLO item** in the last 24h (yesterday's UNIT 2025-2 SSS was the last one; nothing new since).
- **Open follow-ups unchanged (no new email today):** NQM pseudo-pool design thread (Glenn Perillo) and the dv01 BigQuery per-deal view removal have not moved. The **dv01 cutoff (~2026-07-13, now ~9 days out)** is the most time-sensitive item; the `nqm_hz` LMSimData Pre-Merge failure (06-30) is still an open follow-up.
- **CLO:** no live CLO signal reachable this run (CLO folder unreachable; nothing CLO-specific in the primary Inbox). Status unknown.

### Failed / Concerning Jobs

- **Job/source:** RESI/CLO automation pipelines (SimHistVector, ResiTraceFile, CRTDaily-Workflow, Monthly-ResiTracking, WeekendCRTTrackingVectors, RMBSLoader, CLODaily-Workflow, CLO spread-model, colordb, etc.)
  - **What looks suspicious:** **Status unverifiable this run.** The automation feed (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) is unreachable — MCP connector absent, and the COM-visible copies (in the `Online Archive` store) are ~12 months stale (0 items dated in 2026).
  - **Evidence:** Store/folder probe (2026-07-04 08:13 EDT) — 3 COM stores visible (`Online Archive - hzeng@libremax.com`, `Public Folders`, primary `hzeng@LIBREMAX.com`). Primary `Inbox/auto` = 0 items and the primary store has no `Jenkins Automation`/`CLO`/`RESI`/`Tracking`/`HECM`. Prior context: `quant-DailySimHistVector` and `quant-ResiTraceFile` were RED in early June 2026 (SimHistVector ending short ~99.9%; ResiTraceFile `KeyError: 'TRACE'` on empty results); current status **unknown**.
  - **Suggested next action:** Restore the Outlook MCP connector for scheduled runs (top todo), or check `Jenkins Automation` + `Inbox/auto` + `RESI` folders interactively to confirm job status and whether SimHistVector/ResiTraceFile recovered. Note the holiday: many pipelines may not have run 07-04.

- **No new failed/concerning jobs were found in the reachable primary Inbox** over the last 24h. (This is "nothing new in the reachable source," not a clearance of the pipelines above.)

### RESI Updates
- **Completed:** None confirmed via reachable sources (automation feed dark; holiday).
- **In progress (open follow-ups from prior days — no new email today):**
  - NQM tracking update to include **FCLS and REO** loans (branch `nqm_hz`). As of 06-30 the LMSimData **Pre-Merge Checks** run on `nqm_hz` (commit `5993ba1`) was **failing** (2 annotations); no email since confirms a green re-run or merge.
  - Pseudo-pool redesign for NQM (then JUMBO) so delinquent-status tracking isn't constrained by the prepay/current-loan age filter. Glenn Perillo agreed (06-30) and asked to **see the quantified FCLS/REO coverage impact once complete** — still pending on Howard.
- **Risks / follow-ups:**
  - **dv01 BigQuery view removal (~2026-07-13, ~9 days out):** dv01 is removing individual per-deal job views (e.g., `auto_aggregated_loan_age_data_<deal>`), leaving only asset-class-level views; queries must switch to `... WHERE account_name = '<DEAL>'`. Any RESI pipeline/query relying on per-deal dv01 Data Direct views will break at the cutoff unless migrated. **Most time-sensitive open item.**
  - **RESI market context (reachable Inbox, informational, no action):** Scott Gimpel (webbshill) "Non-QM, Investor-DSCR & Investor-Agency Eligible: June 2026 Remittance" (07-01); JPM "Non-Agency RMBS Deal Comp Sheets: July 2026" (John Sim, 07-01) and "Fixed Income Cross Product Relative Value Monitor" (Peter DeGroot, 07-02) — securitized-product market context.

### CLO Updates
- **Completed / In progress:** No CLO signal reachable this run — the `CLO` folder is not accessible via COM and nothing CLO-specific (spread-model MAE, curve comparison v2/v2r/delev, RV lists, surveillance, MVOC, break-even yields) appeared in the reachable primary Inbox.
- **Risks / follow-ups:** CLO pipeline status (`CLODaily-Workflow`, `CLO-restart-spread-model-celery`, `CLO-Loan-Px-Diff-Email`, colordb) **unknown**. Verify via the connector/interactive Outlook.

### Email / AUTO Folder Signals
> Access note: The `AUTO` automation feed was **NOT reviewable** this run (MCP connector absent; primary `Inbox/auto` empty; automation folders exist only in the `Online Archive` store, frozen ~1 year stale). The items below come from the **primary Outlook `Inbox`** (reachable via COM, current through 2026-07-03 15:06 EDT). Times shown in EDT (ReceivedTime is UTC; local = EDT/UTC-4).

- **Last 24h (07-03 → 07-04 08:13 EDT) — no in-scope RESI/CLO items.** The only 07-03 messages in the reachable Inbox were:
  - Computershare — "Automated Reports - KNOCK-2025-1" (recurring daily custody report, 07-03 15:06 EDT) — external, custody; noted, not flagged.
  - Datadog — "Your Daily Digest from Datadog" (07-03 08:48 EDT) — external monitoring digest; noted, not flagged.
- **Observed earlier in the window but out of scope (not flagged — not Howard's model work):**
  - "Large Risk Differences 07/01/26" thread (qrprod risk-run reconciliation; Tyler Ascione / Samantha Grossman / James Barna, 07-02). Risk team confirmed marks — **James Barna: "RMBS risk is correct."** Automated risk runs are out of scope.
  - Udayaditya Vanaja Renukaprasad — 6× "Fw: … Credit Smile 20260701" (Value/EV/LH/LH204/OC-DEF/Master funds), 07-02. Fund credit-smile / risk-PnL analytics, not RESI/CLO model jobs.
  - UNIT 2025-2 SSS (Powell Eddins → Quants, Connor Hunt confirmed, 07-02); SUNRN 2018-1 SSS (Samantha, 06-30) — ABS SSS deliveries, handled by desk; SSS generation is out of scope.
  - Blotter approvals (Craig Sedaka); Trades Summary / Free Cash (Connor Hunt / Christopher Cheung); Thrive connectivity-failure alerts CS4541378 (IT infra — server being decommissioned, Udaya said ignore); postmaster held-message notices; Datadog/LifeMart/EquiLend/BMI/Ai4/JPM external. Noted, not flagged.
- **Continuity check:** the routine ran fine the last several days — "Daily RESI/CLO Summary - 2026-07-03/-07-02/-07-01" self-sends are in the Inbox (07-03 04:16, 07-02 04:14, 07-01 04:16 EDT).

### Todo
1. **Restore Outlook MCP connectivity for scheduled runs** (or run this summary interactively) — today's automation-feed status (`Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`) is **unknown, not clear**. This is the recurring blocker to verifying last-24h RESI/CLO job health.
2. **Migrate dv01 Data Direct BigQuery queries** off per-deal job views to the asset-class views + `WHERE account_name = '…'` pattern before dv01's ~2026-07-13 cutoff (**~9 days**); confirm which RESI pipelines/queries are affected. *(Most time-sensitive.)*
3. **Confirm the LMSimData `nqm_hz` Pre-Merge Checks are green** (commit `5993ba1` was failing 06-30 with 2 annotations) and merge the FCLS/REO tracking change once passing.
4. **Redesign & regenerate the NQM (then JUMBO) pseudo pools** so delinquent-status tracking isn't constrained by the prepay/current-loan age filter; **quantify the FCLS/REO coverage impact for Glenn** as he requested (still pending on you).
5. **Confirm SimHistVector / ResiTraceFile recovery** — both were RED in early June; verify current status once the feed is reachable (ResiTraceFile still needs the empty-`TRACE`-result `KeyError` code fix if not yet merged).
6. **Check CLO pipeline status** (`CLODaily-Workflow`, spread-model celery, Loan-Px-Diff, colordb) once the `CLO` folder is reachable — no CLO signal was visible this run. *(Account for the 07-04 holiday — some pipelines may not have run.)*

---
*Sources: Outlook primary `Inbox` via win32com COM (reachable, current to 2026-07-03 15:06 EDT; ~4,290 items; scanned 2026-07-04 08:13 EDT). Automation folders (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, `HECM`) were unreachable this run — MCP connector absent in scheduled/headless mode; the only COM-visible copies live in the `Online Archive` store and are frozen ~1 year stale. Out-of-scope items (LIBREMAX/SWIB Risk Runs, Daily Resi SSS File Generation, Compliance Engine) excluded per task scope. 2026-07-04 is a US market holiday (Independence Day).*
