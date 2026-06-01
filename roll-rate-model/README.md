# Roll Rate Model

`roll-rate-model` is a Monte Carlo roll-rate and cashflow simulator for marketplace lending loans. It takes a deal loan tape, transition-model coefficients, payment rules, macro assumptions, and optional dial multipliers, then projects monthly loan status transitions and portfolio cashflows.

The current product setup is for unsecured consumer / MPL-style statuses:

- `C`: current
- `D1M`, `D2M`, `D3M`, `D4M`: delinquency buckets
- `PIF`: paid in full terminal state
- `LIQ`: liquidation / charge-off terminal state

There are two simulator implementations in the folder:

- C++ engine: faster production-style path, built with CMake into `sim_main`.
- Python engine: reference and prep-friendly implementation under `python/`.

The intended high-level flow is:

1. Prepare inputs and optionally dump R GAM models into coefficient text files.
2. Run the C++ or Python simulator.
3. Review portfolio, grouped, probability, and debug outputs.

## Quick Start

Run these commands from `roll-rate-model/`.

### Prepare loans and coefficients

```powershell
python python\data_prep_for_sim.py --config config\default.json --skip-dump
```

This loads the configured transition topology, prints model/payment matrices, prepares raw deal CSV loans into `loans_prepped.json`, writes a TSV companion file, and generates a coefficient model report. Omit `--skip-dump` only when the configured R model paths are available and you want to refresh `input/coef/<version>/from*.txt`.

### Build the C++ engine

```powershell
cmake -S . -B build -DBUILD_TESTS=ON
cmake --build build --config Release
```

The main executable is usually:

```powershell
.\build\Release\sim_main.exe
```

### Run the C++ simulator

```powershell
.\build\Release\sim_main.exe --config config\default.json --dup 1 --workers 8 --scen base
```

Useful overrides:

```powershell
.\build\Release\sim_main.exe --config config\default.json --deal-name upst_2026_2 --coef-version DIALED_v3 --group-by term,grade --n-per 84 --dup 10 --seed 42 --workers 8 --scen base
```

### Run the Python simulator

```powershell
python python\run.py --config config\default.json --mode auto --dup 1 --scen base
```

The Python runner is easier to inspect and compare against. The C++ runner is the faster path for larger runs.

## Directory Map

```text
roll-rate-model/
|-- CMakeLists.txt              # Builds simengine, sim_main, debug_calc, optional tests/bindings
|-- config/
|   |-- default.json            # Main run configuration
|   |-- dump_BASE_v2.json       # Alternate coefficient dump config
|   `-- dump_DIALED_v3.json     # Alternate coefficient dump config
|-- include/                    # C++ public headers
|-- src/                        # C++ simulator implementation
|   |-- main.cpp                # C++ CLI, config parsing, output writing
|   |-- data_mgr.cpp            # Loads coefficients, payment matrix, dials, macro tables
|   |-- cf.cpp                  # One-loan cashflow simulation loop
|   |-- model/
|   |   |-- model_coef.cpp      # Coefficient file parsing and model scoring
|   |   |-- transition.cpp      # Multinomial logit transition sampling
|   |   `-- roll.cpp            # Dial multiplier loading and lookup
|   `-- runners/cf_parallel.cpp # OpenMP batch execution and grouped aggregation
|-- python/
|   |-- data_prep_for_sim.py    # Loan prep + optional R GAM coefficient dump
|   |-- run.py                  # Python simulator CLI
|   `-- simengine/              # Python reference implementation
|-- input/
|   |-- coef/                   # Dumped model coefficient files by version
|   |-- deals/                  # Raw CSV and prepared JSON loan tapes
|   |-- dial/                   # Optional transition dial multiplier files
|   |-- macro/                  # CPI and FICO coupon macro lookup tables
|   `-- pmt_matrix.txt          # Payment-count matrix by from/to status
|-- output/                     # Generated simulation outputs and reports
|-- tools/                      # R/Python helper scripts
`-- build/                      # Generated CMake/MSVC build artifacts
```

`build/` and `output/` are generated working directories. They are useful for local runs, but they are not source-of-truth code.

## What The Simulator Does

For each loan and each monthly projection period, the engine:

