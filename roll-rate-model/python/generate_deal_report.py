"""CLI: generate a deal HTML report from sim_results.xlsx.

Examples::

    python python/generate_deal_report.py --deal par_2026_1
    python python/generate_deal_report.py --deal par_2026_1 --scenario dialed
"""
from __future__ import annotations

import argparse
import sys

from deal_report import build_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_deal_report",
        description="Generate a deal HTML report from sim_results.xlsx.",
    )
    parser.add_argument("--deal", required=True,
                        help="Deal name (subfolder under output/).")
    parser.add_argument("--scenario", default="base",
                        help="Scenario subfolder name. Default: base.")
    args = parser.parse_args(argv)

    try:
        _, out_path = build_html(args.deal, args.scenario)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path}  ({size_kb:,.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
