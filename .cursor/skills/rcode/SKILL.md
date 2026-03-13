---
name: rcode
description: >-
  Project knowledge for RCode: residential mortgage, marketplace lending,
  CLO, ABS, and housing price modeling in R. Use when the workspace is
  RCode, or the user references CRT, Non-QM, Jumbo, HE, MPL, severity,
  GAM transition models, Begg method, CtoP, CtoM3, or LMSim export.
---

# RCode

R-based quantitative credit modeling for structured finance. Covers
prepayment, delinquency transition, loss severity, and scenario analysis
across multiple asset classes. The repo lives at
`C:\Users\hzeng\Desktop\Github\RCode`.

## Update Instructions

The agent may proactively propose updates to this file. All writes require a
diff preview and user approval before saving. Write to the S drive first
(`S:\QR\hzeng\howard-toolbox\.cursor\skills\rcode\SKILL.md`), then copy to
`~/.cursor/skills/rcode/SKILL.md`. Consolidate if this file exceeds ~200 lines.

## Project Structure

```
RCode/
├── Residential/              # RMBS models (largest module)
│   ├── crt/                  #   CRT (STACR/CAS): C→M30→M60→M90+→FCLS→REO
│   ├── non_qm/              #   Non-QM: CtoP (v1.0–1.4), CtoM3, adhoc
│   │   ├── C/CtoP/script/   #     Active: 1.3/Fixed/refactored + 1.4/Fixed
│   │   ├── C/CtoM3/         #     Delinquency transition models
│   │   ├── adhoc/            #     Ad-hoc risk analysis scripts
│   │   └── nqm_llpa.R       #     LLPA GAM (spread-at-origination model)
│   ├── jumbo/                #   Jumbo RMBS prepay (turnover + refi + CRR)
│   ├── he/                   #   Home Equity / HELOC
│   ├── Severity/             #   Loss severity (FC cost, NS proceeds, etc.)
│   ├── settings/             #   Per-asset-class config (resi_, nonqm_, crt_, …)
│   ├── util/                 #   Shared utilities (~8K lines across 3 key files)
│   ├── query/                #   Redshift SQL query definitions
│   ├── redshift_data/        #   Data download scripts → parquet on P:/
│   └── support_data/         #   Column maps, deal lists, variable mappings, LLPA
│
├── MPL/                      # Marketplace Lending
│   ├── hist_sim/             #   Monte Carlo simulation engine
│   │   ├── source/           #     Core sim code
│   │   └── runs/             #     Per-deal run scripts (LC, Prosper, Upstart…)
│   ├── trans_model/          #   Transition rate models (from0–from4, per-platform)
│   ├── lmqr_package/         #   Custom R package (Rcpp C++ backends)
│   ├── mob_x/                #   Mob-X seasoning multipliers (XGBoost/LightGBM)
│   ├── m12/, m18/            #   Month-12/18 default models
│   └── BlueVine/             #   BlueVine analysis + LaTeX reporting
│
├── Housing/                  # HPA scenario generation (Goldman → MSA forecasts)
├── CLO/                      # CLO discount margin (GAM, XGBoost, DT)
├── ABS/                      # Ad-hoc ABS deal analysis
└── NonQM/                    # Legacy standalone Non-QM (released coefficients)
```

## Core Utility Files

| File | Lines | Role |
|------|-------|------|
| `util/lmqr_resi_utils.R` | ~2700 | Model lifecycle: sampling, GAM fit (`bam`), parallel predict, PDF reporting, spline export, LMSim text build |
| `util/model_report_optimized.R` | ~1000 | Parallel fork of reporting with `foreach`/`doSNOW`, intermediate file tracking, enhanced ggplot theme |
| `util/nonqm_utils.R` | ~1900 | Non-QM pipeline: `prep_nonqm_data_v1.0_new()`, burnout backfill (loop + vectorized), LLPA scoring, feature engineering, data cleaning |

## Key Functions

