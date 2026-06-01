"""Loan-tape summary statistics — drives the Summary Statistics page.

Reads the raw input CSV (or any DataFrame with equivalent columns), normalises
column names to internal aliases (``balance``, ``term``, ``grade``, ``fico``,
``rate``, ``dti``, ``purpose``), and produces a dict of breakdown DataFrames
ready for HTML rendering.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .aggregation import wavg
from .grade_sort import sort_grades
from .theme import (
    FICO_BUCKET_BINS,
    FICO_BUCKET_LABELS,
    RATE_BUCKET_BINS,
    RATE_BUCKET_LABELS,
)

# Raw column -> internal alias.  Supports both DV01-standard names (loan_*)
# and roll-rate model names (orig_bal, ofico, note_rate).
_COL_ALIASES = {
    # DV01 standard
    "loan_balance_orig": "balance",
    "loan_term_orig": "term",
    "loan_grade": "grade",
    "fico_orig": "fico",
    "loan_rate_gross_orig": "rate",
    "dti_orig": "dti",
    "loan_purpose": "purpose",
    "loan_origination_date": "origination_date",
    "as_of_date": "as_of_date",
    # Roll-rate model standard
    "orig_bal": "balance",
    "note_rate": "rate",
    "ofico": "fico",
    "orig_dt": "origination_date",
    "r_dt": "as_of_date",
    "eop_balance": "current_balance",
    "end_bal": "current_balance",
}

_BUCKET_DEFS = [
    ("fico", FICO_BUCKET_BINS, FICO_BUCKET_LABELS),
    ("rate", RATE_BUCKET_BINS, RATE_BUCKET_LABELS),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply column aliases, only renaming where the target doesn't exist."""
    rename = {k: v for k, v in _COL_ALIASES.items()
              if k in df.columns and v not in df.columns}
    return df.rename(columns=rename) if rename else df.copy()


def _group_by(df: pd.DataFrame, by: list[str], bal: str, wavg_cols: list[str]) -> pd.DataFrame:
    """Generic grouping with Count, Balance, Bal %, Avg Bal, plus weighted means."""
    total_bal = df[bal].sum()
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({"Count": g[bal].count(), "Balance": g[bal].sum()})
    out["Bal %"] = out["Balance"] / total_bal * 100 if total_bal > 0 else 0.0
    out["Avg Bal"] = out["Balance"] / out["Count"]
    excluded = set(by)
    for col in wavg_cols:
        if col in excluded:
            continue
        out[col.upper()] = g.apply(lambda x, c=col: wavg(x, c, bal), include_groups=False)
    return out.reset_index()


def _insert_term_totals(df: pd.DataFrame, term_col: str = "term") -> pd.DataFrame:
    """Insert a ``"<term> (TOTAL)"`` row after each term group.

    Aggregation:
      - Count, Balance, Bal %: simple sums
      - Avg Bal: Balance / Count
      - RATE / FICO / DTI: balance-weighted within the term group
    """
    frames: list[pd.DataFrame] = []
    metric_cols = ("RATE", "FICO", "DTI")
    dim_cols = [c for c in df.columns
                if c not in (term_col, "Count", "Balance", "Bal %", "Avg Bal") + metric_cols]

    for term, group in df.groupby(term_col, sort=False):
        frames.append(group)

        n = group["Count"].sum()
        bal = group["Balance"].sum()
        row = {c: None for c in df.columns}
        row[term_col] = f"{int(term)} (TOTAL)"
        for dc in dim_cols:
            row[dc] = ""
        row["Count"] = n
        row["Balance"] = bal
        row["Bal %"] = group["Bal %"].sum()
        row["Avg Bal"] = bal / n if n > 0 else np.nan

        for mc in metric_cols:
            if mc not in df.columns:
                continue
            valid = group.dropna(subset=[mc])
            wb = valid["Balance"].sum()
            row[mc] = (valid[mc] * valid["Balance"]).sum() / wb if wb > 0 else np.nan

        frames.append(pd.DataFrame([row]))

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_deal_input_stats(input_df: pd.DataFrame, *, balance_col: str = "balance") -> dict:
    """Compute summary statistics breakdowns from a loan tape.

    Returns a dict with:
      - ``overview``    : scalar KPI dict
      - ``by_term``     : per-term totals
      - ``by_term_grade``, ``by_term_fico``, ``by_term_rate``,
        ``by_term_purpose`` : DataFrames crossed with term, with TOTAL rows
    """
    if input_df.empty:
        return {}

    df = _normalise_columns(input_df)
    bal = balance_col if balance_col in df.columns else "balance"
    if bal not in df.columns:
        return {}

    total_bal = df[bal].sum()
    n = len(df)
    wavg_cols = [c for c in ("rate", "fico", "dti") if c in df.columns]

    overview = {
        "loan_count": n,
        "total_balance": total_bal,
        "avg_balance": total_bal / n if n else 0,
    }
    for c in wavg_cols:
        overview[f"w_{c}"] = wavg(df, c, bal)
    if "term" in df.columns:
        overview["w_term"] = wavg(df, "term", bal)

    out: dict = {"overview": overview}

    if "term" in df.columns:
        out["by_term"] = _group_by(df, ["term"], bal, wavg_cols).sort_values("term")

    if "term" in df.columns and "grade" in df.columns:
        tg = _group_by(df, ["term", "grade"], bal, wavg_cols)
        order = sort_grades(tg["grade"].unique())
        tg["grade"] = pd.Categorical(tg["grade"], categories=order, ordered=True)
        tg = tg.sort_values(["term", "grade"])
        out["by_term_grade"] = _insert_term_totals(tg)

    for col, bins, labels in _BUCKET_DEFS:
        if col not in df.columns or "term" not in df.columns:
            continue
        bkt = f"{col}_bkt"
        cut_bins = list(bins) + ([np.inf] if len(bins) == len(labels) else [])
        df[bkt] = pd.cut(df[col], bins=cut_bins, labels=labels, right=False)
        grouped = _group_by(df, ["term", bkt], bal, wavg_cols).sort_values(["term", bkt])
        out[f"by_term_{col}"] = _insert_term_totals(grouped)

    if "term" in df.columns and "purpose" in df.columns:
        tp = _group_by(df, ["term", "purpose"], bal, wavg_cols).sort_values(
            ["term", "Balance"], ascending=[True, False])
        out["by_term_purpose"] = _insert_term_totals(tp)

    return out
