"""Run the PRIME_STACKED scenario across every deal, SEQUENTIALLY (one deal fully
done — sim then report — before the next). Gentle on the box: no concurrent deals.
Assumes input/coef/PRIME_STACKED is already dumped + flattened.

Usage: python tools/run_stacked_all.py
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)

PLATFORM = {"CMAX": "CarMax", "CRVNA": "Carvana", "HART": "Hyundai", "TAOT": "Toyota"}
PY = "C:/QR/miniconda/envs/pyprod/python.exe"
SIM = os.path.join(ROOT, "build", "sim_main.exe")   # absolute (Windows subprocess needs it)
SCEN = "PRIME_STACKED"


def tape_dir(deal):
    pre, *rest = deal.split("_")
    return f"N:/FlatFilesMonthly/Auto/{PLATFORM[pre]}/Prime/{pre} {'-'.join(rest)}"


def deals():
    out = []
    for d in sorted(os.listdir("output")):
        if os.path.isdir(os.path.join("output", d)) and d.split("_")[0] in PLATFORM \
           and any(os.path.isfile(os.path.join("output", d, s, "sim_results.xlsx"))
                   for s in ("PRIME_BASE", "PRIME_BASE_HISTORY", SCEN)):
            out.append(d)
    return out


def main():
    ds = deals()
    print(f"PRIME_STACKED over {len(ds)} deals (sequential):\n{ds}\n", flush=True)
    t0 = time.time()
    for i, deal in enumerate(ds, 1):
        td = tape_dir(deal)
        xlsx = f"output/{deal}/{SCEN}/sim_results.xlsx"
        print(f"[{i}/{len(ds)}] {deal}", flush=True)
        if not os.path.isdir(td):
            print(f"    SKIP — tape dir missing: {td}", flush=True); continue
        if not os.path.isfile(xlsx):
            print("    running sim...", flush=True)
            subprocess.run([SIM, "--config", "config/auto_prime.json", "--deal-name", deal,
                            "--coef-version", SCEN, "--scen", SCEN, "--workers", "0"],
                           check=False)
        else:
            print("    sim_results present — reusing", flush=True)
        print("    generating report...", flush=True)
        subprocess.run([PY, "python/generate_deal_report.py", "--deal", deal,
                        "--scenario", SCEN, "--tape-dir", td], check=False)
    print(f"\nDone in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