1. Reads the current loan status, balance, age, term, rate, and model fields.
2. Evaluates every configured transition model from the current status.
3. Converts transition model logits into probabilities with a multinomial logit / softmax setup.
4. Applies optional dial multipliers, then renormalizes probabilities.
5. Samples the next status using deterministic per-loan/path random seeds.
6. Applies the payment matrix to calculate scheduled payments for that transition.
7. Applies terminal-state cashflow logic for `PIF` and `LIQ`.
8. Records cashflow columns and transition probabilities.
9. Advances time-varying fields like `loan_age`, `age_pct`, `r_dt`, `month`, and macro variables.

This repeats until the projection horizon ends, the balance is near zero, the loan reaches a terminal status, or the loan gets too old.

## Transition Model Logic

Transition topology is configured in `config/default.json` under `status_to_roll`.

For a loan currently in status `from_status`, the configured list tells the engine which statuses it can roll to. Staying in the same status is the residual outcome. Every non-stay outcome looks for a model named:

```text
from{FROM}_{TO}
```

Examples:

- `fromC_D1M`
- `fromC_PIF`
- `fromD1M_C`
- `fromD4M_LIQ`

Coefficient files live under `input/coef/<coef_version>/` and are named by from-status:

```text
input/coef/DIALED_v3/fromC.txt
input/coef/DIALED_v3/fromD1M.txt
input/coef/DIALED_v3/fromD2M.txt
input/coef/DIALED_v3/fromD3M.txt
input/coef/DIALED_v3/fromD4M.txt
```

Each coefficient file is tab-delimited with columns like:

```text
model    var_name1    var_val1    var_name2    var_val2    value
```

The engine auto-detects coefficient term types:

- categorical lookup terms
- 1D smooths
- smooth-by-factor interactions
- smooth-by-numeric interactions
- 2D lookup-style terms

Static terms are cached once per loan. Dynamic terms are recalculated each period.

## Data Preparation

`python/data_prep_for_sim.py` is the main preparation entry point. It does three jobs:

1. Initializes the configured status topology, coefficient folder, payment matrix, dials, and macro settings.
2. Optionally calls `tools/dump_gam_to_coef.R` to convert R GAM `.RData` models into `from*.txt` coefficient files.
3. Converts raw deal CSV loans into simulation-ready JSON.

Loan prep applies:

- DV01-style field renames, for example `dv01_id` to `loan_id`.
- Status value mapping, for example `30 - 59 Days Delinquent` to `D1M`.
- Categorical value normalization for home ownership, employment, and purpose.
- Derived model fields like `int_rate`, `age_pct`, `oterm_f`, `vint_qtr`, and `term_fico`.
- Macro lookup fields such as CPI inflation and FICO-bucket coupon incentives.
- `v_*` flags for missing smooth variables.

`platform_type_f` is no longer derived in the Python registry; current coefficient sets should rely on fields present in the input tape or on the remaining derived fields above.

Prepared loans are written to:

```text
input/deals/<deal_name>/loans_prepped.json
input/deals/<deal_name>/loans_prepped.txt
```

The C++ runner reads the prepared JSON file by default.

## Main Configuration

`config/default.json` controls the current run. The important fields are:

- `deal_name`: selects `input/deals/<deal_name>/`.
- `input_dir`: usually `input`.
- `scenario`: output scenario folder name.
- `coef_version`: selects `input/coef/<coef_version>/`.
- `macro`: declares macro variables and whether they use default or custom lookup tables.
- `group_by`: fields used for grouped output, currently `term` and `grade`.
- `status_to_roll`: allowed transitions for each starting status.
- `terminal_statuses`: statuses that stop projection in the Python path; the C++ path currently stops on hardcoded `PIF` and `LIQ`.
- `dq_buckets`: delinquency status to cashflow column mapping in the Python path; the C++ path currently maps DQ buckets in `src/utils.cpp`.
- `pmt_matrix_path`: documented in config, but current loaders read `input/pmt_matrix.txt` from `input_dir`.
- `liq_severity`: loss severity applied on `LIQ`.
- `n_per`: monthly projection horizon.
- `save_tsv`: prep-only flag for writing a TSV loan tape.
- `model_base`, `r_script`, `rscript_exe`, `gam_models`: prep-only R GAM dump configuration.

The C++ CLI can override common fields such as deal name, coefficient version, grouping, scenario, horizon, duplicate paths, seed, workers, and dial name.

## Inputs

### Loan tape

