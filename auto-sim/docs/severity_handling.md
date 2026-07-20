# Severity & recovery-lag handling — how one loan is processed

This is the **only** behavior that differs from the base roll-rate-model engine (which uses a
single scalar `liq_severity`). Auto uses a **two-part (hurdle) severity**:

```
expected recovery  =  P(recover, timing)            ×  E[recovery rate | recovered, features]
                       └── empirical lag distribution ┘   └── recovery-rate GAM (logit) ─────┘
```

- The **lag distribution** (`input/severity/recovery_lag_dist.tsv`, per platform) carries *whether* and *when* a
  charged-off loan recovers — including the **`never`** mass. It is the only stochastic element.
- The **recovery-rate GAM** (`severity.txt`, dumped from `severity_bam.rds`) gives the recovery
  *rate conditional on recovering*. It was fit on recovered loans only — which is exactly why the
  `never` mass must come from the empirical distribution, not the GAM.

## Per-loan flow at a charge-off (status → LIQ in period `t`, balance `gross`)

1. **Gross loss** is booked at `t` → `cf[t].loss = gross`, `cf[t].liq_bal = gross`. This is CGL and
   is independent of recovery.
2. **Draw a lag** from `lag_cdf[platform]` with one RNG uniform → a label in `{0,1,…,12,"13+","never"}`.
3. **Branch:**
   - **`never`** → `recovery_rate = 0`, no GAM call, no deferred recovery. Net loss = full `gross`.
   - **recovered** → set the event-time covariates, score the GAM, defer the recovery:
     - `recovery_lag_bkt` = bucket(lag)  (`"0","1","2-3","4-6","7-12","13+"`) — note this is *both* the
       draw outcome *and* a GAM input (recovery rate genuinely differs by how fast it comes back).
     - `paydown_fraction` = `1 − gross/orig_bal` (amortization at default).
     - `manheim_drift` = `Manheim(charge-off month) / Manheim(origination month)` (used-car macro).
     - `recovery_rate = logistic( severity_lp(loan) )`.
     - `recovery = gross × recovery_rate`, booked at **`cf[t+lag]`** (deferred). Net loss = `gross − recovery`.
4. **CNL** = `(cum_loss − cum_recovery) / orig_pool` — so net loss **trails** gross loss by the lag.

`severity_lp` = the generic model `calc()` (intercept + main effects + smooths, including the
`platform` and `recovery_lag_bkt` main effects) **plus** the `recovery_lag_bkt × platform`
interaction. The interaction is dumped under var `platform` as composite-key levels like
`Carvana:recovery_lag_bkt2-3`, which the generic `calc()` misses (it looks up one key per var), so
`severity_lp` adds it explicitly.

## Worked example — two real CRVNA 2022-P2 loans (PRIME_STACKED, traced via `tools/debug/trace_loan.py`)

**Loan A — recovers.** Carvana, FICO 678, 75-mo, note 12.0%, LTV 1.07. Pays Current for 25 months,
then `C→D1M→D1M→D1M→D2M→D2M→D2M→D3M→LIQ`, charging off at period **t = 32**, balance **$15,458**.
- Drew lag = **3 months** → `recovery_lag_bkt = "2-3"`.
- `paydown_fraction = 0.296`, `manheim_drift = 0.84` (used-car values fell ~16% from 2022 origination
  to the ~2024 charge-off — the macro signal working).
- `recovery_rate = 0.326` → recovery **$5,033**, net loss **$10,425**.
- Cashflow: `cf[32].loss = 15,458` (gross), `cf[35].recov = 5,033` (deferred by lag=3). ✓

**Loan B — never recovers.** Similar Carvana loan, charges off at period 32 with $15,757. Drew the
**`never`** bucket (~21% for Carvana) → `recovery_rate = 0`, full **$15,757** loss, nothing booked back.

## Where the code lives (Python ↔ C++ are 1:1)

| Piece | Python (`python/simengine/`) | C++ (`src/`) |
|---|---|---|
| severity LP (calc + interaction) | `runner.py::_severity_lp` | `model/model_coef.cpp::severity_calc` |
| two-part draw (recover/never) | `runner.py::_severity_recovery` | inlined in `cf.cpp` LIQ branch |
| LIQ booking (gross@t, recovery@t+lag) | `runner.py` LIQ branch | `cf.cpp` LIQ branch |
| loaders (lag CDF, Manheim, GAM) | `data_prep.py::_load_lag_dist/_load_manheim` + `init_data_manager` | `data_mgr.cpp::load_severity`, `model_coef.cpp::read_model` |
| CNL metric | `runner.py::compute_metrics` + xlsx writer | `main.cpp::compute_metrics` + CSV writer |

Config-gated: with `severity_coef`+`lag_dist_path` set, the two-part path runs; otherwise the engine
falls back to the scalar `liq_severity` (so the base engine behavior is preserved unchanged).

## Parity (C++ vs Python, dup=100, CRVNA 2022-P2)
CGL/CNL agree to **< 0.6 bp** for both BASE and STACKED — pure Monte-Carlo floor (the engines use
different RNGs, so paths differ per-loan but pool aggregates converge).

## Known gotcha
`severity.txt`'s smooth was fit under `orig_period` (archaic), renamed to `lending_environment` in
the coef so it matches the tape. The permanent fix is to **re-fit `ctd1_stacked` with
`lending_environment`** (the Auto source already uses that name). Also: the C++ scorer evaluates a
*missing* smooth var at 0 (→ clamp) where Python skips it — harmless once names match, but worth
hardening so a future name mismatch can't silently blow up.
