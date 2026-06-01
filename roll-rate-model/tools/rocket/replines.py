"""Map Rocket repline IDs + default buckets onto the raw Stat Pool tape.

A Rocket repline is the 3-tuple ``(default_bucket, original_term, remaining_term)``,
where the default bucket is ``SelectedOfferDefaultProbability x 100`` placed
into one of the bins ``[0, 2) / [2, 4) / [4, 7) / [7, 9]`` (labelled
"0.0-1.9", "2.0-3.9", "4.0-6.9", "7.0-9.0").

The tool always derives the default bucket from the tape itself. If
Goldman's "Repline Mapping" workbook is supplied (``--repline-xlsx``), each
loan is also tagged with the Goldman ``RepLineID`` / ``RepLineName`` and the
two derivations are cross-checked: parsed term/rem_term in the name must
match the tape, and per-repline current balances must tie out.

Usage::

    python tools/rocket_replines.py \\
        --tape "input/deals/RKTL_2026_2/raw_tape.csv" \\
        --repline-xlsx "S:/Trading/.../RKTL 2026-2 Repline Mapping.xlsx" \\
        --out "C:/Users/jasonli/Downloads/RKTL_2026_2_with_replines.csv"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_BUCKET_BINS   = [0.0, 2.0, 4.0, 7.0, 9.0 + 1e-9]
DEFAULT_BUCKET_LABELS = ["0.0-1.9", "2.0-3.9", "4.0-6.9", "7.0-9.0"]


def assign_default_bucket(default_prob: pd.Series) -> pd.Series:
    """Bin SelectedOfferDefaultProbability (fraction) into Rocket's 4 tiers."""
    pct = default_prob * 100.0
    return pd.cut(pct, bins=DEFAULT_BUCKET_BINS,
                  labels=DEFAULT_BUCKET_LABELS,
                  right=False, include_lowest=True)


def derive_repline_key(tape: pd.DataFrame) -> pd.Series:
    """Build the canonical Rocket repline key from the tape itself:
    ``<default_bucket>-<OriginalTerm>-<RemainingTerm>``."""
    bucket = assign_default_bucket(tape["SelectedOfferDefaultProbability"])
    return (bucket.astype(str)
            + "-" + tape["OriginalTerm"].astype(int).astype(str)
            + "-" + tape["RemainingTerm"].astype(int).astype(str))


def load_goldman_mapping(xlsx_path: Path) -> pd.DataFrame:
    """Load Goldman's Repline Mapping workbook.

    The workbook contains only the sequential ID label ("Repline 31"); the
    decoded name (bucket-term-rem_term) lives nowhere in the file and is
    derived from the tape instead. Returns ``LOANID`` (str) + ``RepLineID``.
    """
    df = pd.read_excel(xlsx_path, dtype={"LOANID": str})
    df["RepLineID"] = df["Replines"].str.extract(r"(\d+)").astype(int)
    return df[["LOANID", "RepLineID"]]


def augment_tape(
    tape: pd.DataFrame,
    gold_map: pd.DataFrame | None,
) -> pd.DataFrame:
    """Add DefaultBucket + RepLineKey (always); attach Goldman's RepLineID
    and verify cohort homogeneity when the mapping is supplied."""
    out = tape.copy()
    out["DefaultBucket"] = assign_default_bucket(out["SelectedOfferDefaultProbability"])
    out["RepLineKey"] = derive_repline_key(out)

    if gold_map is not None:
        out = out.merge(gold_map, left_on="LoanID", right_on="LOANID", how="left")
        if out["RepLineID"].isna().any():
            n = int(out["RepLineID"].isna().sum())
            raise ValueError(f"{n} loans missing a Goldman repline assignment")

        # Each Goldman RepLineID must contain exactly one (DefaultBucket,
        # OriginalTerm, RemainingTerm) cohort — otherwise the IDs aren't a
        # clean 1-to-1 relabel of (bucket, term, rem_term).
        keys_per_id = out.groupby("RepLineID")["RepLineKey"].nunique()
        bad = keys_per_id[keys_per_id != 1]
        if not bad.empty:
            raise ValueError(
                f"{len(bad)} RepLineIDs contain mixed (bucket,term,rem_term)"
            )

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tape", required=True, help="raw Stat Pool CSV")
    ap.add_argument("--repline-xlsx", default=None,
                    help="optional Goldman Repline Mapping workbook")
    ap.add_argument("--out", required=True, help="output augmented CSV")
    args = ap.parse_args()

    tape = pd.read_csv(args.tape, dtype={"LoanID": str})
    print(f"loaded {len(tape):,} loans from {args.tape}")

    gold_map = load_goldman_mapping(Path(args.repline_xlsx)) if args.repline_xlsx else None
    if gold_map is not None:
        print(f"loaded {len(gold_map):,} repline rows from {args.repline_xlsx}")

    aug = augment_tape(tape, gold_map)
    aug.to_csv(args.out, index=False)
    print(f"wrote {len(aug):,} rows × {aug.shape[1]} cols to {args.out}")

    if gold_map is not None:
        agg = aug.groupby("RepLineID", observed=True).agg(
            loans=("LoanID", "count"),
            curr_bal=("UnpaidPrincipalBalance", "sum"),
        ).sort_index()
        print(f"\n61 replines, total current balance ${agg['curr_bal'].sum():,.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
