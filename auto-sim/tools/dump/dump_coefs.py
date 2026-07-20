#!/usr/bin/env python
"""Dump refit auto GAM bundles -> coef TSVs, driven entirely by a sim config.

Single source of truth is ``<config>::gam_models`` (paths relative to
``model_base``). Output dirs are prefixed by ``<config>::coef_prefix`` (e.g.
PRIME, SUBPRIME). When any from-C model carries a ``stacked`` layer the dump
emits two scenarios; otherwise just the base:

  {PREFIX}_STACKED = gam_models as-is (from-C includes its +stacked
                     lending-environment correction layer).
  {PREFIX}_BASE    = identical bundles, stacked layer stripped from from-C.

Re-run after any refit:

    python tools/dump/dump_coefs.py config/auto_prime.json
    python tools/dump/dump_coefs.py config/auto_subprime.json
"""
import argparse
import copy
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "python"))

from simengine import load_config
from simengine.gam_dump import dump_gam_models


def _strip_stacked(gam_models):
    """Return a deep copy with every model's optional 'stacked' layer removed."""
    out = copy.deepcopy(gam_models)
    for entry in out:
        for m in entry["models"]:
            m.pop("stacked", None)
    return out


def _split_interactions(coef_dir):
    """mgcv emits factor:factor interaction coefs as a single smushed level in
    var_val1 (e.g. '2-3:ever_dq_flagprior_dq') with empty var_name2 — which the
    engine's interaction scoring can't see. Split them into var_name1/val1 +
    var_name2/val2 (the 2nd factor's name is a prefix of the ':' remainder)."""
    for path in glob.glob(os.path.join(coef_dir, "from*.txt")):
        df = pd.read_csv(path, sep="\t", dtype=str)
        factors = set(df["var_name1"].dropna().unique())
        changed = unresolved = 0
        for i, r in df.iterrows():
            v1 = str(r["var_val1"])
            if ":" in v1 and str(r.get("var_name2", "")) in ("", "nan", "None"):
                lvl1, rest = v1.split(":", 1)
                # 2nd factor's name prefixes the remainder — take the LONGEST match
                # so nested names (e.g. "ever_dq" vs "ever_dq_flag") resolve to the
                # right factor, mirroring accum_parametrics' longest-first claim.
                cands = [f for f in factors if rest.startswith(f)]
                f2 = max(cands, key=len) if cands else None
                if f2:
                    df.at[i, "var_val1"] = lvl1
                    df.at[i, "var_name2"] = f2
                    df.at[i, "var_val2"] = rest[len(f2):]
                    changed += 1
                else:
                    unresolved += 1
        if changed:
            df.to_csv(path, sep="\t", index=False)
            print(f"    {os.path.basename(path)}: split {changed} factor:factor interaction rows")
        if unresolved:
            print(f"    WARNING: {os.path.basename(path)}: {unresolved} ':' interaction row(s) "
                  f"had no matching 2nd factor — left unsplit (check factor names)")


def _dump(cfg, out_dir):
    dump_gam_models(cfg, output_dir=out_dir)
    _split_interactions(out_dir)


def main(config_path="config/auto_prime.json", only=None):
    cfg = load_config(config_path)
    if not cfg.get("gam_models"):
        raise SystemExit(f"{config_path} has no gam_models block")
    prefix = cfg.get("coef_prefix") or "MODEL"

    # --only <from_status[,...]>: re-dump just those from-status entries into the
    # existing coef dirs, leaving all other from*.txt untouched. Use after a
    # single-model refit (e.g. `--only severity`) to avoid clobbering/flattening.
    if only:
        want = {s.strip() for s in only.split(",")}
        entries = [e for e in cfg["gam_models"] if e["from_status"] in want]
        missing = want - {e["from_status"] for e in entries}
        if missing:
            raise SystemExit(f"--only: no gam_models entry for {sorted(missing)}")
        cfg = {**cfg, "gam_models": entries}

    has_stacked = any("stacked" in m for e in cfg["gam_models"] for m in e["models"])

    if has_stacked:
        print(f"=== {prefix}_STACKED (base + stacked LE layer on from-C) ===")
        _dump(cfg, f"input/coef/{prefix}_STACKED")
        print(f"=== {prefix}_BASE (stacked layer stripped) ===")
        _dump({**cfg, "gam_models": _strip_stacked(cfg["gam_models"])}, f"input/coef/{prefix}_BASE")
    else:
        print(f"=== {prefix}_BASE ===")
        _dump(cfg, f"input/coef/{prefix}_BASE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default="config/auto_prime.json")
    ap.add_argument("--only", default=None,
                    help="comma-separated from_status list to re-dump (e.g. 'severity'); "
                         "others left untouched in the existing coef dirs")
    a = ap.parse_args()
    main(a.config, a.only)
