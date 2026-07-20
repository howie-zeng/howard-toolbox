#!/usr/bin/env python
"""Realized deal performance + transition matrix from the monthly loan tapes.

Computed only from the N:\\FlatFilesMonthly monthly CSVs (no BigQuery, no engine):
the realized curves and Markov transition matrix the sim backtest is graded against.

Emits three CSVs under output/<deal>/ that overlay onto the sim output (see
``deal_report/backtest.py``):

  actuals_portfolio.csv    period, begin_bal, pool_factor, cpr, cdr, cgl, cnl
  actuals_transitions.csv  loan_age, c_bal, ctd1, ctp  (bal-weighted monthly rates)
  actuals_matrix.csv       from_status, to_status, prob, from_bal

Conventions matched to the sim so the overlay is apples-to-apples:
  * period m aligns to sim Metrics_Portfolio.period m (snapshot tape = period 0);
    begin_bal[m] = pool EOP balance at m-1 (the sim's begin-of-period balance).
  * CGL/CNL denominator = sum of original loan amounts from the prepped tape
    (= sim's ``total_orig_bal``), not the snapshot balance.
  * state rule mirrors auto_tape._status; charge-off -> LIQ, prepay/repurchase -> PIF.
  * transitions are balance-weighted (same as the sim's prob_weighted).

    python realized.py --deal CRVNA_2022_P2 \
        --tape-dir "N:/FlatFilesMonthly/Auto/Carvana/Prime/CRVNA 2022-P2"
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

# Local cache for the raw concatenated monthly tapes (the slow SMB read). The
# panel is model-INDEPENDENT (realized data), so ONE file per deal serves every
# scenario/coef version. One folder, one file per deal, overwritten when any tape
# is newer than the cache — nothing accumulates. Delete the folder to reset.
_PANEL_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "_panel_cache")

# Reg-AB zero-balance codes seen in the auto tapes:
#   1 = Prepaid / Matured, 3 = Repurchased/Replaced  -> voluntary exit (PIF)
#   4 = Charged-off                                   -> default (LIQ)
ZBC_PREPAY = {"1", "3"}
ZBC_DEFAULT = {"4"}

USE_COLS = [
    "date", "assetnumber", "originationdate",
    "reportingperiodactualendbalanceamount",
    "currentdelinquencystatus", "zerobalancecode",
    "chargedoffprincipalamount", "recoveredamount",
]

FROM_STATES = ["C", "D1M", "D2M", "D3M", "D4M"]
TO_STATES = ["C", "D1M", "D2M", "D3M", "D4M", "PIF", "LIQ"]

# Coarse recovery-lag buckets (match the severity GAM's recovery_lag_bkt levels).
LAG_BUCKETS = ["0", "1", "2-3", "4-6", "7-12", "13+", "never"]


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _coarse_lag(L: int) -> str:
    if L <= 0:  return "0"
    if L == 1:  return "1"
    if L <= 3:  return "2-3"
    if L <= 6:  return "4-6"
    if L <= 12: return "7-12"
    return "13+"


def recovery_lag_profile(df: pd.DataFrame, lag_dist_path: str,
                         platform_mix: dict) -> pd.DataFrame:
    """P(recovery lag bucket | charge-off): projected vs actual, long form
    (bucket, series, value).

    Projected = the platform-mix-weighted empirical lag_dist, coarsened to
    LAG_BUCKETS. Actual = from the tapes: each charge-off's FIRST recovery month
    minus co month (matching lag_dist's rec_date = first recoveredamount>0), or
    'never' if nothing recovered. Restricted to charge-offs seasoned >= 12 months
    so late COs aren't miscounted 'never'."""
    rows = []
    # --- actual (resolved charge-offs) ---
    co_first = df.loc[df["co"] > 0].groupby("assetnumber")["period"].min()
    last_p = int(df["period"].max())
    rec = df.loc[df["recov"] != 0, ["assetnumber", "period", "recov"]]
    rec_by_loan = {a: g for a, g in rec.groupby("assetnumber")}
    counts = {b: 0.0 for b in LAG_BUCKETS}
    n_co = 0
    for aid, cp in co_first.items():
        if cp > last_p - 12:                                   # censor unresolved
            continue
        n_co += 1
        g = rec_by_loan.get(aid)
        tot = float(g["recov"].sum()) if g is not None else 0.0
        if tot <= 0:
            counts["never"] += 1
        else:
            # Match the canonical lag_dist definition (panel.build_recovery_summary:
            # rec_date = FIRST recoveredamount>0 on/after co_date, i.e. groupby.min).
            # A $-weighted mean over all remittances smears the lag into later
            # buckets (77% of subprime COs dribble over ~2-3 months / ~9mo span),
            # which is NOT how lag_dist or the sim's single-lump booking works.
            lag = int(g["period"].min()) - cp
            counts[_coarse_lag(int(lag))] += 1
    for b in LAG_BUCKETS:
        rows.append({"bucket": b, "series": "Actual",
                     "value": counts[b] / n_co if n_co else np.nan})
    # --- projected (platform-weighted lag_dist, coarsened) ---
    proj = {b: 0.0 for b in LAG_BUCKETS}
    if os.path.isfile(lag_dist_path):
        raw = pd.read_csv(lag_dist_path, sep="\t", dtype={"lag_bucket": str})
        tot_w = sum(platform_mix.values()) or 1.0
        for plat, w in platform_mix.items():
            sub = raw[raw["platform"] == plat]
            for _, r in sub.iterrows():
                lb, p = r["lag_bucket"], float(r["prob"]) * w / tot_w
                proj["never" if lb == "never" else
                     "13+" if lb == "13+" else _coarse_lag(int(lb))] += p
    for b in LAG_BUCKETS:
        rows.append({"bucket": b, "series": "Projected", "value": proj[b]})
    return pd.DataFrame(rows)


def _status(ebal, dpd, co, zbc):
    """End-of-period state per loan-month (mirrors auto_tape._status, plus the
    zero-balance-code signal which is cleaner than balance==0 for terminals)."""
    is_default = (co > 0) | np.isin(zbc, list(ZBC_DEFAULT))
    is_prepay = (~is_default) & (np.isin(zbc, list(ZBC_PREPAY)) | (ebal <= 0))
    return np.select(
        [is_default, is_prepay, dpd < 30, dpd < 60, dpd < 90, dpd < 120],
        ["LIQ", "PIF", "C", "D1M", "D2M", "D3M"], default="D4M",
    )


def _read_tapes(files: list) -> pd.DataFrame:
    """Read the monthly tapes concurrently (I/O-bound over SMB; pandas releases
    the GIL during read) and concatenate the needed columns."""
    def _read(f):
        return pd.read_csv(f, usecols=lambda c: c in USE_COLS, dtype=str)
    with ThreadPoolExecutor(max_workers=min(16, len(files))) as ex:
        frames = list(ex.map(_read, files))
    return pd.concat(frames, ignore_index=True)


def _load_raw_tapes(tape_dir: str, files: list) -> pd.DataFrame:
    """Concatenated raw tapes, via a local parquet cache keyed on the deal's tape
    folder. Cache is used only if it's at least as new as every tape; otherwise
    the tapes are re-read and the cache overwritten. Any cache error falls back to
    a plain read — the cache is an optimization, never a correctness dependency."""
    try:
        os.makedirs(_PANEL_CACHE_DIR, exist_ok=True)
        base = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(os.path.normpath(tape_dir)))
        cpath = os.path.join(_PANEL_CACHE_DIR, f"{base}.parquet")
        newest = max(os.path.getmtime(f) for f in files)
        if os.path.isfile(cpath) and os.path.getmtime(cpath) >= newest:
            return pd.read_parquet(cpath)
        df = _read_tapes(files)
        try:
            df.to_parquet(cpath, index=False)     # overwrite: one file per deal
        except Exception:
            pass                                   # cache write is best-effort
        return df
    except Exception:
        return _read_tapes(files)                  # any cache issue -> plain read


