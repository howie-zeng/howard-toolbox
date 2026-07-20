#!/usr/bin/env python
"""Regenerate the canonical FICO_BKT_COUPON vintage lookup the *auto way*.

`processing.fico_bkt_coupon` = mean note_rate by (vintage month, FICO bucket) over
the de-duplicated origination snapshot (one row/loan, all Prime issuers) — the
market-coupon reference for both rel_rate and the rate_incentive_ALL macro.

Contamination gotcha: prep_transition.build_training_sets computes it per from-state
and overwrites LOOKUPS_DIR/<shelf>/FICO_BKT_COUPON.csv every run, so the persisted
file reflects whichever state ran last (e.g. high-rate S120), inflating coupons
~20-70%. The from0 models (ctd1/ctp) trained on current-population coupon, so the
sim must use that. This tool rebuilds over the origination snapshot (matching from0)
and writes input/macro/FICO_BKT_COUPON.csv, feeding both auto_tape's rel_rate and
the sim's rate_incentive_ALL macro.

    python tools/lookups/build_coupon_lookup.py [--shelf Prime]
"""
import argparse
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, "S:/QR/jli/Auto")
import config as C                                  # noqa: E402
from lib.prep_data import processing as P           # noqa: E402

COLS = ["originalinterestratepercentage", "obligorcreditscore",
        "originationdate", "deal", "assetnumber"]


def build(shelf: str, out_path: str) -> None:
    slug = shelf.replace(" ", "_")
    panels = glob.glob(os.path.join(C.PANEL_DIR, slug, "*_panel.parquet"))
    if not panels:
        raise SystemExit(f"no per-deal panels under {C.PANEL_DIR}/{slug}")
    print(f"[{shelf}] {len(panels)} per-deal panels", flush=True)

    parts = []
    for f in panels:
        d = pd.read_parquet(f, columns=COLS)
        parts.append(d.drop_duplicates(["deal", "assetnumber"]))
    orig = (pd.concat(parts, ignore_index=True)
              .drop_duplicates(["deal", "assetnumber"]))
    print(f"  origination snapshot: {len(orig):,} unique loans", flush=True)

    bkt = P.fico_bkt_coupon(orig, C)                # {(moyy, fico_bkt): coupon}
    out = (pd.DataFrame([{"vint_moyy": k[0], "fico_bkt": k[1],
                          "fico_bkt_coupon": v} for k, v in bkt.items()])
             .sort_values(["vint_moyy", "fico_bkt"]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"  wrote {out_path}  ({len(out):,} (moyy x bkt) cells)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shelf", default="Prime")
    ap.add_argument("--out", default="input/macro/FICO_BKT_COUPON.csv")
    args = ap.parse_args()
    build(args.shelf, args.out)


if __name__ == "__main__":
    main()
