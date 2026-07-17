## Daily RESI/CLO Summary

_Run date: 2026-07-07 (covers ~last 48h). Source: Outlook via `win32com` COM fallback — see access note below._

### Executive Summary
- **Access gap is the headline.** The Outlook **MCP connector is not connected in this scheduled run**, so the live automation feed — the `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, and `HECM` folders where Howard's RESI/CLO build pipelines and qrprod/qrtest jobs actually report — is **unreachable**. **Last-24h RESI/CLO job status cannot be verified this run** (this is *not* an "all clear").
- The COM fallback did reach the **live primary Inbox** (current), but it holds only **6 low-signal messages in 48h** — no in-scope RESI/CLO job failures, **no GitHub Actions CI-failure notifications**, and no human RESI/CLO model threads.
- The COM-visible copies of the automation folders live only in the **Online Archive** store and are **~12 months stale** (newest items 2025-07-02 → 2025-07-05), so they cannot substitute for the live feed.
- One adjacent item: the qrprod **"Large Risk Differences 07/06/26"** daily DoD review thread (commercial/CMBS bonds; trader responses from Tyler Ascione). This is the risk-review process — out-of-scope-adjacent, noted as context only, not a Howard job failure.
- **Top action: restore the Outlook MCP connector for scheduled runs** so this routine can see live job status again.

### Failed / Concerning Jobs
- **Job/source:** RESI/CLO automation feed (`Jenkins Automation` / `CLO` / `RESI` / `Tracking` / `HECM`)
- **What failed or looks suspicious:** Cannot determine — the live feed was **unreachable** this run. No failures were *observed*, but absence of evidence is not evidence of absence here.
- **Evidence:** Outlook MCP tools (`outlook_email_search`, `read_resource mail:///`) absent from this scheduled/headless session; COM fallback cannot see these folders in the live primary store (they exist only in the ~12-month-stale Online Archive: `Jenkins Automation` newest 2025-07-05, `HECM` 2025-07-02, `Tracking` 2025-06-27).
- **Suggested next action:** Restore the MCP connector for scheduled runs; until then, spot-check `Jenkins Automation` / `CLO` / `RESI` / `Tracking` in the Outlook desktop app manually for any overnight `Build FAILURE` / `RESI Tracking FAILED` / `KeyError: 'TRACE'` items.

_No failed or concerning jobs were **observed** from accessible sources — but coverage was incomplete; see the access gap above._

### RESI Updates
- **Completed:** Unable to verify — the RESI job feed (`quant-DailyNewIssueCRTVectors`, `quant-DailySimHistVector`, `quant-ResiTraceFile`, `quant-Monthly-ResiTracking-*`, `RMBSLoader`, weekend CRT vectors) was unreachable this run.
- **In progress:** Unknown (feed unreachable).
- **Risks / follow-ups:** No RESI signal reached the primary Inbox and **no GitHub Actions CI-failure emails** arrived in the last 48h. Prior known-fragile jobs to re-check once the feed is restored: `quant-DailySimHistVector` (has ended short ~99.9% on a Ray-job tail) and `quant-ResiTraceFile` (`KeyError: 'TRACE'` on empty Sentrace results — unhandled empty-result code bug). Also cross-check the `RESI` folder for per-cohort `RESI Tracking/Unload FAILED` messages that the pipeline-level SUCCESS masks (NONQM_PSEUDO, JUMBO2_0_PSEUDO, CAS_PSEUDO, HELOC_PSEUDO).

### CLO Updates
- **Completed:** Unable to verify — the CLO feed (`quant-CLODaily-Workflow-pipeline`, `quant-CLO-restart-spread-model-celery`, `quant-CLO-Loan-Px-Diff-Email`, spread-model MAE / curve-comparison v2/v2r/delev, surveillance) was unreachable this run.
- **In progress:** Unknown (feed unreachable).
- **Risks / follow-ups:** Only generic touch on CLO this window was the "Large Risk Differences 07/06/26" DoD email, which asks "CLO, Commercial, Residential teams please respond if risk differences are reasonable." No CLO model-job status observable.

### Email / AUTO Folder Signals
- **Direct Outlook MCP access was UNAVAILABLE this run.** The `AUTO` feed (`Inbox/auto`, `Jenkins Automation`, etc.) could not be read live. Below is only what the `win32com` COM fallback could see.
- **Primary Inbox (`hzeng@LIBREMAX.com`, live, 4,400 items) — last 48h (6 messages, none in-scope RESI/CLO failures):**
  - `2026-07-06 03:54 EDT` — **Tyler Ascione** — "Re: Large Risk Differences 07/06/26" — reply on the qrprod DoD risk-review thread (commercial/CMBS: JPMCC 2018-AON XA, FREMF 2016-K56 D, BAMLL 2019-BPR XNM, UB11 E). Risk-review process; out-of-scope-adjacent, informational.
  - `2026-07-06 03:45 EDT` — Hanish Pallapothu (Teams) — chat notification (noise).
  - `2026-07-06 01:06 EDT` — Datadog HQ — "[Dashboard Report] Galileo Dashboard" (external report, noise).
  - `2026-07-05 20:19 EDT` — Stanley Wong (Teams) — chat notification (noise).
  - `2026-07-05 18:00 EDT` — Hanish Pallapothu (Teams) — chat notification (noise).
  - `2026-07-05 08:22 EDT` — Datadog — "Your Daily Digest from Datadog" (external, noise).
- **Primary `Inbox/auto` subfolder:** empty (0 items) in the live primary store — the automation feed does not land here via COM.
- **Online Archive automation folders (COM-visible but STALE):** `Jenkins Automation` (1,200 items, newest 2025-07-05), `HECM` (32, newest 2025-07-02), `Tracking` (50, newest 2025-06-27) — all ~12 months old, unusable for current status.
- Git was checked only as fallback context: no commits in `howard-toolbox` in the last 48h (latest is `1c7d86a`, 2026-06-01).

### Todo
1. **Restore the Outlook MCP connector for scheduled/headless runs** (top priority). Until it's back, this daily routine cannot verify RESI/CLO job status — it can only read the primary Inbox, which the automation feed bypasses.
2. **Manually spot-check today's overnight RESI/CLO jobs** in the Outlook desktop app (`Jenkins Automation`, `CLO`, `RESI`, `Tracking`) for any `Build FAILURE` / `RESI Tracking/Unload FAILED` / `KeyError: 'TRACE'` since ~2026-07-06, since automated coverage was blind this run.
3. **"Large Risk Differences 07/06/26"** — confirm whether any RESI/CLO marks still need a reasonableness response; the commercial bonds appear handled by Tyler Ascione, but the email explicitly pinged the Residential and CLO teams.
