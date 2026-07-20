#!/usr/bin/env python
"""Trace ONE defaulting loan end-to-end: per-period transition path + the two-part severity
handling (lag draw -> recovery-rate GAM -> deferred recovery), for verification/audit.
See docs/severity_handling.md for the worked example this reproduces.

    python tools/debug/trace_loan.py     # scans for a recovering default in CRVNA 2022-P2 (PRIME_STACKED)
"""
import sys, os
sys.path.insert(0, "python")
from simengine import load_config, init_data_manager, load_loans
import simengine.runner as R
from simengine.runner import (run_cf_one, CF_DICT, _build_transition_layout,
                              _build_prob_schema, _get_registry, classify_model_terms)

cfg = load_config("config/auto_prime.json"); cfg["coef_version"] = "PRIME_STACKED"
dm = init_data_manager("input", config=cfg)
# replicate run_simulation's per-dm setup
pk, pl = _build_prob_schema(dm); dm.prob_keys = pk; dm.prob_layout = pl
dm.prob_key_idx = {k: i for i, k in enumerate(pk)}
reg = _get_registry()
classify_model_terms(dm.models, reg.time_varying_names() | reg.macro_names())
dm._transition_layout = _build_transition_layout(dm)
loans = load_loans("input/deals/CRVNA_2022_P2/loans_prepped.json")
ci = CF_DICT
SEED = 42

# 1. scan for first loan that charges off AND recovers (per-loan seed, like the real run)
target = None; n_def = n_rec = 0; trace_seed = SEED
for i, ln in enumerate(loans[:5000]):
    s = SEED + i
    cf, _ = run_cf_one(ln, dm, 1, s)
    co = next((p for p, row in enumerate(cf) if row[ci["liq_bal"]] > 0), None)
    if co is None:
        continue
    n_def += 1
    if any(row[ci["recov"]] > 0 for row in cf):
        n_rec += 1
        if target is None:
            target = (i, ln, co); trace_seed = s
print(f"scan: {n_def} defaults, {n_rec} of them recover (of 5000 loans)")
if target is None:
    print("no recovering default found"); sys.exit()

i, ln, co_per = target
SEED = trace_seed
print(f"\nDEFAULTING LOAN: index {i}, charge-off at period {co_per}")
print("static covariates:")
for k in ["loan_id", "status", "end_bal", "orig_bal", "term", "loan_age", "ofico",
          "platform_f", "note_rate", "ltv", "veh_age", "vehiclevalueamount", "orig_dt"]:
    print(f"    {k:20s} = {ln.get(k)}")

# 2. re-run with tracing (monkeypatch the two hot-path fns)
print("\nPATH (per-period transitions):")
_st = R._softmax_transition
def tst(loan, fs, rt, dm, per, rng, **kw):
    to, pf = _st(loan, fs, rt, dm, per, rng, **kw)
    print(f"  per {per:2d}  age {int(loan.get('loan_age',0)):2d}  {fs:4s} -> {to:4s}   bal {float(loan.get('end_bal',0)):>12,.0f}")
    return to, pf
R._softmax_transition = tst

_sev = R._severity_recovery
def tsev(loan, gross, dm, rng):
    rr, lag = _sev(loan, gross, dm, rng)
    print(f"    >>> CHARGE-OFF  gross={gross:,.0f}")
    print(f"        drawn recovery_lag_bkt={loan.get('recovery_lag_bkt')}  lag={lag} mo")
    print(f"        paydown_fraction={loan.get('paydown_fraction')}  manheim_drift={round(loan.get('manheim_drift',0),4)}")
    print(f"        recovery_rate(GAM)={rr:.4f}  ->  recovery=${gross*rr:,.0f}  net loss=${gross*(1-rr):,.0f}")
    print(f"        recovery booked at period {co_per}+{lag} = {co_per + (lag or 0)}")
    return rr, lag
R._severity_recovery = tsev

cf, _ = run_cf_one(ln, dm, 1, SEED)

print("\ncashflow booking (rows with any loss or recovery):")
for p, row in enumerate(cf):
    if row[ci["liq_bal"]] > 0 or row[ci["recov"]] > 0:
        print(f"    per {p:2d}:  liq_bal={row[ci['liq_bal']]:>12,.0f}  loss(GROSS)={row[ci['loss']]:>12,.0f}  recov={row[ci['recov']]:>12,.0f}")
