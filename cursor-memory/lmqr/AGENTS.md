# AGENTS.md — LMQR Workspace

Durable corrections and conventions learned from past sessions.
Shared across all LMQR workspace clones via hardlink.

## R Code Conventions

- Never write defensive column guards (`if ("col" %in% names(df))`) for columns that must always exist. Let missing required columns fail loudly. Only use `%in% names()` for genuinely optional columns or name variations (e.g., `OriginalRating` vs `original_rating`).
- `data.table` column selection by variable requires `df[, cols, with = FALSE]` or `df[, ..cols]`. Bare `df[, cols]` fails silently or errors.
- R `else` must appear on the same line as the closing `}` of the preceding `if` block. Multi-line `if/else` without braces causes "unexpected 'else'" errors.
- R scripts invoked by Jenkins/subprocess must derive `SCRIPT_DIR` from `commandArgs(trailingOnly=FALSE)` matching `--file=`, not hardcode a fallback path. Hardcoded paths fail in Jenkins workspace directories.
- R's `read.csv()` and `as.data.frame()` convert special characters (parentheses, asterisks) in column names to dots by default (`check.names = TRUE`). When processing `ModelOutputJson` term contributions (e.g., `s(c_MVOC)*by(Rating___AAA)`), always use `check.names = FALSE` — regex-based name cleaning fails silently otherwise.

## CLO Model Workflow

- Capped/floored features always get a `c_` prefix; raw columns keep original names. Examples: `c_MVOC`, `c_OfferSize`, `c_AAAFactor`, `c_PercentPriceLe90`.
- Pooled GAM across ratings (AAA+AA+A): normalize features with non-overlapping distributions by their rating-level mean (`x / rating_mean`) so a single shared smooth works. Freeze the mean constants for prediction.
- R research scripts in `lmunittests/clo_model/research_howard/` save `.rds` model files. Production training is orchestrated by `clo_model/procs/clo_dm_based_model_train.py` (Jenkins daily, `--versions v1 v2 v2r`), using `ModelVersionDef` version registry. V2r backfill only: `--versions v2r --models EUR/AAA-A --start_date YYYY-MM-DD --end_date YYYY-MM-DD`. Output: `S:/QR/Risk/CLOCache/core/dm_based_model_v2/`. EUR senior (A-AAA) model entries exist only in `GAM_MODEL_CONFIG_V3`; production uses `BROAD_PROD_MODEL_CONFIG = GAM_MODEL_CONFIG_V2` — V3 must be promoted (or entries merged into V2) before EUR senior DM-based scoring goes live. `clo_spread_model_lo.py` only runs `[KNN_PROD_MODEL_CONFIG, BROAD_PROD_MODEL_CONFIG]` (V2), so V3 predictions don't appear in `clo_spread_model_result` without an explicit config change.
- Production GAM uses `half_life=30` for time-decay weights (`gam.py:148`). The function signature default is 15, but production overrides it. Always check the actual call site, not the default.
- Production GAM uses only time-decay weights (`time_weight`), not listing-type multipliers. Listing-type multipliers (TRADED=2.0, COLOR=0.3, etc.) are from the LGBM research script, not from the production GAM.
- Prod CLO model predictions live in `Libremax_rd.dbo.clo_spread_model_result`. Query with `ModelName='GAM', ModelVersion='v2.0'` (or `BroadModel v5.0`). Filter: `Purpose IN ('Spread-Model-LO','Spread-Model-BWIC')`, `Scenario='Maturity'`. Dedup: `ROW_NUMBER() OVER (PARTITION BY SecurityName, AsOfDate ORDER BY RunDateTime DESC, RunID DESC)`. Note: `Spread-Model-*` purposes cover most bonds; EUR-only bonds (e.g., PSTET) may only exist under `Galileo-*` purposes (Galileo-COVER, Galileo-OFFER, etc.).
- ListingType factor: use OFFER as the reference level (baseline = 0), not BID. This applies across CLO spread models (GAM and LGBM).
- Non-delevered filter (MVOC ≤ 1.03) applies only to BBB. Senior tranches (AAA, AA, A) have MVOC >> 1.03 so the filter zeros out all rows — never apply it to the A-AAA pooled model.
- R-to-production JSON export: For `scam`/`gam` objects, use `clo_model/model/gam/terms.py` classes (`SplineTermData`, `SplineByGroupTermData`, `FactorTermData`). For `mgcv::bam` models (EUR A-AAA), use `clo_model/model/gam/export_bam_json.R`. Production loads JSON via `GAMReplayModel.from_partial_dependence_json()` with PCHIP interpolation — no R dependency at runtime.
- R GAM models use `Rating` (not `f_OrigRating`) as the factor column name — must match `CLOSpreadModelBond` field names at prediction time. Getting this wrong causes silent NaN predictions.
- Subprocess to R from Python: always add timeout, stderr capture, atomic JSON write (write to tmp then rename), and `shutil.which("Rscript")` pre-flight check. R failures are otherwise silent.
- V2r R-trainer config flow: Python (`dm_based_model_v2r/config.py`) exports all model config (features, caps, hyperparams) to a JSON file; the R trainer (`clo_dm_based_model_train_r.R`) reads that JSON. Single source of truth stays in Python.
- In model config dicts (e.g., `feature_labels`), keys must use the actual DataFrame column names with `c_` prefix — `c_AAAFactor` not `AAAFactor`. Mismatched keys silently skip report plots instead of erroring.
- EUR A-AAA BAM productionization: preserve the senior-fit conventions from `lmunittests/clo_model/research_howard/clo_euro_dm_fit_senior.R` and the shared `research_howard` plotting helpers for `c_OfferSize` (`1k-4mm`) and `c_AAAFactor` (`0.95-1.0`), but keep `weight_mode` and weighted PDF diagnostics; after trainer/report changes, regenerate the standard artifact set and rerun the JSON tieout. EUR senior bonds currently fall through to the MVOC curve in production (no active DM-based model); the new BAM/GAM replaces that fallback.
- `resolve_dated_model_path` (in `curve.py`) picks the latest model folder with date strictly `<` the scoring date. A model trained for date D only takes effect for scoring dates >= D+1. To test a freshly retrained model on date D itself, copy the JSON to the prior date's folder.
- EUR and USD GAM models use different spline term names: EUR senior uses `s(c_OfferSize)` and `s(Crossover)`, USD uses `s(c_Size)` and `s(CdxHY)`. When parsing `ModelOutputJson` contributions for reports, the feature-to-contribution key mapping must account for which model produced the prediction.
- `ModelInputJson` in `clo_spread_model_result` contains both raw and capped (`c_*`) features. Always read `c_*` keys (e.g., `c_MVOC`, `c_AAAFactor`, `c_OfferSize`) for display — these are the actual values the model used. Raw values may be null when fallback logic filled the capped version.

