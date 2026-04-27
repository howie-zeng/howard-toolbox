"""
Update all macro flat files for the simulation engine.

  1. CPIAUCNS.csv      — CPI index from FRED (no API key required)
  2. FICO_BKT_COUPON.csv — cross-platform FICO bucket coupon averages
                           (calls R script: tools/export_macro_lookups.R)

Usage:
    python input/macro/update_macro.py            # update all
    python input/macro/update_macro.py --cpi      # CPI only
    python input/macro/update_macro.py --fico     # FICO coupon only
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

CPI_SERIES = "CPIAUCNS"
CPI_PATH = os.path.join(SCRIPT_DIR, f"{CPI_SERIES}.csv")
FICO_PATH = os.path.join(SCRIPT_DIR, "FICO_BKT_COUPON.csv")
R_EXPORT_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "export_macro_lookups.R")


# ===================================================================
# 1. CPI — download from FRED
# ===================================================================

def fetch_fred_csv(series_id):
    """Download CSV from FRED and return rows as list of (date_str, value)."""
    import requests

    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd=1913-01-01&coed=9999-12-31"
    )
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    rows = []
    for line in csv.reader(resp.text.strip().splitlines()):
        if line[0] in ("DATE", "observation_date"):
            continue
        date_str, val = line[0], line[1]
        if val in (".", ""):
            continue
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        rows.append((f"{dt.month}/{dt.day}/{dt.year}", float(val)))
    return rows


def update_cpi():
    """Fetch CPIAUCNS from FRED and write to CSV."""
    print("=" * 60)
    print("  Updating CPI (CPIAUCNS)")
    print("=" * 60)

    existing_rows = 0
    last_date = None
    if os.path.exists(CPI_PATH):
        with open(CPI_PATH, "r") as f:
            lines = f.read().strip().splitlines()
            existing_rows = len(lines) - 1
            if existing_rows > 0:
                last_date = lines[-1].split(",")[0]

    print(f"Fetching {CPI_SERIES} from FRED...")
    rows = fetch_fred_csv(CPI_SERIES)
    print(f"  Downloaded: {len(rows)} observations")
    print(f"  Range: {rows[0][0]} -> {rows[-1][0]}")
    print(f"  Existing file: {existing_rows} observations (last: {last_date})")

    with open(CPI_PATH, "w", newline="") as f:
        f.write("DATE,CPIAUCNS\n")
        for date_str, val in rows:
            f.write(f"{date_str},{val}\n")

    diff = len(rows) - existing_rows
    if diff > 0:
        print(f"  Added {diff} new observation(s)")
    elif diff == 0:
        print(f"  No new observations (already up to date)")
    else:
        print(f"  Warning: new file has {abs(diff)} fewer rows than before")

    print(f"  Saved: {CPI_PATH}")
    print()


# ===================================================================
# 2. FICO bucket coupon — calls R export script
# ===================================================================

def update_fico_coupon():
    """Run the R export script to generate FICO_BKT_COUPON.csv."""
    print("=" * 60)
    print("  Updating FICO bucket coupon (FICO_BKT_COUPON.csv)")
    print("=" * 60)

    if not os.path.isfile(R_EXPORT_SCRIPT):
        print(f"  ERROR: R script not found: {R_EXPORT_SCRIPT}")
        print(f"  Run manually: Rscript tools/export_macro_lookups.R input/macro")
        return False

    cmd = ["Rscript", R_EXPORT_SCRIPT, SCRIPT_DIR]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    print(result.stdout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr}")
        print(f"  ERROR: R script failed (exit code {result.returncode})")
        return False

    if os.path.isfile(FICO_PATH):
        with open(FICO_PATH) as f:
            n = sum(1 for _ in f) - 1
        print(f"  Saved: {FICO_PATH} ({n} rows)")
    print()
    return True


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Update all macro flat files")
    parser.add_argument("--cpi", action="store_true", help="Update CPI only")
    parser.add_argument("--fico", action="store_true", help="Update FICO coupon only")
    args = parser.parse_args()

    run_all = not args.cpi and not args.fico

    if run_all or args.cpi:
        update_cpi()

    if run_all or args.fico:
        update_fico_coupon()

    # Summary
    print("=" * 60)
    print("  Macro files in:", SCRIPT_DIR)
    print("=" * 60)
    for fname in sorted(os.listdir(SCRIPT_DIR)):
        if fname.endswith(".csv"):
            size = os.path.getsize(os.path.join(SCRIPT_DIR, fname))
            print(f"  {fname}  ({size:,} bytes)")
    print()


if __name__ == "__main__":
    main()
