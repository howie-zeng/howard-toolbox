## Daily RESI/CLO Summary — 2026-06-10 (Wednesday)

_Source: Howard's Outlook (hzeng@libremax.com). Window reviewed: Tue 6/9 ~08:10 ET → Wed 6/10 ~08:10 ET (~last 24h). Folders checked: `Jenkins Automation` (105 msgs in window), `Inbox/auto`, `CLO`, `RESI`, `Tracking`, `HECM`. Times are ET (UTC−4). Out-of-scope per standing instructions: LIBREMAX/SWIB risk runs, Resi SSS file generation, Compliance Engine — excluded below._

### Executive Summary
- **NEW top item — storage/file-share `[Errno 22]` breaking RESI + CLO jobs:** the Azure SMB share `\\lmaxquantstorage.file.core.windows.net\lmaxqr\LMSimData\init_config\*.json` is throwing `OSError: [Errno 22] Invalid argument` on JSON config reads. It killed **`quant-ResiPortCreatioin #1277`** (RESI — can't open `deal_collat_mapping.json` / `jumbo2_0_tape_deal_collat_mapping.json`) **and** the **CLO Surveillance Report 06/09/26** (`MissingRateData` reading `LMUtil.json`). One root cause, two of Howard's in-scope deliverables down — looks like an infra/mount problem, not a code bug.
- **`quant-CLO-Model-ColorClean-EOD` failing for the 2nd straight morning (CLO):** ~14 Build FAILUREs #17037–#17050 (07:02–08:06 ET), same `ValueError: No objects to concatenate` in `clo_color_clean.py` as yesterday. It **self-recovered yesterday** (#16996 "back to normal" 08:38 ET) and is Naginator-looping again today — confirming a recurring early-morning empty-color timing race. Still red at last check; may self-clear ~08:40 ET as it did Tuesday.
- **`quant-Daily-CLO-Report #645` failed (CLO):** Build FAILURE 07:07 ET, same window as the surveillance/color failures — no traceback in the email (just "Running Daily CLO Report / Done / marked build as failure"), likely downstream of the color-clean / file-share problems.
- **Two carryover code bugs still unpatched (RESI):** `quant-ResiTraceFile #1259` failed again (Tue 17:13 ET) with the same **`KeyError: 'TRACE'`** empty-Sentrace-result bug; `quant-DailySimHistVector #15` failed again (Tue 20:55 ET) on the **SIM2/HELOC** family. Both exactly as predicted in the 6/9 summary.
- **Daily RESI + CLO production otherwise green:** `quant-CLODaily-Workflow-pipeline #274`, `quant-Monthly-ResiTracking-Tracking #44` + `-Unload #53` (both to hzeng@), `quant-CLO-restart-spread-model-celery #59`, CreditSmile / MorningReports #230 / morningparalleljobs #136 all SUCCESS. The **`RESI` folder is clean** (no new per-cohort failures — only the stale 6/2 `_PSEUDO` items), so the pipeline-level Tracking SUCCESS is genuine. Most of the CLO report suite (Lists/Offers, IO/PO & break-even yields, MVOC, spread-model MAE & curve-comparison) delivered normally.

### Failed / Concerning Jobs

**1. File-share `[Errno 22]` on `LMSimData\init_config\*.json` — breaks `quant-ResiPortCreatioin #1277` (RESI) + CLO Surveillance Report (CLO) — NEW, TOP PRIORITY, likely infra**
- What failed:
  - `quant-ResiPortCreatioin #1277` — Build FAILURE 07:59 ET. Both the **Resi IO** and **Resi Non-QM** Intex portfolio file steps crashed in `CRTDealManager.__init__` (`crt_deal_manager.py:1066/1087`) on `open(deal_collat_map_file)` → `OSError: [Errno 22] Invalid argument: '\\lmaxquantstorage.file.core.windows.net\lmaxqr\LMSimData\init_config\deal_collat_mapping.json'` (and `…\jumbo2_0_tape_deal_collat_mapping.json`).
  - **`FAILURE: CLO Surveillance Report 06/09/26`** (qrprod → Quants + njain/pcalderon/BGonnella/obian/nangellino, 07:07 ET) — `MissingRateData("no data for rate (asof=2026-06-09, scenario=Base): lm=raised: [Errno 22] Invalid argument: '\\lmaxquantstorage.file.core.windows.net\lmaxqr\LMSimData\init_config\LMUtil.json' …")`. Same share, same error class.
- Why it matters: a single storage-access fault is taking down both a RESI portfolio-file job and the daily CLO surveillance deliverable. `[Errno 22] Invalid argument` on an Azure Files UNC path is the classic symptom of the SMB mount/handle going bad (not a missing file) — an infra issue rather than Howard's code.
- Suggested next action: (a) Check the health of the `lmaxquantstorage` Azure file share / SMB mount on the Jenkins app nodes (LMAX-NYAPP01/03/04) — confirm `\\lmaxquantstorage.file.core.windows.net\lmaxqr\LMSimData\init_config\` is reachable and the JSONs open; remount/retry if stale. (b) Once the share is healthy, rerun `quant-ResiPortCreatioin` and the CLO surveillance report. (c) Consider a retry/backoff wrapper around these `init_config` reads so a transient mount blip doesn't fail the whole job.

**2. `quant-CLO-Model-ColorClean-EOD #17037–#17050` — CLO EOD color clean (CLO) — carryover (2nd day), recurring early-AM**
- What failed: ~14 consecutive Build FAILUREs 07:02–08:06 ET, Naginator auto-retrying after each, started by upstream `quant-CLO-Intraday-Workflow`. Still red at 08:06 ET.
- Root cause (console, #17050): `ValueError: No objects to concatenate` — `clo_color_clean.py:168 get_clo_model_color_clean` → `utils.py:349 CleanCLOColorListingDaily` → `utils.py:170 stack_dataframes` → `pd.concat(concat_dfs)` on an **empty list**. Log again shows `the date passed in was NULL / using todays date = 20260610` then "Color Correction Table Refreshed" but no color rows to stack — i.e. EOD clean fired before today's intraday color landed.
- Pattern: identical to yesterday; it **recovered on its own** at 08:38 ET Tue (#16996 "back to normal") after the early failures, then re-broke this morning. So this is a daily timing race, not a one-off.
- Suggested next action: Same as flagged 6/9 and still open — guard `stack_dataframes` / `CleanCLOColorListingDaily` against an empty input (log "no color yet" and exit 0 instead of raising), and/or fix the NULL-date→today intraday trigger so the EOD clean doesn't run before color is available. Confirm today's 6/9-asof CLO color-based outputs aren't degraded.

**3. `quant-Daily-CLO-Report #645` — daily CLO report (CLO) — NEW**
- What failed: Build FAILURE 07:07 ET (timer-started, LMAX-NYAPP01). Email body is uninformative — `Running Daily CLO Report` → `Done` → `Build step 'PowerShell' marked build as failure` (non-zero exit, no Python traceback surfaced).
- Why it matters: same morning window as the surveillance + color-clean failures; plausibly downstream of the file-share / empty-color problems above.
- Suggested next action: Check the `quant-Daily-CLO-Report/645` console for the real exit cause; re-run after the file share + ColorClean are healthy.

**4. `quant-ResiTraceFile #1259` — RESI trace-file export (RESI) — carryover, code bug still unpatched**
- What failed: Build FAILURE Tue 17:13 ET (business-day evening trigger via `quant-ResiTraceFileTrigger`), exactly as predicted 6/8 and 6/9.
- Root cause (confirmed previously): Sentrace returns no RESI traces → `export_to_file` indexes a missing `TRACE` column → `KeyError: 'TRACE'` (empty-result still unguarded; `ReadTraceResi_Sentrace.py`).
- Suggested next action: Short-circuit `export_to_file` when the Sentrace result is empty / has no `TRACE` column (write empty/skip file, exit 0). Will keep failing every business-day evening until patched.

**5. `quant-DailySimHistVector #15` — LMSim sim-history vectors (RESI) — carryover, still failing**
- What failed: Build FAILURE Tue ~20:55 ET. Same SIM2/HELOC family as the `-freestyle` variant; the new-issue path (`DailyNewIssueCRTVectors`) recovered last week but this sim-history path has not.
- Suggested next action: Treat as the remaining tail of the SIM2-on-HELOC instability — pursue the engine roll-back vs. hotfix independently of the new-issue recovery.

**Lower-confidence / borderline (ownership unclear — noted, not owned):**
- `quant-trimaran-galileo-integration-test #116` — Build FAILURE, Tests NOT_RUN (07:55 ET). MorningChecks carryover from #115. Report `S:\QR\Reports\MorningChecks\trimaran-report.html`.
- `quant-galileo-integration-test #480` — Build SUCCESS but **Tests FAILED** (07:15 ET); SWIB variant `#224` PASSED (06:55 ET). Same recurring MorningChecks pattern.
- `quant-HECMYTRisk #14` — Build FAILURE (22:39 ET Tue), same as #13 yesterday. `quant-HECMMonitor #15` SUCCEEDED (00:27 ET Wed), so the monitor is fine. HECM folder is otherwise quiet (no new failures; latest content = April collateral report). Confirm whether HECM YT-risk is yours.
- `quant-Daily-CMBS-Model-Intex-CSV #637` — Build FAILURE (00:06 ET Wed). CMBS Intex CSV loader — likely not RESI/CLO, flagged for awareness.
- Recovered on their own (no action): `quant-DailySaveVolSurface` #2745 FAIL → #2746 back to normal; `quant-dpa-nightly-risk-check` #2060 FAIL → #2061 back to normal.

### RESI Updates
- **Completed:** `quant-Monthly-ResiTracking-Tracking #44` SUCCESS (23:09 ET Tue) and `-Unload #53` SUCCESS (02:07 ET Wed), both to hzeng@ — **no per-cohort RESI-folder failures**. `RESI` folder is clean (newest = `LM Deal List - All Deals Mapped` 19:26 ET Tue; only the stale 6/2 `_PSEUDO` FAILED items remain), so the pipeline-level Tracking SUCCESS is genuine, not masked. `CRT Monitor Report 20260609` delivered (06:05 ET Wed).
- **In progress / blocked:** `quant-ResiPortCreatioin` blocked by the file-share `[Errno 22]` (Failed #1); SIM2/HELOC sim-history vectors still failing (Failed #5).
- **Risks / follow-ups:** Two open RESI code bugs unchanged — `ResiTraceFile` empty-result `KeyError: 'TRACE'` (Failed #4) and the SIM2-on-HELOC crash (Failed #5). The new file-share fault (Failed #1) is the new, higher-urgency RESI blocker.

### CLO Updates
- **Completed:** `quant-CLODaily-Workflow-pipeline #274` SUCCESS (01:05 ET Wed), `quant-CLO-restart-spread-model-celery #59` SUCCESS (04:55 ET Wed), `quant-stage3-eod-tplus0 #52` SUCCESS. Reports delivered: CLO **IO/PO Yields 20260610** (07:05 ET), **Break-Even Yield 20260609** (06:23 ET), **Loan Price Changes 06/10** (changes ≥ 10.0 present), **Large MVOC 2026-06-09**, **US + Europe Lists & Offers 06/09** (several intraday refreshes 08:18→16:47 ET Tue), **Spread Model LO MAE** (GAM v3.0, 01-01→06-08), **Spread Model Curve Comparison** v2/v2r/delev (06-05 vs 06-08), **RV Trades & Positions 06-08**.
- **In progress / blocked:** EOD color clean (`CLO-Model-ColorClean-EOD`) red again on empty concat (Failed #2); **CLO Surveillance Report 06/09/26 FAILED** on the file-share `[Errno 22]` (Failed #1); `quant-Daily-CLO-Report #645` failed (Failed #3).
- **Risks / follow-ups:** Today's CLO surveillance is the one missing CLO deliverable — re-run once the `lmaxquantstorage` share is healthy. Confirm the ColorClean failure isn't degrading today's color-based CLO RV/spread outputs. No spread-model / walk-forward / curve-comparison failures otherwise.

### Email / AUTO Folder Signals
- Direct Outlook access was available; this summary is built primarily from it.
- `Jenkins Automation` (~13.1k items): dominant signals are the **file-share `[Errno 22]`** failures (ResiPortCreatioin), the **ColorClean-EOD** failure storm (2nd day), `Daily-CLO-Report #645`, and the carryover `ResiTraceFile #1259` / `DailySimHistVector #15` bugs. Daily CLO + Resi-tracking + CreditSmile / MorningReports / HECMMonitor all green.
- `Inbox/auto` (~36.4k items, qrprod/qrtest): full Wed-AM routine suite delivered — **CLO Surveillance Report 06/09/26 FAILURE** (the in-scope item), Credit Smiles (Master/LH/LH204/OC-DEF/Value/EV), Axe Sheets, Scenario Returns 06-09-26, Risk/Hedge reports, CRT Monitor 20260609, Companion Fund Holdings, `Listing File Generation & Galileo Portfolio Risk Refresh completed successfully`. **Compliance Engine** and **LIBREMAX/SWIB Risk Run** messages present but out of scope — excluded.
- `CLO` folder: all RV lists, IO/PO & break-even yields, loan-price, MVOC, spread-model MAE & curve-comparison delivered normally; the only failure is today's surveillance report.
- `RESI` folder: clean (newest = Tue-evening LM Deal List; only stale 6/2 `_PSEUDO` failures). `Tracking` folder: latest QR Model Tracking Report 6/8; no new "NQM called deal-months" alert. `HECM` folder: quiet (no new failures).

### Todo
1. **(Infra/RESI/CLO — top priority, NEW)** Get QR ops / yourself to check the `lmaxquantstorage` Azure file share on the Jenkins app nodes — `\\lmaxquantstorage.file.core.windows.net\lmaxqr\LMSimData\init_config\*.json` is failing with `[Errno 22] Invalid argument`. Once healthy, rerun `quant-ResiPortCreatioin` and the **CLO Surveillance Report 06/09/26**. Add retry/backoff around `init_config` reads.
2. **(CLO)** Triage `quant-CLO-Model-ColorClean-EOD` again (2nd day, `ValueError: No objects to concatenate`). Guard the empty-concat path and/or fix the NULL-date→today intraday trigger so EOD clean doesn't fire before color lands. It self-recovered ~08:38 ET yesterday — verify it clears today and didn't degrade 6/9 color-based outputs.
3. **(CLO)** Check `quant-Daily-CLO-Report #645` console for the real exit cause; rerun after #1/#2 resolve.
4. **(RESI)** Patch `quant-ResiTraceFile` `KeyError: 'TRACE'` — short-circuit `export_to_file` on an empty Sentrace result. Re-failed Tue 17:13 ET (#1259); will recur every business-day evening until patched.
5. **(RESI)** SIM2-on-HELOC crash still failing `quant-DailySimHistVector #15` (Tue 20:55 ET); pursue engine roll-back vs. hotfix.
6. **(Awareness)** Glance at MorningChecks Galileo (`trimaran #116` build fail, `galileo #480` tests fail); confirm `HECMYTRisk #14` and `Daily-CMBS-Model-Intex-CSV #637` aren't yours.
7. **(No action)** Daily CLO + Resi-tracking pipelines healthy; RESI per-cohort tracking clean (stale 6/2 `_PSEUDO` only); most CLO reports delivered.