def load_panel(tape_dir: str, snap_date=None):
    """Stack all monthly tapes into one loan-month panel with derived state,
    month-since-snapshot index, loan age, and next-period state/balance.

    ``snap_date`` (prepped-tape as-of / projection start) pins period 0 and DROPS
    earlier tapes — matters when the first tapes are a prefunding ramp the sim
    doesn't project from. Defaults to the earliest tape."""
    files = sorted(glob.glob(os.path.join(tape_dir, "*.csv")))
    if not files:
        raise SystemExit(f"no tapes under {tape_dir}")
    df = _load_raw_tapes(tape_dir, files)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed")
    df["orig_dt"] = pd.to_datetime(df["originationdate"], errors="coerce",
                                   format="mixed")
    df["ebal"] = _num(df["reportingperiodactualendbalanceamount"])
    df["dpd"] = _num(df["currentdelinquencystatus"])
    df["co"] = _num(df["chargedoffprincipalamount"])
    # recoveredamount is the per-period net recovery; repossessedproceedsamount is
    # the GROSS proceeds feeding into it. Both populated on ~1000 charged-off loans,
    # so adding them double-counts — use recoveredamount alone (~37% of charge-off).
    df["recov"] = _num(df["recoveredamount"])
    zbc = df["zerobalancecode"].fillna("-").astype(str).str.strip().values
    df["status"] = _status(df["ebal"].values, df["dpd"].values, df["co"].values, zbc)

    snap = pd.Timestamp(snap_date) if snap_date is not None else df["date"].min()
    df = df[df["date"] >= snap].copy()          # drop prefunding/ramp tapes before the projection start
    df["period"] = ((df["date"].dt.year - snap.year) * 12
                    + (df["date"].dt.month - snap.month))
    df["loan_age"] = ((df["date"].dt.year - df["orig_dt"].dt.year) * 12
                      + (df["date"].dt.month - df["orig_dt"].dt.month))
    df = df.sort_values(["assetnumber", "period"]).reset_index(drop=True)

    # DEDUP charge-offs. Some servicers (notably CarMax) re-report
    # ``chargedoffprincipalamount`` for the same loan across 2-3 months (it is the
    # standing charged-off amount, not a per-period loss). Summing it double-counts
    # the loss (1.36x on CMAX 2022-1: raw $108.2M vs $79.8M once each loan's charge-off
    # is counted once). Keep co only in the FIRST month a loan reports co>0; zero it
    # thereafter. HART/TAOT/CRVNA are unaffected (they report co once). See
    # _tie/dedup_co.py for the diagnostic.
    _co_pos = df["co"] > 0
    _co_rank = _co_pos.groupby(df["assetnumber"]).cumsum()
    df.loc[_co_pos & (_co_rank > 1), "co"] = 0.0

    df["next_status"] = df.groupby("assetnumber")["status"].shift(-1)
    df["next_period"] = df.groupby("assetnumber")["period"].shift(-1)
    df["prev_status"] = df.groupby("assetnumber")["status"].shift(1)
    df["prev_ebal"] = df.groupby("assetnumber")["ebal"].shift(1)
    return df, snap


