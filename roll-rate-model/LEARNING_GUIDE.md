# Learning the roll-rate model

This guide is for a quantitative researcher who understands credit models but is new to this codebase. It explains the business problem, the model mechanics, the directory layout, and the shortest path to a working run.

Use this guide first. [README.md](README.md) contains broader technical reference material, but its default examples assume a real deal tape. Prefer the commands in this guide for the first run.

## The 30-second mental model

This project answers one question:

> Given a loan's state and characteristics this month, what state will it enter next month, and what cashflow does that transition produce?

The model repeats that question every month for every simulated loan path.

```text
loan tape
   |
   v
prepare and derive model fields
   |
   v
score all allowed exits from the current state
   |
   v
softmax probabilities -> optional dials -> random next state
   |
   v
interest, principal, payoff, delinquency, recovery, loss
   |
   v
advance one month and repeat
   |
   v
portfolio and cohort results -> XLSX -> HTML report
```

The project has a reusable transition-scoring engine, but the surrounding loan and cashflow logic is specific to marketplace lending. It is best described as an MPL roll-rate and cashflow simulator, not a product-neutral modeling framework.

It does not train the transition models. R trains the GAMs elsewhere. This repository loads exported coefficients and executes them.

## MPL in this project

MPL means marketplace lending. These are usually unsecured consumer installment loans originated through platforms such as Upstart, Upgrade, Prosper, or Marlette.

The loans tend to have:

- fixed interest rates;
- scheduled monthly amortization;
- relatively short original terms, commonly 36 or 60 months;
- no property collateral;
- meaningful prepayment and credit-loss risk;
- platform, vintage, FICO, purpose, employment, and macro effects.

That product definition explains why the repository contains consumer-loan fields and why `PIF` and `LIQ` have hardcoded cashflow meanings.

## Loan states

The default state set is:

- `C`: current;
- `D1M`: one month delinquent;
- `D2M`: two months delinquent;
- `D3M`: three months delinquent;
- `D4M`: four or more months delinquent;
- `PIF`: paid in full, a terminal state;
- `LIQ`: liquidation or charge-off, a terminal state.

`config/default.json` defines the allowed destinations from each nonterminal state. For example, a current loan may stay current, become delinquent, pay off, or liquidate. Only destinations with loaded models can receive nonzero modeled probability. Stay is handled separately as the multinomial baseline.

## What one simulated month does

For one loan and one path, `python/simengine/runner.py::run_cf_one()` performs the following work:

1. Read the beginning state, balance, rate, term, age, date, and model fields.
2. Update active monthly fields such as CPI inflators and rate incentive.
3. Find the allowed destinations from `status_to_roll`.
4. Evaluate every available non-stay transition model.
5. Convert model logits into multinomial probabilities.
6. Apply any configured dial multipliers and renormalize.
7. Draw one uniform random number and select the next state.
8. Apply the payment matrix and terminal-state cashflow rules.
9. Record cashflows and transition probabilities.
10. Advance the date, age, balance, and state.

The loop stops when the projection horizon ends, the balance reaches zero, the loan enters a terminal state, or the loan age exceeds the safety limit.

## Transition probability mechanics

Suppose the current state is `C`. The configured destinations include stay, `D1M`, and `PIF`, among others.

For every modeled non-stay destination `j`, the engine calculates:

```text
eta_j = intercept_j + sum(term contributions)
weight_j = exp(eta_j)
```

Stay has no fitted model:

```text
weight_stay = 1
```

The probabilities are:

```text
p_j = weight_j / sum(all weights)
p_stay = 1 / sum(all weights)
```

An allowed destination with no loaded model receives zero weight. The engine does not raise an error for that case.

The main implementations are:

- Python: `python/simengine/runner.py::_softmax_transition()`
- C++: `src/model/transition.cpp`

### Dials

A dial changes a probability after model scoring:

```text
adjusted_weight_j = p_j * dial_j
adjusted_probability_j = adjusted_weight_j / sum(adjusted weights)
```

A missing dial cell means `1.0`. Dials may vary by projection period and by cohort fields such as term and grade.

Do not start with dials. First understand the undialed transition probabilities.

## How coefficient files work

Coefficient files live under:

```text
input/coef/<coefficient_version>/
```

The default version is `STACKED_v4`:

```text
input/coef/STACKED_v4/fromC.txt
input/coef/STACKED_v4/fromD1M.txt
input/coef/STACKED_v4/fromD2M.txt
input/coef/STACKED_v4/fromD3M.txt
input/coef/STACKED_v4/fromD4M.txt
```

