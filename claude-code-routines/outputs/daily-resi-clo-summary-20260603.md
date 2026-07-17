## Daily RESI/CLO Summary

Window: 2026-06-02 ~12:00 → 2026-06-03 ~08:00 ET (last ~24h, incl. overnight batch). Times shown in ET. Source: Outlook — `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, `Inbox/auto`, `Inbox`. Out-of-scope items (LIBREMAX/SWIB Risk Runs, Daily Resi SSS File Generation, Compliance Engine) excluded per scope.

### Executive Summary
- **LMSim daily vectors are broken.** `quant-DailySimHistVector #1560` finished only **11.16% complete (2,556 / 22,893 vectors; 20,337 unfinished, 0 errored)** this morning — looks like a timeout/capacity cutoff, not data errors. No recovery yet. **Top item to chase.**
- **`quant-CRTDaily-Workflow #19` ABORTED** overnight (01:21 ET). The three prior runs (#16–#18, 06-02 evening) all succeeded, so this is a fresh overnight abort — confirm today's CRT vectors are current.
- **Pseudo-deal tracking is failing across NONQM / JUMBO2_0 / CAS / HELOC pseudos** in the Monthly ResiTracking workflow. This lines up with your in-flight **PR #12760 "Fix pseudo tracking readiness month gating."** Real-deal tracking + reports completed and you already sent the June Monthly Tracking Review (no dial change).
- **Your CI is red:** `nqm_hz` Pre-Merge Checks (LMSimData) and PR #12760 Default PR Workflow (LMQR) both failed all jobs on 06-02.
- **CLO side is clean** — daily workflow, spread-model (celery), MAE/curve-comparison v2/v2r/delev, RV lists/offers, surveillance, IO/PO & break-even yields, MVOC and loan-price reports all generated normally.

### Failed / Concerning Jobs

**1. quant-DailySimHistVector #1560 — FAILED (still broken)**
- What failed: LMSim daily historical vector run completed only **11.16%** — `Succeeded: 2,556/22,893 (11.16%); failed: 0; unfinished: 20,337`. Covers JUMBO/NQM/HELOC and Figure cohorts (FIGRE, GRADE, ACHM, VSTA, SAIF, GSMBS, DRMT).
- Evidence: Jenkins email 06-03 07:51 ET; log `20260603 07:49:47:ERROR:main: LMSim Vector Run Failed … Job Status: JobStatus.FAILED` → `Build step 'PowerShell' marked build as failure`. 0 errored + 89% unfinished ⇒ run was cut off (timeout / worker/compute capacity), not per-vector data failures.
- Suggested next action: Check console + Datadog for the run; verify Galileo/worker availability overnight; re-run and confirm today's sim-hist vectors are populated before downstream consumers use them.

**2. quant-CRTDaily-Workflow #19 — ABORTED**
- What failed: Daily CRT workflow aborted at 06-03 01:21 ET. Builds #16/#17/#18 (06-02 14:44–19:44 ET) all SUCCESS, so the overnight run is the anomaly.
- Evidence: Jenkins "Build ABORTED" email, `http://jenkins.libremax.com/job/quant-CRTDaily-Workflow/19/`. (CRT Monitor Report 20260602 still went out at 06:05 ET, but verify the daily CRT vectors themselves are current.)
- Suggested next action: Open console for #19 — ABORTED usually means a timeout or upstream/manual kill; likely shares a root cause with the DailySimHistVector cutoff.

**3. quant-trimaran-galileo-integration-test #111 — Build FAILURE / Tests NOT_RUN**
- What failed: Trimaran↔Galileo integration morning check failed in 3m42s; Playwright tests never ran.
- Evidence: Jenkins/Playwright email 06-03 07:55 ET; report at `S:\QR\Reports\MorningChecks\trimaran-report.html`.
- Suggested next action: Check whether Galileo was reachable/healthy overnight (ties to items 1–2); rerun the integration test once Galileo is confirmed up.

**4. Monthly ResiTracking — PSEUDO-deal sub-jobs FAILED (pipeline wrapper still reported SUCCESS)**
- What failed (06-02):
  - `quant-Monthly-ResiTracking-Tracking #12` — FAILED for **NONQM_PSEUDO** (07:11 ET), **JUMBO2_0_PSEUDO** (07:11 ET), **CAS_PSEUDO** (07:17 ET)
  - `quant-Monthly-ResiTracking-Tracking #14` — FAILED for **CAS_PSEUDO** (13:55 ET)
  - `quant-Monthly-ResiTracking-Unload #24` and `#26` — FAILED incl. **HELOC_PSEUDO** (15:38 / 15:45 ET)
- Evidence: `RESI` folder failure emails from qrprod. Pipeline wrapper `quant-Monthly-ResiTracking-pipeline` #26/#27/#28 reported SUCCESS, masking the pseudo sub-job failures. Real-deal tracking + QR Model Tracking Reports completed (Tracking folder, 06-02 08:03 & 14:16 ET).
- Suggested next action: These are the exact pseudo deals your **PR #12760 "Fix pseudo tracking readiness month gating"** targets — land that fix, then re-run Tracking/Unload for the four pseudo cohorts.

**5. GitHub CI red on your branch/PR**
- `nqm_hz` — **LMSimData "Pre-Merge Checks": all jobs failed** in 3m42s (06-02 12:01 ET).
- PR #12760 — **LMQR "Default PR Workflow" / lint-and-test: all jobs failed** in 1m3s (06-02 11:08 ET); svc-ghactions comment 11:10 ET. The 1-minute failure smells like a lint/import/setup error rather than a real test failure.
- Suggested next action: Open both runs; fix lint-and-test on #12760 (blocking the pseudo-tracking fix) and the nqm_hz pre-merge checks.

**6. quant-galileo-integration-test #475 — Tests FAILED (Build SUCCESS)** *(lower priority)*
- Main Galileo morning-check Playwright suite had test failures 06-03 07:17 ET (the `swib` variant PASSED). Worth a glance given the overnight Galileo cluster (items 1–3). Report: `S:\QR\Reports\MorningChecks\libremax-report.html`.

**Recovered / not Howard's (noise — no action needed):**
- `quant-DailySaveVolSurface #2734` FAILED 06-02 20:09 ET → **back to normal #2735** 23:50 ET.
- `quant-dpa-hyeneedmail #1637–1640` FAILED 20:29–21:31 ET → **back to normal #1641** 21:37 ET.
- `quant-ResiTraceFile #1254` **back to normal** 06-02 17:13 ET.
- `quant-Daily-CMBS-Model-Intex-CSV #632` FAILED 06-03 00:12 ET — CMBS/commercial, not RESI/CLO (route to the commercial team).
- "ISSUE: Trades missing/mismatched in FS 06/02" (qrprod→ops; ascott reply) — ops/desk trade reconciliation, not your model work.

### RESI Updates
- **Completed:** June Monthly Tracking Review sent (recommendation: no action / no dial change; STACR CtoP in line). QR Model Tracking Reports generated (06-02 08:03 & 14:16 ET). CRT Monitor Report 20260602 (model 20.12.10e). LM Deal List – All Deals Mapped.
- **In progress:** NQM vector comparison / recent-vintage review with Kiet & Glenn (you added the no-decay LLPA time-curve case, 06-02 13:35 ET); PR #12760 pseudo-tracking readiness fix; `nqm_hz` branch work.
- **Risks / follow-ups:** DailySimHistVector 89% unfinished (item 1); CRTDaily #19 aborted (item 2); pseudo tracking/unload failing for NONQM/JUMBO2_0/CAS/HELOC (item 4); CI red on `nqm_hz` and PR #12760 (item 5).

### CLO Updates
- **Completed (all healthy):** `quant-CLODaily-Workflow-pipeline` #249/#250/#251 SUCCESS; `quant-CLO-restart-spread-model-celery` #35–#38 SUCCESS; CLO Spread Model LO MAE report (GAM v3.0); Spread Model curve comparison v2/v2r/delev (2026-05-29 vs 06-01, 8 models); CLO RV Positions report (06-01); US+Europe & European lists/offers; CLO Surveillance 20260601/20260602; CLO IO/PO Yields; CLO Break-Even Yields; CLO Large MVOC Movement; CLO Loan Price Changes.
- **In progress:** none flagged.
- **Risks / follow-ups:** none — CLO pipelines and reports look clean.

### Email / AUTO Folder Signals
Direct Outlook access was available. Key non-Jenkins messages:
- **Adam Polay (Director of Operations) — "Pricing Matrix question"** (06-02 20:59 ET, to LibreMax-Quants/Hanish/Alex): Tab 6 "Challenges" in the pricing matrix isn't fully populated; asks if it's a timing issue with the overnight Galileo run. Marked "not urgent tonight," but given the overnight Galileo/vector failures (items 1–3) it may share the same root cause — worth a reply.
- **NQM Vector Comparison – Additional Recent Vintage Review** (you, 06-02 13:35 ET): added a no-decay-LLPA-time-curve comparison case in response to Kiet's CPR-decay feedback. Ongoing.
- **FS DB Loader – New Version** (adamiani, 06-02 15:05 ET): FundStudio DB Loader moved stored-proc logic into Python; FYI for downstream loaders.
- `auto` folder: standard EOD/morning batch (Portfolio Sensitivities, Risk/Hedge reports, Credit Smiles, Axe Sheets, Risk Monitor, Form PF PASS, CRT Monitor) all generated normally.

### Todo
1. **Chase `quant-DailySimHistVector` (89% unfinished).** Check console/Datadog + Galileo/worker capacity, then re-run and confirm today's sim-hist vectors are complete.
2. **Investigate `quant-CRTDaily-Workflow #19` ABORTED** (01:21 ET) and confirm today's CRT vectors are current; likely same overnight root cause as #1.
3. **Fix CI to unblock PR #12760** (LMQR lint-and-test failing in 1m) and **`nqm_hz` Pre-Merge Checks** (LMSimData) — both red since 06-02.
4. **Land PR #12760 and re-run pseudo-deal Tracking/Unload** for NONQM_PSEUDO, JUMBO2_0_PSEUDO, CAS_PSEUDO, HELOC_PSEUDO.
5. **Check `quant-trimaran-galileo-integration-test #111`** (and glance at `galileo-integration-test #475` test failures) once Galileo is confirmed healthy.
6. **Reply to Adam Polay** on the pricing-matrix Tab 6 question — likely tied to the overnight Galileo issues above.