- `fast_fit_model_v2()` — parallel GAM via `bam()`, `quasibinomial(cloglog)` + offset `s` for undersampling correction
- `predict_w_cluster_v2()` — parallel prediction with factor-level mismatch handling
- `model_in_out_sample_report_optimized()` — end-to-end PDF: smooth plots, time-series validation, continuous var diagnostics
- `build_sim_model()` — GAM → LMSim text file (coefficients + spline curves with variable name mapping)
- `prep_nonqm_data_v1.0_new()` — raw Redshift → model-ready: transitions, HPI, PMMS, incentive, burnout, SATO, LLPA
- `fit_nonqm_data_cleaning_v1.0()` — factor creation, clamping, bucket engineering, COVID dummies
- `add_nqm_model_features()` — pre-fit feature clamping and interaction creation (turnover/refi/CtoM3 variants)
- `get_sample_undersampling()` — rare-event undersampling with King-Zeng offset
- `filter_trans()` — Begg binary-outcome filter (target vs CtoC reference)

## Data Flow (Non-QM CtoP)

```
Redshift → redshift_data/non_qm_deal_data.R → P:/NQM/*.parquet
  → nonqm_utils: prep_nonqm_data_v1.0_new() → prep_*.parquet
    → C/dataprep.R: clean + Begg filter → ed_ct0_train.feather
      ├── 1.3 model_run.R: top-level Cto0 + CtoM3 GAMs (Begg normalized)
      ├── 1.4 turnover_model_run.R: inc<=0 universe → turnover GAM
      ├── 1.4 refi_dataprep.R: decontaminate inc>0 prepays → CtoRefi labels
      └── 1.4 refi_model_run.R: refi GAM → reconcile p_turn + p_refi = p_Cto0
    → nqm_llpa.R → support_data/nqm_llpa_gam.rds (feeds _spread_llpa vars)
```

## Modeling Conventions

- **All transition models**: `quasibinomial(link="cloglog")` with `offset(s)` from undersampling
- **Begg method**: binary models (Cto0 vs CtoC, CtoM3 vs CtoC) combined via softmax normalization
- **v1.4 decomposition**: turnover + refi are additive pieces of Cto0, reconciled to Begg total
- **LLPA**: Gaussian GAM predicting SATO; used to construct LLPA-adjusted incentive/burnout variables
- **Parallelism**: `bam()` with PSOCK clusters, 32–48 cores; `foreach`/`doSNOW` for reporting
- **Model export**: R GAM → coefficient CSV + spline CSV → LMSim text file via variable name mapping

## Settings / Source Chain

```
resi_settings.R          # libs, credentials, global constants, sources query/ + util/
  └→ nonqm_settings.R   # NQM-specific maps (servicer, product, doc, index), sources nonqm_utils.R
      └→ C/config.R      # model formulas, Begg config, report slicing configs
          └→ dataprep.R / model_run.R / turnover_model_run.R / refi_*.R
```

## Infrastructure

- **Database**: AWS Redshift via `RPostgres`/`RODBC`; credentials from `.env` via `dotenv`
- **Storage**: raw data on `P:/`, models on `S:\QR\Models\`, deal lists on `N:/LMSimData/`
- **Libraries**: data.table, mgcv, ggplot2, xgboost, lightgbm, arrow, aws.s3, Rcpp, foreach/doSNOW
- **Custom package**: `lmqr` (Rcpp C++ backends for cash flow and vector operations)

## Known Gotchas

- `config.R` exists in two copies: `1.3/Fixed/refactored/config.R` and `C/config.R` (v1.4 additions)
- `ed_ct0_train.feather` is shared by v1.3 model_run and all v1.4 scripts — changes to dataprep affect both
- `mapping_v4` (Intex doc mapping) vs `doc_map` (CoreLogic) — two competing doc-type schemes; `doc_type_compare.R` analyzes the mismatch
- `fit_nonqm_cto0_fixed()` and `fit_nonqm_cto0_floating()` are legacy wrappers; v1.3+ uses `fit_nonqm_data_cleaning_v1.0()` + `add_nqm_model_features()`
- COVID exclusion (Feb–May 2020) is hard-coded in `dataprep.R` via `SKIP_COVID` flag
- Deal-call detection: months where >50% of loans in a deal prepay are flagged and removed
- `.gitignore` excludes `.pdf`, `.xlsx`, `*.txt`, `*.RData` — model artifacts are not version-controlled
- `pd.ExcelFile` leak pattern from howard-toolbox also applies to any `openxlsx` usage here
- `backfill_burnout_loop_nqm()` is extremely slow; always prefer `backfill_burnout_vectorized_nqm()`
