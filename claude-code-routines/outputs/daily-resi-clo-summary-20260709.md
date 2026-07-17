## Daily RESI/CLO Summary

_Coverage window: last ~24h ending 2026-07-09 ~08:15 EDT (focus: 2026-07-08). Source: Outlook primary Inbox via win32com COM. Automation feed unreachable this run — see access note._

### Executive Summary
- **Top in-scope item, still open:** Howard's `nqm_hz` branch failed **LMSimData Pre-Merge Checks 7 more times on 07-08** (last: commit `1ded967`, 15:22 EDT), on top of the 07-07 and 07-06 failures. A heavy afternoon debugging burst (6 runs 13:53→15:22) still ended red — the NQM model update remains **blocked from merging**. The single `pre-merge-checks` job fails in ~3.5 min with **2 annotations**.
- **Two genuinely-new CLO signals from Yiming Zhang (first real CLO items in this feed in a while):** (1) Yiming is **out sick today (Thu 07-09), back Fri**, and asks Howard/Glenn to **"go ahead and release the EUR models"** (non-delev changes "benign"); (2) he shipped a **Spread Model ensemble framework** (multi-artifact per Ccy/Rating, USD/BB first, comparing HL15D vs HL30D half-lives, weighted-average prediction) and asks Howard to **review**. Both are actionable while he's out.
- **Substantive RESI progress:** Howard posted an **NQM tracking update** (pseudo-pool redesign for FCLS/REO + deep-delinquent) to Glenn Perillo / Kiet Sam / LibreMax-Modeling — status-specific pseudo flat files (M30/M60/M90P/M270P/FCLS/REO), ~5x more loans without the age filter, NQM deep-delinquent behavior materially different from STACR/CAS. This is the modeling work behind the `nqm_hz` branch.
- **Access gap persists (not an "all-clear"):** the Outlook MCP connector is not connected in this scheduled run, so the live `Jenkins Automation` / `CLO` / `RESI` / `Tracking` / `auto` feeds are **unreachable**. Confirmed fresh this run: those folders exist only in the Online Archive store and are frozen **exactly ~1 year stale** (Jenkins Automation newest = 2025-07-08). So last-24h Jenkins/qrprod job outcomes could not be verified.

### Failed / Concerning Jobs
- **Job/source:** GitHub Actions — `LibreMax-QR/LMSimData`, workflow **Pre-Merge Checks**, branch `nqm_hz`.
- **What failed or looks suspicious:** "Pre-Merge Checks: All jobs have failed." The `pre-merge-checks` job fails in ~3m 38s with **2 annotations**, and it failed repeatedly through 07-08 with **no later SUCCESS / "back to normal"** in the accessible window — so the branch is **still red** at end of 07-08. Third straight day failing (07-06 → 07-07 → 07-08).
- **Evidence (all in primary Inbox, GitHub Actions notifications):**
  - 2026-07-08 — 7 failed runs on `nqm_hz`: `f8c15c6` (07:23), `a2b67a7` (13:53), `4cecb30` (14:01), `7ab519d` (14:17), `0602018` (14:49), `5dafa19` (15:05), **`1ded967` (15:22, latest)**.
  - 2026-07-07 09:55 — `nqm_hz (29c5972)` (prior-day failure).
  - 2026-07-06 07:58 — `nqm_hz (473ddf9)` (first-day failure).
- **Suggested next action:** Open the Pre-Merge Checks run for `1ded967`, read the **2 annotations** on the `pre-merge-checks` job (~3.5 min, so likely a fast lint/unit/format break rather than a long integration failure), fix, and confirm the branch goes green so the NQM model update can merge. The rapid-fire afternoon commits suggest Howard was mid-debug at day's end.

_Access caveat: this GitHub CI failure is visible only because GitHub emails the primary Inbox. The **Jenkins/qrprod automation job outcomes** (RESI Tracking/Unload per-cohort, SimHistVector, ResiTraceFile, CLO spread-model/MVOC, etc.) are **not verifiable this run** — see access note. Do not read the short "Failed Jobs" list as evidence those pipelines were clean._

### RESI Updates
- **Completed:** None confirmed via accessible sources in the last 24h (automation-feed completions unreachable — see access note).
- **In progress:**
  - **NQM tracking pseudo-pool redesign (FCLS/REO + deep-delinquent).** Howard (07-08 12:18, thread to Glenn Perillo / Kiet Sam / LibreMax-Modeling): regenerated NQM tracking using status-specific pseudo flat files for M30/M60/M90P/M270P/FCLS/REO and added FCLS→REO transitions. Undialed findings: NQM FCLS loans move to REO far more than STACR/CAS with limited direct default; M270P/M90P show low cure + higher foreclosure movement; M60 may need a separate FCLS state. Removing the age filter raises loan count ~5x. Would need a strong dial (~0.1x or 3x) if kept as-is.
  - **NQM model update** (the `nqm_hz` branch) to fix fast CtoP tracking — **blocked** by the Pre-Merge Checks failures above.
- **Risks / follow-ups:**
  - The pseudo-pool inconsistency Howard flagged (age filter applied differently across statuses) should be resolved **before relying on any non-CRT deep-delinquent tracking output** — his own caution to Modeling.
  - NQM remains the tracking outlier (fast CtoP, 12-mo 1.34 / 2-mo 1.92 per the 07-07 Monthly Tracking Review); the model fix can't land until the branch is green.
  - Market context (no action): JPM **STACR/CAS Prepayment Estimates July 2026** (Alex Kraus, 07-08 12:48) and **Agency MBS Prepay Model Performance July 2026** (Nick Maciunas, 07-07) — relevant prepay backdrop given the CtoP-fast issue.

