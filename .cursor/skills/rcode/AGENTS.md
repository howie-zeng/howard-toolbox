# AGENTS.md

## Learned User Preferences

- Do not delete user comments in code when editing; preserve all existing comments
- Do not wrap code in tryCatch or other defensive error-handling unless explicitly requested; do not add output-suppression flags (`quiet`, `capture.output`) to hide warnings — keep all diagnostic output visible
- Assume required columns/variables always exist; do not write column-existence checks or fallback logic (e.g., `if ("col" %in% names(dt))`)
- Undersampling belongs in model_run scripts, not dataprep scripts; dataprep should output the full dataset
- Explain reasoning and present a plan before changing code; do not make changes without being asked
- Review plans carefully before implementing — user will ask for double-checks; never add items not in the plan
- Use raw (uncapped) variable names for report continuous vars (e.g., `cur_factor` not `c_cur_factor`, `dscr_ratio` not `c_dscr`) so reports show actual data distributions
- Only add model features that are statistically significant; do not add variables just because they seem relevant
- Store SQL queries in separate files from analysis scripts; put ad-hoc analysis under `Residential/non_qm/adhoc/`
- When presenting model output, pass only one `model_list` at a time to report functions; for insample reports use `ed_fit_full` (all data) with Begg normalization applied, dropping excluded states; default `use_parallel = TRUE` in optimized reporting where supported
- Keep time-series and overlay chart styling on one consistent path; avoid separate overlay-only palette/linetype helper layers unless necessary

## Learned Workspace Facts

- NQM CtoP uses Begg competing-risk (Cto0, CtoM3, CtoC); Fixed is split into turnover (non-positive incentive) and refi (positive incentive) sub-models; ARM CtoP is a single prepayment model (no turnover/refi split); scripts under `C/CtoP/script/1.4/Fixed/` with shared `C/` config/dataprep; CtoC report needs `annulize = FALSE` (monthly ~97-98% annualizes to flat 100%)
- `add_nqm_model_features()` `model_type` must match the model ("turnover", "refi", etc.) — there is no "Cto0" branch
- Non-QM LLPA uses a GAM (not a static FICO x LTV grid); doc groups FULL/BANKSTAT/DSCR/ALT/PL_CPA/OTHER; doc/fix normalization shared via helpers in `nonqm_settings.R` (`normalize_nqm_llpa_doc_map`, `get_nqm_llpa_fix_f`, `assign_nqm_doc_group`) to prevent train/serve drift; LLPA on lag1 rates, SATO and incentive use lag0/lowest-weekly; pure risk-grid predictions exclude time, in-sample keeps time with `orig_date_num` capped to training range; export via `build_sim_model_from_list()` — time smooth as standard (x,y) curve pairs per doc_group (not endpoints), C++ treats time identically to other spline features; LLPA time smooth uses `bs='ad'` (adaptive), which creates numbered basis component names (e.g. `doc_groupFULL1`) that don't match `predict(type="terms")` columns — standard `get_gam_splines_csv()` silently skips them, so the JSON payload builder extracts time curves via `predict(type="terms")` workaround; 2 SD residual trimming for SATO
- Incentive pipeline is spread-based: `inc_0_spread_llpa`, `sato_lag0_spread_llpa`, `burnout_lag0_spread_llpa`; `full_index_spread_fade15` replaced `full_index_inc_fade15`; turnover incentive capping targets `c_inc_0_spread_llpa`; ARM models use `rate_chg` (`c_noterate - o_noterate`) instead of `full_index_spread_fade15` (fade is always 1.0 for post-reset ARM; Fixed models still use `full_index_spread_fade15`)
- Turnover prepayment penalty: `inc_regime_f` includes `pp_active_Y`; `new_m2ppexp_f` bins months-to-PP-expiry for `pp_penalty == 1` (No PP plus ordered buckets through 4+)
- Model extract pipeline: TXT via `build_sim_model()` / `build_sim_model_from_list()`; JSON via `build_sim_model_json()` / `build_sim_model_json_from_list()` with product-specific schema+payload builder (production driver `nonqm_extract_model_json.R` outputs JSON only; `nonqm_model_json_compare.R` is a disposable parity harness); `variable_mapping_{product}_test.csv` maps R names to C++ names — any new factor-level coefficients (e.g. `*_fN`, `*_fY`) need explicit mapping rows or `verify_model_txt()` will fail; when a model uses a smooth without `by=` interaction (e.g. ARM CtoP's plain `s(c_inc_0_spread_llpa)`), the CSV needs plain `_X/Y` rows in addition to any interaction rows; CSV OLD column needs spaces stripped (`check.names=FALSE`); extract sources `C/config.R` for model paths; production C++ scoring uses logit (sigmoid)
- Fixed Balloon loans are ARM (`fix_f = "ARM"`) via NON_QM_FIX_MAP but often margin=0 — treat margin=0 as missing for ARM reset calculations
- DSCR doc_map: loans with `dscr_ratio` should be "DSCR" when doc_map is NA, "NO DATA", or "OTHER"; `dscr_valid_f` and `doc_type_2` can be near-collinear in GAM (bam contrast errors)
- ROUNDING_RULES in `resi_settings.R` must have a matching pattern for any new continuous variable used in reports
- Shared feature engineering (doc_map normalization, factor creation, penalty features, continuous clamps) lives in `fit_nonqm_data_cleaning_v1.0()`; model-type-specific branches stay in `add_nqm_model_features()`; when cleaning and model feature definitions conflict, the `add_nqm_model_features()` version wins; `c_age` is clamped 0–24 in shared cleaning but ARM post-reset loans are all age 60+, so ARM branches must override to `clamp_vec(age, 0, 120)`
- NQM burnout window 60 months (`burnout_inv_b2_60`); `inc_fade_period` 36; seasonality categorical (`month_f`); prefer `months_since_m30p` over `mc_age_ratio`; exclude COVID 2020-02–2020-06 from Fixed insample reports only (ARM models keep all COVID data and have no vintage floor filter); foreign national `lmt.foreign` 0–3, not binary
- Data sources: loan-level `lps.lp_stat`, `lps.lp_dy`, `lps.lp_loss`; NQM rates `Libremax..MonthlyNQMRate`; HPI joins for inflation-adjusted o_bal
