"""Summary Statistics page — input loan-tape breakdowns.

KPI overview (loan count, total balance, WAC/FICO/term) followed by
collapsible sections for By Term, By Term × Grade, By Term × FICO,
By Term × Rate.  Each section pairs an HTML table with a faceted bar chart
that switches metrics via the metric-tabs widget.
"""
from __future__ import annotations

import pandas as pd

from ..formatters import (
    TABLE_FMT,
    df_to_html_table,
    fmt_dollars,
    fmt_pct,
    json_safe,
    kpi_grid,
    strip_total_rows,
)
from ..theme import (
    CHART_HEIGHT,
    CHART_SIMPLE_WIDTH,
    SOURCE_COLORS,
)
from ..vega_specs import bar_spec, faceted_bar_spec

# Metrics shown in the section's chart switcher.  Each ``y_format`` matches
# what the underlying column actually contains (Bal % is already in %).
_CHART_METRICS = [
    ("Bal %",   ".1f"),
    ("Avg Bal", "$,.0f"),
    ("RATE",    ".2%"),
    ("FICO",    ",.0f"),
    ("DTI",     ".2%"),
]

# Columns that receive heatmap shading in the breakdown tables
_GRADIENT_COLS = ["Bal %", "Avg Bal", "RATE", "FICO", "DTI"]


# ---------------------------------------------------------------------------
# KPI overview
# ---------------------------------------------------------------------------

def _kpi_section(stats: dict) -> str:
    ov = stats.get("overview", {})
    if not ov:
        return ""
    items = [
        ("Loans",         f"{ov.get('loan_count', 0):,}",            None),
        ("Total Balance", fmt_dollars(ov.get("total_balance")),      None),
        ("Avg Balance",   fmt_dollars(ov.get("avg_balance")),        None),
    ]
    if "w_rate" in ov:
        items.append(("WAC", fmt_pct(ov["w_rate"]), None))
    if "w_fico" in ov:
        items.append(("Wtd FICO", f"{ov['w_fico']:.0f}", None))
    if "w_term" in ov:
        items.append(("Wtd Term", f"{ov['w_term']:.1f}mo", None))
    return kpi_grid(items)


# ---------------------------------------------------------------------------
# Section chart (one metric switch per section)
# ---------------------------------------------------------------------------

def _section_chart(
    df: pd.DataFrame,
    section_key: str,
    color_col: str | None,
    title_prefix: str,
    specs: list[dict],
    plot_id: int,
) -> tuple[str, int]:
    """Build a metric-tabs chart bar + one chart per metric.

    When *color_col* is set, the chart is faceted by term with bars coloured
    by the dimension (grade / fico_bkt / rate_bkt).  Otherwise, a simple bar
    chart of metric vs term is rendered.
    """
    clean = strip_total_rows(df)
    if clean.empty:
        return "", plot_id
    clean["term"] = clean["term"].astype(str)
    term_order = sorted(clean["term"].unique(), key=lambda t: int(t) if t.isdigit() else 0)

    avail = [(mc, fmt) for mc, fmt in _CHART_METRICS if mc in clean.columns]
    if not avail:
        return "", plot_id

    chart_group = f"cg_{section_key}"
    parts = [f'<div class="metric-tabs" data-chart-group="{chart_group}">']
    for i, (mc, _) in enumerate(avail):
        cls = " active" if i == 0 else ""
        parts.append(f'<button data-metric="{mc}" class="{cls.strip()}">{mc}</button>')
    parts.append("</div>")

    for i, (mc, y_fmt) in enumerate(avail):
        active_cls = " active" if i == 0 else ""
        cid = f"chart_{plot_id}"
        plot_id += 1

        rec_df = clean[["term"] + ([color_col] if color_col and color_col in clean.columns else []) + [mc]].copy()
        if color_col and color_col in rec_df.columns:
            rec_df[color_col] = rec_df[color_col].astype(str)
        rec_df["Source"] = "Deal"
        records = json_safe(rec_df.to_dict("records"))

        if color_col and color_col in clean.columns:
            dim_order = clean[color_col].astype(str).unique().tolist()
            n_terms = len(term_order)
            full_w = 1600
            avail_w = full_w - 50 - (n_terms - 1) * 5
            facet_w = max(60, avail_w // max(n_terms, 1))
            spec = faceted_bar_spec(
                records, color_col, mc, y_fmt,
                source_order=["Deal"], source_colors=SOURCE_COLORS[:1],
                term_order=term_order, dim_order=dim_order,
                facet_w=facet_w, height=CHART_HEIGHT,
                title=f"{title_prefix} — {mc}",
            )
            box_style = ""
        else:
            spec = bar_spec(
                records, "term", mc, color="Source",
                title=f"{title_prefix} — {mc}",
                y_format=y_fmt, width=CHART_SIMPLE_WIDTH, height=CHART_HEIGHT,
                x_sort=term_order, colors=SOURCE_COLORS[:1],
            )
            box_style = f"max-width:{CHART_SIMPLE_WIDTH + 120}px; margin:12px auto;"

        specs.append({"id": cid, "spec": spec})
        parts.append(
            f'<div class="metric-chart{active_cls}" '
            f'data-chart-group="{chart_group}" data-metric="{mc}">'
            f'<div class="chart-box" style="{box_style}">'
            f'<div id="{cid}"></div></div></div>'
        )

    return "\n".join(parts), plot_id


# ---------------------------------------------------------------------------
# Page builder
# ---------------------------------------------------------------------------

# Sections to render: (stats key, display title, dim column for facet color)
_SECTIONS = [
    ("by_term",       "By Term",          None),
    ("by_term_grade", "By Term × Grade",  "grade"),
    ("by_term_fico",  "By Term × FICO",   "fico_bkt"),
    ("by_term_rate",  "By Term × Rate",   "rate_bkt"),
]


def build_summary_page(
    stats: dict,
    *,
    specs: list[dict],
    plot_id: int = 0,
) -> tuple[str, int]:
    """Render the Summary Statistics page from input-tape stats.

    Appends Vega specs to *specs* (mutated) and returns ``(html, next_plot_id)``.
    """
    if not stats:
        return "", plot_id

    parts: list[str] = [_kpi_section(stats)]
    parts.append('<div class="section-toggle"><span class="label">Sections:</span></div>')
    parts.append('<button class="gradient-toggle">Heatmap On</button>')

    for key, title, color_col in _SECTIONS:
        if key not in stats:
            continue
        section_html: list[str] = [f'<h2>{title}</h2>']
        section_html.append(
            f'<div class="table-box">'
            f'{df_to_html_table(stats[key], TABLE_FMT, gradient_cols=_GRADIENT_COLS)}'
            f'</div>'
        )
        chart_html, plot_id = _section_chart(
            stats[key], section_key=key, color_col=color_col,
            title_prefix=title, specs=specs, plot_id=plot_id,
        )
        section_html.append(chart_html)
        parts.append(
            f'<div class="report-section" data-section="{title}">'
            f'{"".join(section_html)}'
            f'</div>'
        )

    return "\n".join(parts), plot_id
