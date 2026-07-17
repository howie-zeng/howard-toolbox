## Daily RESI/CLO Summary

_Coverage window: 2026-07-13 00:00 EDT → 2026-07-14 ~08:11 EDT (new material since the last summary is 07-13 ~08:48 → 07-14 morning; 07-13 items overlap the prior run and are already reflected there). Source: Outlook primary Inbox via win32com COM after a forced Send/Receive. This run the Inbox synced current on the **first poll** (newest 2026-07-14 04:02 EDT, 5,047 items) — no stale-sync issue, and the scheduled-task date (2026-07-14) matched the machine clock. Live automation feed (Jenkins / qrprod / CLO / RESI / Tracking folders) unreachable — archive frozen ~1 year stale. See access note._

### Executive Summary
- **Quiet, in-scope-clean window — no new RESI/CLO work signal in the reachable Inbox.** No new NQM dial/vector updates from Howard, no new CLO notes from Yiming, no Modeling replies. The only new traffic 07-13 → 07-14 is out-of-scope risk/ops reconciliation and market/vendor noise.
- **`nqm_hz` CI-failure break holds (5th day clear):** **zero** new `LMSimData` Pre-Merge Checks failure emails 07-13 or 07-14. The last failure was 07-09 14:20 EDT (`8acb809`); the streak has now had no continuation 07-10 through 07-14. GitHub emails **failures only**, so this is still **not a confirmed green** — verify the branch/PR state directly before merging the NQM fix.
- **CLO carry-overs with Yiming still open and unverified:** the **EUR spread-model release** and the **Spread Model ensemble-framework review** (both from 07-08; Yiming back 07-10) had **no confirmation traffic** again this window. Can't be verified from the Inbox — settle directly with Yiming.
- **Access gap persists (not an "all-clear"):** the Outlook MCP connector is again not connected in this scheduled run, so the live `Jenkins Automation` / `CLO` / `RESI` / `Tracking` / `auto` feeds are **unreachable** (archive-only, frozen ~1 year: Jenkins Automation newest = 2025-07-11). Last-24h Jenkins/qrprod/CLO job outcomes — including the RESI/CRT pipelines — **could not be verified this run**.

### Failed / Concerning Jobs
- **No failed or concerning jobs surfaced from accessible sources across 2026-07-13 → 2026-07-14.** No `nqm_hz` Pre-Merge Checks failures in the window; no GitHub CI-failure notifications of any kind reached the primary Inbox.

