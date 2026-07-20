"""Aggregate Overview page.

KPIs + per-period portfolio charts: balance + pool factor, CPR & CDR, CGL,
cumulative interest, delinquency pipeline + payments breakdown.
(CTD1/CTP live on the curves page DQ tab, not here.)
"""
from __future__ import annotations

import pandas as pd

from ..render.formatters import (
    fmt_dollars, fmt_pct, json_safe, kpi_grid,
)
from ..render.theme import (
    CHART_FULL_WIDTH, CHART_HALF_WIDTH, CHART_HEIGHT, CURVE_PALETTE, DQ_COLORS,
    METRIC_COLORS, PMT_COLORS,
)
from ..metrics.kpis import pool_horizon
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


def _lag_bar_spec(records: list, sort: list) -> dict:
    """Projected recovery-lag profile: P(lag bucket | charge-off) as bars.

    Carries a single-series "Projected" legend so the top-legend block matches
    the neighbouring severity line chart and the two plot areas align.
    """
    color = METRIC_COLORS["cum_interest"]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": CHART_HALF_WIDTH, "height": CHART_HEIGHT,
        "title": "Recovery Lag Profile (share of charge-offs)",
        "data": {"values": records},
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "bucket", "type": "nominal", "sort": sort,
                  "title": "recovery lag (months after charge-off)", "axis": {"labelAngle": 0}},
            "y": {"field": "value", "type": "quantitative", "title": "share",
                  "axis": {"format": ".0%"}},
            "color": {"field": "series", "type": "nominal",
                      "scale": {"domain": ["Projected"], "range": [color]},
                      "legend": {"orient": "top", "title": None}},
            "tooltip": [{"field": "bucket", "type": "nominal", "title": "lag"},
                        {"field": "value", "type": "quantitative", "format": ".1%"}],
        },
        "config": {"view": {"stroke": None}, "background": "#f8f9fa",
                   "axis": {"labelColor": "#212529", "titleColor": "#212529",
                            "gridColor": "#eef1f5", "domainColor": "#ced4da",
                            "tickColor": "#ced4da"},
                   "legend": {"labelColor": "#212529"}, "title": {"color": "#212529"}},
    }


def _cohort_chart_box(chart_id: str, cohort_records: list) -> str:
    """Vega chart + a custom HTML cohort legend (hidden until JS sees the chart's
    `show_cohorts` toggle). Swatch colours follow the same sorted-cohort ->
    CURVE_PALETTE order as the lines."""
    cohorts = sorted({r["cohort"] for r in cohort_records})
    items = "".join(
        f'<span class="cl-item" data-cohort="{c}"><span class="cl-sw" '
        f'style="background:{CURVE_PALETTE[i % len(CURVE_PALETTE)]}"></span>{c}</span>'
        for i, c in enumerate(cohorts)
    )
    legend = (f'<div class="cohort-legend" data-for="{chart_id}">{items}</div>'
              if cohorts else "")
    # Legend sits below the chart so toggling cohorts never resizes it.
    return f'<div class="chart-box"><div id="{chart_id}"></div>{legend}</div>'


