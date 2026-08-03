# Handoff — Report refactor (next session)

_Written 2026-07-14. Pick up here after clearing session._

> This handoff covers simulation and reporting work in `auto-sim`. For the
> upstream ABS-EE transition and severity model-training pipeline, see
> [`docs/abs_ee_training_runbook.md`](docs/abs_ee_training_runbook.md).

## Where we are (model state — done, don't redo)
- **`ctco` (C→LIQ) transition** is live: `config/auto_prime.json` fromC gam_models has
  `{"path":"from0/models/ctco_bam.rds","to_status":"LIQ"}` and `status_to_roll["C"] = ["C","D1M","PIF","LIQ"]`.
  This closed the HART topology gap (direct-from-Current charge-offs): HART sim 0.84→1.83% ≈ actual 1.68%.
- **`dq6_bkt` momentum feature** (6-month bounded delinquency memory, count of DQ months in trailing 6 →
  buckets `0/1/2-3/4-6`) is implemented in Python (`simengine/register_vars.py::reg_dq6_bkt`) and C++
  (`src/var_registry.cpp::reg_dq6_bkt`, uses a 64-entry lookup table), seeded from tapes in
  `auto_tape.py::_delinquency_history`. Old momentum vars (ever_dq_flag, months_in_current_bkt, _mic) were
  removed. Dumped under **`input/coef/PRIME_BASE_HISTORY`** via `tools/dump/dump_history.py`.
- **realized.py dedup fix**: `chargedoffprincipalamount` re-reporting (CarMax 1.36×) is zeroed after first
  charge-off per assetnumber. CarMax realized CGL 5.40→3.99%.
- **ctd1 aging flatten**: `tools/flatten_ctd1_aging.py` floors the post-peak fit dip at `min(peak,recovery)`,
  preserving the true peak and the age_pct>1 tail.

### CarMax / PRIME_BASE_HISTORY finding (closed)
Only CMAX_2022_1 moved materially under PRIME_BASE_HISTORY (−0.57 CGL, now *under* its ~4% actual).
Diagnosis (verified, not resecuritization — 0 assetnumber overlap): `dq6_bkt` buildup is **similar across
deals** (CMAX 5.2%, CRVNA 4.3%, HART 3.5%, TAOT 3.4% of Current pool by p48), so it's not "CarMax cycles
more." The feature is a near-wash for **fresh, correctly-seeded** pools (Carvana/HART) — it just redistributes
entry between `dq6=0` and `dq6>0` without shifting the pool total. It only moves the aggregate for **CarMax**,
whose 26%-seasoned collateral sits at high `c_age_pct` where the refit re-leveled entry down, AND whose
pre-securitization delinquency is **unobservable** → seeded `dq6=0` → eats the lowered baseline without the
compensating bump. Net: **PRIME_BASE_HISTORY is the fresh-deal model; PRIME_BASE (with ctco) remains better
for seasoned-collateral platforms like CarMax.** Open (not started): optional seasoning-conditioned `dq6`
floor so seasoned loans aren't treated as pristine.

---

## NEXT TASK — Report refactor (`python/deal_report/pages/backtest.py`)

Three pieces, in priority order. All live in the **backtest page** ("Sim Performance vs Actual"), 551 LOC.
Entry: `builder.py:105 build_backtest_html(...)`. The curve/heatmap helpers (`_curve_spec`, `_long_records`,
`_ymax`, `_matrix_heatmap_spec`, `_lag_bar_spec`) are all in the same file.

### 1. (PRIMARY) Prune transition-rate plots + revisit cutoffs — **DONE (pruning); horizon revisit optional**
Some transition rates are **not worth plotting** — near-zero in both realized and modeled, they clutter the
tabbed "Transition Rates" section.
- **DONE — plot-worthiness cutoff** (`backtest.py`): added `_RATE_PLOT_MIN_PEAK = 0.005` +
  `_RATE_ALWAYS` (structural entry/charge-off transitions) + `_worth_plotting(p,a,fs,to,horizon)`. The
  transition-rate loop now skips any `(fs→to)` whose modeled AND realized rate both stay below 0.5% over the
  horizon, and drops a whole tab if every transition in it is pruned (first surviving tab becomes active).
  Nothing hard-deleted from `_RATE_TABS` — filtering is dynamic, so a deal where a transition IS material
  still shows it. Verified with synthetic frames: 6 noise transitions (D1M→PIF, D2M→D1M, D3M→C, D3M→D2M,
  D4M→C, D4M→D3M) pruned; structural + cures kept; full-tab-drop path works.