_Access caveat: this is **not** evidence the pipelines were clean. GitHub emails only failures (a green `nqm_hz` can't be confirmed from the Inbox), and the **Jenkins/qrprod/CLO automation job outcomes** — the RESI/CRT pipelines (`quant-CRTDaily-Workflow`, `quant-DailyNewIssueCRTVectors`, `quant-DailySimHistVector` + `-freestyle`, `quant-ResiTraceFile`, `quant-RMBSLoader`, `quant-Monthly-ResiTracking-*`), per-cohort `RESI Tracking/Unload FAILED`, and CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC / surveillance — are **not verifiable this run** (see access note). `quant-DailySimHistVector` and `quant-ResiTraceFile` are known to run red, so they warrant a manual spot-check in the Outlook client._

### RESI Updates
- **Completed:** None confirmed via accessible sources (automation-feed completions unreachable — see access note).
- **In progress:**
  - **NQM model update (`nqm_hz` branch in `LMSimData`).** Pre-Merge Checks failure-email streak still stopped (no failures 07-10 → 07-14). Green is **not confirmed** (failures-only email), so verify the branch state directly before landing the fix.
  - **NQM dial / framework work (carry-over from 07-09, awaiting Modeling sign-off).** The permanent (non-decaying) deep-delinquent dials (`M270PtoFCLS`, `M90PtoFCLS`, `M90PtoD`, `FCLStoD`, `FCLStoREO`), the CDR comparison showing dialed-NQM CDR well above base, and the plan to add FCLS→REO transitions and switch deep-delinquent models to the **STACR** deep-delinquent models — all posted 07-09 to Glenn Perillo / Kiet Sam / LibreMax-Modeling — had **no further email traffic** this window. Still pending sign-off.
- **Risks / follow-ups:**
  - Confirm `nqm_hz` is actually green, then land the NQM fix (the failure emails merely stopped — that isn't proof).
  - Get Modeling sign-off on the two deliberate-but-material NQM decisions (permanent non-decaying dials; NQM CDR now well above base) before shipping the FCLS-REO / STACR deep-delinquent framework change.
  - **RPM 2026-4A new-issue setup** — Samantha Grossman's 07-09 request ("Can you use this sss for RPM 2026-4A?") still has no visible resolution in the Inbox; confirm whether any RESI model/vector setup falls to Howard (routine SSS *generation* is out of scope, but a new-deal onboarding ask may not be).

### CLO Updates
- **Completed:** Unknown from accessible sources — CLO automation folder not reachable this run.
- **In progress / action needed (all carry-overs, no new email this window):**
  - **Release the EUR spread models** — Yiming's 07-08 handoff ("go ahead and release the EUR models. For non-delev, I believe the changes are benign"). Yiming returned 07-10; no release confirmation surfaced in the reachable Inbox. Settle with him directly.
  - **Review the Spread Model ensemble framework** (Yiming, 07-08) — multi-artifact per Ccy/Rating starting **USD/BB**, comparing **HL15D vs HL30D** half-lives with optional weighted-average prediction; `run_spread_model(...)` interface unchanged. Still awaiting Howard's review.
- **Risks / follow-ups:**
  - **No CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC / surveillance / BWIC-color signal could be verified** (automation folder unreachable).

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM. Confirmed this run:
- **The primary store `hzeng@LIBREMAX.com` Inbox synced current on the first poll** (newest **2026-07-14 04:02 EDT, 5,047 items**) — no lazy-sync stall this time. Its `Inbox/auto` subfolder is empty via COM.
- **The automation folders exist only in the `Online Archive - hzeng@libremax.com` store and remain frozen ~1 year stale:** `Jenkins Automation` newest = **2025-07-11 16:16** (1,466 items), `Tracking` = 2025-07-10, `HECM` = 2025-07-02 — a rolling 12-month archive-retention artifact, **not the live feed**.
- **Net:** last-24h automation job status is **unverified**; findings above are from the primary Inbox only (which carries GitHub CI notifications + human RESI/CLO threads, but not the qrprod/Jenkins automation feed).

Relevant / notable messages (primary Inbox, new since the 07-13 summary):
- **No `nqm_hz` Pre-Merge Checks failure emails 07-13 → 07-14** — the streak (last `8acb809` 07-09 14:20) still has no continuation. In-scope; flagged above.
- **07-13 13:54 / 07-14 03:55 / 04:02 — Alex Damiani, Tyler Ascione, Bryan Gonnella:** the `Large Risk Differences 07/13/26` thread and `ISSUE: Trades missing or mismatched in FS on 07/13/2026` (qrprod → ops/desk). The latter is a **swaptions description mismatch** between the live blotter and the trades table (Alex Damiani updated the Galileo description; root cause TBD). Both are **ops/risk-run reconciliation — out of scope, not Howard's RESI/CLO model work.** Noted for context only.
- **07-13 15:07 — Computershare:** `Automated Reports - KNOCK-2025-1` custody reports — noise.
- **07-13 13:05 — Third Bridge:** `Q2 2026 Earnings Preview – Week of July 20` — external vendor research, no action.
- **07-13 04:21 — Peter DeGroot (JPM):** `Fixed Income Cross Product Relative Value Monitor` (muni-centric this issue) — market context, low RESI relevance.
- Noise / out-of-scope (ignored): `Free Cash 7.13.26` (Christopher Cheung), `Trades Summary + Hedge Changes 07/10/26` (Kiet Sam), JPM Extel-survey vote (John Sim), Datadog `Galileo Dashboard` report, and Howard's own 07-13 summary email.

### Todo
1. **Confirm `nqm_hz` Pre-Merge Checks is actually green and land the NQM model fix.** The failure-email streak has now been clear 07-10 → 07-14, but GitHub emails failures only — verify the branch/PR state directly. **Highest priority** (unblocks the NQM dial / FCLS-REO / STACR deep-delinquent framework merge).
2. **Close out the CLO carry-overs with Yiming (back since 07-10):** confirm/perform the **EUR spread-model release** (non-delev benign) and give the **Spread Model ensemble framework** (USD/BB, HL15D vs HL30D) the review he requested.
3. **Get Modeling sign-off on the two NQM decisions** — permanent (non-decaying) deep-delinquent dials, and NQM CDR now well above base — then ship the FCLS-REO / STACR deep-delinquent framework change once the branch is green.
4. **Manually spot-check the automation folders via the Outlook client for 07-13 → 07-14** — the Inbox-only fallback can't see them: `quant-DailySimHistVector` and `quant-ResiTraceFile` (both known to run red), the CRT/RMBS pipelines, per-cohort `RESI Tracking/Unload FAILED`, and CLO spread-model MAE / curve-comparison / MVOC.
5. **Restore the Outlook MCP connector for scheduled runs** so `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` are covered — this run again could not verify Jenkins/qrprod/CLO job status (COM reaches only the current primary Inbox + a ~1-year-stale archive). Recurring blocker across recent runs.
6. **Confirm ownership of the `RPM 2026-4A` new-issue setup** (Samantha Grossman, 07-09) — still unresolved; quick check on whether any RESI/CLO model or vector setup falls to Howard.
