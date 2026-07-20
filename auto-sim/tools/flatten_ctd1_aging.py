"""Remove the survivorship VALLEY in the ctd1 (C->D1M) c_age_pct aging curve while
preserving the curve's shape.

The fitted s(c_age_pct, by=term_bkt) dips into a valley between ~age_pct 0.7 and ~1.0
(loans that reach high age_pct are seasoned survivors, all current -- a selection
artifact) and then recovers near age_pct 1.0. This fills ONLY that valley: it floors
the curve along the straight line from the pre-dip peak to the post-dip recovery, so
values above the line (the rise, the recovery) are untouched and only the dip is
lifted. The age_pct>1 extrapolation region is left ALONE. Only model==D1M,
var_name1==c_age_pct; ctp (PIF) and everything else untouched. Idempotent; writes a
.orig backup once.

Usage: flatten_ctd1_aging.py <fromC_coef.txt> [model=D1M] [peak_lo=0.5] [peak_hi=0.8] [rec_hi=1.02]
"""
import sys, os, shutil
import pandas as pd

COEF = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "D1M"
VAR = "c_age_pct"
PLO = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
PHI = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
REC_HI = float(sys.argv[5]) if len(sys.argv) > 5 else 1.02   # recovery searched up to here; >1 left alone

df = pd.read_csv(COEF, sep="\t", dtype=str)
if not os.path.exists(COEF + ".orig"):
    shutil.copy(COEF, COEF + ".orig")
    print(f"backup -> {COEF}.orig")

mask = (df["model"] == MODEL) & (df["var_name1"] == VAR)
sub = df[mask].copy()
sub["x"] = sub["var_val1"].astype(float)
sub["v"] = sub["value"].astype(float)
print(f"filling {MODEL} {VAR} survivorship dip (floor valley at min(peak,recovery); peak & recovery kept; age_pct>1 untouched):")
for tb, g in sub.groupby("var_val2"):
    g = g.sort_values("x")
    win = g[(g["x"] >= PLO) & (g["x"] <= PHI)]
    if win.empty:
        continue
    pk = win.loc[win["v"].idxmax()]; pkx, pkv = pk["x"], pk["v"]
    # right anchor = the in-range point nearest age_pct 1.0 (do NOT search for a max,
    # which would grab the peak plateau). Everything past this (age_pct>~1) is untouched.
    inrange = g[(g["x"] > pkx) & (g["x"] <= 1.0)]
    if inrange.empty:
        continue
    rc = inrange.loc[(inrange["x"] - 1.0).abs().idxmin()]; rcx, rcv = rc["x"], rc["v"]
    if rcx <= pkx:
        continue
    # Fill the dip ONLY: floor the valley horizontally at min(peak, recovery), so the
    # peak, its descent, and the recovery ascent are all kept (values above the floor
    # untouched) and only the dip below the floor is raised. Retains the peak as a
    # peak; keeps the recovery even where it exceeds the peak. Nothing rises to reach
    # the peak via a ramp.
    floor = min(pkv, rcv)
    valley = g[(g["x"] > pkx) & (g["x"] < rcx)]
    n_lift = 0; trough = valley["v"].min() if len(valley) else pkv
    for idx, r in valley.iterrows():
        if r["v"] < floor:                                       # only lift the dip below the floor
            df.loc[idx, "value"] = repr(float(floor))
            n_lift += 1
    print(f"  {tb:>6}: peak {pkv:+.3f}@{pkx:.3f}, recovery {rcv:+.3f}@{rcx:.3f}; "
          f"floor dip at {floor:+.3f} ({n_lift} pts lifted; trough was {trough:+.3f})")

df.to_csv(COEF, sep="\t", index=False)
print(f"wrote {COEF}")