- **DONE — surfaced `C → LIQ` (ctco)** in the From-C tab (it wasn't plotted before, though ctco is now live).
- **REMAINING (optional) — revisit horizon / y-window** (backtest.py `horizon` calc, perf loop, `_ymax`):
  the runoff-tail spike and unified `horizon` sometimes over-plot. Confirm CDR/CPR y-clamp still reads well;
  consider trimming the x-axis where the pool is nearly gone. Low urgency.
- Config-driven: `_RATE_PLOT` whitelist near `_RATE_TABS` (final approach — see below).

**UPDATE (superseded the threshold approach):** peak-threshold pruning fired on nothing for real deals
(delinquent-state rates are large; runoff tail spikes to 100% rescued dead transitions). Replaced with an
explicit whitelist `_RATE_PLOT = {C→D1M, C→PIF, D1M→C, D1M→D2M}` — only the well-populated C/D1M
transitions; deep buckets (D2M/D3M/D4M) dropped entirely (their late-deal rates are single-loan noise).
Matrix heatmap in-cell labels now 2 dp (`.2f`) since from-C rates are small.

**UPDATE — backtest page inlined (consistency refactor):** the Sim-Performance-vs-Actual page is no longer
an iframe. It's now an inline `.report-page` fragment like Aggregate/Pool-Composition — `build_backtest_html`
takes `specs`/`plot_id`, appends its Vega specs to the shared list (shell `renderSpecs` renders them), and
returns `(fragment_html, plot_id)`. Added a KPI-card row on top (projected vs actual CGL/CNL/pool-factor at
last reported month). Ported `.note`/`.mtx-legend`/`.l2-*` CSS + an `initL2Tabs()` handler into the shell
(`render/assets.py`). Dead `_HEAD`/`_compose` full-doc scaffolding removed. This also fixes the
sticky-header inconsistency (the page now scrolls like the others; nav stays sticky via `.page-nav`).
Cashflow Comparison is ALSO inlined now (`build_cf_comparison_html` takes `specs`/`plot_id`, returns a
fragment via the shared `kpi_grid`; `_iframe_page` deleted — no iframes anywhere in the report). NOTE: the
CF tab returns None for every AUTO deal because no auto deal has a config under
`S:/QR/jli/Cashflow_Engine/deals/` (only MPL deals: par_*, afrm_*, rktl_*, upst_*). So the tab won't render
for CRVNA/HART/etc. until a CF config is added — the inline code is verified via unit test, not a live report.

Also done this round: dropped the "Reported Through" backtest KPI; restyled the transition-matrix heatmap
to the report's sans-serif stack (`_FONT`), smaller cells (`step` 38→31) and fonts (title 12, axis 9, cell
labels 8.5), thinner cell borders.

NEXT (user flagged): revisit the cutoff/horizon values (the optional item under Task 1).

