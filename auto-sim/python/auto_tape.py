#!/usr/bin/env python
"""auto_tape.py -- build a sim-ready loan tape from an auto-ABS deal snapshot.

Reuses Auto's own add_static_features so covariates match what the GAMs were
trained on, then runs the engine's prepare_loans() and writes loans_prepped.json.

Usage:
    python auto_tape.py --config config/auto_prime.json \
        --snapshot "N:/FlatFilesMonthly/Auto/Carvana/Prime/CRVNA 2022-P2/CRVNA 2022-P2_2022-04-30.csv" \
        --issuer Carvana --shelf Prime
"""
import argparse, glob, os, sys
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
AUTO = "S:/QR/jli/Auto"
sys.path.insert(0, AUTO)

import config as C                                   # auto config (paths, breaks, tokens)
from lib.prep_data import io, macro as MAC           # noqa
from lib.prep_data import processing as P
from simengine import load_config, prepare_loans, save_prepped_loans


def _build_lookups(shelf):
    # Canonical vintage-coupon lookup from tools/lookups/build_coupon_lookup.py. NOT
    # C.LOOKUPS_DIR's copy: prep_transition overwrites that per from-state, so it
    # reflects whichever state ran last (inflated). See docs/coupon_lookup.md.
    # rel_rate is shelf-relative: the coupon table is pooled per modelling shelf
    # (Prime vs Subprime -- near/deep-subprime fold into Subprime). Prefer the
    # per-shelf file FICO_BKT_COUPON_<slug>.csv when present; fall back to the
    # canonical (Prime) file. Build via build_coupon_lookup.py --shelf <shelf>.
    slug = str(shelf).replace(" ", "_")
    shelf_path = os.path.join("input", "macro", f"FICO_BKT_COUPON_{slug}.csv")
    coup_path = shelf_path if os.path.exists(shelf_path) else \
        os.path.join("input", "macro", "FICO_BKT_COUPON.csv")
    print(f"  coupon lookup [{shelf}]: {coup_path}", flush=True)
    bkt = pd.read_csv(coup_path, dtype={"vint_moyy": int, "fico_bkt": str})
    # vint_moyy MUST be int: add_static_features reindexes with vint_moyy = year*100
    # + month (int64); a str-keyed MultiIndex silently misses -> rel_rate all-NaN.
    bkt_coupon = {(int(r.vint_moyy), str(r.fico_bkt)): float(r.fico_bkt_coupon)
                  for r in bkt.itertuples()}
    return {"bkt_coupon": bkt_coupon,
            "cpi": MAC.load_cpi(C.CPI_PATH),
            "manheim": MAC.load_manheim(C.MANHEIM_PATH),
            "mkt_coupon": None}


def _status(bal, dpd, co):
    if co > 0:           return "LIQ"
    if not (bal > 0):    return "PIF"
    if dpd < 30:         return "C"
    if dpd < 60:         return "D1M"
    if dpd < 90:         return "D2M"
    if dpd < 120:        return "D3M"
    return "D4M"


_DQ6_COUNT_BUCKET = ("0", "1", "2-3", "2-3", "4-6", "4-6", "4-6")   # index = #bits


def _dq6_bucket(mask: int) -> str:
    return _DQ6_COUNT_BUCKET[bin(mask & 63).count("1")]


