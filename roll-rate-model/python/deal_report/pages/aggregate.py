"""Aggregate Overview page.

KPIs + per-period portfolio charts: balance + pool factor, CPR & CDR, CGL,
cumulative interest, delinquency pipeline + payments breakdown.

(CTD1/CTP charts are intentionally absent — they live on the curves page DQ
tab now.)
"""
from __future__ import annotations

import pandas as pd

from ..formatters import (
    fmt_dollars,
    fmt_pct,
    json_safe,
    kpi_grid,
)
from ..theme import (
    CHART_HALF_WIDTH,
    DQ_COLORS,
    METRIC_COLORS,
    PMT_COLORS,
)
from ..vega_specs import area_spec, line_spec

# Top KPI cards — (label, kpi_key, formatter)
_KPI_DEFS = [
    ("Initial Balance", "initial_balance", fmt_dollars),
    ("Final Balance",   "final_balance",   fmt_dollars),
    ("Total Cum. Loss", "cum_loss",        fmt_dollars),
    ("Lifetime CGL",    "lifetime_cgl",    fmt_pct),
    ("Avg CPR (bal-wt)", "avg_cpr",        fmt_pct),
    ("Avg CDR (bal-wt)", "avg_cdr",        fmt_pct),
    ("Total Interest",  "total_interest",  fmt_dollars),
    ("Total Prepay",    "total_prepay",    fmt_dollars),
]


def _kpi_section(kpi: dict) -> str:
    items = [(label, fmt(kpi.get(key)), None) for label, key, fmt in _KPI_DEFS]
    return kpi_grid(items)


def _chart_box(chart_id: str) -> str:
    return f'<div class="chart-box"><div id="{chart_id}"></div></div>'


