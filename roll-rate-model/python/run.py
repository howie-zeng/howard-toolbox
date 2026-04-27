#!/usr/bin/env python
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from simengine import (
    load_config, load_loans, run_simulation,
    init_data_manager, print_model_matrix,
)
from simengine.runner import write_results_xlsx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/default.json")
    parser.add_argument("--deal-name", type=str, default=None,
                        help="Override deal_name from config")
    parser.add_argument("--coef-version", type=str, default=None,
                        help="Override coef_version from config")
    parser.add_argument("--output", default=None)
    parser.add_argument("--dup", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--n-per", type=int, default=None)
    parser.add_argument("--group-by", type=str, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--mode", choices=["sequential", "pool", "ray", "auto"],
                        default="auto",
                        help="Execution mode: sequential, pool, ray, or auto (default)")
    parser.add_argument("--scen", type=str, default=None,
                        help="Scenario name (default: 'base')")
    parser.add_argument("--dump", action="store_true", default=False,
                        help="Enable debug dump for first few loans")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.dump and "dump" not in config:
        config["dump"] = {"enabled": True, "max_loans": 10, "max_paths": 10}
    if args.deal_name:
        config["deal_name"] = args.deal_name
    if args.coef_version:
        config["coef_version"] = args.coef_version
    deal_name = config.get("deal_name", "default")
    scenario = args.scen or config.get("scenario", "base")
    input_dir = config.get("input_dir", "input")
    deal_dir = f"{input_dir}/deals/{deal_name}"
    loans_path = config.get("prepped_loans_path", f"{deal_dir}/loans_prepped.json")
    n_per = args.n_per or config.get("n_per", 360)
    dup = args.dup or config.get("dup", 1)
    seed = args.seed or config.get("seed", 42)
    severity = config.get("liq_severity", 1.0)
    default_workers = max(1, (os.cpu_count() or 4) // 2)
    workers = args.workers or config.get("workers", default_workers)
    output_path = args.output or f"output/{deal_name}/{scenario}/sim_results.xlsx"

    if args.group_by:
        group_by = [g.strip() for g in args.group_by.split(",")]
    else:
        group_by = config.get("group_by", ["term", "grade"])

    dm = init_data_manager(input_dir, config=config)
    print_model_matrix(dm)

    print(f"Loading prepped loans from {loans_path}...")
    loans = load_loans(loans_path)
    print(f"  {len(loans)} loans")

    # resolve execution mode
    mode = args.mode
    if mode == "auto":
        n_tasks = len(loans) * dup
        if workers <= 1 or n_tasks < 50_000:  mode = "sequential"
        elif n_tasks < 500_000:               mode = "pool"
        else:                                 mode = "ray"

    label = mode if mode == "sequential" else f"{mode} ({workers} workers)"
    print(f"Running simulation: n_per={n_per}, dup={dup}, seed={seed}, mode={label}, scenario={scenario}")
    if group_by:
        print(f"  Group by: {group_by}")
    t0 = time.time()
    result = run_simulation(
        loans=loans,
        input_dir=input_dir,
        n_per=n_per,
        dup=dup,
        seed0=seed,
        liq_severity=severity,
        config=config,
        workers=workers,
        mode=mode,
    )
    elapsed = time.time() - t0

    n_tasks = len(loans) * dup
    n_loans = len(result["loan_results"])
    print(f"  Done in {elapsed:.2f}s ({n_tasks} tasks, {n_loans} loans, {len(result['errors'])} errors)")

    if result["errors"]:
        print(f"  Errors ({len(result['errors'])} total):")
        for e in result["errors"][:5]:
            print(f"    {e}")

    write_results_xlsx(result, output_path, group_by=group_by)
    print(f"  Output: {output_path}")
    print(f"  Group by: {group_by}")


if __name__ == "__main__":
    main()
