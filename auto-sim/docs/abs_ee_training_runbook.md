# Auto (ABS-EE roll-rate + severity) — Runbook

This runbook covers the upstream model-training pipeline in `S:\QR\jli\Auto`.
The vendored `auto-sim/` project consumes its transition and severity model
outputs; training data and fitted-model artifacts remain outside this repository.

Loan-level auto-ABS models off the SEC ABS-EE tape (Reg AB II Schedule AL), per
shelf (Prime / Subprime, always fit separately):

- **Transition models** — monthly Markov hazards between loan states (current,
  30/60/90/120+ dpd, prepaid, charged-off). Binomial GAMs (`mgcv::bam`) on a
  loan-month panel.
- **Severity model** — recovery rate given a charge-off. Quasibinomial GAM,
  dollar-weighted, one row per terminal charge-off.

Code: **`S:\QR\jli\Auto`** (see its `README.md` and `handoff.md`). The pipeline
is a chain — each step's output feeds the next:

```text
Jenkins scrape → Trino → dump (N: CSVs) → panel (per-deal parquet) → merge (shelf cache)
                                        → prep (training sets) → fit (R GAM) → PDF/HTML reports
```

## Paths

| What | Where |
|---|---|
| Code / repo | `S:\QR\jli\Auto` |
| Raw tapes (dump output) | `N:\FlatFilesMonthly\Auto\<Issuer>\<Shelf>\<deal>\<deal>_<asof>.csv` |
| Per-deal panels | `R:\Consumer\jli\Auto\_panel\<Shelf>\<Issuer>_<deal>_panel.parquet` |
| Merged shelf cache | `R:\Consumer\jli\Auto\_panel\<Shelf>\_prepped\state=N\` |
| Training sets | `R:\Consumer\jli\Auto\_train\<Shelf>\from<N>\<target>_train.parquet` |
| Severity dataset | `R:\Consumer\jli\Auto\_severity\<Shelf>\severity_data.parquet` |
| Fitted models / PDFs / HTML | `S:\QR\jli\Auto\trans_model\<Shelf>\<fromN or severity>\{models, rpt, export, html}` |
| Python | `C:\QR\miniconda\envs\pyprod\python.exe` |
| R | `C:\Program Files\R\R-4.3.2\bin\Rscript.exe` (shortcut from repo root: `.\r.ps1 <script>`) |

All commands below assume:

```powershell
cd S:\QR\jli\Auto
$py = "C:\QR\miniconda\envs\pyprod\python.exe"
```

### Where the training data lives

Training data is on the **R: drive, not in the repo** — the repo only holds the
code that reads it.

- **Transition models**:
  `R:\Consumer\jli\Auto\_train\<shelf>\from<N>\<target>_train.parquet`
  (for example, `...\_train\Subprime\from0\ctd1_train.parquet`) — the path is
  built by `model\models.R::model_spec()$paths`.
- **Severity**:
  `R:\Consumer\jli\Auto\_severity\<shelf>\severity_data.parquet`.
- Defaults come from generated `model\config_shared.R` (`TRAIN_DIR_DEFAULT`,
  `SEV_DIR_DEFAULT`), while Python prep writes to the fixed roots in
  `config.py`. `AUTO_TRAIN_DIR` and `AUTO_SEV_DIR` are R-side overrides for
  direct `model\train.R` report/refit runs against existing data; do not use
  them to redirect a `run.py` prep because Python will still write to its
  configured roots. `run.py` also sets `AUTO_SEV_DIR` to the configured shelf
  directory before fitting severity.
- With `run.py`, select a version through `--model-version <v>`. It sets
  `AUTO_MODEL_VERSION` for R and passes the same version to Python prep.
  **Transition** training parquets are version-tagged
  (`<target>_<v>_train.parquet` — versions can differ in sampling); the
  **severity** parquet is shared across versions. Setting only the environment
  variable does not version Python prep and can make R read a stale tagged
  parquet.

## Pipeline steps, in order

### 0. EDGAR → Trino (Jenkins, Padraic's job)

[`quant-creditflow-loan-history`](http://jenkins.libremax.com/job/quant-creditflow-loan-history/)
scrapes CreditFlow/EDGAR ABS-EE filings into the Trino table
`loan_history.loans.creditflow_abs`. Run it with a deal pattern — `crvna 2022`
(all CRVNA 2022 deals) or `CarMax Select Receivables Trust` (a whole shelf).
Run this first whenever a deal or shelf is not in Trino yet, or when new monthly
filings are due.

### 1. Acquire: Trino → N: CSVs

Run this on the QR box only; Trino is not reachable from remote machines.

```powershell
$env:AUTO_ISSUER = "CarMax"
& $py -u data-dump\dump_creditflow.py
```

This writes one CSV per `(deal, report-month)`; the latest filing wins. The
operation is **idempotent**: rerunning only patches missing or changed dates, so
the monthly refresh is simply another run.

Run one issuer at a time (`Carvana`, `CarMax`, `Toyota`, `Hyundai`, `Exeter`,
`Santander Drive`, `Drive`, and so on). No shelf argument processes every shelf
configured for the issuer (CarMax includes CAOT Prime and CMXS Subprime); pass
one shelf (`Prime`, `Subprime`, and so on) to narrow the run.

### 2. Panel: CSVs → per-deal loan-month parquets

This stage derives monthly loan state from balance, DPD, and charge-off amount;
derives `state` → `next_state`; and writes one panel parquet per deal plus
per-loan recovery summaries used by severity.

It runs first inside `run.py` unless `--skip-panel` is set. It wipes and rebuilds
every deal for the selected issuer and shelf. To add one issuer without
rebuilding the others, invoke it directly:

```powershell
& $py -c "from lib.prep_data import panel; panel.build_parallel('CarMax','Subprime', raw_shelf='Subprime')"
```

### 3. Merge ("Data Concat & Dedup"): per-deal panels → shelf cache

This stage:

- concatenates all deals;
- deduplicates loans appearing in multiple deals because of resecuritization;
- drops sponsor repurchases misreported as prepays;
- computes momentum features such as `dq6_bkt`; and
- writes a state-partitioned cache.

It runs automatically inside `run.py` when the cache is older than any panel.
Use `--consolidate` to force it. Subprime usually takes about 20–30 minutes.

### 4. Prep: cache → per-target training sets

For each from-state, prep reads that state's slice, filters the COVID window,
excluded platforms, and known bad report-months, balances platforms, builds
features (FICO, PTI, `rel_rate`, `rate_incentive`, `real_manheim`, age, and
others), applies King-Zeng undersampling for from0 only, and writes one parquet
per transition target. Use `--skip-prep` to skip this stage.

### 5. Fit + report: training set → GAM → PDF

`run.py` invokes `Rscript model\train.R` for each target. Formulas live in
`model\formulas.R` and are shelf-specific. Outputs are:

- fitted bundle:
  `trans_model\<Shelf>\from<N>\models\<target>_bam.rds`;
- PDF report:
  `trans_model\<Shelf>\from<N>\rpt\<target>_report.pdf`.

## Running the pipeline

### Full shelf: panels → merge → prep → all fits → severity

```powershell
& $py -u run.py --shelf Subprime --kinds both --target all --from-state all --cores 40 --target-p 0.40
& $py -u run.py --shelf Prime    --kinds both --target all --from-state all --cores 40
```

`--target-p 0.40` is the Subprime convention (smaller King-Zeng frame). Prime
uses the default `0.20`.

### One specific transition

Every transition belongs to a **from-state**. Pass both the target and its
from-state; `--from-state` defaults to `0`.

| from-state | Targets (`config.py::TRANSITIONS`) |
|---|---|
| 0 (current) | `ctd1` (→30dpd), `ctp` (→prepaid), `ctco` (→charge-off) |
| 1 (30dpd) | `d1tc` (cure), `d1td2` (roll), `d1tp` (prepay) |
| 2 (60dpd) | `d2tc`, `d2td1`, `d2td3`, `d2tco` |
| 3 (90dpd) | `d3tc`, `d3td2`, `d3tco`, `d3td4` |
| 4 (120+dpd) | `d4tc`, `d4td3`, `d4tco` |

```powershell
# Refit only: formula or bounds changed, data unchanged (fastest).
& $py -u run.py --shelf Subprime --kinds transition --target ctp --skip-panel --skip-prep --cores 40

