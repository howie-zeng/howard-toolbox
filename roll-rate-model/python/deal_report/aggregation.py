"""Pure-Python aggregation primitives — no LoanProspector / streamlit deps.

All functions are stateless and operate on pandas DataFrames or numpy arrays.
The model already emits per-period CDR/CPR/CGL in ``Metrics_Grouped``, so we
only need weighted averages and KPI extraction here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Weighted averages
# ---------------------------------------------------------------------------

def wavg(df: pd.DataFrame, col: str, weight: str) -> float:
    """Balance-weighted average; NaN when weight sums to zero."""
    total = df[weight].sum()
    return (df[col] * df[weight]).sum() / total if total > 0 else np.nan


def balance_weighted_avg(
    df: pd.DataFrame,
    metric_cols: list[str],
    weight_col: str,
    group_cols: list[str],
) -> pd.DataFrame:
    """Compute balance-weighted means of *metric_cols* grouped by *group_cols*.

    Returns a DataFrame with *group_cols* + the weighted *metric_cols*.
    """
    group_cols = [c for c in group_cols if c in df.columns]
    metric_cols = [c for c in metric_cols if c in df.columns]
    if not metric_cols or not group_cols or weight_col not in df.columns:
        return pd.DataFrame(columns=group_cols + metric_cols)

    work = df[group_cols + metric_cols + [weight_col]].copy()
    work[weight_col] = pd.to_numeric(work[weight_col], errors="coerce").fillna(0)
    for m in metric_cols:
        work[m] = pd.to_numeric(work[m], errors="coerce").fillna(0)
        work[f"__wn_{m}"] = work[m] * work[weight_col]

    agg_dict = {weight_col: "sum"}
    for m in metric_cols:
        agg_dict[f"__wn_{m}"] = "sum"

    result = work.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    denom = result[weight_col].replace(0, np.nan)
    for m in metric_cols:
        result[m] = result[f"__wn_{m}"] / denom
    return result[group_cols + metric_cols]


# ---------------------------------------------------------------------------
# Period-level KPIs
# ---------------------------------------------------------------------------

def compute_kpis(
    df: pd.DataFrame,
    *,
    period_col: str = "period",
    bal_col: str = "begin_bal",
) -> dict:
    """Compute standard KPIs from a period-level metrics DataFrame.

    Returns: ``initial_balance``, ``final_balance``, ``final_period``,
    ``avg_cdr``, ``avg_cpr``, ``lifetime_cgl``, ``cum_loss``,
    plus optional flow totals (``total_interest``, ``total_prepay``, etc.)
    when the underlying columns are present.
    """
    kpi: dict = {}
    if df.empty or bal_col not in df.columns:
        return kpi

    kpi["initial_balance"] = df[bal_col].iloc[0]

    nonzero = df[df[bal_col] > 0]
    if not nonzero.empty:
        kpi["final_balance"] = nonzero[bal_col].iloc[-1]
        kpi["final_period"] = int(nonzero[period_col].iloc[-1])
    else:
        kpi["final_balance"] = 0.0
        kpi["final_period"] = int(df[period_col].iloc[-1])

    bal = df[bal_col].astype(float)
    if bal.sum() > 0:
        for rate_col, key in [("cdr", "avg_cdr"), ("cpr", "avg_cpr")]:
            if rate_col not in df.columns:
                kpi[key] = np.nan
                continue
            rate = df[rate_col].astype(float)
            valid = rate.between(-1, 1)
            denom = bal[valid].sum()
            kpi[key] = (rate[valid] * bal[valid]).sum() / denom if denom > 0 else np.nan
    else:
        kpi["avg_cdr"] = kpi["avg_cpr"] = np.nan

    if "cgl" in df.columns:
        kpi["lifetime_cgl"] = df["cgl"].iloc[-1]
    if "cum_loss" in df.columns:
        kpi["cum_loss"] = df["cum_loss"].iloc[-1]

    for col, key in [
        ("int_pmt", "total_interest"),
        ("pif_bal", "total_prepay"),
        ("loss", "total_loss"),
        ("net_recov", "total_recovery"),
        ("prin_pmt", "total_principal"),
    ]:
        if col in df.columns:
            kpi[key] = df[col].sum()

    return kpi
