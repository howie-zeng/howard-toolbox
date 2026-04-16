# AGENTS.md — LMQR Workspace

Durable corrections and conventions learned from past sessions.
Shared across all LMQR workspace clones via hardlink.

## R Code Conventions

- Never write defensive column guards (`if ("col" %in% names(df))`) for columns that must always exist. Let missing required columns fail loudly. Only use `%in% names()` for genuinely optional columns or name variations (e.g., `OriginalRating` vs `original_rating`).
- `data.table` column selection by variable requires `df[, cols, with = FALSE]` or `df[, ..cols]`. Bare `df[, cols]` fails silently or errors.
- R `else` must appear on the same line as the closing `}` of the preceding `if` block. Multi-line `if/else` without braces causes "unexpected 'else'" errors.
- R scripts invoked by Jenkins/subprocess must derive `SCRIPT_DIR` from `commandArgs(trailingOnly=FALSE)` matching `--file=`, not hardcode a fallback path. Hardcoded paths fail in Jenkins workspace directories.
- R's `read.csv()` and `as.data.frame()` convert special characters (parentheses, asterisks) in column names to dots by default (`check.names = TRUE`). When processing `ModelOutputJson` term contributions (e.g., `s(c_MVOC)*by(Rating___AAA)`), always use `check.names = FALSE` — regex-based name cleaning fails silently otherwise.
- `mpd`/`mpi`/`mdcv`/`micx` basis types are `scam`-only; `mgcv::bam`/`gam` don't support them. `formula_to_gam()` in `model_config.R` auto-converts `mpd`/`mpi` → `ps`. Write formulas in scam syntax and let the converter handle bam/gam.
- When a SCAM `mpd`/`mpi` constrained spline gets shrunk to zero edf (rank deficient), try `ts` (thin-plate with shrinkage) — the term may be significant without the monotone constraint and may emerge approximately monotone naturally. Happened with `c_WAL` and `c_NumMosToReinv` in the EUR senior model.

## CLO Model Workflow

