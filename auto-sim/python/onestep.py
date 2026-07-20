"""Rolling-Forecast C->D1M (ctd1) and C->PIF (ctp) rates for the backtest overlay.

At each realized month t, re-seed from the REALIZED pool (that month's actual
panel) and score the model one step (t -> t+1) with the sim's own softmax,
balance-weighted over the FULL Current pool. Contrast with the compounding
multi-step "Projected" rate and the realized "Actual" rate:

    Actual - Rolling      = per-step model error (is the rate right this month?)
    Rolling - Projected   = compounding / pool-drift error

Reuses the prepped START tape (static covariates) + the realized panel (survival,
balance, delinquency history) + the sim's run_cf_one, so no extra tape reads and
the scoring is identical to the sim's. Scores in parallel across a worker pool
(each worker builds the DataManager once); no sampling.
"""
from __future__ import annotations

import json
import math
import os
import random

import numpy as np
import pandas as pd

import realized
from auto_tape import _dq6_bucket
from simengine import init_data_manager
from simengine import runner as _rn

# Age/calendar fields the prep bakes from loan_age + r_dt. Baked at period 0 in
# the start tape; strip so derive_initial re-bakes them for the target period's
# loan_age / r_dt (macro fields are re-applied by run_cf_one).
_REDERIVE = ("age", "age_pct", "c_age_pct", "age_fc", "month", "days_to_month_end")
_C_FIELDS = frozenset({"c_age_pct"})


def _prepare_dm(dm) -> None:
    """Per-run setup run_simulation does after init_data_manager, so the scorer can
    be called directly (prob schema, term classification, transition layout).

    CRITICAL: dynamic_vars MUST include PATH_DEPENDENT vars (e.g. dq6_bkt). We reuse
    one static-logit cache per loan across its months, so any term baked into that
    cache is frozen at the first month's value. dq6_bkt changes month-to-month, so
    it must be classified dynamic (excluded from the static cache) or its bump is
    frozen at the seed (=0) and never fires. The sim's own classify omits these
    because the production path is C++ (which handles dq6 per-period itself)."""
    pk, pl = _rn._build_prob_schema(dm)
    dm.prob_keys, dm.prob_layout = pk, pl
    dm.prob_key_idx = {k: i for i, k in enumerate(pk)}
    reg = _rn._get_registry()
    path_dep = {v.name for v in reg._vars.values() if v.kind.name == "PATH_DEPENDENT"}
    _rn.classify_model_terms(dm.models,
                             reg.time_varying_names() | reg.macro_names() | path_dep)
    dm._transition_layout = _rn._build_transition_layout(dm)


def _load_prepped(prepped_json: str) -> dict:
    obj = json.load(open(prepped_json))
    loans = obj if isinstance(obj, list) else obj.get("loans", obj.get("data", []))
    return {str(l["loan_id"]): l for l in loans}


def _dq6_by_loan_period(panel: pd.DataFrame) -> dict:
    """(loan_id, period) -> 6-bit trailing delinquency mask (bit0 = period-1),
    matching auto_tape._delinquency_history's rule. Vectorised via per-loan shifts
    (rows are consecutive months for surviving loans)."""
    p = panel[["assetnumber", "period", "dpd", "co", "ebal"]].sort_values(
        ["assetnumber", "period"]).copy()
    p["delq"] = ((p["co"] <= 0) & (p["ebal"] > 0) & (p["dpd"] >= 30)).astype(int)
    g = p.groupby("assetnumber")["delq"]
    mask = np.zeros(len(p), dtype=np.int64)        # np supports <<, pandas Series doesn't
    for k in range(1, 7):                          # k months before -> bit k-1
        mask |= g.shift(k).fillna(0).astype(np.int64).to_numpy() << (k - 1)
    return dict(zip(zip(p["assetnumber"].astype(str), p["period"].astype(int)),
                    mask.tolist()))


