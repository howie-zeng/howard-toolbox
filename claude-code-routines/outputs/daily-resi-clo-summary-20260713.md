## Daily RESI/CLO Summary

_Coverage window: 2026-07-10 00:00 EDT → 2026-07-13 ~08:48 EDT (the full weekend gap; focus: 07-10 Fri, 07-11 Sat, 07-12 Sun, early 07-13 Mon). Source: Outlook primary Inbox via win32com COM after a forced Send/Receive. **Run-timing note:** this scheduled run's metadata date was 2026-07-11 but it actually executed Monday 2026-07-13, and no 07-11/07-12 summaries were produced — so this one covers everything since the last summary (which focused on 07-09). First COM read was ~2 days stale (lazy-sync); a forced Send/Receive pulled the Inbox current (newest 2026-07-13 04:34 EDT, 5,040 items). Live automation feed (Jenkins/qrprod/CLO folders) unreachable — archive frozen ~1 year stale. See access note._

### Executive Summary
- **The `nqm_hz` CI failure streak appears to have ended (top in-scope change):** **zero** new `LMSimData` Pre-Merge Checks failure emails arrived across the **entire weekend (07-10, 07-11, 07-12) and into Mon 07-13**. The last failure was 07-09 14:20 EDT (`8acb809`), which had extended the streak to 4 straight days (07-06 → 07-09). GitHub emails **only failures** for this workflow, so this is **not a confirmed green** — but 3+ clear days is a sustained break in a daily-failure run. Verify the branch/PR is actually green and land the NQM fix.
- **Genuinely quiet weekend in the reachable Inbox — no new in-scope RESI/CLO work:** no new NQM dial/vector updates from Howard after the 07-09 18:54 "NQM Vector Update," and no new CLO notes from Yiming. Weekend traffic was market research (JPM/John Sim), out-of-scope risk-run reconciliation ("Large Risk Differences"), and ops/admin.
- **CLO carry-overs with Yiming remain open and unverified:** the **EUR spread-model release** and **Spread Model ensemble-framework review** (both requested 07-08; Yiming back 07-10) had **no confirmation traffic** in the reachable Inbox. Status can't be verified here — settle directly with Yiming.
- **Access gap persists (not an "all-clear"):** the Outlook MCP connector is still not connected in this scheduled run, so the live `Jenkins Automation` / `CLO` / `RESI` / `Tracking` / `auto` feeds are **unreachable** (archive-only, frozen ~1 year stale — Jenkins Automation newest = 2025-07-11). **Weekend Jenkins/qrprod/CLO job outcomes — including the weekend CRT pipelines — could not be verified.**

### Failed / Concerning Jobs
- **No new failed or concerning jobs surfaced from accessible sources across 2026-07-10 → 2026-07-13.** The `nqm_hz` Pre-Merge Checks failure streak had **no continuation** anywhere in the window (last failure 07-09 14:20 `8acb809`; nothing 07-10 through 07-13).

_Access caveat: this is **not** evidence the pipelines were clean. GitHub emails only failures, so a green `nqm_hz` cannot be confirmed from the Inbox; and the **Jenkins/qrprod/CLO automation job outcomes** (weekend CRT pipelines `quant-WeekendCRTTrackingVectors`/`-Workflow`, `quant-DailySimHistVector`, `quant-ResiTraceFile` — both known to run red, per-cohort RESI Tracking/Unload, CLO spread-model MAE / curve-comparison / MVOC) are **not verifiable this run** — see access note. Because this window spans a full weekend, the weekend CRT pipelines in particular warrant a manual spot-check._

### RESI Updates
- **Completed:** None confirmed via accessible sources (automation-feed completions unreachable — see access note).
- **In progress:**
  - **NQM model update (`nqm_hz` branch in `LMSimData`).** The Pre-Merge Checks **failure-email streak stopped after 07-09** — no failures all weekend or into 07-13. Green is **not confirmed** (GitHub emails failures only), so the branch state must be checked directly before assuming the NQM fix can merge.
  - **NQM dial / framework work from 07-09 (carry-over, awaiting Modeling sign-off).** The permanent (non-decaying) deep-delinquent dials (`M270PtoFCLS`, `M90PtoFCLS`, `M90PtoD`, `FCLStoD`, `FCLStoREO`), the CDR comparison showing dialed-NQM CDR well above base, and the plan to add FCLS→REO transitions and switch deep-delinquent models to the **STACR** deep-delinquent models — all posted 07-09 to Glenn Perillo / Kiet Sam / LibreMax-Modeling — had **no further email traffic this window**. Still pending sign-off.