The filename identifies the origin state. The `model` column identifies the destination state.

For example, a row with `model=D1M` in `fromC.txt` contributes to the `C -> D1M` model. A row with `model=PIF` in the same file contributes to `C -> PIF`.

The header is:

```text
model  var_name1  var_val1  var_name2  var_val2  value
```

Common row types are:

- `intercept`: the model intercept;
- one categorical variable and level, such as `platform_f = Upstart`;
- a numeric grid, which the engine treats as a clamped, linearly interpolated smooth;
- a smooth by factor;
- a smooth multiplied by a numeric field, often a `v_*` missingness flag;
- a two-variable categorical interaction.

Reference categorical levels do not need explicit rows. Their contribution is zero.

Start by opening the first 40 lines of `fromC.txt`:

```powershell
Get-Content input\coef\STACKED_v4\fromC.txt -TotalCount 40
```

You should see:

- categorical coefficients for employment, homeownership, month, platform, and purpose;
- an intercept for `D1M`;
- numeric grid rows for smooth terms.

The parsers and scorers live in:

- Python: `python/simengine/data_prep.py`
- C++: `src/model/model_coef.cpp`

## Cashflow mechanics

### Scheduled payment

The engine calculates a level payment using the current balance, note rate, and loan term.

For monthly rate `r`, balance `B`, and term `n`:

```text
payment = B * r * (1 + r)^n / ((1 + r)^n - 1)
```

The zero-rate fallback is `B / n`.

The code treats rates below `1.0` as decimal rates. A value of `0.15` means 15 percent. Larger values are interpreted as percentages and divided by 1200 for the monthly rate.

### Payment matrix

`input/pmt_matrix.txt` tells the simulator how many scheduled payments to collect for each state transition.

Examples:

- `C -> C` collects one scheduled payment.
- `D1M -> C` collects two payments because the loan cures one missed payment and makes the current payment.
- `D2M -> C` collects three payments.
- A transition deeper into delinquency may collect zero payments.
- `PIF` uses `-1` as a marker, but payoff cashflow is handled explicitly rather than by the normal payment loop.

### PIF

When the sampled state is `PIF`:

- principal equals the full beginning balance;
- interest equals one month of interest on the beginning balance;
- ending balance becomes zero;
- `pif_cnt` and `pif_bal` are populated.

### LIQ

When the sampled state is `LIQ`:

```text
loss = beginning balance * liquidation severity
recovery = beginning balance - loss
```

Principal and interest are zero and the ending balance becomes zero.

The current default has `liq_severity = 1`, so a liquidation produces a 100 percent principal loss and no recovery.

The implementations are:

- Python: `python/simengine/runner.py::run_cf_one()`
- C++: `src/cf.cpp`

## Portfolio metrics

The simulator derives three familiar annualized or cumulative metrics.

Prepayment:

```text
SMM = pif_bal / (begin_bal - scheduled_principal)
CPR = 1 - (1 - SMM)^12
```

Default:

```text
monthly_default_rate = liq_bal / begin_bal
CDR = 1 - (1 - monthly_default_rate)^12
```

Loss:

```text
CGL = cumulative_loss / original_balance
```

Transition probabilities in grouped output are beginning-balance weighted.

## Directory map