def portfolio_curves(df: pd.DataFrame, orig_pool: float) -> pd.DataFrame:
    """Per-period realized pool curves (period = months since snapshot)."""
    eop = df.groupby("period")["ebal"].sum().sort_index()
    snap_bal = float(eop.iloc[0])
    co_m = df.groupby("period")["co"].sum()
    recov_m = df.groupby("period")["recov"].sum()

    is_new_pif = (df["status"] == "PIF") & df["prev_status"].isin(FROM_STATES)
    prepay_m = df.loc[is_new_pif].groupby("period")["prev_ebal"].sum()

    # Per-period state balances -> delinquency shares (30+ and % current, both as
    # a share of the active pool = C + D1M..D4M, excluding paid-off/charged-off).
    active_st = ["C", "D1M", "D2M", "D3M", "D4M"]
    state = df.groupby(["period", "status"])["ebal"].sum().unstack(fill_value=0.0)
    for s in active_st:
        if s not in state.columns:
            state[s] = 0.0

    rows, cum_co, cum_recov = [], 0.0, 0.0
    for m in [p for p in eop.index if p >= 1]:
        begin = float(eop.get(m - 1, np.nan))
        co = float(co_m.get(m, 0.0)); rec = float(recov_m.get(m, 0.0))
        pp = float(prepay_m.get(m, 0.0))
        cum_co += co; cum_recov += rec
        smm = pp / begin if begin > 0 else np.nan
        mdr = co / begin if begin > 0 else np.nan
        active_m = float(state.loc[m, active_st].sum()) if m in state.index else np.nan
        dq30_m = float(state.loc[m, ["D1M", "D2M", "D3M", "D4M"]].sum()) if m in state.index else np.nan
        dq60_m = float(state.loc[m, ["D2M", "D3M", "D4M"]].sum()) if m in state.index else np.nan
        rows.append({
            "period": int(m), "begin_bal": begin,
            "pool_factor": begin / snap_bal if snap_bal > 0 else np.nan,
            "cpr": 1 - (1 - smm) ** 12 if np.isfinite(smm) else np.nan,
            "cdr": 1 - (1 - mdr) ** 12 if np.isfinite(mdr) else np.nan,
            "cgl": cum_co / orig_pool if orig_pool > 0 else np.nan,
            "cnl": (cum_co - cum_recov) / orig_pool if orig_pool > 0 else np.nan,
            "dq30p": dq30_m / active_m if active_m and active_m > 0 else np.nan,
            "dq60p": dq60_m / active_m if active_m and active_m > 0 else np.nan,
            # cumulative distress: currently-30+ + cumulative charge-off, as a
            # share of the ORIGINAL pool (monotone-ish, like CGL).
            "dist30": (dq30_m + cum_co) / orig_pool if orig_pool > 0 and np.isfinite(dq30_m) else np.nan,
        })
    return pd.DataFrame(rows)


