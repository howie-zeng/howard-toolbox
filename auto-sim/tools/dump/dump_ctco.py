"""Dump ONLY the ctco (C->LIQ direct charge-off) bundle and APPEND its LIQ rows to
the existing PRIME_BASE/fromC.txt -- without re-dumping ctd1/ctp (so the ctd1 aging
flatten already applied to fromC.txt is preserved). Idempotent: strips any existing
model==LIQ rows from fromC.txt before appending. ctco has no stacked layer, so BASE
and STACKED are identical -- we write into PRIME_BASE (and PRIME_STACKED if present).

Usage: python tools/dump/dump_ctco.py [config/auto_prime.json]
"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "python"))
import pandas as pd
from simengine import load_config
from simengine.gam_dump import dump_gam_models

CONFIG = sys.argv[1] if len(sys.argv) > 1 else "config/auto_prime.json"
CTCO_PATH = "from0/models/ctco_bam.rds"
TMP = "input/coef/_ctco_tmp"

def split_interactions(df):
    factors = set(df["var_name1"].dropna().unique())
    for i, r in df.iterrows():
        v1 = str(r["var_val1"])
        if ":" in v1 and str(r.get("var_name2", "")) in ("", "nan", "None"):
            lvl1, rest = v1.split(":", 1)
            cands = [f for f in factors if rest.startswith(f)]
            f2 = max(cands, key=len) if cands else None
            if f2:
                df.at[i, "var_val1"] = lvl1
                df.at[i, "var_name2"] = f2
                df.at[i, "var_val2"] = rest[len(f2):]
    return df

def main():
    cfg = load_config(CONFIG)
    prefix = cfg.get("coef_prefix") or "MODEL"
    os.makedirs(TMP, exist_ok=True)
    mini = {**cfg, "gam_models": [{
        "from_status": "C", "output_file": "fromC_ctco.txt",
        "models": [{"path": CTCO_PATH, "to_status": "LIQ"}],
    }]}
    dump_gam_models(mini, output_dir=TMP)
    ctco = pd.read_csv(os.path.join(TMP, "fromC_ctco.txt"), sep="\t", dtype=str)
    ctco = split_interactions(ctco)
    assert (ctco["model"] == "LIQ").all(), "ctco dump should be all model==LIQ"
    print(f"ctco dump: {len(ctco)} LIQ rows")

    targets = [f"input/coef/{prefix}_BASE/fromC.txt"]
    st = f"input/coef/{prefix}_STACKED/fromC.txt"
    if os.path.isfile(st):
        targets.append(st)
    for tgt in targets:
        base = pd.read_csv(tgt, sep="\t", dtype=str)
        n_old = (base["model"] == "LIQ").sum()
        base = base[base["model"] != "LIQ"]          # idempotent
        out = pd.concat([base, ctco], ignore_index=True)
        out.to_csv(tgt, sep="\t", index=False)
        print(f"  {tgt}: removed {n_old} old LIQ rows, appended {len(ctco)} -> {len(out)} total")
    # cleanup temp
    for f in glob.glob(os.path.join(TMP, "*")):
        os.remove(f)
    os.rmdir(TMP)
    print("done. Remember: add 'LIQ' to status_to_roll['C'] in the config.")

if __name__ == "__main__":
    main()
