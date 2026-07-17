## Daily RESI/CLO Summary

_Coverage window: 2026-07-09 00:00 EDT → 2026-07-10 ~02:30 EDT (focus: 2026-07-09). Source: Outlook primary Inbox via win32com COM, after a forced Send/Receive to defeat the lazy-sync cache (first read was a full day stale). Live automation feed (Jenkins/qrprod/CLO folders) unreachable this run — see access note._

### Executive Summary
- **Top in-scope item, still open:** Howard's `nqm_hz` branch failed **LMSimData Pre-Merge Checks 6 more times on 07-09** (05:39 → last `8acb809` at 14:20 EDT), extending the 07-06/07-07/07-08 streak to a **4th straight day red**. GitHub emails failures only, so no green can be confirmed from the Inbox — the NQM model update is **still blocked from merging**.
- **Heavy, substantive RESI/NQM progress on 07-09 (Howard's dominant activity):** he applied a set of **larger, permanent (non-decaying) NQM deep-delinquent dials** — `M270PtoFCLS`, `M90PtoFCLS`, `M90PtoD`, `FCLStoD`, `FCLStoREO` — (11:54 "NQM Dial Update"), then posted a **CDR-focused vector comparison** across ~16 Non-QM deals (18:54 "NQM Vector Update"): base CDR ≈ JPM, but JPM runs much higher CDR in superbear; the newly-dialed NQM CDR sits well above base. He is adding **FCLS→REO transitions to the NQM framework** and switching the deep-delinquent models to the **STACR deep-delinquent models**, because NQM deep-delinquent loans behave materially differently from CRT.
- **CLO carry-over now actionable directly with Yiming:** Howard signaled a hand-back to CLO ("Going back to CLO after this email," 11:54), but no CLO output landed in the Inbox window. Yiming Zhang was out sick Thu 07-09 and is **back today (Fri 07-10)**, so his two open asks — **release the EUR spread models** (non-delev changes "benign") and **review the Spread Model ensemble framework** (USD/BB, HL15D vs HL30D) — can now be settled with him rather than handled solo.
- **Access gap persists (not an "all-clear"):** the Outlook MCP connector is still not connected in this scheduled run. The primary Inbox is current (after a forced Send/Receive), but the live `Jenkins Automation` / `CLO` / `RESI` / `Tracking` / `auto` feeds are **unreachable** — those folders exist only in the Online Archive store, frozen ~1 year stale (Jenkins Automation newest = **2025-07-08**). Last-24h Jenkins/qrprod/CLO automation job outcomes could **not** be verified.

### Failed / Concerning Jobs
- **Job/source:** GitHub Actions — `LibreMax-QR/LMSimData`, workflow **Pre-Merge Checks**, branch `nqm_hz`.
- **What failed or looks suspicious:** "Pre-Merge Checks: All jobs have failed." Failed **6 times on 07-09** with no later SUCCESS / "back to normal" in the accessible window — so the branch is presumed **still red** at end of 07-09. This is the **4th consecutive day** of failures (07-06 → 07-09), and the second straight day of a rapid-fire debugging burst.
- **Evidence (all in primary Inbox, GitHub Actions notifications on `nqm_hz`):**
  - 2026-07-09 — 6 failed runs: `6263dfc` (05:39), `1a87dd2` (06:16), `901cbc8` (06:29), `ca7d6fe` (07:15), `d81cd9f` (09:49), **`8acb809` (14:20, latest)**.
  - Prior days (context): 07-08 7 failures ending `1ded967`; 07-07 `29c5972`; 07-06 `473ddf9`.
- **Suggested next action:** Open the Pre-Merge Checks run for `8acb809`, read the annotations on the `pre-merge-checks` job, fix, and confirm the branch goes green so the NQM dial / FCLS-REO framework changes can merge. Absence of a failure email after 14:20 does **not** confirm green — GitHub only emails failures for this workflow.

_Access caveat: this GitHub CI failure is visible only because GitHub emails the primary Inbox. The **Jenkins/qrprod automation job outcomes** (RESI Tracking/Unload per-cohort, `quant-DailySimHistVector`, `quant-ResiTraceFile`, CLO spread-model MAE / curve-comparison / MVOC, etc.) are **not verifiable this run** — see access note. Do not read the short "Failed Jobs" list as evidence those pipelines were clean._

### RESI Updates
- **Completed:** None confirmed via accessible sources (automation-feed completions unreachable — see access note). Howard did complete and circulate two substantive NQM analyses on 07-09 (below).
- **In progress:**
  - **NQM deep-delinquent dials applied (07-09 11:54, "NQM Dial Update" → Glenn Perillo / Kiet Sam / LibreMax-Modeling).** Applied larger dials to the delinquency-transition states; largest adjustments: `M270PtoFCLS`, `M90PtoFCLS`, `M90PtoD`, `FCLStoD`, `FCLStoREO`. Howard's recommendation: **keep these dials permanent, not decaying over the next 36 months.** Sample of the applied table: M30 (C 0.870, P 1.136), M60 (C 0.702, M30 1.123, M90 0.840, P 1.759), M90P (C 0.425, …).
  - **NQM vector / CDR comparison (07-09 18:54, "NQM Vector Update").** Recap: NQM CPR is good; the remaining work is adding **FCLS and REO transitions** to the NQM framework and switching the **deep-delinquent models to the STACR deep-delinquent models**. On CDR: base CDR ≈ JPM, but JPM is much higher in the **superbear** scenario; the dialed-NQM CDR is well above base for PROD and for the new NQM model on the old framework. Compared Prod / New-NQM / JPM / Dialed-NQM across ~16 Non-QM deals (NYMT 2026-INV1, BARC 2026-NQM1, GCAT 2025-NQM3, NRZT 2024-NQM2, GSMBS 2025-R1, ADMT 2025-NQM1, CROSS 2025-H7, JPMMT 2025-NQM4, OBX 2026-NQM1, LMAT 2024-INV1, BRAVO 2021-NQM1, ADMT 2023-NQM3, COLT 2022-3, CHNGE 2023-4, VISIO 2023-1, VERUS 2022-1).
  - **NQM model update (the `nqm_hz` branch)** — **blocked** by the Pre-Merge Checks failures above.
- **Risks / follow-ups:**
  - Two model decisions Howard has put to Modeling deserve a sign-off before they ship: (1) making the **deep-delinquent dials permanent (non-decaying)**, and (2) the **NQM CDR now running well above base** after dialing. Both are deliberate but material — worth Glenn/Kiet confirmation.
  - The NQM model fix can't land until the branch is green (see Failed Jobs).
  - Market context (no action): JPM RMBS Credit Commentary "Whole Loan-ta Love: Best Execution" (John Sim, 07-10 02:32) and Fixed Income Cross-Product RV Monitor (Peter DeGroot, 07-09 04:17) — securitized/RMBS backdrop.

### CLO Updates
- **Completed:** Unknown from accessible sources — CLO automation folder not reachable this run.
- **In progress / action needed:**
  - **Release the EUR spread models** — carried over from Yiming's 07-08 sick-day handoff ("please go ahead and release the EUR models. For non-delev, I believe the changes are benign."). No release confirmation appeared in the Inbox window. Yiming is **back today (Fri 07-10)**, so this can be settled with him directly.
  - **Review the Spread Model ensemble framework** (Yiming, 07-08) — multiple DM-based artifacts per Ccy/Rating starting **USD/BB**, comparing **HL15D vs HL30D** half-lives with an optional weighted-average prediction; `run_spread_model(...)` interface unchanged. Still awaiting Howard's review.
  - Howard indicated he was **returning to CLO after the 11:54 NQM email**, but the afternoon's CLO work (if any) did not surface in the Inbox (it would flow through the unreachable automation feed).
- **Risks / follow-ups:**
  - **No CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC / surveillance / BWIC-color signal could be verified** (automation folder unreachable).
  - Out-of-scope context only: within the "Large Risk Differences 07/08/26" risk-run thread, Olive Bian (07-09 04:21) wrote "**CLO risk is not reasonable. We will override.**" — a risk-run reconciliation call (not Howard's, out of scope), noted only because it flipped from the prior day's "CLO risk is reasonable."

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM. Confirmed this run:
- **Primary store `hzeng@LIBREMAX.com` → Inbox was a full day stale on first read** (newest 2026-07-09 04:17). A forced **Send/Receive ("All Accounts")** pulled it current — newest then **2026-07-10 02:32**, 4,678 items — before scanning. Its `Inbox/auto` subfolder is **empty (0 items)**.
- **The automation folders exist only in the `Online Archive - hzeng@libremax.com` store and are frozen ~1 year stale:** `Jenkins Automation` newest = **2025-07-08 16:19** (1,396 items), `Tracking` = 2025-06-27, `HECM` = 2025-07-02. A 12-month archive-retention artifact — **not the live feed**.
- **Net:** last-24h automation job status is **unverified**; findings above are from the primary Inbox only (which does carry GitHub CI notifications + human RESI/CLO threads).

Relevant messages (primary Inbox, 07-09 → 07-10):
- **07-09 05:39–14:20 — Howard Zeng (GitHub Actions):** 6 `nqm_hz` Pre-Merge Checks failures (latest `8acb809`). In-scope RESI/NQM CI failure — flagged above.
- **07-09 18:54 — Howard Zeng → Glenn Perillo / Kiet Sam / LibreMax-Modeling:** `Re: NQM Vector Comparison - Additional Recent Vintage Review` ("NQM Vector Update") — CDR comparison, FCLS/REO framework + STACR deep-delinquent switch. In-scope RESI progress.
- **07-09 11:54 — Howard Zeng → Glenn / Kiet / Modeling:** `Re: NQM Tracking: Pseudo Pool Design Issue for FCLS/REO Coverage` ("NQM Dial Update") — permanent deep-delinquent dials. In-scope RESI progress.
- **07-09 13:45 — Samantha Grossman:** `RPM 2026-4A new issue` — "Can you use this sss for RPM 2026-4A?" New-issue setup request to the team; unclear whether Howard owns any model/vector/SSS setup for it — worth a quick confirm (note: routine SSS *generation* is out of scope, but a new-deal onboarding ask may not be).
- **07-09 08:33 / 09:02 / 09:18 / 14:35 — Janae Paquet / Hanish Pallapothu / Udayaditya Vanaja Renukaprasad (LibreMax-Quants):** `Galileo cvs Export Issue` — CSV portfolio export had unpopulated fields / "[object Object]" errors; **fixed same day by Uday**. Quants-team data-platform issue, resolved, no Howard action. Context only.
- Noise (ignored): Christopher Cheung `Free Cash` (fund cash), Craig Sedaka `Blotter Overview`, Kiet Sam `Trades Summary + Hedge Changes`, Olive Bian `Large Risk Differences` (risk run — out of scope), Datadog daily digest, Computershare `KNOCK-2025-1` custody report, LifeMart marketing.

### Todo
1. **Fix `nqm_hz` Pre-Merge Checks in LMSimData** (latest commit `8acb809`) — read the failing-job annotations and get the branch green. **4th day red** and blocking the NQM dial / FCLS-REO framework merge. **Highest priority.**
2. **Close out the CLO carry-overs with Yiming (back today, Fri 07-10):** confirm/perform the **EUR spread-model release** (non-delev benign) and give the **Spread Model ensemble framework** (USD/BB, HL15D vs HL30D) the review he requested.
3. **Get Modeling sign-off on the two NQM decisions** before they ship: permanent (non-decaying) deep-delinquent dials, and the dialed-NQM CDR sitting well above base — then land the framework change once the branch is green.
4. **Manually spot-check the automation folders via the Outlook client** for last-24h items the Inbox-only fallback can't see: per-cohort `RESI Tracking/Unload FAILED`, `quant-DailySimHistVector`, `quant-ResiTraceFile` (both known to run red), and CLO spread-model MAE / curve-comparison / MVOC.
5. **Restore the Outlook MCP connector for scheduled runs** so `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` are covered — today's Jenkins/qrprod/CLO automation status is unverified because COM only reaches the current primary Inbox + a ~1-year-stale archive.
6. **Confirm ownership of the `RPM 2026-4A` new-issue SSS request** (Samantha Grossman) — quick check on whether any RESI/CLO model or vector setup falls to Howard.