def _valid_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Consecutive-month (from active -> known next) loan-month rows, weighted
    by begin-of-next balance (= this row's EOP balance)."""
    return df[df["status"].isin(FROM_STATES)
              & (df["next_period"] == df["period"] + 1)
              & df["next_status"].notna()
              & (df["ebal"] > 0)].copy()


def transition_curves(df: pd.DataFrame) -> pd.DataFrame:
    """Balance-weighted monthly transition rates by period and from-state, long form.
    rate(from->to) = Σbal(from->to) / Σbal(from->*). Period axis matches the sim's
    Metrics_Grouped_Period (from-row period m -> sim period m+1)."""
    pairs = _valid_pairs(df)
    pairs = pairs[pairs["period"] >= 0]
    num = (pairs.groupby(["period", "status", "next_status"])["ebal"].sum()
           .rename("bal").reset_index())
    den = (pairs.groupby(["period", "status"])["ebal"].sum()
           .rename("from_bal").reset_index())
    m = num.merge(den, on=["period", "status"])
    m["rate"] = m["bal"] / m["from_bal"]
    m["period"] = m["period"].astype(int) + 1            # align to sim period
    m = m.rename(columns={"status": "from_status", "next_status": "to_status"})
    return (m[["period", "from_status", "to_status", "rate", "from_bal"]]
            .sort_values(["from_status", "to_status", "period"])
            .reset_index(drop=True))


def transition_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Full realized Markov matrix, balance-weighted over the deal's observed life:
    prob(from->to) = Σbal(from->to) / Σbal(from->*). Long form."""
    pairs = _valid_pairs(df)
    num = (pairs.groupby(["status", "next_status"])["ebal"].sum()
           .rename("bal").reset_index())
    denom = pairs.groupby("status")["ebal"].sum()
    rows = []
    for fs in FROM_STATES:
        fb = float(denom.get(fs, 0.0))
        for ts in TO_STATES:
            b = float(num[(num["status"] == fs)
                          & (num["next_status"] == ts)]["bal"].sum())
            rows.append({"from_status": fs, "to_status": ts,
                         "prob": (b / fb) if fb > 0 else np.nan, "from_bal": fb})
    return pd.DataFrame(rows)


def _orig_pool_and_asof(prepped_json: str):
    """Original-pool balance (CGL/CNL denominator) and as-of date (period-0 anchor),
    both from the prepped tape so the overlay shares the sim's denominator/anchor."""
    with open(prepped_json) as f:
        loans = json.load(f)
    if isinstance(loans, dict):
        loans = loans.get("loans", loans.get("data", []))
    orig_pool = float(sum(float(l.get("orig_bal") or l.get("end_bal") or 0) for l in loans))
    asof = next((l.get("r_dt") for l in loans if l.get("r_dt")), None)
    return orig_pool, asof


def _platform_mix(prepped_json: str) -> dict:
    """Loan-count platform mix from the prepped tape (weights the projected lag dist)."""
    with open(prepped_json) as f:
        loans = json.load(f)
    if isinstance(loans, dict):
        loans = loans.get("loans", loans.get("data", []))
    mix: dict = {}
    for l in loans:
        p = l.get("platform_f") or l.get("platform")
        if p:
            mix[p] = mix.get(p, 0) + 1
    return mix


def compute_realized(tape_dir: str, prepped_json: str,
                     lag_dist_path: str = "input/severity/recovery_lag_dist.tsv") -> dict:
    """Compute the realized curves + transition matrix for a deal, in memory.

    Returns a dict of DataFrames (``portfolio``/``transitions``/``matrix``) plus
    ``snap`` and ``orig_pool``, all anchored to the prepped tape (period 0 + loss
    denominator), ignoring prefunding tapes before the projection start. The deal
    report calls this once and overlays the result directly (see build_html) —
    nothing is written to disk. The --write CLI path is standalone-inspection only.
    """
    orig_pool, asof = _orig_pool_and_asof(prepped_json)
    df, snap = load_panel(tape_dir, snap_date=asof)
    return {
        "portfolio": portfolio_curves(df, orig_pool),
        "transitions": transition_curves(df),
        "matrix": transition_matrix(df),
        "lag_profile": recovery_lag_profile(df, lag_dist_path, _platform_mix(prepped_json)),
        "snap": snap,
        "orig_pool": orig_pool,
        "panel": df,          # reused by onestep so the tapes aren't read twice
    }


def _print_summary(res: dict) -> None:
    port, matrix = res["portfolio"], res["matrix"]
    fin = port.iloc[-1]; last = int(port["period"].max())
    print(f"snapshot {res['snap'].date()} | orig pool {res['orig_pool']/1e6:.1f}M | "
          f"actual through period {last}")
    if (port.period == 48).any():
        r = port.loc[port.period == 48].iloc[0]
        print(f"  @48: CGL {100*r['cgl']:.2f}%  CNL {100*r['cnl']:.2f}%  "
              f"pool_factor {100*r['pool_factor']:.1f}%")
    print(f"  lifetime CGL {100*fin['cgl']:.2f}%  CNL {100*fin['cnl']:.2f}%")
    cc = matrix[(matrix.from_status == "C")].set_index("to_status")["prob"]
    print(f"  realized C-> : C {100*cc['C']:.2f}%  D1M {100*cc['D1M']:.3f}%  "
          f"PIF {100*cc['PIF']:.2f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deal", default="CRVNA_2022_P2")
    ap.add_argument("--tape-dir",
                    default="N:/FlatFilesMonthly/Auto/Carvana/Prime/CRVNA 2022-P2")
    ap.add_argument("--prepped-json", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--write", action="store_true",
                    help="Also write actuals_*.csv (standalone inspection only; "
                         "the deal report computes these in memory and needs no CSVs).")
    args = ap.parse_args()

    prepped = args.prepped_json or f"input/deals/{args.deal}/loans_prepped.json"
    res = compute_realized(args.tape_dir, prepped)
    _print_summary(res)

    if args.write:
        out_dir = args.out_dir or f"output/{args.deal}"
        os.makedirs(out_dir, exist_ok=True)
        for name, key in (("actuals_portfolio.csv", "portfolio"),
                          ("actuals_transitions.csv", "transitions"),
                          ("actuals_matrix.csv", "matrix")):
            res[key].to_csv(os.path.join(out_dir, name), index=False)
            print(f"  wrote {os.path.join(out_dir, name)}")


if __name__ == "__main__":
    main()