# Re-prep and refit one target after data or feature changes.
# Prep touches only this target's parquet.
& $py -u run.py --shelf Subprime --kinds transition --target ctp   --skip-panel --cores 40 --target-p 0.40
& $py -u run.py --shelf Subprime --kinds transition --target d2tco --skip-panel --cores 40 --from-state 2

# All targets from one state.
& $py -u run.py --shelf Subprime --kinds transition --target all --from-state 1 --skip-panel --cores 40
```

States 1–4 do not use King-Zeng, so `--target-p` is irrelevant there. The
`hist` model version (`ctd1` with `dq6` momentum and stratified King-Zeng) uses
the same command plus `--model-version hist`. It writes its own tagged training
parquet; do not add `--skip-prep` on the first run.

### Severity

There is one dollar-weighted GAM per shelf: recovery rate conditional on
recovering. The cohort contains charge-offs resolved at least 12 months ago,
weights are gross-loss dollars, and platforms are rebalanced according to
`SEV_BALANCE_PLATFORMS`. Prep rebuilds the dataset and lag distribution from
per-deal recovery summaries.

Severity prep also reads the shelf's
`R:\Consumer\jli\Auto\_lookups\<Shelf>\FICO_BKT_COUPON.csv`, which is persisted
by transition prep and is required for `rel_rate`. Run at least one transition
prep for the shelf before the first severity-only prep. A full `--kinds both`
run already does this in the correct order.

```powershell
# Prep + fit + PDF for severity only. The default target is ctd1, so select
# severity explicitly; --target all also fits severity when --kinds includes it.
& $py -u run.py --shelf Subprime --kinds severity --target severity --skip-panel --cores 40

