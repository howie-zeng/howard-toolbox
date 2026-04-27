#!/usr/bin/env python
"""Generate a universal calendar-indexed macro table from CPI data.

Reads:  input/macro/CPIAUCNS.csv
Writes: input/macro/cpi_table.csv

The output CSV is date-indexed (YYYY-MM) and covers 2000-01 through
the last available CPI month + 120 months of padding (frozen at last
known value). It is reusable across all deals — the sim looks up by
r_dt YYYY-MM each period.

Usage:
    python tools/generate_macro_table.py [--input input/macro/CPIAUCNS.csv] [--output input/macro/cpi_table.csv]
"""
import argparse
import csv
import os


def parse_cpi_date(date_str: str) -> str:
    """Convert CPI date formats to YYYY-MM. Handles 'M/D/YYYY' and 'YYYY-MM-DD'."""
    date_str = date_str.strip()
    if "/" in date_str:
        parts = date_str.split("/")
        return f"{parts[2]}-{int(parts[0]):02d}"
    return date_str[:7]


def ym_offset(ym: str, months: int) -> str:
    """Shift a YYYY-MM key by N months."""
    y, m = int(ym[:4]), int(ym[5:7])
    total = y * 12 + (m - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def load_cpi(path: str) -> dict:
    """Load CPI CSV -> {YYYY-MM: float}."""
    lookup = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            ym = parse_cpi_date(row["DATE"])
            lookup[ym] = float(row["CPIAUCNS"])
    return lookup


def main():
    parser = argparse.ArgumentParser(description="Generate universal macro table from CPI data")
    parser.add_argument("--input", default="input/macro/CPIAUCNS.csv", help="CPI source CSV")
    parser.add_argument("--output", default="input/macro/cpi_table.csv", help="Output macro table")
    parser.add_argument("--start", default="2000-01", help="Start YYYY-MM (default: 2000-01)")
    parser.add_argument("--pad", type=int, default=120, help="Months of padding after last CPI month")
    args = parser.parse_args()

    print(f"Loading CPI: {args.input}")
    cpi = load_cpi(args.input)
    print(f"  {len(cpi)} months loaded")

    # Find last available CPI month
    all_months = sorted(cpi.keys())
    last_cpi_ym = all_months[-1]
    print(f"  CPI range: {all_months[0]} to {last_cpi_ym}")

    # Compute total months from start through last_cpi + pad
    start_y, start_m = int(args.start[:4]), int(args.start[5:7])
    end_ym = ym_offset(last_cpi_ym, args.pad)
    end_y, end_m = int(end_ym[:4]), int(end_ym[5:7])
    n_months = (end_y * 12 + end_m) - (start_y * 12 + start_m)

    print(f"  Generating: {args.start} to {end_ym} ({n_months} months)")

    last_36 = None
    last_12 = None
    rows = []

    for p in range(n_months):
        ym = ym_offset(args.start, p)
        cpi_now = cpi.get(ym)

        if cpi_now:
            cpi_36 = cpi.get(ym_offset(ym, -36))
            if cpi_36 and cpi_36 > 0:
                last_36 = round(cpi_now / cpi_36 - 1, 6)

            cpi_12 = cpi.get(ym_offset(ym, -12))
            if cpi_12 and cpi_12 > 0:
                last_12 = round(cpi_now / cpi_12 - 1, 6)

        rows.append({
            "date": ym,
            "cpi_inflator_36": last_36 if last_36 is not None else "",
            "cpi_inflator_12": last_12 if last_12 is not None else "",
        })

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "cpi_inflator_36", "cpi_inflator_12"])
        writer.writeheader()
        writer.writerows(rows)

    # Find where freeze starts (first month after last CPI data)
    frozen_at = ym_offset(last_cpi_ym, 1)

    # Summary
    non_empty = [r for r in rows if r["cpi_inflator_36"] != ""]
    if non_empty:
        print(f"\n  cpi_inflator_36: {non_empty[0]['cpi_inflator_36']} -> {non_empty[-1]['cpi_inflator_36']}")
        print(f"  cpi_inflator_12: {non_empty[0]['cpi_inflator_12']} -> {non_empty[-1]['cpi_inflator_12']}")
    if frozen_at:
        print(f"  Frozen from: {frozen_at} (last CPI month: {last_cpi_ym})")
    print(f"\n  Wrote: {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