def _apply_macro(loan: dict, ms) -> None:
    """Replicate run_cf_one's per-period macro override (calendar vars +
    rate_incentive_ALL) for the loan's r_dt."""
    if not ms:
        return
    r_dt = loan.get("r_dt", "")
    ym = str(r_dt)[:7] if r_dt else ""
    if ms.get("calendar_table"):
        row = ms["calendar_table"].get(ym)
        if row:
            ms["_last_calendar"] = row
        last = ms.get("_last_calendar")
        if last:
            for v in ms["calendar_vars"]:
                if v in last:
                    loan[v] = last[v]
    if ms.get("fico_coupon") and "rate_incentive_ALL" in ms.get("active_vars", ()):
        bkt = loan.get("_fico_bkt", "")
        if bkt:
            cr = ms["fico_coupon"].get(f"{ym.replace('-', '')}|{bkt}")
            cv = loan.get("_coupon_at_vintage")
            if cr is not None and cv is not None:
                loan["rate_incentive_ALL"] = cr - cv


# ── parallel worker ──────────────────────────────────────────────────────────
_W: dict = {}


def _init_worker(config: dict, prepped_json: str) -> None:
    """Build the DataManager + start tape once per worker process."""
    cfg = {**config, "n_per": 1}
    dm = init_data_manager(cfg.get("input_dir", "input"), n_per=1, config=cfg)
    _prepare_dm(dm)
    roll = dm.status_to_roll.get("C", ["C", "D1M", "PIF", "LIQ"])
    _W.update(dm=dm, base=_load_prepped(prepped_json), reg=_rn._get_registry(),
              roll=roll, tl=dm._transition_layout.get("C"),
              ms=(dm._macro_state if getattr(dm, "_macro_state", None) else None),
              i_d1=(roll.index("D1M") if "D1M" in roll else None),
              i_pif=(roll.index("PIF") if "PIF" in roll else None),
              rng=random.Random(0))


def _score_chunk(chunk):
    """Score a chunk of (loan_id, [(period, r_dt, loan_age, dq6_mask, bal), ...]).
    The static logit is built ONCE per loan and reused across its months (the same
    reuse run_cf_one does internally). Returns {period: [Σ ctd1·bal, Σ ctp·bal, Σ bal]}."""
    dm, base, reg = _W["dm"], _W["base"], _W["reg"]
    roll, tl, ms = _W["roll"], _W["tl"], _W["ms"]
    i_d1, i_pif, rng = _W["i_d1"], _W["i_pif"], _W["rng"]
    build_static = _rn.build_static_cache
    init_tv = _rn.init_time_varying_state
    softmax = _rn._softmax_transition
    acc: dict = {}
    for lid, states in chunk:
        b = base.get(lid)
        if b is None:
            continue
        ot = b.get("orig_term")
        logit_cache = None                         # built on this loan's first month
        for per, r_dt, la, mask, bal in states:
            if bal <= 0:
                continue
            try:
                ln = dict(b)
                ln["status"] = "C"; ln["end_bal"] = bal; ln["loan_age"] = la
                if ot:
                    ln["term"] = max(1, int(ot) - la)
                ln["r_dt"] = r_dt
                ln["_dq6_mask"] = mask; ln["dq6_bkt"] = _dq6_bucket(mask)
                for k in _REDERIVE:
                    ln.pop(k, None)
                reg.derive_initial(ln, c_fields=_C_FIELDS)   # re-bake age/calendar
                init_tv(ln)
                if logit_cache is None:                       # static terms: once/loan
                    logit_cache = build_static(dm.models, ln)
                _apply_macro(ln, ms)
                _, pf = softmax(ln, "C", roll, dm, 0, rng, logit_cache=logit_cache, tl=tl)
            except Exception:
                continue
            a = acc.setdefault(per, [0.0, 0.0, 0.0])
            if i_d1 is not None:
                a[0] += pf[i_d1] * bal
            if i_pif is not None:
                a[1] += pf[i_pif] * bal
            a[2] += bal
    return acc


