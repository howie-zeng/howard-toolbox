# Daily RESI/CLO Summary — 2026-07-06

## Daily RESI/CLO Summary

### Executive Summary
- **First business day after the July 4th holiday weekend — nothing new in scope reachable.** 2026-07-03 was the observed Independence Day holiday, 07-04 Saturday, 07-05 Sunday. The reachable primary Inbox shows **no new messages at all since 2026-07-04 12:45 EDT** (a Datadog digest) as of this 07-06 08:11 EDT run — **no GitHub Actions CI-failure email, no automation/job-failure email, no new human RESI/CLO thread.**
- **Access gap this run (recurring in scheduled/headless mode) — this is NOT an "all clear."** The Outlook MCP connector — the only path to the live qrprod/qrtest/Jenkins automation feed — is **not connected**. The primary Outlook `Inbox` was reachable via COM and **is current**, but `Inbox/auto` (0 items), `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, and `HECM` are **unreachable** (COM-visible copies live only in the frozen `Online Archive` store, ~1 year stale: newest items 2025-07-05). **Today's (07-06) post-holiday RESI/CLO pipeline status cannot be verified from reachable sources.**
- **This is the first real post-holiday cycle to check.** 07-03/07-04/07-05 pipelines likely did not run (holiday + weekend), so the **07-06 overnight/morning cycle is the first meaningful health check** for Jenkins/CLO/RESI jobs — and it is exactly what is *not* visible this run.
- **Most time-sensitive open item: the dv01 BigQuery per-deal view removal, cutoff ~2026-07-13 — now ~7 days out.** Any RESI pipeline/query on dv01 Data Direct per-deal views must migrate to the asset-class views + `WHERE account_name = '…'` pattern before then. No email moved this thread over the holiday weekend.
- **Routine itself is healthy:** the "Daily RESI/CLO Summary - 2026-07-04" self-send is in the Inbox (07-04 08:15 EDT), confirming the prior run and email delivery succeeded.

### Failed / Concerning Jobs

- **Job/source:** RESI/CLO automation pipelines (SimHistVector, ResiTraceFile, CRTDaily-Workflow, Monthly-ResiTracking, WeekendCRTTrackingVectors, RMBSLoader, CLODaily-Workflow, CLO spread-model, colordb, etc.)
  - **What looks suspicious:** **Status unverifiable this run.** The automation feed (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) is unreachable — MCP connector absent, and the COM-visible copies (in the `Online Archive` store) are ~12 months stale (newest 2025-07-05; 0 items dated in 2026).
  - **Evidence:** Store/folder probe (2026-07-06 08:11 EDT) — 3 COM stores visible (`hzeng@LIBREMAX.com`, `Online Archive - hzeng@libremax.com`, `Public Folders`). Primary `Inbox/auto` = 0 items; the primary store has no `Jenkins Automation`/`CLO`/`RESI`/`Tracking`/`HECM`. Archive-store probe: `auto`=16,786 (newest 2025-07-05), `Jenkins Automation`=1,200 (newest 2025-07-05), `Tracking`=50 (newest 2025-06-27), `HECM`=32 (newest 2025-07-02). Prior context: `quant-DailySimHistVector` and `quant-ResiTraceFile` were RED in early June 2026 (SimHistVector ending short ~99.9%; ResiTraceFile `KeyError: 'TRACE'` on empty results); current status **unknown**.
  - **Suggested next action:** Restore the Outlook MCP connector for scheduled runs (top todo), or check `Jenkins Automation` + `Inbox/auto` + `RESI` folders interactively to confirm today's post-holiday job status and whether SimHistVector/ResiTraceFile recovered.
- **No new failed/concerning jobs were found in the reachable primary Inbox** over the last 24h. (This is "nothing new in the reachable source," not a clearance of the pipelines above.)

### RESI Updates
- **Completed:** None confirmed via reachable sources (automation feed dark; post-holiday weekend).
- **In progress (open follow-ups from prior days — no new email over the holiday weekend):**
  - NQM tracking update to include **FCLS and REO** loans (branch `nqm_hz`). As of 06-30 the LMSimData **Pre-Merge Checks** run on `nqm_hz` (commit `5993ba1`) was **failing** (2 annotations); no email since confirms a green re-run or merge.
  - Pseudo-pool redesign for NQM (then JUMBO) so delinquent-status tracking isn't constrained by the prepay/current-loan age filter. Glenn Perillo agreed (06-30) and asked to **see the quantified FCLS/REO coverage impact once complete** — still pending on Howard.
- **Risks / follow-ups:**
  - **dv01 BigQuery view removal (~2026-07-13, ~7 days out):** dv01 is removing individual per-deal job views (e.g., `auto_aggregated_loan_age_data_<deal>`), leaving only asset-class-level views; queries must switch to `... WHERE account_name = '<DEAL>'`. Any RESI pipeline/query relying on per-deal dv01 Data Direct views will break at the cutoff unless migrated. **Most time-sensitive open item.**
  - **RESI market context (reachable Inbox, informational, no action):** Scott Gimpel "Non-QM, Investor-DSCR & Investor-Agency Eligible: June 2026 Remittance" (07-01, external); John Sim "Non-Agency RMBS Deal Comp Sheets: July 2026" (07-01); Peter DeGroot "Fixed Income Cross Product Relative Value Monitor" (07-02). Securitized-product market/data context only.

### CLO Updates
- **Completed / In progress:** No CLO signal reachable this run — the `CLO` folder is not accessible via COM and nothing CLO-specific (spread-model MAE, curve comparison v2/v2r/delev, RV lists, surveillance, MVOC, break-even yields) appeared in the reachable primary Inbox.
- **Risks / follow-ups:** CLO pipeline status (`CLODaily-Workflow`, `CLO-restart-spread-model-celery`, `CLO-Loan-Px-Diff-Email`, colordb) **unknown**. Verify via the connector/interactive Outlook once the feed is reachable (first post-holiday cycle is 07-06).

### Email / AUTO Folder Signals
> Access note: The `AUTO` automation feed was **NOT reviewable** this run (MCP connector absent; primary `Inbox/auto` empty; automation folders exist only in the frozen `Online Archive` store, newest 2025-07-05). The items below come from the **primary Outlook `Inbox`** (reachable via COM, current). Times in EDT (COM `ReceivedTime` is UTC-tagged; local = EDT = UTC−4).

- **Last 24h+ (07-05 → 07-06 08:11 EDT) — no in-scope RESI/CLO items and, in fact, no new messages of any kind.** The most recent Inbox item is a Datadog digest at 07-04 12:45 EDT; nothing has landed on 07-05 (Sunday) or 07-06 morning yet.
- **Earlier in the window (07-01→07-04), out of scope or informational — not flagged:**
  - Datadog "Your Daily Digest" (07-04, 07-03, 07-02, 07-01) — external monitoring digests.
  - Computershare "Automated Reports - KNOCK-2025-1" (07-01/-02/-03 ~19:06 EDT) — recurring daily external custody report.
  - "Large Risk Differences 07/01/26" thread (Tyler Ascione / Samantha Grossman / James Barna, 07-02) — automated risk-run reconciliation; **out of scope**.
  - UNIT 2025-2 SSS (Powell Eddins → Connor Hunt confirmed, 07-02) — ABS SSS delivery handled by the desk; SSS file generation is **out of scope**.
  - Udayaditya Vanaja Renukaprasad — 6× "Fw: … Credit Smile 20260701" (Value/EV/LH/LH204/OC-DEF/Master, 07-02) — fund credit-smile/risk-PnL analytics, not RESI/CLO model jobs.
  - Blotter Overview (Craig Sedaka); Free Cash / Trades Summary + Hedge Changes (Christopher Cheung / Connor Hunt) — desk ops. Thrive CS4541378 connectivity-failure alerts (07-01, IT infra; resolved). Datadog/LifeMart/EquiLend/BMI external marketing; postmaster held-message notices. Noted, not flagged.
- **Continuity check:** the routine ran fine the last several days — self-sends "Daily RESI/CLO Summary - 2026-07-04 / -07-03 / -07-02 / -07-01" are all in the Inbox (04:xx–08:xx EDT).

### Todo
1. **Restore Outlook MCP connectivity for scheduled runs** (or run this summary interactively) — today's automation-feed status (`Jenkins Automation`, `Inbox/auto`, `CLO`, `RESI`, `Tracking`) is **unknown, not clear**. This is the recurring blocker to verifying last-24h RESI/CLO job health.
2. **Migrate dv01 Data Direct BigQuery queries** off per-deal job views to the asset-class views + `WHERE account_name = '…'` pattern before dv01's ~2026-07-13 cutoff (**~7 days**); confirm which RESI pipelines/queries are affected. *(Most time-sensitive.)*
3. **Check today's post-holiday (07-06) automation cycle** once the feed is reachable — 07-03/07-04/07-05 pipelines likely did not run, so 07-06 is the first meaningful health check for Jenkins/CLO/RESI jobs. Watch specifically for SimHistVector/ResiTraceFile and the CLODaily/spread-model jobs.
4. **Confirm the LMSimData `nqm_hz` Pre-Merge Checks are green** (commit `5993ba1` was failing 06-30 with 2 annotations) and merge the FCLS/REO tracking change once passing.
5. **Redesign & regenerate the NQM (then JUMBO) pseudo pools** so delinquent-status tracking isn't constrained by the prepay/current-loan age filter; **quantify the FCLS/REO coverage impact for Glenn** as he requested (still pending on you).
6. **Confirm SimHistVector / ResiTraceFile recovery** — both were RED in early June; verify current status once the feed is reachable (ResiTraceFile still needs the empty-`TRACE`-result `KeyError` code fix if not yet merged).
7. **Check CLO pipeline status** (`CLODaily-Workflow`, spread-model celery, Loan-Px-Diff, colordb) once the `CLO` folder is reachable — no CLO signal was visible this run.

---
*Sources: Outlook primary `Inbox` via win32com COM (reachable, current; 4,391 items; scanned 2026-07-06 08:11 EDT — 50 items in the trailing 5-day window, newest 2026-07-04 12:45 EDT). Automation folders (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, `HECM`) were unreachable this run — MCP connector absent in scheduled/headless mode; the only COM-visible copies live in the `Online Archive` store and are frozen ~1 year stale (newest 2025-07-05). Secondary sources checked: no workspace git commits since before 07-01; no report/log/output files modified in the last 48h other than the prior daily summaries. Out-of-scope items (LIBREMAX/SWIB Risk Runs, Daily Resi SSS File Generation, Compliance Engine) excluded per task scope. 2026-07-03 was the observed US market holiday (Independence Day); 07-04 Saturday, 07-05 Sunday.*
