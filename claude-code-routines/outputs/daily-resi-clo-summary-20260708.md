## Daily RESI/CLO Summary

_Coverage window: last 24h ending 2026-07-08 morning (focus: 2026-07-07). Source: Outlook primary Inbox via COM. See access note below._

### Executive Summary
- **One in-scope failure to act on:** Howard's `nqm_hz` branch failed **LMSimData Pre-Merge Checks** again on 07-07 (commit `29c5972`) — a repeat of the 07-06 failure (`473ddf9`). All pre-merge jobs failed; merge of the NQM model update is blocked until the 2 failing checks are fixed.
- This failing branch lines up with Howard's own **"Monthly Tracking Review - July"**: NQM CtoP is running materially fast (12-mo avg **1.34**, recent 2-mo **1.92**), and an NQM model update + deep-delinquent pseudo-population redesign are being pushed — `nqm_hz` is very likely that work-in-progress.
- **No reachable CLO signal** in the last 24h. CLO automation reports land in the `CLO` / `Jenkins Automation` folders, which are **not accessible in this scheduled/headless run** (Outlook MCP connector absent — see note). Do not read this as "CLO all-clear."
- Risk-difference reconciliation (07-06 thread), the KNOCK-2025-1 custody report, and JPM Home Price Monitor were seen but are out-of-scope or context-only.

### Failed / Concerning Jobs
- **Job/source:** GitHub Actions — `LibreMax-QR/LMSimData`, workflow **Pre-Merge Checks**, branch `nqm_hz`.
- **What failed or looks suspicious:** "Pre-Merge Checks: All jobs have failed" — `pre-merge-checks` failed in 3m 51s with **2 annotations**. Same branch failed the prior day, so the latest push is still red (no later success/"back to normal" seen in the accessible window).
- **Evidence:**
  - 2026-07-07 09:55 EDT — subject `[LibreMax-QR/LMSimData] Run failed: Pre-Merge Checks - nqm_hz (29c5972)` (body: "All jobs have failed", 2 annotations).
  - 2026-07-06 07:58 EDT — subject `[LibreMax-QR/LMSimData] Run failed: Pre-Merge Checks - nqm_hz (473ddf9)` (prior-day failure on same branch).
- **Suggested next action:** Open the LMSimData Pre-Merge Checks run for `29c5972`, read the 2 annotations, and fix the failing checks so the NQM model update can merge. Confirm whether the failure is a test/lint break in the new NQM logic vs. an environment issue.

_Note: the `LMQR` PR #12984 "Add stats-freshness gate (stats-readiness CLI) to pseudo_gating" also had a failed run on 07-06 (`eb6c12e`); no follow-up seen on 07-07. Worth a glance since it's part of the pseudo-tracking gating work, but it is outside the strict 24h window._

### RESI Updates
- **Completed:** None confirmed via accessible sources in the last 24h (automation-feed completions unreachable — see access note).
- **In progress:**
  - **NQM model update** to fix rate-sensitivity — NQM CtoP running fast (12-mo 1.34, 2-mo 1.92; model projecting too fast). Being pushed via the `nqm_hz` branch, which is currently failing pre-merge checks (see above).
  - **Deep-delinquent pseudo-population redesign** for NQM, JUMBO, and possibly HELOC — expected to raise deep-delinquent loan counts ~4x–8x and make future dials more reliable (per Monthly Tracking Review).
- **Risks / follow-ups:**
  - Tracking is broadly in line for STACR (12-mo 1.00), CAS (0.99), JUMBO (1.17 / 3-mo 0.91), HELOC (1.10 / CPR 1.02); **NQM is the outlier** (fast) and the reason for the model push.
  - The pre-merge failures are blocking the NQM fix from landing — this is the gating item.
  - Market context: JPM Home Price Monitor (07-07, fwd'd by Glenn Perillo) — CoreLogic HPI +1% YoY / +0.5% MoM in May; supply rising in Sun Belt/West Coast. Relevant HPA backdrop for RESI models; no action.

### CLO Updates
- **Completed:** Unknown — CLO automation folder not reachable in this run.
- **In progress:** Unknown — same access gap.
- **Risks / follow-ups:** Only CLO mention in the accessible Inbox was "CLO risk is reasonable" inside the out-of-scope risk-differences thread (07-07). **No CLO spread-model / V2·V2R·V3 / BWIC-color / MVOC / surveillance signal could be verified.** Restore the Outlook MCP connector for scheduled runs to cover CLO (see Todo).

### Email / AUTO Folder Signals
**Access note:** The Outlook MCP connector (`outlook_email_search` / `read_resource mail:///`) that reaches the live `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` feeds is **not connected in this scheduled/headless run** (a known limitation — interactively-authenticated MCP servers are absent in cron runs). Fallback was Python `win32com` COM, which reads the **live primary Inbox** fine but **cannot see the RESI/CLO automation folders** (the primary store's `Inbox/auto` is empty; the archived copies are ~1 year stale). So last-24h **automation job status could not be verified** — findings below are from the primary Inbox only.

Relevant messages (primary Inbox, 2026-07-07 unless noted):
- **09:55 — Howard Zeng (GitHub Actions):** `[LibreMax-QR/LMSimData] Run failed: Pre-Merge Checks - nqm_hz (29c5972)`. In-scope RESI/NQM CI failure — the flag above.
- **06:51 — Howard Zeng:** `Monthly Tracking Review - July`. Source for the NQM fast-tracking finding and the model-update / pseudo-population-redesign plan.
- **05:42 — James Barna (+ Olive Bian, Tyler Ascione):** `RE: Large Risk Differences 07/06/26` — "adjusted the risk for the top 3; JPMMT 2025-7MPR XS reasonable subject to a pending challenge resolution; CLO risk is reasonable." Risk-run reconciliation → **out of scope**; noted only because it touches a RESI bond challenge and CLO risk sign-off.
- **11:08 / 11:37 — John Sim (JPM) / fwd Glenn Perillo:** `Home Price Monitor: Slow build`. RESI market/HPA context; no action.
- **15:05 — Computershare custody (`#nacctdocumentcustody…`):** `Automated Reports - KNOCK-2025-1` — secure document-custody report; not Howard's model work.
- Early 07-08 items (held-message quarantine notice, JPM Extel survey vote) are noise.

### Todo
1. **Fix `nqm_hz` Pre-Merge Checks in LMSimData** (commit `29c5972`, 2 annotations) — failing 2 days running and blocking the NQM model update merge. Highest priority.
2. **Verify the NQM model update actually addresses the fast CtoP** (12-mo 1.34 / 2-mo 1.92) once the branch is green.
3. **Restore the Outlook MCP connector for scheduled runs** so `AUTO` / `Jenkins Automation` / `CLO` / `RESI` / `Tracking` are covered — today's CLO status and automation job outcomes are unverified because of this gap.
4. **Manually spot-check CLO + the RESI automation folders** (Jenkins pipelines, per-cohort `RESI Tracking/Unload FAILED` emails, CLO spread-model/MVOC) via the Outlook client for anything the Inbox-only fallback missed.
5. (Lower) Check whether **LMQR PR #12984** "stats-freshness gate for pseudo_gating" (failed 07-06 `eb6c12e`) has since gone green — part of the pseudo-tracking work.