def build_aggregate_page(
    portfolio_df: pd.DataFrame,
    metrics_portfolio_df: pd.DataFrame,
    kpi: dict,
    *,
    specs: list[dict],
    plot_id: int = 0,
) -> tuple[str, int]:
    """Render the aggregate page HTML.

    Appends Vega specs to *specs* (mutated in place) and returns
    ``(html, next_plot_id)``.
    """
    parts: list[str] = [_kpi_section(kpi)]
    parts.append('<div class="section-toggle"><span class="label">Sections:</span></div>')

    # Truncate to active periods (where balance is non-zero)
    final_period = kpi.get("final_period")
    port = portfolio_df.copy()
    met = metrics_portfolio_df.copy()
    if not port.empty:
        port = port[port["begin_bal"] > 0]
    if final_period is not None:
        if not port.empty and "period" in port.columns:
            port = port[port["period"] <= final_period]
        if not met.empty and "period" in met.columns:
            met = met[met["period"] <= final_period]
    xmax = final_period

    def add_section(title: str, body_html: str) -> None:
        parts.append(f'<div class="report-section" data-section="{title}">{body_html}</div>')

    # ---- Balance + Pool Factor ----
    if not port.empty and "pool_factor" in kpi:
        port_chart = port.copy()
        port_chart["pool_factor"] = kpi["pool_factor"].reindex(port_chart.index).values
        records = json_safe(port_chart[["period", "begin_bal", "pool_factor"]].to_dict("records"))
        cid_bal = f"chart_{plot_id}"
        cid_pf = f"chart_{plot_id + 1}"
        plot_id += 2
        specs.append({"id": cid_bal, "spec": line_spec(
            records, "period", ["begin_bal"],
            title="Outstanding Balance", y_format="$,.0f", width=CHART_HALF_WIDTH,
            colors=[METRIC_COLORS["begin_bal"]], x_domain_max=xmax,
            y_labels=["Outstanding Balance"],
        )})
        specs.append({"id": cid_pf, "spec": line_spec(
            records, "period", ["pool_factor"],
            title="Pool Factor", y_format=".2%", width=CHART_HALF_WIDTH,
            colors=[METRIC_COLORS["pool_factor"]], x_domain_max=xmax,
            y_labels=["Pool Factor"],
        )})
        add_section("Balance & Pool Factor",
                    f'<h2>Balance & Pool Factor</h2>'
                    f'<div class="chart-row">{_chart_box(cid_bal)}{_chart_box(cid_pf)}</div>')

    # ---- CPR & CDR ----
    cpr_cdr_boxes = []
    for metric in ("cpr", "cdr"):
        if metric not in met.columns:
            continue
        cid = f"chart_{plot_id}"
        plot_id += 1
        records = json_safe(met[["period", metric]].to_dict("records"))
        specs.append({"id": cid, "spec": line_spec(
            records, "period", [metric],
            title=metric.upper(), y_format=".2%", width=CHART_HALF_WIDTH,
            colors=[METRIC_COLORS[metric]], x_domain_max=xmax,
            y_labels=[metric.upper()],
        )})
        cpr_cdr_boxes.append(_chart_box(cid))
    if cpr_cdr_boxes:
        add_section("CPR & CDR",
                    f'<h2>CPR & CDR</h2><div class="chart-row">{"".join(cpr_cdr_boxes)}</div>')

    # ---- CGL ----
    if "cgl" in met.columns:
        cid = f"chart_{plot_id}"
        plot_id += 1
        records = json_safe(met[["period", "cgl"]].to_dict("records"))
        specs.append({"id": cid, "spec": line_spec(
            records, "period", ["cgl"],
            title="Cumulative Gross Loss (CGL)", y_format=".2%",
            colors=[METRIC_COLORS["cgl"]], x_domain_max=xmax,
            y_labels=["CGL"],
        )})
        add_section("CGL",
                    f'<h2>Cumulative Gross Loss (CGL)</h2>{_chart_box(cid)}')

    # ---- Cumulative Interest ----
    if not port.empty and "cum_interest" in kpi:
        port_chart = port.copy()
        port_chart["cum_interest"] = kpi["cum_interest"].reindex(port_chart.index).values
        records = json_safe(port_chart[["period", "cum_interest"]].to_dict("records"))
        cid = f"chart_{plot_id}"
        plot_id += 1
        specs.append({"id": cid, "spec": line_spec(
            records, "period", ["cum_interest"],
            title="Cumulative Interest Paid", y_format="$,.0f",
            colors=[METRIC_COLORS["cum_interest"]], x_domain_max=xmax,
            y_labels=["Cum. Interest"],
        )})
        add_section("Cum. Interest",
                    f'<h2>Cumulative Interest Paid</h2>{_chart_box(cid)}')

    # ---- Delinquency Pipeline + Payments Breakdown ----
    if not port.empty:
        dq_cols = [c for c in ("dq30_bal", "dq60_bal", "dq90_bal", "dq120_bal") if c in port.columns]
        pmt_cols = [c for c in ("int_pmt", "prin_pmt", "pif_bal") if c in port.columns]

        if dq_cols or pmt_cols:
            charts: list[str] = []
            if dq_cols:
                cid = f"chart_{plot_id}"
                plot_id += 1
                records = json_safe(port[["period"] + dq_cols].to_dict("records"))
                specs.append({"id": cid, "spec": area_spec(
                    records, "period", dq_cols,
                    title="Delinquency Pipeline", y_format="$,.0f", width=CHART_HALF_WIDTH,
                    colors=DQ_COLORS, x_domain_max=xmax,
                    y_labels=["DQ 30", "DQ 60", "DQ 90", "DQ 120"][:len(dq_cols)],
                )})
                charts.append(_chart_box(cid))
            if pmt_cols:
                cid = f"chart_{plot_id}"
                plot_id += 1
                records = json_safe(port[["period"] + pmt_cols].to_dict("records"))
                specs.append({"id": cid, "spec": area_spec(
                    records, "period", pmt_cols,
                    title="Payments Breakdown", y_format="$,.0f", width=CHART_HALF_WIDTH,
                    colors=PMT_COLORS, x_domain_max=xmax,
                    y_labels=["Interest", "Principal", "Paid-in-Full"][:len(pmt_cols)],
                )})
                charts.append(_chart_box(cid))

            add_section("Delinquency & Payments",
                        f'<h2>Delinquency & Payments</h2>'
                        f'<div class="chart-row">{"".join(charts)}</div>')

    return "\n".join(parts), plot_id