# Refit only when the dataset is already current.
& $py -u run.py --shelf Subprime --kinds severity --target severity --skip-panel --skip-prep --cores 40
```

Outputs:

- `trans_model\<Shelf>\severity\models\severity_bam.rds`;
- `trans_model\<Shelf>\severity\rpt\severity_report.pdf`;
- `R:\Consumer\jli\Auto\_severity\<Shelf>\severity_data.parquet`.

### HTML reports

```powershell
# 1. Refresh the export seam for one target (report only, no refit; about five minutes).
# Clear a version inherited from an earlier direct-R run when exporting base.
Remove-Item Env:AUTO_MODEL_VERSION -ErrorAction SilentlyContinue
$env:AUTO_SHELF = "Subprime"
$env:AUTO_FROM_STATE = "from0"
$env:AUTO_TRANS_NAME = "ctd1"
$env:AUTO_MODE = "report"
$env:AUTO_EXPORT_BUNDLE = "1"
.\r.ps1 model\train.R

# Repeat the report-only run for every version that should be current:
# $env:AUTO_MODEL_VERSION = "hist"
# .\r.ps1 model\train.R
#
# Severity report-only runs also require:
# $env:AUTO_SEV_DIR = "R:\Consumer\jli\Auto\_severity\Subprime"

# 2. Build the pages.
& $py tools\html_report.py   Subprime ctd1 from0
& $py tools\html_explorer.py Subprime ctd1 from0

# Direct-R controls persist in PowerShell. Clear them before any later run.py fit.
Remove-Item Env:AUTO_MODE -ErrorAction SilentlyContinue
Remove-Item Env:AUTO_EXPORT_BUNDLE -ErrorAction SilentlyContinue
Remove-Item Env:AUTO_MODEL_VERSION -ErrorAction SilentlyContinue
```

Outputs:

- `trans_model\<Shelf>\from<N>\html\ctd1_deals.html` — per-deal actual versus
  model;
- `trans_model\<Shelf>\from<N>\html\ctd1_explorer.html` — vintage and deal
  panels.

Both HTML generators auto-discover existing version exports. If old
`hist`/`stacked` exports remain on disk, their stale lines will still appear;
refresh each desired version or remove a deliberately retired export before
building the page.

### Preflight before any refit

```powershell
.\r.ps1 tools\preflight.R
```

Preflight resolves every formula in the registry and smoke-fits each model on
synthetic data (about two minutes). It catches formula typos and
basis-construction failures such as `bs="ps"` with `k < 4` before a long fit.

## Flag reference (`run.py`)

| Flag | Meaning |
|---|---|
| `--shelf` | `Prime` or `Subprime`; one shelf per invocation |
| `--kinds` | `transition`, `severity`, or `both`; selects prep and fit pipelines |
| `--target` | One target, `severity`, or `all` (all transitions for `--from-state`, plus severity when included in `--kinds`) |
| `--from-state` | `0`–`4` or `all`; defaults to `0`, so deeper targets require an explicit value |
| `--skip-panel` | Do not rebuild per-deal panels (the usual case) |
| `--skip-prep` | Do not rebuild training sets; use for formula-only refits |
| `--consolidate` | Force the shelf-cache rebuild; it also runs automatically when stale |
| `--cores` | `bam` fit threads; use `40` on the big box |
| `--target-p` | King-Zeng event share; Subprime uses `0.40`, Prime defaults to `0.20` |
| `--model-version` | Structural variant tag such as `hist`; uses its own transition parquet, model, and report |

## Gotchas

- `--target all` covers the selected `--from-state` (or every state with
  `--from-state all`) and also fits severity whenever `--kinds` includes
  severity. For a severity-only run, use `--kinds severity --target severity`.
- Trino is reachable only from the QR box; all later stages can run elsewhere.
- To add an issuer or shelf, update `config.py::ISSUERS` (including `alt_deals`
  for a second trust prefix such as CarMax's CMXS) and `SHELF_MEMBERS`; then run
  Jenkins scrape → dump → direct panel build → full shelf run.
- `model\config_shared.R` is generated from `config.py`; never edit it.
- Population policy (exclusions, balancing, COVID window, King-Zeng) lives in
  `config.py`; formulas live in `model\formulas.R`; report layout lives in
  `model\config.R`.
- `run.py` currently invokes each R fit with `check=False` and prints
  `[ALL DONE]` even if an R subprocess failed. Read every `[fit]` block for R
  errors and confirm the expected model/report file timestamps before treating
  a run as successful.
- Direct-R variables persist in the PowerShell session. In particular, leaving
  `AUTO_MODE=report` set causes later `run.py` fits in that session to run in
  report-only mode. Clear the report/version variables after HTML export as
  shown above.
- Read `S:\QR\jli\Auto\handoff.md` for current state, history, exclusions, stale
  model/report warnings, and outstanding work before running a fit.
