"""Aggregate KPI computation from sim output.

Mirrors LoanProspector's ``compute_aggregate_metrics``: reads the
``Portfolio`` and ``Metrics_Portfolio`` sheets and produces a dict of scalar
KPIs plus derived per-period series (``pool_factor``, ``cum_interest``).

Also enriches ``Metrics_Portfolio`` with balance-weighted CTD1/CTP from
``Metrics_Grouped`` — kept for completeness even though the aggregate page
no longer charts them (they're still used on the curves page DQ tab).
"""
from __future__ import annotations

import pandas as pd

from .aggregation import balance_weighted_avg, compute_kpis

# ---------------------------------------------------------------------------
# Column standardisation — model output -> canonical
# ---------------------------------------------------------------------------

_MODEL_TO_CANONICAL = {
    "fromC_D1M": "ctd1",
    "fromC_PIF": "ctp",
}


def standardize_metrics_grouped(df: pd.DataFrame) -> pd.DataFrame:
    """Rename roll-rate model columns to canonical names (non-destructive)."""
    if df.empty:
        return df
    rename = {k: v for k, v in _MODEL_TO_CANONICAL.items()
              if k in df.columns and v not in df.columns}
    return df.rename(columns=rename) if rename else df


# ---------------------------------------------------------------------------
# Aggregate KPIs
# ---------------------------------------------------------------------------

def compute_aggregate_metrics(
    portfolio_df: pd.DataFrame,
    metrics_portfolio_df: pd.DataFrame,
) -> dict:
    """Portfolio-level KPI scalars + per-period series for charts.

    Returns a dict that includes scalar KPIs (``initial_balance``,
    ``final_balance``, ``avg_cdr``, ...) plus pandas Series keyed off the
    portfolio index for charting (``pool_factor``, ``cum_interest``,
    ``cum_loss_portfolio``).
    """
    kpi: dict = {}

    if not portfolio_df.empty:
        initial = portfolio_df["begin_bal"].iloc[0]
        kpi["initial_balance"] = initial

        nonzero = portfolio_df[portfolio_df["end_bal"] > 0]
        if not nonzero.empty:
            kpi["final_balance"] = nonzero["end_bal"].iloc[-1]
            kpi["final_period"] = int(nonzero["period"].iloc[-1])
        else:
            kpi["final_balance"] = 0.0
            kpi["final_period"] = int(portfolio_df["period"].iloc[-1])

        kpi["total_interest"] = portfolio_df["int_pmt"].sum()
        kpi["total_principal"] = portfolio_df["prin_pmt"].sum()
        kpi["total_loss"] = portfolio_df["loss"].sum()
        kpi["total_prepay"] = portfolio_df["pif_bal"].sum()

        if "net_recov" in portfolio_df.columns:
            kpi["total_recovery"] = portfolio_df["net_recov"].sum()

        kpi["pool_factor"] = (
            portfolio_df["end_bal"] / initial if initial > 0
            else pd.Series(0.0, index=portfolio_df.index)
        )
        kpi["cum_interest"] = portfolio_df["int_pmt"].cumsum()
        kpi["cum_loss_portfolio"] = portfolio_df["loss"].cumsum()

    if not metrics_portfolio_df.empty:
        rate_kpis = compute_kpis(metrics_portfolio_df)
        for key in ("avg_cdr", "avg_cpr", "lifetime_cgl", "cum_loss"):
            if key in rate_kpis:
                kpi[key] = rate_kpis[key]

    return kpi


def enrich_portfolio_with_transition_rates(
    metrics_portfolio_df: pd.DataFrame,
    metrics_grouped_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add balance-weighted aggregate CTD1/CTP to portfolio-level metrics.

    The model exports ``fromC_D1M`` (-> ctd1) and ``fromC_PIF`` (-> ctp) per
    cohort.  This collapses across (term × grade) per period using ``begin_bal``
    weights and merges the result into ``metrics_portfolio_df``.
    """
    if metrics_portfolio_df.empty or metrics_grouped_df.empty:
        return metrics_portfolio_df

    mg = standardize_metrics_grouped(metrics_grouped_df.copy())
    age_col = "loan_age" if "loan_age" in mg.columns else "period"
    rate_cols = [c for c in ("ctd1", "ctp") if c in mg.columns]

    if not rate_cols or "begin_bal" not in mg.columns or age_col not in mg.columns:
        return metrics_portfolio_df

    agg = balance_weighted_avg(mg, rate_cols, "begin_bal", [age_col])
    agg = agg.rename(columns={age_col: "period"})
    return metrics_portfolio_df.merge(agg, on="period", how="left")
