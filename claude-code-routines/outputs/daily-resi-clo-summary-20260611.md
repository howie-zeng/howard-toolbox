# Daily RESI/CLO Summary — 2026-06-11

_Window: last ~24h (2026-06-10 → 2026-06-11 morning). Source: Outlook `Jenkins Automation`, `CLO`, `RESI`, `Tracking`, and `Inbox/auto` folders (queried directly). Times shown ET (UTC−4). Risk runs, Resi SSS generation, and the Compliance Engine are out of scope and excluded._

## Executive Summary

- **CLO color-clean is red this morning.** `quant-CLO-Model-ColorClean-EOD` failed ~14 times in a row (#17103–#17116, 07:02–08:06 ET) with `ValueError: No objects to concatenate` — the color listing came back empty. The same job did this on 06-10 then self-recovered by ~09:08 ET, so this is most likely the recurring "color data not yet populated" morning timing failure; **confirm it cleared after the intraday color feed landed.**
- **Two RESI vector/export jobs need Howard's attention.** `quant-DailySimHistVector` is red two nights running (#15 FAILURE, #16 ABORTED), and `quant-ResiTraceFile` #1260 failed on a **real code bug** (`KeyError: 'TRACE'`) whenever Sentrace returns no RESI traces — it will keep failing until the empty-result case is handled.
- **CLO Spread-Model LO T0 report is red** (US #447 and EUR #133/#134) with no recovery in the window — needs a console-log look.
- **The daily report pipelines are otherwise healthy** — CLO surveillance/yields/RV/MAE/curve-comparison and the RESI monthly-tracking + deal-mapping all delivered. The June-2 pseudo-cohort tracking failures (NONQM/JUMBO2_0/CAS/HELOC_PSEUDO) did **not** recur.
- One transient CLO surveillance failure (06-10, `LMUtil.json` Azure read error) **recovered on its own** — monitor only.

## Failed / Concerning Jobs

**1. quant-CLO-Model-ColorClean-EOD — RED (CLO color ingestion)**
- What failed: ~14 consecutive build failures on 06-11, #17103–#17116 (07:02–08:06 ET), auto-retried by Naginator after each failure. Latest still FAILURE as of the snapshot.
- Evidence (#17116): `ValueError: No objects to concatenate` — `clo_color_clean.py:168` → `utils.py:349 stack_dataframes` → `pd.concat(concat_dfs)`. Log shows "Color Correction Table Refreshed" then nothing to concatenate, i.e. the raw color listing was empty for as-of 2026-06-11.
- Context: identical morning loop on 06-10 (#17037–#17061) **self-recovered** at #17062 "back to normal" (~09:08 ET). Pattern = color data not yet present when the EOD clean fires.
- Suggested next action: confirm #17117+ went green once the intraday color feed populated. If still red past midday, check why `CleanCLOColorListingDaily` is getting an empty raw set from `quant-CLO-Intraday-Workflow`; consider a guard so an empty listing logs a skip instead of a hard `concat` error.

**2. quant-DailySimHistVector — RED two nights (RESI/CRT LMSim sim-history vectors)**
- What failed: #15 FAILURE (06-09 20:55 ET), #16 ABORTED (06-10 20:53 ET). Covers CRT/NQM/CES/HELOC/Figure deals.
- Evidence: #16 ended in ABORTED (kill/timeout, no traceback in the notice). Consistent with the known pattern of ending short (~99.9%) on a tail of deals / the Ray job dying.
- Suggested next action: this is now multi-day — pull the #16 console log for the deal tail that hangs; decide whether to raise the Ray timeout or quarantine the offending deal(s).

**3. quant-ResiTraceFile #1260 — FAILURE, code bug (RESI TRACE export)**
- What failed: build #1260 (06-10 17:13 ET), triggered by `quant-ResiTraceFileTrigger` #440.
- Evidence: log shows "No traces fetched from Sentrace for the Residential Bonds for the provided time range", then `KeyError: 'TRACE'` at `ReadTraceResi_Sentrace.py:308` — `export_df["TRACE"] = export_df["TRACE"].str.lstrip("$")` assumes the `TRACE` column exists. Empty Sentrace result → no such column.
- Suggested next action: **Howard's fix** — guard `export_to_file()` for the empty / no-TRACE-column case (early return, or build an empty frame with the expected schema). It will fail every time Sentrace returns zero RESI traces.

**4. quant-CLO-Spread-Model-LO-Report-T0-Workflow (+ -EUR) — RED (CLO spread model report)**
- What failed: US #447 FAILURE (06-11 08:03 ET); EUR #133 (06-10 08:30 ET) and #134 (06-11 07:49 ET) FAILURE. No "back to normal" seen in the window.
- Evidence: build-failure notices only (no traceback in the emails).
- Suggested next action: pull the console log for #447 / #134 (GAM v3.0 Spread-Model-LO T0 report) to get the underlying error.

**5. quant-HECMYTRisk — RED two nights (HECM, lower priority / confirm ownership)**
- What failed: #14 FAILURE (06-09 22:39 ET), #15 FAILURE (06-10 22:38 ET). `quant-HECMMonitor` ran SUCCESS both nights, so the HECM monitor itself is fine.
- Suggested next action: confirm whether HECM YT-Risk is yours; if so, check the #15 log. Flagged because HECM is in your folder map.

## RESI Updates

- **Completed:** `quant-Monthly-ResiTracking-Tracking` #45 ✓ and `-Unload` #54 ✓ (overnight into 06-11); "LM Deal List — All Deals Mapped" (06-10 19:26 ET, clean — all deals mapped); CRT Monitor Report 20260610 ✓ (06-11 06:05 ET); `quant-HECMMonitor` #16 ✓.
- **In progress / risks:** `quant-DailySimHistVector` (RED), `quant-ResiTraceFile` (code bug), `quant-HECMYTRisk` (RED).
- **Good news:** No new per-cohort RESI tracking/unload failures in the last 24h — the June-2 pseudo-cohort failures (NONQM/JUMBO2_0/CAS/HELOC_PSEUDO, tied to LMQR PR #12760 gating fix) did **not** recur; the monthly-tracking sub-jobs ran SUCCESS and the deal list mapped fully.

## CLO Updates

- **Completed:** `quant-CLODaily-Workflow-pipeline` #275 ✓; `quant-CLO-restart-spread-model-celery` #60 ✓; CLO Surveillance Report 20260610 ✓ (delivered 06-11 07:12 ET) and 20260609 ✓; CLO IO/PO Yields, Break-Even Yields, Loan Price Changes, Large MVOC Movement ✓; CLO US+Europe RV Lists & Offers ✓ (multiple intraday); CLO Spread Model LO MAE Report (GAM v3.0) ✓; Spread Model Curve Comparison v2/v2r/delev (8 models) ✓; CLO RV Trades & Positions ✓.
- **In progress / risks:** `quant-CLO-Model-ColorClean-EOD` (RED — likely morning timing); `quant-CLO-Spread-Model-LO-Report-T0-Workflow` US + EUR (RED).
- **Recovered (monitor only):** CLO Surveillance 06/09/26 sent two FAILURE notices on 06-10 (07:07 & 08:50 ET) — `MissingRateData … [Errno 22] Invalid argument: '…\LMSimData\init_config\LMUtil.json'` (transient Azure file-share read). It recovered: surveillance reports delivered later the same/next morning, and `quant-Daily-CLO-Report` went #645/#646 FAILURE → #648 "back to normal".

## Email / AUTO Folder Signals

- **`Jenkins Automation`** (105 msgs in window) — dominated by the `quant-CLO-Model-ColorClean-EOD` failure loop above. Other in-scope failures: DailySimHistVector, ResiTraceFile, Spread-Model-LO-Report-T0 (US+EUR), HECMYTRisk. Recoveries: `quant-ResiPortCreatioin` #1277→#1278 back to normal; `quant-DailySaveVolSurface` flapped (#2745/#2747 fail → #2746/#2748 recover, not RESI/CLO core).
- **`CLO`** (qrprod) — all standard CLO products delivered (surveillance, yields, RV lists/offers, MAE, curve comparison). Only the 06-09 surveillance failure (recovered, above).
- **`Inbox/auto`** (181 msgs in window, qrprod/compliance) — standard daily distribution all delivered cleanly: Portfolio Sensitivities, Fund Reports, Credit Smiles, Axe Sheets, Risk Monitor, Hedge/Carry, CRT Monitor, Companion Fund Holdings, "PASS — Form PF Compliance". No failure notices.
- **`RESI` / `Tracking`** — no new failures in window; latest RESI per-cohort FAILED notices date to 2026-06-02 (resolved).
- _Excluded as out of scope:_ LIBREMAX/SWIB risk runs, Daily Resi SSS, Compliance Engine. _Excluded as not RESI/CLO core:_ CMBS loaders (`quant-Daily-CMBS-Model-Intex-CSV` #637/#638, `quant-CMBSLoader` #1171 failing), creditsmile equity-hist (recovered), galileo/trimaran integration morning-check tests (`quant-trimaran-galileo-integration-test` build FAILURE / tests NOT_RUN; `quant-galileo-integration-test` tests FAILED) — noted in case they overlap your work.

## Todo

1. **Confirm CLO ColorClean-EOD recovered** today after the intraday color feed landed (#17117+); if still red past midday, investigate the empty color listing from `quant-CLO-Intraday-Workflow`. Consider a guard so an empty listing skips cleanly instead of raising `No objects to concatenate`.
2. **Fix `quant-ResiTraceFile` empty-result bug** — handle the no-traces / missing `TRACE` column case in `ReadTraceResi_Sentrace.py:308` (`export_to_file`). Real code bug; recurs on any zero-trace day.
3. **Investigate `quant-DailySimHistVector`** — now red two nights (#15 FAILURE, #16 ABORTED). Check the deal tail / Ray timeout; quarantine or re-run.
4. **Check `quant-CLO-Spread-Model-LO-Report-T0` (US #447 + EUR #134)** console logs — red with no recovery.
5. **Triage `quant-HECMYTRisk`** (#14/#15 FAILURE) — confirm ownership, then read the #15 log.
6. **Monitor** the CLO surveillance `LMUtil.json` Azure read error for recurrence (recovered for now).
