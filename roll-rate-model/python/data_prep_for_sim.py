#!/usr/bin/env python
"""Data preparation for simulation.

1. Print transition / payment matrices
2. Dump R GAM models -> coef .txt files + PDF report
3. Prep raw loans -> sim-ready JSON

Usage:
    python data_prep_for_sim.py --config config/default.json
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "python")
from simengine import (
    load_config, load_loans, prepare_loans, save_prepped_loans,
    init_data_manager, print_model_matrix,
    dump_gam_models,
)
from simengine.model_report import generate_model_report_html


def main():
    parser = argparse.ArgumentParser(description="Data preparation for simulation")
    parser.add_argument("--config", default="config/default.json")
    parser.add_argument("--deal-name", type=str, default=None, help="Override deal_name")
    parser.add_argument("--coef-version", type=str, default=None, help="Override coef_version")
    parser.add_argument("--skip-dump", action="store_true", help="Skip R model dump")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.deal_name:
        config["deal_name"] = args.deal_name
    if args.coef_version:
        config["coef_version"] = args.coef_version
    input_dir = config.get("input_dir", "input")
    coef_version = config.get("coef_version", "")
    coef_dir = os.path.join(input_dir, "coef", coef_version) if coef_version else os.path.join(input_dir, "coef")

    # ── Matrices ────────────────────────────────────────────────
    dm = init_data_manager(input_dir, config=config)
    print_model_matrix(dm)
    print()

    # ── Model dump ──────────────────────────────────────────────
    if not args.skip_dump:
        print(f"Dumping GAM models -> {coef_dir}")
        print(f"  Model base: {config.get('model_base', '(not set)')}")
        dump_gam_models(config)
    else:
        print("Skipping model dump (--skip-dump)")

    print()
    print("Dumped files:")
    for f in sorted(os.listdir(coef_dir)):
        if f.endswith(".txt"):
            size = os.path.getsize(os.path.join(coef_dir, f))
            print(f"  {f}  ({size:,} bytes)")

    print()
    generate_model_report_html(coef_dir, config)

    # ── Loan prep ───────────────────────────────────────────────
    deal_name = config.get("deal_name", "default")
    deal_dir = os.path.join(config.get("input_dir", "input"), "deals", deal_name)
    os.makedirs(deal_dir, exist_ok=True)

    loans_path = config.get("loans_path", None)
    if not loans_path:
        csvs = sorted(f for f in os.listdir(deal_dir) if f.lower().endswith(".csv"))
        if not csvs:
            raise FileNotFoundError(f"No CSV files found in {deal_dir}")
        loans_path = os.path.join(deal_dir, csvs[0])
        print(f"  Auto-detected loan file: {csvs[0]}")
        if len(csvs) > 1:
            print(f"  (also found: {', '.join(csvs[1:])})")

    output_path = config.get("prepped_loans_path", os.path.join(deal_dir, "loans_prepped.json"))

    print()
    print(f"Prepping loans: {loans_path} -> {output_path}")
    raw_loans = load_loans(loans_path)
    print(f"  Loaded {len(raw_loans)} raw loans")

    loans = prepare_loans(raw_loans, config, coef_dir=coef_dir)
    print(f"  Prepared {len(loans)} loans")

    if raw_loans and loans:
        added = sorted(set(loans[0].keys()) - set(raw_loans[0].keys()))
        if added:
            print(f"  Fields added ({len(added)}):")
            for f in added:
                print(f"    {f}")

    save_prepped_loans(loans, output_path, save_tsv=True)
    print(f"  Saved to {output_path}")

    # ── Macro scenario ─────────────────────────────────────────
    macro_cfg = config.get("macro", {})
    active = [k for k, v in macro_cfg.items() if isinstance(v, dict) and v.get("mode") == "custom"]
    if active:
        print(f"\n  Macro (custom): {', '.join(active)}")
        for var in active:
            p = macro_cfg[var].get("path", "")
            exists = os.path.isfile(p) if p else False
            print(f"    {var}: {p} {'[OK]' if exists else '[NOT FOUND]'}")
    else:
        print(f"\n  Macro: default (flat)")

    print()
    print("Done.")


if __name__ == "__main__":
    main()