- Capped/floored features always get a `c_` prefix; raw columns keep original names. Examples: `c_MVOC`, `c_OfferSize`, `c_AAAFactor`, `c_PercentPriceLe90`.
- Pooled GAM across ratings (AAA+AA+A): normalize features with non-overlapping distributions by their rating-level mean (`x / rating_mean`) so a single shared smooth works. Freeze the mean constants for prediction.
- R research scripts in `lmunittests/clo_model/research_howard/` save `.rds` model files. Production training is orchestrated by `clo_model/procs/clo_dm_based_model_train.py` (Jenkins daily, `--versions v1 v2 v2r`), using `ModelVersionDef` version registry. V2r backfill only: `--versions v2r --models EUR/AAA-A --start_date YYYY-MM-DD --end_date YYYY-MM-DD`. Output: `S:/QR/Risk/CLOCache/core/dm_based_model_v2/`. EUR senior (A-AAA) model entries exist only in `GAM_MODEL_CONFIG_V3`; production uses `BROAD_PROD_MODEL_CONFIG = GAM_MODEL_CONFIG_V2` — V3 must be promoted (or entries merged into V2) before EUR senior DM-based scoring goes live. `clo_spread_model_lo.py` only runs `[KNN_PROD_MODEL_CONFIG, BROAD_PROD_MODEL_CONFIG]` (V2), so V3 predictions don't appear in `clo_spread_model_result` without an explicit config change.
- Production GAM uses `half_life=30` for time-decay weights (`gam.py:148`). The function signature default is 15, but production overrides it. Always check the actual call site, not the default.
- Research R scripts in `research_howard/` may default to uniform weights (`weight = 1.0`) while production uses time-decay (`half_life=30`). Always verify that the research script's weighting scheme matches production before drawing conclusions from fit diagnostics.
- Walk-forward / OOS evaluation scripts must exactly replicate the fit script's full config: `half_life`, `weight_floor`, formula, and feature engineering. Mismatches (e.g., walk-forward defaulting to `half_life=15` while the fit script uses `30`) silently invalidate OOS comparisons.
- Highly correlated candidate features (e.g., WAL_Maturity and NumMosToReinv) mutually shrink to zero edf in SCAM/GAM when included together — always test candidates individually before combining.
- Production GAM uses only time-decay weights (`time_weight`), not listing-type multipliers. Listing-type multipliers (TRADED=2.0, COLOR=0.3, etc.) are from the LGBM research script, not from the production GAM.
- Prod CLO model predictions live in `Libremax_rd.dbo.clo_spread_model_result`. Query with `ModelName='GAM', ModelVersion='v2.0'` (or `BroadModel v5.0`). Filter: `Purpose IN ('Spread-Model-LO','Spread-Model-BWIC')`, `Scenario='Maturity'`. Dedup: `ROW_NUMBER() OVER (PARTITION BY SecurityName, AsOfDate ORDER BY RunDateTime DESC, RunID DESC)`. Note: `Spread-Model-*` purposes cover most bonds; EUR-only bonds (e.g., PSTET) may only exist under `Galileo-*` purposes (Galileo-COVER, Galileo-OFFER, etc.).
- `lmunittests/clo_model/research_howard/clo_euro_dm_v2_v3_compare.R` is report-only: fetch both V2 (`GAM v2.0`) and V3 (`GAM v3.0`) from `Libremax_rd.dbo.clo_spread_model_result` and generate the comparison workbook/PDF. Do not load models or rerun scoring inside the report script.
- ListingType factor: use OFFER as the reference level (baseline = 0), not BID. This applies across CLO spread models (GAM and LGBM).
- TRADED listing type maps to COVER (not a separate factor level) in both EUR and USD CLO models. Recode TRADED → COVER before fitting.
- Non-delevered filter (MVOC ≤ 1.03) applies only to BBB. Senior tranches (AAA, AA, A) have MVOC >> 1.03 so the filter zeros out all rows — never apply it to the A-AAA pooled model.
- EUR delevering bond definition: `NumMosToReinv < 0` AND `AAAFactor < 1.0` (past reinvestment period, actively deleveraging). No MVOC filter for the delev model.
- MVOC > 1.03 serves two independent roles: (1) a training-data filter (excluded from EUR delev training per Glenn) and (2) a scoring-time routing gate in `predict_single` that directs bonds to delev vs non-delev model. Removing the filter from training data does not affect the scoring-time routing gate — both must be reasoned about separately.
- R-to-production JSON export: For `scam`/`gam` objects, use `clo_model/model/gam/terms.py` classes (`SplineTermData`, `SplineByGroupTermData`, `FactorTermData`). For `mgcv::bam` models (EUR A-AAA), use `clo_model/model/gam/export_bam_json.R` — this also works with `scam` objects (scam inherits from gam), so exported PCHIP curves are monotone by construction from the scam fit. Production loads JSON via `GAMReplayModel.from_partial_dependence_json()` with PCHIP interpolation — no R dependency at runtime.
- R GAM models use `Rating` (not `f_OrigRating`) as the factor column name — must match `CLOSpreadModelBond` field names at prediction time. Getting this wrong causes silent NaN predictions.
- Subprocess to R from Python: always add timeout, stderr capture, atomic JSON write (write to tmp then rename), and `shutil.which("Rscript")` pre-flight check. R failures are otherwise silent.
- V2r R-trainer config flow: Python (`dm_based_model_v2r/config.py`) exports all model config (features, caps, hyperparams) to a JSON file; the R trainer (`clo_dm_based_model_train_r.R`) reads that JSON. Single source of truth stays in Python. Promoting research to V2R production requires syncing formula, feature clips, weight_mode, and model_type across 3 files: `clo_model/spread_model/common.py` (bond derived fields), `dm_based_model_v2r/config.py` (Python config), and `clo_dm_based_model_train_r.R` (R trainer).
- In model config dicts (e.g., `feature_labels`), keys must use the actual DataFrame column names with `c_` prefix — `c_AAAFactor` not `AAAFactor`. Mismatched keys silently skip report plots instead of erroring.
- EUR A-AAA BAM productionization: preserve the senior-fit conventions from `lmunittests/clo_model/research_howard/clo_euro_dm_fit_senior.R` and the shared `research_howard` plotting helpers for `c_OfferSize` (`1k-4mm`) and `c_AAAFactor` (`0.95-1.0`), but keep `weight_mode` and weighted PDF diagnostics; after trainer/report changes, regenerate the standard artifact set and rerun the JSON tieout. EUR senior bonds currently fall through to the MVOC curve in production (no active DM-based model); the new BAM/GAM replaces that fallback.
- In `lmunittests/clo_model/research_howard/clo_euro_dm_fit_senior.R`, derive size by listing side (`BID` -> `BidSize`, `OFFER`/`COVER`/`TRADED` -> `OfferSize`, `BID/OFFER` -> midpoint) and drop rows with missing/non-positive derived size instead of filling them with `1e6`.
- `clo_color_*_{start}_{end}_{rating}_{ccy}.parquet` files do not sort "latest" lexicographically because the start date comes first. When loading the newest color parquet (e.g., in `eur_model_utils.R`), parse the embedded end date and choose the max end date instead of `max(filename)`. When multiple files share the same end date but differ in start date, the default tiebreaker (`order(end_dates, start_dates, decreasing = TRUE)`) picks the **shorter-history** file; use a `prefer_start_date` parameter in `load_eur_color_data`/`find_latest_color_parquet` to explicitly pick the longer-history file when needed.
- Unmapped `ListingType` values (e.g., `"LM BWIC"` present in 2024+ windows) silently pass through `derive_listing_type` as literal factor levels and then break `predict.scam(newdata, type="terms", se.fit=TRUE)` during JSON export with `number of items to replace is not a multiple of replacement length`. Add new variants to `EXCLUDE_LISTING_TYPES` and enforce an allow-list filter (`f_ListingType %in% c("OFFER","BID","COVER","BID/OFFER")`) post-mapping before fitting/exporting.
- `NAV` vs `EquityNAV`: `NAV` is tranche-level (collateral minus senior claims, normalized by tranche balance); `EquityNAV` is equity-specific (collateral minus all debt tranches). Use `EquityNAV` for delev BBB/BB/B models as a deal-health signal orthogonal to `MVOC`/`Attach`; use `NAV` normalized by rating mean for senior A-AAA pooled models.
- `resolve_dated_model_path` (in `curve.py`) picks the latest model folder with date strictly `<` the scoring date. A model trained for date D only takes effect for scoring dates >= D+1. For verification, prefer scoring date D+1 or retraining for the prior dated folder; avoid copying JSON across `core/dm_based_model_v2/{date}/` folders unless the user explicitly wants a manual override.
- Never run V2R/V3 model training from a feature branch against the shared `dm_based_model_v2/` output path — incompatible model JSON (e.g., V3 features like `c_MVOC_norm`) will silently overwrite production V2 models. This caused a prod incident where `CLOSpreadModelBond` lacked the V3-only attribute. Always verify the active git branch matches the target model version before training.
- EUR and USD GAM models use different spline term names: EUR senior uses `s(c_OfferSize)` and `s(Crossover)`, USD uses `s(c_Size)` and `s(CdxHY)`. When parsing `ModelOutputJson` contributions for reports, the feature-to-contribution key mapping must account for which model produced the prediction.
- `ModelInputJson` in `clo_spread_model_result` contains both raw and capped (`c_*`) features. Always read `c_*` keys (e.g., `c_MVOC`, `c_AAAFactor`, `c_OfferSize`) for display — these are the actual values the model used. Raw values may be null when fallback logic filled the capped version.
- Cap/floor rules in `rules.py` define broad feature ranges (e.g., WAP [90,100], AAAFactor [0.85,1.0]), not tight model training clips. The model JSON handles out-of-range values at prediction time via PCHIP boundary behavior. Derive features for all bonds through the shared rules tables (`CAP_FLOOR_RULES`, `PRICE_BASED_CAP_FLOOR_RULES`) — no hardcoded `is_eur_delev` or per-path branching in `common.py`.
- Running `clo_spread_model_lo.py` from a feature branch writes predictions with the same ModelName/ModelVersion/Purpose as prod Jenkins, silently overriding prod predictions in `clo_spread_model_result`. Use a custom purpose string (e.g., `EUR-Delev-NewModel-LO`) when scoring from a feature branch for comparison.

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
- `wh_lp_update.py` main loop: when `runUnload` returns `None` (exception path), the deal must be skipped entirely — do NOT fall through to `runDealStats`, which updates `libremax..lp_deal_last_update.last_download_factor_date` and silently marks a failed download as complete (no retry next run). Guard with `if unload_result is False or unload_result is None: return`. The `False`-only guard is a bug.
- `wh_lp_update.py` supports `--max_workers` (default 4) for parallel deal processing via `ThreadPoolExecutor`; use `--max_workers 1` for sequential. Safe to parallelize because `executeSQLTableDF`/`executeSQLRedshiftDF` open a fresh DB connection per call, ZIP/UNZIP output files are uniquely named by `pool_id`+date, `deal_manager` is read-only in the loop, and each deal writes only its own `bb_deal` row to `lp_deal_last_update`.

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
- Feature clips (`pmax`/`pmin`) must leave sufficient spread for spline fitting. If floor/cap collapses all data to a single value, scam/bam errors with "x data must be in range X to X". Always check `summary(feature)` before setting clip bounds.

