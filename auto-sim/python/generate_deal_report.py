"""CLI: generate a deal HTML report from sim_results.xlsx.

Examples::

    # one scenario, no backtest overlay
    python python/generate_deal_report.py --deal par_2026_1 --scenario base

    # both scenarios, with the realized-tape overlay computed ONCE in memory
    # (no actuals_*.csv written to disk):
    python python/generate_deal_report.py --deal CRVNA_2022_P1 \
        --scenario PRIME_BASE PRIME_STACKED \
        --tape-dir "N:/FlatFilesMonthly/Auto/Carvana/Prime/CRVNA 2022-P1"
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pandas as pd

import realized
import onestep as onestep_mod
from deal_report import build_html
from deal_report.loader import model_root
from simengine import load_config


def _newest_mtime(paths) -> float:
    mts = [os.path.getmtime(p) for p in paths if os.path.exists(p)]
    return max(mts) if mts else 0.0


def _cached_onestep(cfg, prepped, tape_dir, snap, horizon, panel, out_dir, coef_dir):
    """Rolling-forecast output cache: it's fully determined by the realized tapes,
    the coef version, AND the prepped tape (start pool + as-of anchor), so store the
    ~48-row result at output/<deal>/<scenario>/rolling_forecast.parquet and reuse it
    unless a tape, coef, or the prepped tape is newer (freshly-dumped data/model or a
    re-prep from a different snapshot -> recompute). ~16s -> ~0s on a hit.

    NOTE: prepped MUST be in the key — re-prepping from a different start tape (e.g.
    EART_2022_1 2022-01-31 -> 2022-02-28) changes the RF anchor/horizon; without it
    the stale RF is one period off vs the realigned realized/projected curves."""
    cache = out_dir / "rolling_forecast.parquet"
    newest = max(_newest_mtime(glob.glob(os.path.join(tape_dir, "*.csv"))),
                 _newest_mtime(glob.glob(os.path.join(coef_dir, "**", "*.txt"), recursive=True)),
                 _newest_mtime([prepped]))
    try:
        if cache.is_file() and os.path.getmtime(cache) >= newest:
            return pd.read_parquet(cache)
    except Exception:
        pass
    df = onestep_mod.compute_onestep(cfg, prepped, tape_dir, snap, horizon, panel=panel)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache, index=False)
    except Exception:
        pass
    return df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_deal_report",
        description="Generate a deal HTML report from sim_results.xlsx.",
    )
    parser.add_argument("--deal", required=True,
                        help="Deal name (subfolder under output/).")
    parser.add_argument("--scenario", nargs="+", default=["base"],
                        help="One or more scenario subfolder names. Default: base.")
    parser.add_argument("--tape-dir", default=None,
                        help="Monthly-tape directory. If given, the realized "
                             "overlay is computed in memory (once, shared across "
                             "scenarios) and no actuals_*.csv are written.")
    parser.add_argument("--prepped-json", default=None,
                        help="Override the prepped-tape path (CGL/CNL denominator).")
    parser.add_argument("--config", default="config/auto_prime.json",
                        help="Sim config (for the one-step-ahead overlay's model).")
    parser.add_argument("--no-onestep", action="store_true",
                        help="Skip the one-step-ahead transition overlay.")
    args = parser.parse_args(argv)

    # Realized overlay: computed once, in memory, and reused for every scenario.
    actuals = None
    prepped = args.prepped_json or str(
        model_root() / "input" / "deals" / args.deal / "loans_prepped.json")
    snap = horizon = base_config = None
    if args.tape_dir:
        # The projected recovery-lag profile is re-derived from the same shelf lag
        # dist the sim used, so it must come from the config (subprime deals point
        # at recovery_lag_dist_Subprime.tsv) — not compute_realized's Prime default.
        base_config = load_config(args.config)
        lag_dist_path = base_config.get("lag_dist_path",
                                        "input/severity/recovery_lag_dist.tsv")
        actuals = realized.compute_realized(args.tape_dir, prepped,
                                            lag_dist_path=lag_dist_path)
        realized._print_summary(actuals)
        # one-step needs the projection anchor + the realized horizon
        if not args.no_onestep and actuals.get("portfolio") is not None:
            snap = realized._orig_pool_and_asof(prepped)[1]
            horizon = int(actuals["portfolio"]["period"].max())

    rc = 0
    for scenario in args.scenario:
        # one-step is model-specific -> recompute per scenario's coef version.
        onestep_df = None
        if base_config is not None and snap is not None:
            cfg = {**base_config, "deal_name": args.deal, "coef_version": scenario}
            out_dir = model_root() / "output" / args.deal / scenario
            coef_dir = os.path.join(base_config.get("input_dir", "input"), "coef", scenario)
            onestep_df = _cached_onestep(
                cfg, prepped, args.tape_dir, snap, horizon,
                actuals.get("panel"), out_dir, coef_dir)
        try:
            _, out_path = build_html(args.deal, scenario, actuals=actuals,
                                     onestep=onestep_df)
        except FileNotFoundError as e:
            print(f"error ({scenario}): {e}", file=sys.stderr)
            rc = 1
            continue
        size_kb = out_path.stat().st_size / 1024
        print(f"Wrote {out_path}  ({size_kb:,.1f} KB)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