def _cohort_rate_records(grouped_period_df, metric: str, *, trim: bool = True) -> list[dict]:
    """Per-cohort (term|grade) points for `metric`.

    With `trim`, each cohort is cut to its own material life (begin_bal >= 1% of
    its initial) — right for runoff-noisy rates (CPR/CDR). Pass trim=False for
    cumulative series (CGL) to keep the full curve.
    """
    if grouped_period_df is None or grouped_period_df.empty:
        return []
    cols = list(grouped_period_df.columns)
    # Strat/group-by columns = whatever the sim wrote before 'period' (auto:
    # term_bkt[, fico_bkt]; MPL: term+grade). Detected, not hard-coded, so any
    # group_by is handled.
    if "period" not in cols or not {metric, "begin_bal"}.issubset(cols):
        return []
    keys = cols[:cols.index("period")]
    if not keys:
        return []
    recs: list[dict] = []
    for key_vals, g in grouped_period_df.groupby(keys):
        g = g.sort_values("period")
        init = float(g["begin_bal"].iloc[0]) if not g.empty else 0.0
        if init <= 0:
            continue
        gm = g[g["begin_bal"] >= 0.01 * init] if trim else g
        label = "|".join(str(v) for v in (key_vals if isinstance(key_vals, tuple) else (key_vals,)))
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
    lag_profile: pd.DataFrame | None = None,
) -> tuple[str, int]:
    """Render the aggregate page HTML.

    Appends Vega specs to *specs* (mutated in place) and returns
    ``(html, next_plot_id)``.
    """
    parts: list[str] = [_kpi_section(kpi)]
    parts.append('<div class="section-toggle"><span class="label">Sections:</span></div>')

    # Unified horizon: cut at pool < 0.20% (kpis.pool_horizon), matching the
    # sim-performance-vs-actual page. TRIM the data (not just the x-domain) so
    # the off-page runoff tail doesn't inflate the auto y-scale.
    final_period = kpi.get("final_period")
    port = portfolio_df.copy()
    met = metrics_portfolio_df.copy()
    if not port.empty:
        port = port[port["begin_bal"] > 0]
    xmax = (pool_horizon(port["begin_bal"], port["period"])
            if not port.empty else None) or final_period
    if xmax is not None:
        if not port.empty and "period" in port.columns:
            port = port[port["period"] <= xmax]
        if not met.empty and "period" in met.columns:
            met = met[met["period"] <= xmax]

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
            y_clip_pct=0.90,                      # clip the top ~10% end-of-life hike
            width=CHART_HALF_WIDTH,
        )})
        cpr_cdr_boxes.append(_cohort_chart_box(cid, cohort_records))
    if cpr_cdr_boxes:
        add_section("CPR & CDR",
                    f'<h2>CPR & CDR</h2><div class="chart-row">{"".join(cpr_cdr_boxes)}</div>')

    # ---- Cumulative Loss: Gross (CGL) and Net (CNL) side by side ----
    cl_boxes = []
    for metric, title, lab in (("cgl", "Cumulative Gross Loss (CGL)", "CGL"),
                               ("cnl", "Cumulative Net Loss (CNL)", "CNL")):
        if metric not in met.columns:
            continue
        cid = f"chart_{plot_id}"; plot_id += 1
        agg_records = json_safe([
            {"period": int(p), "value": float(v), "series": lab}
            for p, v in zip(met["period"], met[metric]) if pd.notna(v)
        ])
        cohort_records = json_safe(
            _cohort_rate_records(metrics_grouped_period_df, metric, trim=False))
        specs.append({"id": cid, "spec": rate_cohort_spec(
            agg_records, cohort_records,
            title=title, series_label=lab, y_format=".2%",
            color=METRIC_COLORS.get(metric, "#2c7a4b"), x_domain_max=xmax,
            width=CHART_HALF_WIDTH,
        )})
        cl_boxes.append(_cohort_chart_box(cid, cohort_records))
    if cl_boxes:
        add_section("Cumulative Loss",
                    '<h2>Cumulative Loss: Gross (CGL) vs Net (CNL)</h2>'
                    f'<div class="chart-row">{"".join(cl_boxes)}</div>')

    # ---- Loss Severity (cumulative CNL/CGL) + Recovery Lag profile (2-up) ----
    sev_box = lag_box = ""
    if {"cgl", "cnl"} <= set(met.columns):
        m2 = met.sort_values("period")
        # Per-period LGD: 1 - Δ(recovery share)/Δ(gross-loss share), recovery
        # share = cgl - cnl. Marginal (not cumulative) severity.
        cgl = pd.to_numeric(m2["cgl"], errors="coerce")
        recov = cgl - pd.to_numeric(m2["cnl"], errors="coerce")
        dco = cgl.diff(); drec = recov.diff()
        sev = (1 - drec / dco).where(dco > 0)
        recs = json_safe([{"period": int(p), "severity": float(v)}
                          for p, v in zip(m2["period"], sev) if pd.notna(v)])
        if recs:
            cid = f"chart_{plot_id}"; plot_id += 1
            specs.append({"id": cid, "spec": line_spec(
                recs, "period", ["severity"],
                title="Loss Severity (per-period net ÷ gross charge-off)", y_format=".1%",
                width=CHART_HALF_WIDTH, colors=["#8b5cf6"], x_domain_max=xmax,
                y_labels=["Severity"],
            )})
            sev_box = _chart_box(cid)
    if lag_profile is not None and not lag_profile.empty:
        proj = lag_profile[lag_profile["series"] == "Projected"]
        order = list(dict.fromkeys(lag_profile["bucket"]))
        lag_recs = json_safe([{"bucket": b, "value": float(v), "series": "Projected"}
                              for b, v in zip(proj["bucket"], proj["value"])])
        if lag_recs:
            cid = f"chart_{plot_id}"; plot_id += 1
            specs.append({"id": cid, "spec": _lag_bar_spec(lag_recs, order)})
            lag_box = _chart_box(cid)
    if sev_box or lag_box:
        add_section("Severity",
                    '<h2>Loss Severity &amp; Recovery Lag</h2>'
                    f'<div class="chart-row">{sev_box}{lag_box}</div>')

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