```text
roll-rate-model/
|-- CMakeLists.txt             C++ build definition
|-- config/                    run and R-export configuration
|-- input/
|   |-- coef/                 exported GAM terms
|   |-- deals/                raw and prepared loan tapes
|   |-- dial/                 optional probability multipliers
|   |-- macro/                CPI and FICO coupon inputs
|   `-- pmt_matrix.txt        state-transition payment counts
|-- python/
|   |-- data_prep_for_sim.py  raw tape preparation CLI
|   |-- run.py                Python simulation CLI
|   |-- generate_deal_report.py
|   |-- simengine/            Python model and simulator
|   `-- deal_report/          HTML report builder
|-- include/                  C++ interfaces
|-- src/                      C++ implementation
|-- tools/                    export, dial, conversion, and debug utilities
|-- output/                   generated simulation results
|-- README.md                 technical reference
`-- LEARNING_GUIDE.md         this guide
```

### Configuration

`config/default.json` controls:

- the default deal and scenario;
- coefficient version;
- macro inputs;
- state topology;
- terminal states and delinquency buckets for Python;
- grouping fields;
- loss severity;
- projection horizon;
- external R GAM paths used only when exporting coefficients.

The current loaders ignore the configured `pmt_matrix_path`. They read `input/pmt_matrix.txt` under `input_dir`.

`config/dump_BASE_v2.json` and `config/dump_DIALED_v3.json` are coefficient-export configurations. They are not drop-in replacements for the normal runtime configuration.

### Input data

`input/deals/<deal>/` holds:

```text
<deal>.csv
loans_prepped.json
loans_prepped.txt
```

The raw CSV is a human-readable input tape. Data preparation creates the JSON consumed by C++ and Python. The TSV is useful for inspection.

Deal tapes are deliberately gitignored. A fresh checkout therefore has no runnable loan tape even when coefficients are present.

### Macro data

The default model uses:

- `CPIAUCNS.csv` for 12- and 36-month CPI inflation;
- `FICO_BKT_COUPON.csv` for rate incentive by month and FICO bucket.

Preparation derives the starting macro fields. During simulation, the engines update available monthly values and freeze the previous value after source data ends.

`FICO_BKT_COUPON_BY_PLATFORM.csv` is a reference output. The simulator does not consume it.

`cpi_table.csv` supports an older generic calendar-table workflow. The default configuration uses raw CPI instead.

### Python engine

`python/data_prep_for_sim.py`

- loads configuration;
- checks coefficient and transition coverage;
- optionally invokes the external R export;
- prepares the raw loan tape;
- writes JSON and TSV;
- generates a coefficient-model HTML report.

`python/run.py`

- loads prepared loans;
- chooses sequential, multiprocessing, or Ray execution;
- runs Monte Carlo paths;
- writes `sim_results.xlsx`.

Use `--mode sequential` while learning. It produces the simplest call stack and error output.

`python/simengine/data_prep.py`

- parses config and coefficient files;
- maps raw fields and category values;
- builds smooth and factor terms;
- loads dials and macros;
- prepares and validates loans;
- defines `DataManager`.

`python/simengine/register_vars.py`

- defines static and time-varying fields;
- advances age and date;
- derives model lookup fields;
- maps unsupported GAM terms to fitted stacks.

The model stack mapping is:

```text
24-month term -> 36-month model stack
48-month term -> 60-month model stack
84-month term -> 60-month model stack
```

This changes model lookup fields such as `oterm_f` and `term_platform`. It does not change the actual amortization term.

`python/simengine/runner.py`

- evaluates softmax probabilities;
- applies dials;
- samples transitions;
- calculates cashflows;
- runs sequential, pool, or Ray workloads;
- aggregates by age and projection period;
- writes XLSX output.

`python/simengine/dump.py`

- records loan fields before model scoring;
- records the selected destination, probabilities, balances, payments, and loss;
- writes `output/<deal>/dump/dump.csv`.

`python/simengine/model_report.py`

- turns coefficient files into an interactive model report;
- lets you inspect factor coefficients and smooth curves without reading thousands of TSV rows.

### Deal report

`python/deal_report/loader.py` reads the simulation workbook and raw tape.

`python/deal_report/metrics/` calculates KPIs and input summaries.

`python/deal_report/render/` contains formatting, themes, CSS, JavaScript, and Vega chart specifications.

`python/deal_report/pages/` assembles the aggregate, summary, and optional cashflow-comparison pages.

`python/deal_report/builder.py` writes:

```text
output/<deal>/<deal>_<scenario>_deal_report.html
```

The HTML loads Vega libraries from a CDN. Charts need network access when you open the report.

### C++ engine

The C++ path performs the same broad calculation but is designed for larger simulations.

Important files:

- `CMakeLists.txt`: C++ targets, OpenMP, optional tests, and optional Python bindings;
- `src/model/model_coef.cpp`: coefficient parsing and term evaluation;
- `src/model/transition.cpp`: softmax, dials, and sampling;
- `src/model/roll.cpp`: segmented dial loading and lookup;
- `src/cf.cpp`: one loan-path cashflow loop;
- `src/runners/cf_parallel.cpp`: OpenMP parallel execution and grouped reductions;
- `src/data_mgr.cpp`: input and model initialization;
- `src/var_registry.cpp`: monthly variable updates;
- `src/main.cpp`: CLI, output metrics, and XLSX consolidation.

Headers under `include/` define the matching interfaces.

C++ reads prepared JSON. It does not prepare raw CSVs. It writes intermediate CSVs, then calls `tools/csvs_to_xlsx.py` to create the workbook and remove the intermediate files.

### Tools

`tools/dump_gam_to_coef.R`

- reads external fitted R GAM objects;
- exports factor, smooth, and interaction terms;
- depends on Jason's RCode paths in the current configuration.

`tools/csvs_to_xlsx.py`

- consolidates C++ CSV output into the four-sheet workbook;
- removes the CSV files after a successful conversion.

`tools/make_dial.py`

- multiplies a base period schedule by a custom dial;
- can generate rows for every term and grade in a prepared deal.

`tools/find_crash_loan.py`

- repeatedly subsets a prepared loan JSON to isolate a C++ crash;
- temporarily rewrites the selected prepared file and restores it afterward;
- should not be part of a first learning run.

## Prerequisites for the demo

Use the company Windows environment with Python 3.11. From `roll-rate-model/`, install the repository dependencies if the imports are not already available:

```powershell
python -m pip install -r ..\requirements.txt
```

The demo needs all five `STACKED_v4` coefficient files and the two default macro inputs. Confirm they exist before creating a tape:

```powershell
$required = @(
    "input\coef\STACKED_v4\fromC.txt",
    "input\coef\STACKED_v4\fromD1M.txt",
    "input\coef\STACKED_v4\fromD2M.txt",
    "input\coef\STACKED_v4\fromD3M.txt",
    "input\coef\STACKED_v4\fromD4M.txt",
    "input\macro\CPIAUCNS.csv",
    "input\macro\FICO_BKT_COUPON.csv",
    "input\pmt_matrix.txt"
)