### CLO Updates
- **Completed:** Unknown from accessible sources — CLO automation folder not reachable this run.
- **In progress / action needed:**
  - **Release the EUR spread models.** Yiming Zhang (07-08 13:43, "Sick Day Tomorrow and CLO Progress"): "please go ahead and **release the EUR models. For non-delev, I believe the changes are benign.**" Yiming is **out sick today (Thu 07-09), back Friday**, so this falls to Howard/Glenn while he's out.
  - **Spread Model ensemble framework — review requested.** Yiming (07-08 07:51, "Update on Spread Model Ensemble Framework"): added support for running multiple DM-based model artifacts per Ccy/Rating, starting **USD/BB**, comparing two half-lives (**HL15D vs HL30D**) with an optional weighted-average prediction; downstream `run_spread_model(...)` interface unchanged; member-model outputs preserved separately in the result table. He asks Howard to review ("should be straightforward").
- **Risks / follow-ups:**
  - EUR-model release + ensemble review both land on Howard while Yiming is out — sequence them today if the EUR release is time-sensitive.
  - **No CLO spread-model MAE / v2·v2r·delev curve-comparison / MVOC / surveillance / BWIC-color signal could be verified** (automation folder unreachable). The only other CLO mention was "CLO risk is reasonable" inside the out-of-scope Large Risk Differences risk-run thread.

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM. Confirmed this run:
- **Primary store `hzeng@LIBREMAX.com` → Inbox is current** (newest item 2026-07-09 04:13 EDT; 4,523 items) and was fully scanned. Its `Inbox/auto` subfolder is **empty (0 items)**.
- **The automation folders exist only in the `Online Archive - hzeng@libremax.com` store and are frozen ~1 year stale:** `Jenkins Automation` newest = **2025-07-08 16:19**, `Inbox/auto` newest = 2025-07-08 16:32, `Tracking` = 2025-06-27, `HECM` = 2025-07-02. A 12-month archive-retention artifact — **not the live feed**.
- **Net:** last-24h automation job status is **unverified**; findings above are from the primary Inbox only (which does carry GitHub CI notifications + human RESI/CLO threads).

Relevant messages (primary Inbox):
- **07-08 13:53–15:22 — Howard Zeng (GitHub Actions):** 6 `nqm_hz` Pre-Merge Checks failures in ~90 min (latest `1ded967`), plus `f8c15c6` at 07:23. In-scope RESI/NQM CI failure — flagged above.
- **07-08 13:43 — Yiming Zhang → Glenn/Howard:** `Sick Day Tomorrow and CLO Progress` — out sick 07-09; **release EUR models** (non-delev benign); review ensemble framework. In-scope CLO action.
- **07-08 12:48 — Alex Kraus (JPM):** `STACR/CAS Prepayment Estimates and Projections: July 2026` — RESI prepay context.
- **07-08 12:18 — Howard Zeng → Glenn/Kiet/Modeling:** `Re: NQM Tracking: Pseudo Pool Design Issue for FCLS/REO Coverage` — NQM pseudo-pool redesign update (details above). In-scope RESI progress.
- **07-08 07:51 — Yiming Zhang:** `Update on Spread Model Ensemble Framework` — CLO USD/BB ensemble (HL15D/HL30D). In-scope CLO, review requested.
- **07-08 06:39 — Joe Kwan:** `RE: Loading Day 3 Marks` — 6/30 Day-3 marks loaded, all-bonds risk file generated (`S:\QR\Risk\DurationReport\monthend\20260630\DAY3\`). Month-end ops → context only.
- **07-08 early am — James Barna / Powell Eddins / Olive Bian / Tyler Ascione:** `Large Risk Differences 07/07/26` — GRADE 2026-HB1 B1 adjusted; PAID 24-4 C, AON XA, BPR XNM addressed; "CLO risk is reasonable." Risk-run reconciliation → **out of scope**; noted only as context.
- **07-09 04:13 — Christopher Cheung:** `Free Cash 7.09.26` — fund cash → out of scope (only new 07-09 item at scan time).
- Noise (ignored): Mimecast held-message digests, ADP/HR harassment training, Datadog daily digest, JPM Extel survey / bootcamp invite, Computershare KNOCK-2025-1 custody report, external marketing (LifeMart, Ai4, BMI, Third Bridge, patent/data vendors).

### Todo
1. **Fix `nqm_hz` Pre-Merge Checks in LMSimData** (latest commit `1ded967`) — read the 2 annotations on the `pre-merge-checks` job and get the branch green. Failing 3 days running and blocking the NQM model-update merge. **Highest priority.**
2. **Release the EUR CLO spread models** per Yiming's request (non-delev changes benign) — Yiming is out sick today, so this is on Howard/Glenn. Do it today if the release is time-sensitive.
3. **Review Yiming's Spread Model ensemble framework** (USD/BB, HL15D vs HL30D, weighted-average, unchanged `run_spread_model` interface) — he asked for a review; feedback can wait for his Friday return but the read can happen now.
4. **Land the NQM model fix once the branch is green** and confirm it actually corrects the fast CtoP (12-mo 1.34 / 2-mo 1.92); resolve the pseudo-pool age-filter inconsistency before relying on non-CRT deep-delinquent tracking.
5. **Restore the Outlook MCP connector for scheduled runs** so `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` are covered — today's Jenkins/qrprod/CLO automation job status is unverified because of this gap (COM only reaches the current primary Inbox + a ~1-year-stale archive).
6. **Manually spot-check the automation folders via the Outlook client** for anything the Inbox-only fallback missed: per-cohort `RESI Tracking/Unload FAILED` emails, `quant-DailySimHistVector` / `quant-ResiTraceFile` (both known to run red), and CLO spread-model MAE / curve-comparison / MVOC.