Raw loan CSVs live under:

```text
input/deals/<deal_name>/
```

Prepared JSON is expected at:

```text
input/deals/<deal_name>/loans_prepped.json
```

Required simulation fields after prep are:

- `loan_id`
- `end_bal`
- `int_rate`
- `term`
- `loan_age`
- `status`
- `r_dt`

Other fields are required if the loaded coefficient models reference them.

### Payment matrix

`input/pmt_matrix.txt` is a tab-delimited matrix. Rows are from-statuses, columns are to-statuses, and each value is the number of scheduled monthly payments to apply when rolling from row status to column status.

For example, the current matrix says a current loan that stays current gets one payment, while a current loan that pays off uses special payoff logic:

```text
        C   D1M D2M D3M D4M PIF LIQ
C       1   0   0   0   0   -1  0
D1M     2   1   0   0   0   -1  0
```

`PIF` and `LIQ` are handled specially in the cashflow loop, so their terminal cashflows do not depend only on this matrix.

### Dials

Dial files live under `input/dial/`. They are optional transition probability multipliers. A dial file can be unsegmented or segmented by fields such as `term` and `grade`.

Example header:

```text
Status    term    grade    C    D1M    D2M    D3M    D4M    PIF    LIQ
```

When `--dial-name upst_ctd1` is passed, the engine loads matching files from `input/dial/`, applies the multiplier for each from/to/period/segment, and renormalizes the transition probabilities.

### Macro inputs

Macro files live under `input/macro/`.

- `CPIAUCNS.csv`: source CPI index data.
- `cpi_table.csv`: calendar-indexed CPI inflation variables used by the simulator.
- `FICO_BKT_COUPON.csv`: FICO bucket coupon benchmark used for rate incentive variables.
- `FICO_BKT_COUPON_BY_PLATFORM.csv`: reference output by platform, not directly consumed by the simulator.

Useful scripts:

```powershell
python input\macro\update_macro.py
python tools\generate_macro_table.py
```

## Outputs

The C++ runner defaults to:

```text
output/<deal_name>/<scenario>/
```

It writes intermediate CSVs and then consolidates them into:

```text
output/<deal_name>/<scenario>/sim_results.xlsx
```

The workbook contains:

- `Portfolio`: raw projected portfolio cashflow columns by projection period.
- `Metrics_Portfolio`: portfolio CPR, CDR, CGL, balances, PIF, LIQ, loss, and cumulative loss.
- `Metrics_Grouped`: grouped metrics by loan age, with transition probability columns.
- `Metrics_Grouped_Period`: grouped metrics by projection period, with transition probability columns.

If dump mode is enabled, it also writes:

```text
output/<deal_name>/<scenario>/dump/dump.csv
```

The dump file records loan-path snapshots around transition evaluation and is useful for debugging probability calculations, feature evolution, and cashflow outcomes.

### Deal HTML reports

After a run produces `sim_results.xlsx`, generate a compact HTML report with:

```powershell
python python\generate_deal_report.py --deal par_2026_1 --scenario base
```

The report reads:

```text
output/<deal_name>/<scenario>/sim_results.xlsx
```

and writes an HTML summary under `python/deal_report/`. Use this for quick review of portfolio and grouped simulation results without opening the workbook manually.

## C++ Engine

The C++ source is organized around these modules:

- `src/main.cpp`: CLI, config parser, output metrics, CSV/XLSX consolidation.
- `src/data_mgr.cpp`: loads status topology, coefficient files, payment matrix, dials, macro tables, and variable registry.
- `src/model/model_coef.cpp`: reads coefficient files and scores model logits.
- `src/model/transition.cpp`: converts logits to transition probabilities and samples the next status.
- `src/model/roll.cpp`: loads and applies dial multipliers.
- `src/cf.cpp`: simulates one loan path and produces cashflow rows.
- `src/runners/cf_parallel.cpp`: runs all loans and duplicate paths, aggregates portfolio and grouped outputs, and uses OpenMP when available.
- `src/var_registry.cpp`: updates time-varying and macro variables each period.
- `src/dump.cpp`: writes detailed debug dumps.
- `src/io/*.cpp`: readers for JSON, TSV coefficients, payment matrix, and macro lookup files.

`CMakeLists.txt` builds:

- `simengine`: core C++ library.
- `sim_main`: main simulator executable.
- `debug_calc`: small diagnostic executable.
- `tests`: optional GoogleTest target if `tests/*.cpp` exists.
- `_simengine`: optional pybind11 module when `BUILD_PYTHON=ON` and pybind11 is available.

## Python Engine

The Python engine mirrors much of the C++ logic and is useful for inspection, data prep, and debugging:

- `python/simengine/data_prep.py`: config loading, loan prep, coefficient parsing, model scoring, dials, macro lookups.
- `python/simengine/runner.py`: Python simulation loop, grouping, metrics, XLSX output.
- `python/simengine/dump.py`: Python debug dump helpers.
- `python/simengine/model_report.py`: interactive HTML coefficient report.
- `python/simengine/register_vars.py`: Python variable registry for time-varying fields.
- `python/generate_deal_report.py`: HTML report CLI for `sim_results.xlsx`.

Run it with:

```powershell
python python\run.py --config config\default.json --mode auto
```

`--mode auto` selects sequential, multiprocessing pool, or Ray based on task count. Use `--mode sequential` for the easiest debugging path.

## Debugging

### C++ dump mode

```powershell
.\build\Release\sim_main.exe --config config\default.json --dump 10 10 --scen debug
```

This dumps the first 10 loans and first 10 paths per loan.

### Python dump mode

```powershell
python python\run.py --config config\default.json --dump --mode sequential --scen debug
```

### Crash isolation helper

`tools/find_crash_loan.py` binary-searches `input/deals/upst_2026_2/loans_prepped.json` to find a crashing loan for the C++ executable. It temporarily rewrites that JSON file and restores it in a `finally` block, so use it only when you understand that side effect.

## Tests And Validation

CMake is configured to build GoogleTest tests from `tests/*.cpp`, but this checkout currently does not contain a checked-in `tests/` folder. Some generated build artifacts show prior test executables, but those are not source files.

Useful validation commands:

```powershell
.\build\Release\sim_main.exe --help
python python\run.py --help
python python\data_prep_for_sim.py --help
```

For a substantive engine change, validate at least:

1. Data prep on a known deal.
2. C++ run with `--dup 1` and a short `--n-per`.
3. Python run in `--mode sequential` for comparison when feasible.
4. Review `sim_results.xlsx` and optional `dump.csv` for expected transitions and cashflows.

## Common Changes

### Switch to another deal

```powershell
.\build\Release\sim_main.exe --config config\default.json --deal-name par_2026_1 --scen base
```

Make sure `input/deals/<deal_name>/loans_prepped.json` exists. If not, run data prep first.

### Switch coefficient version

```powershell
.\build\Release\sim_main.exe --config config\default.json --coef-version BASE_v2 --scen base
```

The engine will read coefficients from `input/coef/BASE_v2/`.

### Add or change transition statuses

Update these together:

- `status_to_roll` in config.
- `terminal_statuses` in config if the new state stops projection in the Python path.
- `dq_buckets` in config if the new state is a delinquency bucket in the Python path.
- `src/utils.cpp` if the C++ path needs new terminal-status or DQ-bucket behavior.
- `input/pmt_matrix.txt` rows and columns.
- R GAM dump config and coefficient files for any modeled transition.
- C++/Python cashflow logic if the new state needs a new cashflow treatment.

### Refresh macro inputs

```powershell
python input\macro\update_macro.py
python tools\generate_macro_table.py
```

The first command refreshes source macro files; the second regenerates the calendar CPI table used during simulation.

## Caveats

- The C++ config parser in `src/main.cpp` is intentionally minimal. It extracts only the fields the C++ runner needs and skips unknown JSON values.
- `tools/dump_gam_to_coef.R` and the macro export R scripts depend on local RCode paths under `S:/QR/jli/GitHub/RCode/...`; they will only work where those paths and R packages are available.
- `build/` contains generated MSVC/CMake files and should not be used to understand source behavior except for confirming built target names.
- `output/` contains generated historical simulation outputs and reports. They document prior runs but are not required to run the engine.
- The C++ runner writes intermediate CSV files and then calls `python tools/csvs_to_xlsx.py` to consolidate them. That helper removes the individual CSVs after creating the workbook.
- The Python and C++ implementations are similar but not a packaging boundary. Treat the Python path as a reference/prep/debug implementation and the C++ path as the main performance engine.