$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    throw "Missing required roll-rate assets: $($missing -join ', ')"
}
```

If any `STACKED_v4` file is missing, complete the approved upstream sync. Do not substitute an older coefficient version and assume the fields are compatible.

## First run: one synthetic loan

The repository does not track deal tapes, so the default `upst_2026_2` command cannot run from a clean checkout. Create a one-loan demo instead.

Run all commands from:

```powershell
S:\QR\hzeng\howard-toolbox\roll-rate-model
```

### 1. Create the demo tape

```powershell
$demoDir = "input\deals\learning_demo"
[IO.Directory]::CreateDirectory($demoDir) | Out-Null

$csv = @'
loan_id,end_bal,note_rate,term,loan_age,status,r_dt,orig_bal,orig_dt,ofico,platform_f,f_pmt_dt,grade,opti,credit_age,hm_owner,employed_f,purpose,days_to_month_end,month_group
DEMO-001,10000,0.15,36,6,C,2026-05-31,12000,2025-11-15,700,Upstart,2025-12-15,UP-B,0.25,120,Rent,Yes,Credit Card Refinancing,16,30_Day
'@

[IO.File]::WriteAllText(
    (Join-Path $demoDir "learning_demo.csv"),
    $csv,
    [Text.UTF8Encoding]::new($false)
)
```

The two explicit calendar fields, `days_to_month_end` and `month_group`, make the first-period Python and C++ inputs align.

### 2. Prepare the loan

```powershell
python python\data_prep_for_sim.py `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --skip-dump
```

Keep `--skip-dump`. Without it, the script invokes external R models and may overwrite the local coefficient files.

A successful preparation prints `Prepared 1 loans`. The macro summary should mark the CPI and FICO coupon paths `[OK]`. Stop if the script reports a missing required field.

Inspect:

```text
input/deals/learning_demo/loans_prepped.json
input/deals/learning_demo/loans_prepped.txt
input/coef/STACKED_v4/model_report.html
```

In the prepared loan, find:

- normalized category values;
- `int_rate`;
- `month`;
- `oterm_f`;
- `term_platform`;
- `v_*` missingness flags;
- CPI and FICO coupon fields.

### 3. Run Python sequentially

```powershell
python python\run.py `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --mode sequential `
  --dup 1 `
  --seed 42 `
  --n-per 12 `
  --scen demo `
  --dump
```

This is a learning run, not a stable Monte Carlo estimate. With one path, the result is one random state path.

Read the final summary. It must report one completed loan and zero errors:

```text
1 tasks, 1 loans, 0 errors
```

The Python CLI may still return process exit code zero when an individual loan fails, so do not rely on the exit code alone.

Confirm the main outputs:

```powershell
Test-Path output\learning_demo\dump\dump.csv
Test-Path output\learning_demo\demo\sim_results.xlsx
```

Inspect:

```text
output/learning_demo/dump/dump.csv
output/learning_demo/demo/sim_results.xlsx
```

In `dump.csv`, follow:

- `_per`: zero-based simulation period;
- `_from`: current state;
- `_to`: sampled next state;
- `from...` columns: transition probabilities;
- loan feature columns used for scoring;
- `_begin_bal`, `_end_bal`, `_int_pmt`, `_prin_pmt`, `_loss`.

This file is the best starting point for understanding one monthly transition.

For each dump row, the applicable `from...` probabilities should sum to approximately `1.0`. The period-one probabilities should match the same cohort and period in `Metrics_Grouped_Period`.

The workbook has:

- `Portfolio`: raw cashflow totals by projection period;
- `Metrics_Portfolio`: CPR, CDR, CGL, balances, payoff, and loss;
- `Metrics_Grouped`: cohort output indexed by loan age;
- `Metrics_Grouped_Period`: cohort output indexed by projection period.

### 4. Generate the HTML report

```powershell
python python\generate_deal_report.py `
  --deal learning_demo `
  --scenario demo
```

A successful command prints `Wrote` followed by the scenario-qualified report path.

Open:

```text
output/learning_demo/learning_demo_demo_deal_report.html
```

The report should contain aggregate and input-summary pages. The optional cashflow-comparison page appears only when Jason's separate Cashflow Engine has a matching deal and scenario configuration.

## Trace the first month in code

After the demo runs, trace one row of `dump.csv` in this order:

1. `python/run.py::main()` selects the horizon, seed, execution mode, and output.
2. `python/simengine/runner.py::run_simulation()` initializes models and dispatches loans.
3. `_run_one_loan()` loops over Monte Carlo paths.
4. `run_cf_one()` performs the monthly simulation.
5. `_softmax_transition()` computes probabilities and samples the destination.
6. `python/simengine/data_prep.py::calc()` evaluates model terms.
7. `_compute_payments()` calculates scheduled interest and principal.
8. `step_period_fields()` advances the loan to the next month.

Then find the same responsibilities in:

```text
src/main.cpp
src/runners/cf_parallel.cpp
src/cf.cpp
src/model/transition.cpp
src/model/model_coef.cpp
src/var_registry.cpp
```

## Build and run C++ later

Do this only after the Python demo makes sense.

The C++ build requires:

- CMake 3.16 or newer;
- Visual Studio 2022 or Build Tools 2022;
- the "Desktop development with C++" workload.

```powershell
cmake -S . -B build `
  -DBUILD_TESTS=OFF `
  -DBUILD_PYTHON=OFF

cmake --build build `
  --config Release `
  --target sim_main
```

Use `BUILD_TESTS=OFF` because the repository currently has no checked-in C++ tests and the default setting fetches GoogleTest.

Run:

```powershell
.\build\Release\sim_main.exe `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --n-per 12 `
  --dup 100 `
  --seed 42 `
  --workers 8 `
  --scen cpp_demo
```

With one loan and `--dup 100`, the run summary must report `100 done, 0 errors`. Confirm the workbook exists:

```powershell
Test-Path output\learning_demo\cpp_demo\sim_results.xlsx
```

Generate its report:

```powershell
python python\generate_deal_report.py `
  --deal learning_demo `
  --scenario cpp_demo
```

Python and C++ use different random-number generators. Do not expect `dup=1` paths to match even with the same seed. Compare probabilities and sufficiently large aggregate simulations.

## Suggested 75-minute learning session

### First 10 minutes

Read:

```text
config/default.json
input/pmt_matrix.txt
```

Draw the state graph on paper. Mark `PIF` and `LIQ` as terminal.

### Minutes 10 to 20

Open:

```text
input/coef/STACKED_v4/fromC.txt
```

Identify:

- destination models;
- intercepts;
- factor coefficients;
- one numeric smooth.

### Minutes 20 to 35

Create and prepare `learning_demo`. Compare the raw CSV with `loans_prepped.json`.

### Minutes 35 to 50

Run Python with `--dump`. Follow one period through probabilities, sampled state, payment, and ending balance.

### Minutes 50 to 60

Open `sim_results.xlsx`. Reconcile the first `Portfolio` row with the first dump row.

### Minutes 60 to 70

Trace:

```text
_softmax_transition()
run_cf_one()
compute_metrics()
```

### Final 5 minutes

Map the Python functions to their C++ equivalents. Stop there. Do not introduce dials or real deal tapes until the base path is clear.

## Safe first experiments

Change one thing at a time.

### Change the random seed

```powershell
python python\run.py `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --mode sequential `
  --dup 1 `
  --seed 43 `
  --n-per 12 `
  --scen seed43
```