## NLP / Color Parsing

- CLO/ABS/CMBS/RMBS dealer color and BWIC emails are parsed by an in-house custom-trained **spaCy NER + PyTorch/Thinc** model in `NLP_Parsers/` (not a hosted LLM like OpenAI/Anthropic). Training entrypoint: `NLP_Parsers/nlp_model_training.py:runNlpModel`; utilities and CLO sector classification in `nlp_utils.py`. Feature vectors are injected into the spaCy `tok2vec` layer via sub-models (header/listing/dealer/type/asset) — spaCy version bumps can silently break predictions (see header warning in `nlp_model_training.py`). Model artifacts live under `S:\QR\Models\NLP_Parse`.
- CLO-specific orchestration: `colordb/parserclo.py:ParserCLO` (email/Excel parser), `colordb/parser.py`/`parserprice.py`/`parserfactory.py` (shared base classes, price string parsing). Production Jenkins runners per dealer live in `JenkinsScripts/ColorParser/` (`baml_parser.py`, `goldman_parser.py`, `jpm_bwic_parser.py`, `morganstanley_parser.py`, `wellsfargo_parser.py`, `mufg_parser.py`, dispatched by `parse_bwic_color.py`).

## DV01 / Figure Platform Sync

- `dv01_redshift.py` syncs BigQuery → Redshift via multi-part gzipped CSV upload to `s3://lmsim-prd/exports/{table}/part_NNNN.csv.gz`. Schema validation and COPY retry are per-table; a single table failure doesn't block the others.
- Never use `SET statement_timeout TO 0` in production Redshift queries — optimize the query itself (multi-part COPY, filter pushdown) instead of disabling the safety timeout.