## LP / Non-QM ETL

- `wh_lp_config.py` holds SQL templates (UNLOAD_LP_CORE, LP_STATS, LP_MONTHLY_DEAL_TRANS); `wh_lp_update.py` orchestrates the ETL.
- LP date formulas (LP_ASOFDATE, LP_FACTORDATE, LP_ORIG_DATE) use Jumbo formulas as the single default (no DEFAULT/JUMBO branching).
- `doc_type` in SQL_UNLOAD_LP_CORE replaced by `nm.doc_map` from `lps.nonqm_map`; `doc_group` categorization column added.
- `modification_flag` uses temporal check (`factor_date >= mod_date`) to avoid forward-looking bias.
- `lps.lp_svcr` provides `servicer_curr`; `lps.nonqm_map` provides `doc_map`.
- NONQM_MULTI_DEAL_QUERY is a multi-deal variant with `{deal_name_list}` and `{data_start_date}` placeholders; differs from SQL_UNLOAD_LP_CORE in joins and column set.
- In LP unload queries, join `lp_dyn` to `lp_stat` on both `loan_id` and `pool_id`; `loan_id`-only joins can cross-match pools.
- If `dscr_ratio` is coalesced (e.g., NULL -> `1`), any "no ratio" metric must use raw `mspt.dscr_ratio` or `dscr_valid`, not `dscr_ratio is null`; doc normalization/grouping should also test raw DSCR presence.
- User provides R data.table code and expects equivalent Redshift SQL translations in LP config queries.
- User is vigilant about forward-looking bias in loan-level time-series queries; temporal correctness matters.

## HECM / Figure HELOC

- In the HECM collateral-report flow, `Libremax_RD.intex_hecm_deal_loan_map` is a downstream artifact written by `refresh_deal_info()` / `get_deal_info(..., savedb=True)`, so it is not a reliable pre-run Intex readiness signal. Gate pre-run availability with a direct Intex CDU check, then verify the refreshed table contains the target `fctrdt`.
- In the HECM scheduled readiness flow, the live Intex probe samples `2` current portfolio deals by default and must have all sampled deals cover the target `fctrdt` before the job is considered ready.
- In `lmdv01`, `dv01_config.py` and `dv01_config_platf.py` intentionally define different `SQL_UNLOAD_FIGURE_CORE` variants: the former unloads by deal/account name against configurable tables, while the latter unloads explicit `loan_id` lists against the hardcoded Figure Platform tables.
- For Figure HELOC draw-expiry analysis, use the Figure platform query path directly instead of the standard exported `.txt` flat files: the platform SQL computes `loan_draw_period_remaining`, but the flat-file export drops that field.
- Figure-platform Redshift syncs in this repo use the `lmsim-prd` S3 bucket with the shared `lmax_aws_quant` credentials; `lmax-quant` is the wrong bucket and produces `NoSuchBucket`.
- When querying Figure platform BigQuery tables for HELOC analysis, always filter with `loan_program = 'FIGURE_HELOC'` to exclude other Figure products (SL, PF).
- The Figure platform dynamic history table has a `loan_draw_period_remaining` column, but it is 100% NULL for 2019-2025 vintages and therefore unusable. Some loans (especially 2025-vintage) show `line_of_credit_draw_period_end_date` inconsistencies, so when computing draw-term remaining, provide both methods: `DATE_DIFF(line_of_credit_draw_period_end_date, as_of_date)` and `line_of_credit_draw_period - loan_age`.
- When creating analytical report PDFs, always include companion count/observation tables alongside each chart to show sample size per bucket.
- HECM error notification emails (`_send_error_notification`) always go to the hardcoded `MAINTAINER_EMAIL` regardless of who triggers the script; `--email-recipients` only controls success report distribution. Origin tracing (`_collect_origin_info`) was added to identify the source machine/user of phantom failures.

## Plotting

- `plot.gam`/`plot.scam` scale parameter: `scale = 0` → common y-axis across panels; `scale = -1` → free y-axis per panel. These are easily inverted — always verify.
- For binned residual/diagnostic plots on skewed features, use `quantile()`-based breaks instead of equal-width `cut()`. Equal-width bins leave most bins empty when data clusters (e.g., AAAFactor near 1.0).

## General

- LMQR Python tests should run under `conda activate pyprod`; otherwise imports such as `lmdata.lmdb` can fail before the repo's test mocks load.
- V2R training pipeline requires `Rscript` on PATH. On Windows dev machines, add `C:\Program Files\R\R-4.3.2\bin` to PATH if `_find_rscript()` fails.
- "Do not do anything else, but read" means literally only read—no analysis, no suggestions.