def _delinquency_history(snapshot_csv, as_of):
    """Seed dq6_bkt from pre-snapshot tapes: the trailing-6-month delinquency mask
    as of the snapshot (mirrors consolidate.py's shift(1..6), which EXCLUDES the
    snapshot month). Returns {loan_id: (dq6_mask, dq6_bkt)} where dq6_mask is a
    6-bit int (bit 0 = the month immediately before the snapshot, older months in
    higher bits; months with no observed tape default to 0 / not-delinquent).
    Loans absent from all 6 pre-snapshot months default to (0, "0")."""
    tape_dir = os.path.dirname(snapshot_csv)
    as_of_ts = pd.Timestamp(as_of)
    pre = []
    for f in sorted(glob.glob(os.path.join(tape_dir, "*.csv"))):
        ds = os.path.basename(f).rsplit("_", 1)[-1].replace(".csv", "")
        dt = pd.to_datetime(ds, errors="coerce")
        if pd.notna(dt) and dt < as_of_ts:                     # STRICTLY before snapshot
            pre.append(f)
    files6 = pre[-6:]                                          # last 6 pre-snapshot months, oldest->newest
    nf = len(files6)
    mask: dict = {}
    for k, f in enumerate(files6):
        bitpos = nf - 1 - k                                    # newest file -> bit 0
        d = pd.read_csv(f, dtype=str, low_memory=False)
        ids = d["assetnumber"].astype(str).values
        bal = io.num(d["reportingperiodactualendbalanceamount"], C.NULL_TOKENS).fillna(0.0).values
        dpd = io.num(d["currentdelinquencystatus"], C.NULL_TOKENS).fillna(0.0).values
        co  = io.num(d["chargedoffprincipalamount"], C.NULL_TOKENS).fillna(0.0).values
        dq = (co <= 0) & (bal > 0) & (dpd >= 30)               # delinquent = state in D1M..D4M
        for i, lid in enumerate(ids):
            if dq[i]:
                mask[lid] = mask.get(lid, 0) | (1 << bitpos)
    n_dq = sum(1 for m in mask.values() if m)
    print(f"  dq6 history: {nf} pre-snapshot tape(s); {n_dq} loans with prior-6mo delinquency")
    return {lid: (m, _dq6_bucket(m)) for lid, m in mask.items()}


