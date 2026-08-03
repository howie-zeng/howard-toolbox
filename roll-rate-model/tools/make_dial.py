"""Compose dial files: multiply a base per-period dial schedule with a custom dial.

Usage:
    python tools/make_dial.py --out PAR_2026_2_FINAL \
        --base CURTAIL_PROSPER \
        --custom PAR_2026_2_FINAL_D1M \
        --deal-name PAR_2026_2

  --base    unsegmented dial file (Status + transition columns, per-period rows),
            e.g. a curtailment PIF schedule. Optional.
  --custom  dial file to multiply with (may be segmented by term/grade). Optional.
  --out     output dial name (written to input/dial/<OUT>.txt).
  --deal-name  enumerate every (term, grade) combo from the deal's prepped JSON so
            the output covers the whole pool. Without it, combos come from the
            custom file (or output is unsegmented).

Each transition-column cell = base[period] * custom[segment][period] (missing -> 1.0).
Terms are written as integers (the engine matches segment keys as raw strings).
"""
import argparse
import json
import os

STATUS_COLS = ["C", "D1M", "D2M", "D3M", "D4M", "PIF", "LIQ"]
N_PER_DEFAULT = 84


def read_dial(path):
    """Parse a dial txt -> {(status, term, grade): [{col: val} x n_per]}.
    term/grade are None for unsegmented files."""
    with open(path) as f:
        lines = [L.rstrip("\n") for L in f if L.strip()]
    header = lines[0].split("\t")
    seg_cols = [c for c in header if c not in ("Status",) and c not in STATUS_COLS]
    col_idx = {c: header.index(c) for c in header}
    blocks = {}
    cur_key = None
    for L in lines[1:]:
        cells = L.split("\t")

        def get(c):
            i = col_idx.get(c)
            return cells[i].strip() if i is not None and i < len(cells) else ""

        if get("Status"):
            term = get("term") if "term" in col_idx else ""
            grade = get("grade") if "grade" in col_idx else ""
            term = int(float(term)) if term else None
            cur_key = (get("Status"), term, grade or None)
            blocks[cur_key] = []
        if cur_key is None:
            continue
        row = {}
        for c in STATUS_COLS:
            v = get(c)
            row[c] = float(v) if v else 1.0
        blocks[cur_key].append(row)
    return blocks, seg_cols


def deal_combos(deal_name):
    path = os.path.join("input", "deals", deal_name, "loans_prepped.json")
    with open(path) as f:
        d = json.load(f)
    loans = d["loans"] if isinstance(d, dict) and "loans" in d else d
    return sorted({(int(L["term"]), L["grade"]) for L in loans})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--custom", default=None)
    ap.add_argument("--deal-name", default=None)
    ap.add_argument("--n-per", type=int, default=N_PER_DEFAULT)
    args = ap.parse_args()
    if not (args.base or args.custom):
        ap.error("need --base and/or --custom")

    def resolve(name):
        p = name if name.endswith(".txt") else os.path.join("input", "dial", name + ".txt")
        if not os.path.isfile(p):
            raise SystemExit(f"dial file not found: {p}")
        return p

    base_blocks = {}
    if args.base:
        base_blocks, base_segs = read_dial(resolve(args.base))
        if any(k[1] is not None for k in base_blocks):
            raise SystemExit("--base must be unsegmented (per-period schedule only)")

    custom_blocks = {}
    if args.custom:
        custom_blocks, _ = read_dial(resolve(args.custom))

    statuses = sorted({k[0] for k in base_blocks} | {k[0] for k in custom_blocks}) or ["C"]

    if args.deal_name:
        combos = deal_combos(args.deal_name)
    else:
        combos = sorted({(k[1], k[2]) for k in custom_blocks if k[1] is not None})
        if not combos:
            combos = [(None, None)]

    def cell(status, term, grade, per, col):
        v = 1.0
        b = base_blocks.get((status, None, None))
        if b:
            v *= b[min(per, len(b) - 1)][col]
        c = custom_blocks.get((status, term, grade)) or custom_blocks.get((status, None, None))
        if c:
            v *= c[min(per, len(c) - 1)][col]
        return v

    out_path = os.path.join("input", "dial", args.out + ".txt")
    segmented = combos != [(None, None)]
    with open(out_path, "w") as f:
        if segmented:
            f.write("Status\tterm\tgrade\t" + "\t".join(STATUS_COLS) + "\n")
        else:
            f.write("Status\t" + "\t".join(STATUS_COLS) + "\n")
        for status in statuses:
            for term, grade in combos:
                for p in range(args.n_per):
                    vals = "\t".join(f"{cell(status, term, grade, p, c):.6g}" for c in STATUS_COLS)
                    if p == 0:
                        lead = f"{status}\t{term}\t{grade}" if segmented else status
                    else:
                        lead = "\t\t" if segmented else ""
                    f.write(f"{lead}\t{vals}\n")
    n_rows = len(statuses) * len(combos) * args.n_per
    print(f"wrote {out_path}: {n_rows} rows ({len(statuses)} status x {len(combos)} segments x {args.n_per} periods)")


if __name__ == "__main__":
    main()
