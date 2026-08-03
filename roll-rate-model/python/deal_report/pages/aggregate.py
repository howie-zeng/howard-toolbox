"""Aggregate Overview page.

KPIs + per-period portfolio charts: balance + pool factor, CPR & CDR, CGL,
cumulative interest, delinquency pipeline + payments breakdown.

(CTD1/CTP charts are intentionally absent — they live on the curves page DQ
tab now.)
"""
from __future__ import annotations

import pandas as pd

from ..render.formatters import (
    fmt_dollars, fmt_pct, json_safe, kpi_grid,
)
from ..render.theme import (
    CHART_FULL_WIDTH, CHART_HALF_WIDTH, CURVE_PALETTE, DQ_COLORS, METRIC_COLORS,
    PMT_COLORS,
)
from ..render.vega_specs import area_spec, line_spec, rate_cohort_spec


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


def _cohort_chart_box(chart_id: str, cohort_records: list) -> str:
    """Chart box for a cohort chart: the Vega chart + a custom HTML cohort legend
    (hidden by default; JS shows it when the chart's `show_cohorts` toggle is on).
    Swatch colours follow the same sorted-cohort -> CURVE_PALETTE order as the lines."""
    cohorts = sorted({r["cohort"] for r in cohort_records})
    items = "".join(
        f'<span class="cl-item" data-cohort="{c}"><span class="cl-sw" '
        f'style="background:{CURVE_PALETTE[i % len(CURVE_PALETTE)]}"></span>{c}</span>'
        for i, c in enumerate(cohorts)
    )
    legend = (f'<div class="cohort-legend" data-for="{chart_id}">{items}</div>'
              if cohorts else "")
    # Chart fills the box (constant size); the legend sits BELOW it so toggling
    # cohorts on/off never resizes the chart itself.
    return f'<div class="chart-box"><div id="{chart_id}"></div>{legend}</div>'


def _cohort_rate_records(grouped_period_df, metric: str, *, trim: bool = True) -> list[dict]:
    """Per-cohort (term|grade) points for `metric`.

    When `trim`, each cohort is cut to its own material life (begin_bal >= 1% of
    that cohort's initial) — right for runoff-noisy rates (CPR/CDR). For
    cumulative series (CGL) pass trim=False so the full curve is kept.
    """
    if grouped_period_df is None or grouped_period_df.empty:
        return []
    need = {"term", "grade", "period", metric, "begin_bal"}
    if not need.issubset(grouped_period_df.columns):
        return []
    recs: list[dict] = []
    for (term, grade), g in grouped_period_df.groupby(["term", "grade"]):
        g = g.sort_values("period")
        init = float(g["begin_bal"].iloc[0]) if not g.empty else 0.0
        if init <= 0:
            continue
        gm = g[g["begin_bal"] >= 0.01 * init] if trim else g
        label = f"{term}|{grade}"
        for _, r in gm.iterrows():
            v = r[metric]
            if pd.notna(v):
                recs.append({"period": int(r["period"]), "cohort": label, "value": float(v)})
    return recs


def build_aggregate_page(
    portfolio_df: pd.DataFrame,
    metrics_portfolio_df: pd.DataFrame,
    kpi: dict,
    *,
    specs: list[dict],
    plot_id: int = 0,
    metrics_grouped_period_df: pd.DataFrame | None = None,
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

    # ---- CPR & CDR (with toggleable per-cohort overlay) ----
    cpr_cdr_boxes = []
    for metric in ("cpr", "cdr"):
        if metric not in met.columns:
            continue
        cid = f"chart_{plot_id}"
        plot_id += 1
        agg_records = json_safe([
            {"period": int(p), "value": float(v), "series": metric.upper()}
            for p, v in zip(met["period"], met[metric]) if pd.notna(v)
        ])
        cohort_records = json_safe(
            _cohort_rate_records(metrics_grouped_period_df, metric))
        specs.append({"id": cid, "spec": rate_cohort_spec(
            agg_records, cohort_records,
            title=metric.upper(), y_format=".2%",
            color=METRIC_COLORS[metric], x_domain_max=xmax,
            width=CHART_HALF_WIDTH,
        )})
        cpr_cdr_boxes.append(_cohort_chart_box(cid, cohort_records))
    if cpr_cdr_boxes:
        add_section("CPR & CDR",
                    f'<h2>CPR & CDR</h2><div class="chart-row">{"".join(cpr_cdr_boxes)}</div>')

    # ---- Cumulative Gross Loss (full width) ----
    if "cgl" in met.columns:
        cid = f"chart_{plot_id}"; plot_id += 1
        agg_records = json_safe([
            {"period": int(p), "value": float(v), "series": "CGL"}
            for p, v in zip(met["period"], met["cgl"]) if pd.notna(v)
        ])
        cohort_records = json_safe(
            _cohort_rate_records(metrics_grouped_period_df, "cgl", trim=False))
        specs.append({"id": cid, "spec": rate_cohort_spec(
            agg_records, cohort_records,
            title="Cumulative Gross Loss (CGL)", series_label="CGL",
            y_format=".2%", color=METRIC_COLORS["cgl"], x_domain_max=xmax,
            width=CHART_FULL_WIDTH,
        )})
        add_section("CGL",
                    f'<h2>Cumulative Gross Loss (CGL)</h2>'
                    f'{_cohort_chart_box(cid, cohort_records)}')

    # ---- Cumulative Interest (full width) ----
    if not port.empty and "cum_interest" in kpi:
        port_chart = port.copy()
        port_chart["cum_interest"] = kpi["cum_interest"].reindex(port_chart.index).values
        records = json_safe(port_chart[["period", "cum_interest"]].to_dict("records"))
        cid = f"chart_{plot_id}"; plot_id += 1
        specs.append({"id": cid, "spec": line_spec(
            records, "period", ["cum_interest"],
            title="Cumulative Interest Paid", y_format="$,.0f", width=CHART_FULL_WIDTH,
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
                cid = f"chart_{plot_id}"; plot_id += 1
                records = json_safe(port[["period"] + dq_cols].to_dict("records"))
                specs.append({"id": cid, "spec": area_spec(
                    records, "period", dq_cols,
                    title="Delinquency Pipeline", y_format="$,.0f", width=CHART_HALF_WIDTH,
                    colors=DQ_COLORS, x_domain_max=xmax,
                    y_labels=["DQ 30", "DQ 60", "DQ 90", "DQ 120"][:len(dq_cols)],
                )})
                charts.append(_chart_box(cid))
            if pmt_cols:
                cid = f"chart_{plot_id}"; plot_id += 1
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