## CRT Pseudo Deals

- In `wh_crt_pseudo_sample.py`, push status/age/dirty-current filters **before** the 6 HPI table joins for UPDLTV buckets. Joining HPI on the unfiltered universe causes CC/DC UPDLTV queries to timeout (~2 hrs).
- When validating a SQL rewrite for equivalence, use `EXCEPT`-based exact row comparison (old EXCEPT new, new EXCEPT old), not just row-count matching. Counts can match while individual rows differ.

## General

- LMQR Python tests should run under `conda activate pyprod`; otherwise imports such as `lmdata.lmdb` can fail before the repo's test mocks load.
- V2R training pipeline requires `Rscript` on PATH. On Windows dev machines, add `C:\Program Files\R\R-4.3.2\bin` to PATH if `_find_rscript()` fails.
- `S:\QR\hzeng\howard-toolbox\cursor-memory\` is the canonical store for all project memory files. `sync-memory.ps1` runs bidirectional newer-wins sync every 15 min. LMQR has 4 clones on C:\Git that are hardlinked (same physical AGENTS.md file). When the agent updates AGENTS.md, it should also sync to the canonical store at `cursor-memory/lmqr/AGENTS.md`. Never copy one project's AGENTS.md to another project's repo root.
- "Do not do anything else, but read" means literally only read—no analysis, no suggestions.