### 2. (LOWER PRIORITY) Overlay multiple models/scenarios
Today `build_backtest_html` takes a **single** scenario's metrics and overlays it vs Actual. We want to
overlay **multiple model configs** (e.g. `PRIME_BASE` vs `PRIME_BASE_HISTORY`) as extra series on the same
curves — so we can eyeball model deltas against actual on one chart. The plumbing largely exists:
`_long_records` + `_curve_spec` already build long-form multi-series records with a color/series encoding
(that's how Projected vs Actual works). Generalize the signature to accept a **dict `{label: metrics_dfs}`**
(or a list of scenario bundles), assign a color per series, and extend `_trans_pair`/the perf loop to append
one record set per model. `builder.py:105` would pass the extra scenario(s) it loaded from
`output/<deal>/<other_scenario>/sim_results.xlsx`. The original port plan (BASE/STACKED/Actual overlay) is
the same shape — see `.claude/plans/let-s-do-a-cleanup-*.md` Phase 6.

### 3. Rolling-Forecast overlay — **DONE**
(Named "Rolling Forecast" — red, dashed — in the UI; internally still `onestep`.)
Full pool, no sampling, scored in **parallel** (`multiprocessing.Pool`, worker-initializer builds the
DataManager once per process; lightweight task chunks). Off-by-one FIXED (score the FROM pool at tape period
`per-1`; sim/realized convention is from-row m → period m+1). Panel is loaded ONCE by `realized.compute_realized`
(returns `panel`) and reused by `onestep` (no 2nd SMB read); dq6 masks vectorized. Whole report ~86s (was
139s). `compute_onestep(..., sample=N)` caps loans/month if ever needed (None = full). NOTE: Windows spawn —
must be driven from a real file entry (`generate_deal_report.py`/`regen_all_reports.py`), never a heredoc/stdin
(stdin main breaks worker bootstrap → spawn loop).

### Report-gen performance — **DONE**
`realized.load_panel` now (a) reads the monthly tapes **concurrently** (ThreadPoolExecutor, I/O-bound over
SMB) and (b) caches the raw concatenated panel to `output/_panel_cache/<deal>.parquet` — ONE folder, one file
per deal, overwritten when any tape is newer (mtime check), model-independent (realized data → serves all
scenarios), self-invalidating, graceful fallback on any cache error. CRVNA_2022_P2 PRIME_BASE full report:
139s → 86s (panel shared) → 67s (parallel reads) → 33s (panel cache) → **29s warm** (static-logit cache);
raw report 65s → **13s warm**. `onestep` now (a) groups each loan's months so its **static logit is built
once and reused** (mirrors run_cf_one's internal reuse; validated bit-identical to the per-call version) and
(b) **adaptively** runs sequentially for small deals / pools for large (total loan-months ≥ 800k), since the
static cache made scoring cheap enough that the ~12s Windows-spawn pool startup isn't worth it on small
deals. **dq6-freeze bug (FIXED):** the static-logit cache froze `dq6_bkt` at its month-1 value (=0) because
`dq6_bkt` is PATH_DEPENDENT and the registry's `time_varying_names()|macro_names()` excludes PATH_DEPENDENT
→ classified static → baked into the per-loan static cache → the dq6 bump never fired. Symptom: PRIME_BASE_HISTORY
Rolling Forecast was flat/low (HART ctd1 0.24→0.39 vs Projected 0.24→1.06). Fix: `onestep._prepare_dm` now adds
PATH_DEPENDENT var names to `dynamic_vars` before `classify_model_terms`, so dq6_bkt is evaluated fresh each
period. Only HISTORY reports were affected (BASE has no dq6). NB: RF caches keyed on tape/coef mtime don't
invalidate on code changes — delete `output/*/*/rolling_forecast.parquet` after touching onestep scoring.

Full pool, no sampling (the `sample` knob remains, unused). **Rolling-forecast OUTPUT cache** (the key
win): the ~48-row result is fully determined by (tapes + coef version), so `generate_deal_report._cached_onestep`
stores it at `output/<deal>/<scenario>/rolling_forecast.parquet` and reuses it unless a tape OR a coef file
is newer. So the ~16s one-step compute happens ONCE per (deal, tapes, coefs); every re-run loads ~48 numbers
(~0s). Timings: full report RF-miss ~28s, **RF-hit 13s** (== raw report; one-step free). Panel cache
invalidates on new tapes; both caches self-invalidate on freshly-dumped data/models. At the optimization floor.

### 3-orig. One-step-ahead overlay — **DONE**
Implemented as a toggle-able **One-step** series (dotted amber) on the `ctd1` (C→D1M) and `ctp` (C→PIF)
transition charts. `python/onestep.py::compute_onestep` re-seeds from the realized pool each month (reuses the
prepped start tape's static covariates + the realized panel for survival/balance/dq6, re-bakes age/calendar
via `registry.derive_initial(..., c_fields={"c_age_pct"})`, and scores one period with the sim's own
`run_cf_one`) — no extra tape reads, exact sim scoring, ~70s/scenario. Validated: at period 1 One-step ≈
Projected (pool hasn't drifted), diverging above Projected later (the compounding signal). `_curve_spec` gained
an `onestep` mode (3rd series + `showOS` param); `build_backtest_html` takes `onestep_df`; a bottom toggle in
the shell (`initOnestepToggle`) drives `showOS`. Computed per scenario in `generate_deal_report.py`
(`--no-onestep` to skip). Gap-vs-Projected = compounding drift; gap-vs-Actual = per-step model error.

### 3b. (original scoping notes, for reference) One-step-ahead plot + divergence
Add a **one-step-ahead** view: instead of the compounding multi-step projection (which is what all current
curves show), re-seed the model from the **realized state at period t** and predict period **t+1** only, for
each t. Overlay one-step-ahead prediction vs realized next-period. This isolates **per-step model error**
from the **compounding/path-dependence error** that accumulates in the full projection — i.e. answers "is the
model wrong each step, or does small per-step error just snowball?" (This was the user's original intuition on
HART: "small errors in tiny transition rates cause major issues down the line.") Plot the one-step series
alongside the cumulative series and/or a **divergence** panel (cumulative − one-step). Likely needs a new
sim/dump mode that scores one-step-ahead from realized tapes (the `--dump` path already scores per-step
transitions; the realized state per period is in `actuals_transitions`/`actuals_matrix`). Scope this properly
at the start of the session — it's the largest of the three.

---

## Regenerate everything (run remotely — heavy)
Per-deal loop (prep → fit-free dump already done → sim → realized → report). The sim uses the C++
`build/sim_main.exe` (ties out with Python, ~60s/deal). Reports:
```
C:/QR/miniconda/envs/pyprod/python.exe python/generate_deal_report.py --deal <DEAL> --scenario PRIME_BASE_HISTORY
```
Scenarios: `PRIME_BASE` (ctco, best for CarMax) and `PRIME_BASE_HISTORY` (dq6_bkt, fresh deals).
Deals validated this cycle: CMAX_2022_1, HART_2022_A, TAOT_2022_A, CRVNA_2022_P1/P2, CRVNA_2024_P2.

## Scratch cleaned up
- `_dq6_dist.py` (repo-root scratch) — **deleted** after use.
