# Daily RESI/CLO Summary — 2026-07-01

## Daily RESI/CLO Summary

### Executive Summary
- **Access gap this run:** the Outlook MCP connector (the only path to the live qrprod/qrtest/Jenkins automation feed) is **not connected in scheduled/headless runs**, as expected. The primary Outlook `Inbox` was reachable via COM and **is current** (newest item 2026-07-01 01:32 UTC), so it was reviewed — but `Inbox/auto` (0 items in the primary store) and the `Jenkins Automation` / `CLO` / `RESI` / `Tracking` folders are **unreachable/frozen ~1 yr stale**. **I cannot confirm last-24h status of the RESI/CLO pipelines from this run — this is NOT an "all clear."**
- **One confirmed in-scope failure:** LMSimData **Pre-Merge Checks** GitHub Actions run **failed** on Howard's `nqm_hz` branch (commit `5993ba1`), 2 annotations, failed in 3m38s.
- **Active RESI design item (Howard-led):** Howard flagged a pseudo-pool construction inconsistency in NQM/JUMBO/HELOC tracking that materially under-counts FCLS/REO deep-delinquent loans. Glenn Perillo agreed and asked to see the quantified impact once the redesign is done.
- **Upcoming external dependency risk:** dv01 is **removing per-deal BigQuery "job views" in ~2 weeks** (~mid-July). Single-dataset queries must migrate to the asset-class view + `WHERE account_name = '...'` pattern or they will break.
- **CLO:** no live CLO signal reachable this run (CLO folder unreachable; nothing CLO-specific in the primary Inbox). Status unknown.

### Failed / Concerning Jobs

- **Job/source:** LMSimData — `Pre-Merge Checks` GitHub Actions workflow (repo `LibreMax-QR/LMSimData`)
  - **What failed:** "All jobs have failed" — `pre-merge-checks` job failed in 3m38s with **2 annotations**, on branch/context `nqm_hz`, commit `5993ba1`.
  - **Evidence:** GitHub notification email in primary Inbox, 2026-06-30 14:31 UTC (10:31 EDT), subject `[LibreMax-QR/LMSimData] Run failed: Pre-Merge Checks - nqm_hz (5993ba1)`.
  - **Suggested next action:** Open the run, review the 2 failing annotations, fix, and confirm green before merging `nqm_hz`. This is the branch behind the NQM FCLS/REO tracking work below.

- **Job/source:** RESI/CLO automation pipelines (SimHistVector, ResiTraceFile, CRTDaily-Workflow, Monthly-ResiTracking, WeekendCRTTrackingVectors, RMBSLoader, CLODaily-Workflow, CLO spread-model, colordb, etc.)
  - **What looks suspicious:** **Status unverifiable this run.** The automation feed (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) is unreachable — MCP connector absent, and the COM-visible archive copies are frozen at ~2025-06-29.
  - **Evidence:** Store/folder probe — primary `Inbox/auto` = 0 items; `Online Archive` `Jenkins Automation`/`auto`/`Tracking` newest ~2025-06-27/29. Prior context: `quant-DailySimHistVector` and `quant-ResiTraceFile` were running **RED** in early June 2026 (SimHistVector ending short ~99.9%; ResiTraceFile `KeyError: 'TRACE'` on empty results); whether they're still broken is **unknown**.
  - **Suggested next action:** Restore the Outlook MCP connector for scheduled runs (top todo), or check `Jenkins Automation` + `Inbox/auto` + `RESI` folders interactively to confirm today's job status and whether SimHistVector/ResiTraceFile recovered.

### RESI Updates
- **Completed:** None confirmed via reachable sources (automation feed dark).
- **In progress:** NQM tracking update to include **FCLS and REO** loans (branch `nqm_hz`) — pre-merge checks currently failing (see above). Pseudo-pool redesign proposed for NQM (then JUMBO).
- **Risks / follow-ups:**
  - **Pseudo-pool age-filter design flaw:** For JUMBO/HELOC/NQM, pseudo pools apply one broad age filter (e.g., JUMBO 6–36 mo) across **all** statuses, unlike STACR/CAS which build status-specific pools. This filter, meant for current-loan prepay analysis, materially reduces the deep-delinquent population — **FCLS/REO loans may be mostly/entirely excluded**, making deep-delinquency tracking misleading. Howard recommends regenerating pseudo pools so delinquent-status tracking isn't constrained by the prepay/current-loan age filter, starting with NQM then JUMBO. Glenn Perillo agreed (2026-06-30 15:10 EDT) and asked to **see the impact once complete**.
  - **dv01 BigQuery view removal (~2 weeks):** dv01 is removing individual per-deal job views (e.g., `auto_aggregated_loan_age_data_<deal>`), leaving only asset-class-level views; queries must switch to `... WHERE account_name = '<DEAL>'`. Any RESI pipeline/query relying on per-deal dv01 Data Direct views will break at the cutoff (~2026-07-13) unless migrated.