- **Risks / follow-ups:**
  - Confirm `nqm_hz` is actually green, then land the NQM fix (the failure emails merely stopped — that isn't proof).
  - Get Modeling sign-off on the two deliberate-but-material NQM decisions (permanent non-decaying dials; NQM CDR now well above base) before shipping.
  - **RPM 2026-4A new-issue setup** — Samantha Grossman's 07-09 13:45 request ("Can you use this sss for RPM 2026-4A?") still has no visible resolution; confirm whether any RESI model/vector setup falls to Howard (routine SSS *generation* is out of scope, but a new-deal onboarding ask may not be).
  - Market context (no action): JPM `MBS Credit Monthly: July 2026` and `Securitized Products Weekly` (John Sim, 07-10), `RMBS Credit Commentary: Whole Loan-ta Love` (07-10 02:32) — RMBS/securitized backdrop.

### CLO Updates
- **Completed:** Unknown from accessible sources — CLO automation folder not reachable this run.
- **In progress / action needed (all carry-overs, no new email this window):**
  - **Release the EUR spread models** — Yiming's 07-08 handoff ("go ahead and release the EUR models. For non-delev, I believe the changes are benign"). Yiming returned 07-10; no release confirmation surfaced in the reachable Inbox. Settle with him directly.
  - **Review the Spread Model ensemble framework** (Yiming, 07-08) — multi-artifact per Ccy/Rating starting **USD/BB**, comparing **HL15D vs HL30D** half-lives with optional weighted-average prediction; `run_spread_model(...)` interface unchanged. Still awaiting Howard's review.
- **Risks / follow-ups:**
  - **No CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC / surveillance / BWIC-color signal could be verified** (automation folder unreachable).
  - Out-of-scope context only: the "Large Risk Differences 07/10/26" thread continued into 07-13 04:34 (Samantha Grossman / Tyler Ascione / James Barna) — risk-run reconciliation, **not Howard's, out of scope**.

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM. Confirmed this run:
- **First COM read was ~2 days stale** (newest showed 07-10 16:19). A forced **Send/Receive ("All Accounts")** pulled the primary store `hzeng@LIBREMAX.com` Inbox current — newest then **2026-07-13 04:34 EDT, 5,040 items**, stable across repeated polls. Its `Inbox/auto` subfolder is **empty (0 items)**.
- **The automation folders exist only in the `Online Archive - hzeng@libremax.com` store and remain frozen ~1 year stale:** `Jenkins Automation` newest = **2025-07-11 16:16** (1,466 items), `Tracking` = 2025-07-10, `HECM` = 2025-07-02 — a rolling 12-month archive-retention artifact, **not the live feed**.
- **Net:** last-weekend automation job status is **unverified**; findings above are from the primary Inbox only (which carries GitHub CI notifications + human RESI/CLO threads, but not the qrprod/Jenkins automation feed).

Relevant / notable messages (primary Inbox, 07-10 → 07-13):
- **No `nqm_hz` Pre-Merge Checks failure emails 07-10 → 07-13** — the 4-day streak (last `8acb809` 07-09 14:20) had no continuation. In-scope; flagged above.
- **07-10 11:20 / 11:51 / 02:32 — John Sim (JPM):** `MBS Credit Monthly: July 2026`, `Securitized Products Weekly: July 10`, `RMBS Credit Commentary: Whole Loan-ta Love: Best Execution` — RESI/securitized market context, no action.
- **07-13 04:21 — Peter DeGroot (JPM):** `Fixed Income Cross Product Relative Value Monitor` (this issue centers on munis) — market context, low RESI relevance.
- **07-13 01:07 — Datadog HQ:** `[Dashboard Report] Galileo Dashboard` — automated dashboard snapshot, not a job-failure alert. Context only.
- **07-10 06:08 — Joe Kwan:** `QR Team Resource Alloc for Jun 2026` — QR team admin; may require Howard to submit his June allocation. Minor personal action, not a RESI/CLO model signal.
- Out-of-scope (noted, not flagged): `Large Risk Differences 07/09/26` & `07/10/26` threads (Samantha Grossman / James Barna / Tyler Ascione — risk-run reconciliation), `ABS Bonds Not Running Overnight Risk Report` (Alex Damiani, 07-10 — overnight risk report), `Free Cash 7.10.26` (Christopher Cheung), `Trades Summary + Hedge Changes` (Kiet Sam), `Blotter Overview` (Craig Sedaka).
- Noise (ignored): Datadog daily digests (07-10/07-11/07-12), Zoom sign-in code, SAP Concur, held-message digest, KNOCK-2025-1 custody reports, JPM Extel-survey / bootcamp invites, Connor Hunt `Claude Cowork Release` (IT tooling), Gloria Radeff (personal/HR), Howard's own 07-10 summary email.

### Todo
1. **Confirm `nqm_hz` Pre-Merge Checks is actually green and land the NQM model fix.** The failure-email streak stopped after 07-09 (`8acb809`) — no failures all weekend — but GitHub emails failures only, so verify the branch/PR state directly. **Highest priority** (unblocks the NQM dial / FCLS-REO / STACR deep-delinquent framework merge).
2. **Close out the CLO carry-overs with Yiming (back since 07-10):** confirm/perform the **EUR spread-model release** (non-delev benign) and give the **Spread Model ensemble framework** (USD/BB, HL15D vs HL30D) the review he requested.
3. **Get Modeling sign-off on the two NQM decisions** — permanent (non-decaying) deep-delinquent dials, and NQM CDR now well above base — then ship the FCLS-REO / STACR deep-delinquent framework change once the branch is green.
4. **Manually spot-check the automation folders via the Outlook client for the WEEKEND (07-10 → 07-12)** — the Inbox-only fallback can't see them: weekend CRT pipelines (`quant-WeekendCRTTrackingVectors` / `-Workflow`), `quant-DailySimHistVector`, `quant-ResiTraceFile` (both known to run red), per-cohort `RESI Tracking/Unload FAILED`, and CLO spread-model MAE / curve-comparison / MVOC.
5. **Restore the Outlook MCP connector for scheduled runs** so `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` are covered — this run again could not verify Jenkins/qrprod/CLO job status (COM reaches only the current primary Inbox + a ~1-year-stale archive).
6. **Fix the scheduled-run timing.** This run's metadata date (07-11) was 2 days stale and **no 07-11/07-12 summaries were produced** — check why the Sat/Sun runs didn't fire and why the run date was wrong, so the daily cadence isn't silently skipping days.
7. **Confirm ownership of the `RPM 2026-4A` new-issue setup** (Samantha Grossman, 07-09) — still unresolved; quick check on whether any RESI/CLO model or vector setup falls to Howard.
8. **(Minor) Submit QR Team Resource Alloc for Jun 2026** if that's an ask on Howard (Joe Kwan, 07-10).