def build_tape(snapshot_csv, issuer, shelf, as_of):
    df = pd.read_csv(snapshot_csv, dtype=str, low_memory=False)
    df["issuer"] = issuer
    df["shelf"] = shelf
    od = pd.to_datetime(df["originationdate"], format="%m/%Y", errors="coerce")
    df["vint_yr"] = od.dt.year

    lookups = _build_lookups(shelf)
    feats = P.add_static_features(df, lookups, C)      # ofico, pti, note_rate, rel_rate, ltv, pmt_cpi,
                                                        # platform_f, vehtype_f, term_bkt, fico_bkt,
                                                        # _coupon_at_vintage, lending_environment, veh_age
    bal = io.num(df["reportingperiodactualendbalanceamount"], C.NULL_TOKENS).fillna(0.0)
    dpd = io.num(df["currentdelinquencystatus"], C.NULL_TOKENS).fillna(0.0)
    co  = io.num(df["chargedoffprincipalamount"], C.NULL_TOKENS).fillna(0.0)
    asof_dt = pd.Timestamp(as_of)
    loan_age = ((asof_dt.year - od.dt.year) * 12 + (asof_dt.month - od.dt.month)).fillna(0)
    ipt = pd.to_datetime(df["interestpaidthroughdate"].astype(str).str.strip(), errors="coerce")
    # payment day-of-month = interestPaidThroughDate's day (training's days_to_month_end
    # source). Missing before a loan's first reported payment — fill with the deal
    # median rather than a flat 15.
    pmt_day = ipt.dt.day
    pmt_day = pmt_day.fillna(int(pmt_day.median()) if pmt_day.notna().any() else 15).astype(int)

    # vectorized status (auto Markov rule)
    status = np.select(
        [co > 0, bal <= 0, dpd < 30, dpd < 60, dpd < 90, dpd < 120],
        ["LIQ", "PIF", "C", "D1M", "D2M", "D3M"], default="D4M")

    # new/used flag (Reg AB II: 1=New, 2=Used)
    newused_f = df["vehiclenewusedcode"].astype(str).str.strip().map({"1": "New", "2": "Used"}).fillna("Used")

    # path-dependent history seed: trailing-6-month delinquency mask (dq6_bkt) from
    # pre-snapshot tapes. _dq6_mask is the 6-bit rolling window the sim advances each
    # period; dq6_bkt is the initial bucket used to score period 0.
    hist = _delinquency_history(snapshot_csv, as_of)
    lid = df["assetnumber"].astype(str)
    dq6_mask = lid.map(lambda x: hist.get(x, (0, "0"))[0]).astype(int)
    dq6_bkt = lid.map(lambda x: hist.get(x, (0, "0"))[1])

    out = pd.DataFrame({
        "loan_id":   df["assetnumber"].astype(str),
        "status":    status,
        "end_bal":   bal,
        "orig_bal":  io.num(df["originalloanamount"], C.NULL_TOKENS),
        # `term` = REMAINING term (drives amortization: current balance amortizes
        # over the months left, not the original term). `orig_term` = ORIGINAL term
        # (drives c_age_pct = loan_age/orig_term and term_bkt). Splitting these fixes
        # the seasoned-deal under-amortization without changing any model covariate.
        "orig_term": io.num(df["originalloanterm"], C.NULL_TOKENS).round().astype("Int64"),
        "term":      (io.num(df["originalloanterm"], C.NULL_TOKENS).round()
                      - loan_age.round()).clip(lower=1).astype("Int64"),
        "loan_age":  loan_age.round().astype("Int64"),
        "note_rate": feats["note_rate"], "int_rate": feats["note_rate"],
        "r_dt":      asof_dt.strftime("%Y-%m-%d"),
        "orig_dt":   od.dt.strftime("%Y-%m-%d"),
        "f_pmt_dt":  ipt.dt.strftime("%Y-%m-%d"), "pmt_day": pmt_day,
        "platform_f": feats["platform_f"], "vehtype_f": feats["vehtype_f"],
        "term_bkt":  feats["term_bkt"],    "fico_bkt": feats["fico_bkt"],
        "ofico":     feats["ofico"], "pti": feats["pti"], "rel_rate": feats["rel_rate"],
        "ltv":       feats["ltv"],   "pmt_cpi": feats["pmt_cpi"], "veh_age": feats["veh_age"],
        "lending_environment": feats["lending_environment"],
        "_coupon_at_vintage":  feats["_coupon_at_vintage"],
        "vehiclevalueamount":  io.num(df["vehiclevalueamount"], C.NULL_TOKENS),
        "newused_f":           newused_f,
        "dq6_bkt":             dq6_bkt,
        "_dq6_mask":           dq6_mask,
    })
    # Guard LTV against inf (vehicle value 0 -> balance/0). No v_flag on ltv, so
    # cap at the pool max (Smooth1D clamps to its knot range anyway) rather than
    # null it — and inf would also break the C++ JSON reader.
    _ltv = pd.to_numeric(out["ltv"], errors="coerce")
    _mx = _ltv[np.isfinite(_ltv)].max()
    out["ltv"] = _ltv.where(np.isfinite(_ltv), _mx)

    out = out[(bal > 0) | (co > 0)].reset_index(drop=True)        # drop already-paid-off
    out = out.replace([np.inf, -np.inf], np.nan)                 # no inf literals in JSON
    out = out.astype(object).where(pd.notna(out), None)          # NaN -> None for JSON
    return out.to_dict("records")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/auto_prime.json")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--issuer", default="Carvana")
    ap.add_argument("--shelf", default="Prime")
    ap.add_argument("--deal-name", default=None, help="Override deal_name from config (output dir)")
    ap.add_argument("--as-of", default=None, help="snapshot date YYYY-MM-DD (default: parse from filename)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.deal_name:
        cfg["deal_name"] = args.deal_name
    coef_dir = os.path.join(cfg.get("input_dir", "input"), "coef", cfg.get("coef_version"))
    as_of = args.as_of or args.snapshot.rsplit("_", 1)[-1].replace(".csv", "")

    print(f"Building tape from {os.path.basename(args.snapshot)} (as_of={as_of}) ...")
    raw = build_tape(args.snapshot, args.issuer, args.shelf, as_of)
    print(f"  {len(raw)} active loans")
    st_counts = pd.Series([l["status"] for l in raw]).value_counts().to_dict()
    print(f"  status: {st_counts}")

    loans = prepare_loans(raw, cfg, coef_dir=coef_dir)
    out = os.path.join(cfg.get("input_dir", "input"), "deals", cfg["deal_name"], "loans_prepped.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    save_prepped_loans(loans, out, save_tsv=True)
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
