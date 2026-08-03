# AGENTS.md — LMQR Workspace

Durable corrections and conventions learned from past sessions.

## R Code Conventions

- Never write defensive column guards (`if ("col" %in% names(df))`) for columns that must always exist. Let missing required columns fail loudly. Only use `%in% names()` for genuinely optional columns or name variations (e.g., `OriginalRating` vs `original_rating`).
- `data.table` column selection by variable requires `df[, cols, with = FALSE]` or `df[, ..cols]`. Bare `df[, cols]` fails silently or errors.
- R `else` must appear on the same line as the closing `}` of the preceding `if` block. Multi-line `if/else` without braces causes "unexpected 'else'" errors.

## CLO Model Workflow

- Capped/floored features always get a `c_` prefix; raw columns keep original names. Examples: `c_MVOC`, `c_OfferSize`, `c_AAAFactor`, `c_PercentPriceLe90`.
- Pooled GAM across ratings (AAA+AA+A): normalize features with non-overlapping distributions by their rating-level mean (`x / rating_mean`) so a single shared smooth works. Freeze the mean constants for prediction.
- R research scripts in `lmunittests/clo_model/research_howard/` save `.rds` model files. Production training is orchestrated by `clo_model/procs/clo_dm_based_model_train.py` (Jenkins daily, `--versions v1 v2`), using `ModelVersionDef` version registry. Output: `S:/QR/Risk/CLOCache/core/dm_based_model_v2/`. EUR senior (A-AAA) model entries exist only in `GAM_MODEL_CONFIG_V3`; production uses `BROAD_PROD_MODEL_CONFIG = GAM_MODEL_CONFIG_V2` — V3 must be promoted (or entries merged into V2) before EUR senior DM-based scoring goes live.
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

## Plotting

- `plot.gam`/`plot.scam` scale parameter: `scale = 0` → common y-axis across panels; `scale = -1` → free y-axis per panel. These are easily inverted — always verify.
- For binned residual/diagnostic plots on skewed features, use `quantile()`-based breaks instead of equal-width `cut()`. Equal-width bins leave most bins empty when data clusters (e.g., AAAFactor near 1.0).