This changes the sampled path, not the transition probabilities.

### Increase paths

```powershell
python python\run.py `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --mode sequential `
  --dup 100 `
  --seed 42 `
  --n-per 12 `
  --scen paths100
```

More paths reduce Monte Carlo noise. They do not change the fitted model.

### Change the horizon

```powershell
python python\run.py `
  --config config\default.json `
  --deal-name learning_demo `
  --coef-version STACKED_v4 `
  --mode sequential `
  --dup 1 `
  --seed 42 `
  --n-per 24 `
  --scen months24
```

### Inspect a different origin state

Duplicate the demo row, assign a different `loan_id`, and change `status` to `D1M`. Compare the available destinations and probabilities.

### Add a dial last

Only add dials after you can explain the undialed probabilities. A dial can hide whether a surprising result came from the model or from an override.

## Gotchas worth knowing

### This is not a clean-room generic framework

The state names, raw field mappings, GAM stack assumptions, payment logic, PIF behavior, LIQ behavior, and report metrics are MPL-specific. Supporting a materially different asset class requires code changes.

### Do not regenerate coefficients casually

`config/default.json` points to external R models under Jason's RCode directory. Omitting `--skip-dump` runs the export and can overwrite local coefficient files.

### No loan tapes are committed

`input/deals/` is gitignored. Build your own synthetic demo or obtain an approved tape separately.

### Generated output is ignored

`build/`, `output/`, deal tapes, model reports, and Python bytecode are not source-of-truth files.

### Model term is not always loan term

The GAMs use 36- and 60-month stacks. The registry maps 24-month loans to 36 and 48- or 84-month loans to 60 for model lookup. Cashflow amortization still uses the actual loan term.

### Legacy platform type

The current engines do not derive `platform_type_f`. Some older `DIALED_*` assets use that field. Do not regenerate or mix legacy coefficients without checking the input contract.

### Macro values eventually freeze

The default uses raw CPI and FICO coupon data. When future monthly values are unavailable, the runtime keeps the last prepared or updated value.

### Python and C++ are separate implementations

Python is not a wrapper around C++. A change in one engine does not automatically update the other.

Some differences remain:

- C++ supports a dial CLI; Python's CLI does not expose one.
- Python reads configurable terminal and delinquency definitions; C++ still hardcodes parts of that behavior.
- Missing numeric model fields do not have identical treatment.
- The engines use different random-number generators.

Compare calculations and aggregate distributions. Do not demand identical one-path output.

### Use sequential mode while learning

`--mode auto` may select multiprocessing or Ray for large tasks. Sequential mode keeps errors and the call stack in one process.

### Report paths differ

The workbook is scenario-specific:

```text
output/<deal>/<scenario>/sim_results.xlsx
```

The HTML report sits one level higher:

```text
output/<deal>/<deal>_<scenario>_deal_report.html
```

The Python debug dump is not scenario-specific:

```text
output/<deal>/dump/dump.csv
```

## Glossary

`roll rate`

The probability of moving from one credit state to another over one period.

`transition model`

A fitted model for one non-stay destination, such as `C -> D1M` or `D1M -> C`.

`stay`

Remaining in the current state. Stay is the multinomial baseline with logit zero.

`GAM`

Generalized additive model. It combines factor coefficients with nonlinear smooth functions.

`logit`

The linear predictor before softmax conversion to probability.

`dial`

A post-model probability multiplier used to apply judgment or scenario assumptions.

`path`

One random realization of a loan's monthly states and cashflows.

`dup`

The number of Monte Carlo paths simulated per loan.

`CPR`

Annualized conditional prepayment rate.

`CDR`

Annualized conditional default rate.

`CGL`

Cumulative gross loss as a fraction of original balance.

`PIF`

Paid in full.

`LIQ`

Liquidation or charge-off.

## What to read next

After the demo:

1. Read [README.md](README.md) for full CLI and configuration details.
2. Inspect `python/simengine/data_prep.py` to understand coefficient terms and input preparation.
3. Inspect `python/simengine/runner.py` to understand transition sampling and cashflows.
4. Compare the Python functions with `src/model/`, `src/cf.cpp`, and `src/runners/cf_parallel.cpp`.
5. Move to a real deal only after you can explain one synthetic loan month by month.
