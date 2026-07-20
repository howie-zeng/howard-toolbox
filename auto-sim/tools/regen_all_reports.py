"""Regenerate every deal HTML report (all scenarios, all shelves) from existing
sim_results.

For each deal with a sim_results.xlsx, computes the realized-tape overlay ONCE and
renders every available scenario against it. Deal -> (platform, shelf, config) is
derived from the deal-name prefix; scenarios are discovered from disk (not a fixed
list), so prime BASE/HISTORY/STACKED and subprime BASE all regenerate.

Usage:
    python tools/regen_all_reports.py            # every deal
    python tools/regen_all_reports.py CMAX_2022_1 EART_2023_1   # a subset
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "python"))

import generate_deal_report  # noqa: E402
from deal_meta import resolve  # noqa: E402 — shared deal -> tape/config mapping

OUTPUT_ROOT = os.path.join(HERE, "..", "output")


def _resolve(deal: str):
    """Return (tape_dir, config_path) for a deal, or (None, None) if unmapped."""
    meta = resolve(deal)
    return (meta["tape_dir"], meta["config"]) if meta else (None, None)


def _scenarios(deal: str) -> list[str]:
    ddir = os.path.join(OUTPUT_ROOT, deal)
    return sorted(s for s in os.listdir(ddir)
                  if os.path.isfile(os.path.join(ddir, s, "sim_results.xlsx")))


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    want = set(argv)
    deals = [d for d in sorted(os.listdir(OUTPUT_ROOT))
             if os.path.isdir(os.path.join(OUTPUT_ROOT, d)) and not d.startswith("_")
             and (not want or d in want)]
    deals = [d for d in deals if _scenarios(d)]
    print(f"Regenerating {len(deals)} deals\n", flush=True)
    t0 = time.time()
    rc = 0
    for i, deal in enumerate(deals, 1):
        scens = _scenarios(deal)
        td, cfg = _resolve(deal)
        print(f"[{i}/{len(deals)}] {deal}  scenarios={scens}  cfg={cfg}", flush=True)
        if td is None:
            print(f"    SKIP — unmapped prefix", flush=True); rc = 1; continue
        if not os.path.isdir(td):
            print(f"    SKIP — tape dir missing: {td}", flush=True); rc = 1; continue
        try:
            # Realized overlay computed once, shared across the deal's scenarios.
            rc |= generate_deal_report.main(
                ["--deal", deal, "--scenario", *scens, "--tape-dir", td, "--config", cfg])
        except Exception as e:  # noqa: BLE001 — keep going through the batch
            print(f"    ERROR: {e}", flush=True); rc = 1
    print(f"\nDone in {time.time() - t0:.0f}s  (rc={rc})", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