def _merge(acc: dict, part: dict) -> None:
    for per, (d1, pif, den) in part.items():
        t = acc.setdefault(per, [0.0, 0.0, 0.0])
        t[0] += d1
        t[1] += pif
        t[2] += den


def compute_onestep(config: dict, prepped_json: str, tape_dir: str,
                    snap_date, horizon: int, workers: int | None = None,
                    sample: int | None = None, panel=None) -> pd.DataFrame:
    """Per-period Rolling-Forecast ctd1/ctp (fractions), scored across a worker
    pool. ``sample`` caps loans scored per month (None/0 = full pool); a few
    thousand gives a balance-weighted rate statistically identical to the full
    pool at a fraction of the cost. ``panel`` (+ ``snap_date``) may be passed in to
    reuse the already-loaded realized panel and skip a second SMB tape read.
    Empty DataFrame if inputs are unusable."""
    try:
        if panel is not None:
            snap = pd.Timestamp(snap_date)
        else:
            panel, snap = realized.load_panel(tape_dir, snap_date)
        masks = _dq6_by_loan_period(panel)
        roll = config.get("status_to_roll", {}).get("C", ["C", "D1M", "PIF", "LIQ"])
        has_d1, has_pif = "D1M" in roll, "PIF" in roll
        if not has_d1 and not has_pif:
            return pd.DataFrame(columns=["period", "ctd1", "ctp"])

        # Group work BY LOAN (all its months together) so each loan's static logit
        # is built once and reused. For output period `per`, score the FROM pool at
        # tape period per-1 (realized.transition_curves: from-row m -> sim period m+1).
        by_loan: dict = {}
        for per in range(1, int(horizon) + 1):
            fp = per - 1
            cur = panel[(panel["period"] == fp) & (panel["status"] == "C") & (panel["ebal"] > 0)]
            if cur.empty:
                continue
            r_dt = (pd.Timestamp(snap) + pd.DateOffset(months=fp)).strftime("%Y-%m-%d")
            for lid, bal, age in zip(cur["assetnumber"].astype(str),
                                     cur["ebal"].astype(float), cur["loan_age"]):
                la = int(age) if pd.notna(age) else fp
                by_loan.setdefault(lid, []).append(
                    (per, r_dt, la, masks.get((lid, fp), 0), float(bal)))
        if sample and len(by_loan) > sample:          # optional: cap #loans (full = None)
            keep = random.Random(42).sample(list(by_loan), sample)
            by_loan = {k: by_loan[k] for k in keep}
        tasks = list(by_loan.items())                 # (loan_id, [month-states])
        if not tasks:
            return pd.DataFrame(columns=["period", "ctd1", "ctp"])

        # With the static-logit cache, scoring is cheap; the pool only pays off once
        # the work outweighs the ~12s Windows spawn startup. Small deals run
        # sequentially (no startup tax), large deals fan out.
        if workers is None:
            total = sum(len(s) for s in by_loan.values())
            workers = 1 if total < 800_000 else max(1, (os.cpu_count() or 4) // 2)
        acc: dict = {}
        if workers <= 1:
            _init_worker(config, prepped_json)
            _merge(acc, _score_chunk(tasks))
        else:
            from multiprocessing import Pool
            csize = max(200, math.ceil(len(tasks) / (workers * 6)))
            chunks = [tasks[i:i + csize] for i in range(0, len(tasks), csize)]
            with Pool(workers, initializer=_init_worker,
                      initargs=(config, prepped_json)) as pool:
                for part in pool.imap_unordered(_score_chunk, chunks):
                    _merge(acc, part)

        rows = []
        for per in sorted(acc):
            d1, pif, den = acc[per]
            if den > 0:
                rows.append({"period": per,
                             "ctd1": d1 / den if has_d1 else np.nan,
                             "ctp": pif / den if has_pif else np.nan})
        return pd.DataFrame(rows)
    except Exception as e:  # noqa: BLE001 — overlay is optional; never break the report
        print(f"  rolling-forecast overlay skipped: {e}")
        return pd.DataFrame(columns=["period", "ctd1", "ctp"])
