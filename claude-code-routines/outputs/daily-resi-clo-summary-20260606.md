## Daily RESI/CLO Summary

*Window: ~2026-06-05 morning → 2026-06-06 ~08:40 UTC. Source: Howard's Outlook (Jenkins Automation, auto/AUTO, CLO, RESI, Tracking, HECM folders). Times shown in UTC unless noted.*

### Executive Summary
- **One RESI incident is still open this morning:** the LMSim vector backend (Ray cluster) failed Friday night, taking down **WeekendCRTVectors**, **WeekendCRTTrackingVectors** (+ their workflow wrapper), and **DailySimHistVector** — hundreds of CRT/NQM/CES/HELOC deals came back with `actual=0` vectors and the Ray job ended `JobStatus.FAILED`. No recovery seen yet.
- **`quant-ResiTraceFile` is failing on a separate code bug** (`KeyError: 'TRACE'`) that surfaces when Sentrace returns no RESI traces — the export step doesn't handle an empty trace set.
- **CLO side is healthy.** CLODaily pipeline (#270) and the full CLO report suite (RV lists/offers, spread-model MAE & curve comparison v2/v2r/delev, surveillance, IO/PO & break-even yields, loan price changes, MVOC) all delivered. The CLO spread-model workflow failed 3× Friday evening but **recovered (#132 back to normal)**.
- **Monthly Resi Tracking is healthy again:** pipeline #44 SUCCESS Friday, overnight Tracking #40 + Unload #48 SUCCESS (both mailed to you). The 06-02 pseudo-cohort failures (NONQM/JUMBO2_0/CAS/HELOC PSEUDO) did **not** recur in this window.
- Out-of-scope noise excluded as usual (LIBREMAX Risk Run bond failures incl. HECM_YT_PX, Compliance Engine, Resi SSS).

### Failed / Concerning Jobs

**1. LMSim vector generation incident (RESI · CRT/NQM/CES/HELOC) — STILL OPEN**
- **Job/source:** `quant-WeekendCRTVectors #325`, `quant-WeekendCRTTrackingVectors #36`, `quant-WeekendCRTVectorsWorkflow #167` (all 2026-06-05 ~22:54–23:02), and `quant-DailySimHistVector #12` / `-freestyle #1563` (2026-06-06 00:57–00:58). Jenkins → LibreMax-Quants + PagerDuty.
- **What failed:** Vectors did not generate. WeekendCRTVectors logged hundreds of deals with `expected=15 actual=0` (also some 5/10) across VERUS, SAN, SEMT, STAR, STACR, RCKT, TPMT, JPMMT, FIGRE, GRADE, GSMBS, etc., ending `LMSim Vector Process Completed with Failures`. DailySimHistVector submitted 2779 SIM2 requests to the Ray cluster; the Ray job (`raysubmit_geScgCaNSGpRHLfY`) finished `JobStatus.FAILED` → **2133/2779 succeeded (76.75%), 0 failed, 646 unfinished** (HELOC/Figure cohorts among the unfinished).
- **Evidence / common cause:** `actual=0` on the CRT side plus a hard `JobStatus.FAILED` on the Ray side point to the **LMSim Ray backend (`lmsim-ray.qr.libremax.com`) being degraded/down Friday night** rather than per-deal data issues. Full Ray log: `\\libremax-nas\QR_sanbox\QR\logs\sim\20260605_205658_sim2_raysubmit_geScgCaNSGpRHLfY.log`. No "back to normal"/SUCCESS for any of these jobs as of 08:40 UTC.
- **Suggested next action:** Check Ray/LMSim cluster health and the log above; once the cluster is healthy, rerun `quant-WeekendCRTVectors`, `quant-WeekendCRTTrackingVectors`, and `quant-DailySimHistVector`. (Note: `quant-CRTDaily-Workflow #34/#35` — the weekday CRT path — succeeded Friday afternoon, so the breakage is specific to the Fri-night/weekend vector batch.)

**2. quant-ResiTraceFile #1257 — STILL OPEN (separate root cause)**
- **Job/source:** `quant-ResiTraceFile #1257` (2026-06-05 21:13), triggered by `quant-ResiTraceFileTrigger #437`. Jenkins → LibreMax-Quants.
- **What failed:** `KeyError: 'TRACE'` at `LMQR\Trace\RESI\ReadTraceResi_Sentrace.py:308` (`export_df["TRACE"].str.lstrip("$")`). Preceded by `No traces fetched from Sentrace for the Residentials Bonds for the provided time range` — i.e. the trade set came back empty and the export step assumes the `TRACE` column exists.
- **Evidence:** Sentrace returned 0 traces for the 288 RESI bonds for the Friday window; export then crashed on the missing column.
- **Suggested next action:** Harden `export_to_file` to short-circuit / write an empty file when no traces are returned (guard the `TRACE` column). Also confirm whether an empty Friday-evening trace set is expected (no RESI prints) or a Sentrace API hiccup.

### RESI Updates
- **Completed:** Monthly ResiTracking pipeline `#42/#43/#44` SUCCESS (Fri 17:07–17:27); overnight `Tracking #40` SUCCESS (03:10) + `Unload #48` SUCCESS (06:07), both emailed to you. `quant-CRTDaily-Workflow #34/#35` SUCCESS. `LM Deal List – All Deals Mapped` delivered (06-05 23:26).
- **In progress:** Weekend CRT vectors + DailySimHistVector awaiting Ray-cluster fix and rerun (see Failed Job #1).
- **Risks / follow-ups:** (a) Clear the LMSim/Ray incident and rerun the three vector jobs. (b) Fix the empty-trace `KeyError` in ResiTraceFile. (c) Good news: the 06-02 pseudo-cohort Tracking/Unload failures did not recur — monthly tracking looks back to normal.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline #268/#269/#270` SUCCESS; `quant-CLO-restart-spread-model-celery #55/#56` SUCCESS. Full report suite delivered Friday: RV US+Europe Lists & Offers, RV Trades & Positions reports, Spread Model LO MAE (GAM v3.0, 2026-01-01→06-04), Spread Model Curve Comparison (v2/v2r/delev, 06-03 vs 06-04), Surveillance 20260604, IO/PO Yields, Break-Even Yield, Loan Price Changes, Large MVOC Movement. Overnight CLO Loan Pricing, CLO Surveillance, and Intex loader/transaction-loader (0 failed / 35 loaded) ran clean.
- **In progress:** None outstanding.
- **Risks / follow-ups:** `quant-CLO-trades-spread-model-workflow` failed 3× Friday evening (#129/#130/#131, manual reruns by U. Vanaja Renukaprasad) before `#132` returned to normal — worth a quick glance to confirm today's run stays clean.

### Email / AUTO Folder Signals
- **Jenkins Automation** (primary signal source): in-scope failures and recoveries as detailed above. Also recovered overnight (non-core): `quant-cashflows` (#20 FAIL/#21 ABORT → #23 SUCCESS), `quant-creditsmilelive-pipeline` (#283 FAIL/#284 ABORT → #285–288 SUCCESS), `quant-Daily-CMBS-Model-Intex-CSV #635` back to normal.
- **`quant-MorningReports-pipeline #225` FAILURE (06-06 08:39) + `quant-ListingReport #1596` FAILURE (08:11):** this morning's reports pipeline failed and paged. Scope is uncertain (general morning-reports/listing pipeline, not a clear RESI/CLO model job; #222–224 succeeded Friday) — flagging for a quick look in case the listing/morning reports are needed today.
- **auto / CLO / RESI / Tracking / HECM folders:** CLO report deliverables all present (see CLO Updates). RESI folder's only 24h item was the routine "All Deals Mapped" email; the per-cohort RESI FAILED emails there are all dated 06-02 (now stale/resolved). Tracking & HECM folders had nothing new in the window.
- **Out of scope (noted, not flagged):** numerous `LIBREMAX Risk Run` bond-failure emails (CLO/CRT/CON ABS/HECM) and `quant-HECMYTRisk #12` / `LIBREMAX Risk Run Failed: 'HECM_YT_PX'`; `Compliance Engine 3.0 started/stopped`; `quant-dpa-nightly-risk-check #2053` (risk-check, paged) treated as a risk run.

### Todo
1. **Investigate the LMSim/Ray cluster** (`lmsim-ray.qr.libremax.com`); review `\\libremax-nas\QR_sanbox\QR\logs\sim\20260605_205658_sim2_raysubmit_geScgCaNSGpRHLfY.log`. Once healthy, **rerun** `quant-WeekendCRTVectors`, `quant-WeekendCRTTrackingVectors`, and `quant-DailySimHistVector`.
2. **Fix `ReadTraceResi_Sentrace.py`** to handle an empty Sentrace result (guard the `TRACE` column in `export_to_file`); rerun `quant-ResiTraceFile`. Confirm whether the empty Friday trace set is expected.
3. **Glance at `quant-CLO-trades-spread-model-workflow`** today to confirm it stays green after Friday's 3 failures (#132 recovered).
4. **(Optional)** Check `quant-MorningReports-pipeline #225` / `quant-ListingReport #1596` since they failed this morning and paged.