### CLO Updates
- **Completed / In progress:** No CLO signal reachable this run — the `CLO` folder is not accessible via COM and nothing CLO-specific (spread-model MAE, curve comparison v2/v2r/delev, RV lists, surveillance, MVOC, break-even yields) appeared in the reachable primary Inbox.
- **Risks / follow-ups:** CLO pipeline status (`CLODaily-Workflow`, `CLO-restart-spread-model-celery`, `CLO-Loan-Px-Diff-Email`, colordb) **unknown**. Verify via the connector/interactive Outlook.

### Email / AUTO Folder Signals
> Access note: The `AUTO` automation feed was **NOT reviewable** this run (MCP connector absent; primary `Inbox/auto` empty; archived copies ~1 yr stale). The items below come from the **primary Outlook `Inbox`** (reachable via COM), which is current through 2026-07-01 01:32 UTC. Times shown in UTC.

- **Glenn Perillo — "Re: NQM Tracking: Pseudo Pool Design Issue for FCLS/REO Coverage"** — 2026-06-30 19:10 UTC. Glenn agreed with Howard's pseudo-pool redesign proposal and asked to see the quantified impact once complete. *(In-scope; Howard's action.)*
- **Howard Zeng — "NQM Tracking: Pseudo Pool Design Issue for FCLS/REO Coverage"** — 2026-06-30 17:40 UTC. Howard's write-up of the pseudo-pool inconsistency (to Kiet Sam, Glenn Perillo, cc LibreMax-Modeling). *(Origin of the design item above.)*
- **GitHub (via Howard) — "[LibreMax-QR/LMSimData] Run failed: Pre-Merge Checks - nqm_hz (5993ba1)"** — 2026-06-30 14:31 UTC. CI failure on the NQM branch (see Failed Jobs). *(In-scope failure.)*
- **dv01 / Mathew Borja / Jay Shaver — "dv01 Data Direct - BigQuery job views update"** thread — 2026-06-29 (latest 16:40 UTC). dv01 removing per-deal BigQuery views in ~2 weeks; migrate to `WHERE account_name`. Jay flagged LibreMax uses single-dataset queries extensively. *(In-scope dependency risk; slightly >24h but active.)*
- **Scott Gimpel — "Non-QM RMBS: Delinquency & Prepay Timeline Analysis - by Loan Size"** — 2026-06-29 18:50 UTC. External research relevant to Non-QM RESI space. *(Context only.)*
- **Datadog HQ — "[Dashboard Report] Galileo Dashboard"** — 2026-06-29 05:04 UTC. Scheduled Galileo dashboard report. *(Informational; Galileo relates to the trimaran-galileo integration test.)*
- Desk/ops items seen but not Howard's model work (SSS generation is out of scope): Samantha Grossman "SUNRN 2018-1 A updated sss" (06-30), "UPST 26-3 sss" (06-29). *(Noted, not flagged.)*

### Todo
1. **Fix the LMSimData Pre-Merge Checks failure on `nqm_hz` (`5993ba1`)** — review the 2 failing annotations and get the branch green before merging the FCLS/REO tracking change.
2. **Redesign & regenerate the NQM (then JUMBO) pseudo pools** so delinquent-status tracking isn't constrained by the prepay/current-loan age filter; **quantify the FCLS/REO coverage impact for Glenn** as he requested.
3. **Migrate dv01 Data Direct BigQuery queries** off per-deal job views to the asset-class views + `WHERE account_name = '...'` pattern before dv01's ~mid-July cutoff (~2026-07-13); confirm which RESI pipelines/queries are affected.
4. **Restore Outlook MCP connectivity for scheduled runs** (or run this summary interactively) so last-24h RESI/CLO pipeline status is actually verifiable — today's automation-feed status is unknown, not clear.
5. **Confirm SimHistVector / ResiTraceFile recovery** — these were RED in early June; verify current status once the feed is reachable (ResiTraceFile still needs the empty-`TRACE`-result `KeyError` code fix if not yet merged).
6. **Check CLO pipeline status** (`CLODaily-Workflow`, spread-model celery, Loan-Px-Diff, colordb) once the `CLO` folder is reachable — no CLO signal was visible this run.

---
*Sources: Outlook primary `Inbox` via win32com COM (reachable, current to 2026-07-01 01:32 UTC). Automation folders (`Inbox/auto`, `Jenkins Automation`, `CLO`, `RESI`, `Tracking`) were unreachable this run — MCP connector absent in scheduled/headless mode; archived COM copies frozen ~2025-06-29. Out-of-scope items (LIBREMAX/SWIB Risk Runs, Daily Resi SSS File Generation, Compliance Engine) excluded per task scope.*
