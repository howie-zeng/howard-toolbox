"""Value formatters and small HTML widget renderers (KPI grid, tables).

Pure helpers — no imports of theme constants needed at the top level since
each function takes whatever it needs as an argument.  Kept out of the CSS/JS
bundle so they can be unit-tested without HTML coupling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Scalar formatters
# ---------------------------------------------------------------------------

def fmt_dollars(val) -> str:
    """Compact dollar formatter: $1.23B / $4.56M / $7.89K / $123."""
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return "N/A"
    if abs(val) >= 1e9:
        return f"${val / 1e9:,.2f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:,.2f}M"
    if abs(val) >= 1e3:
        return f"${val / 1e3:,.1f}K"
    return f"${val:,.0f}"


def fmt_pct(val) -> str:
    """Format a fraction as ``XX.XX%``."""
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return "N/A"
    return f"{val * 100:.2f}%"


def fmt_cell(val, spec: str | None) -> str:
    """Format a single cell value using a ``"$"``/``"%"``-aware spec.

    Examples::

        fmt_cell(1234.56, "$,.0f")  -> "$1,235"
        fmt_cell(0.0421,  ".2%")    -> "4.21%"
        fmt_cell(680,     ",.0f")   -> "680"
    """
    try:
        if val is None or pd.isna(val):
            return "—"
    except (TypeError, ValueError):
        pass
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return "—"
    if isinstance(val, str):
        return val
    if not spec:
        return f"{val:,.2f}" if isinstance(val, float) else str(val)

    prefix, suffix = "", ""
    if spec.startswith("$"):
        prefix, spec = "$", spec[1:]
    # Strip a trailing "%" *only* when the format wouldn't already do the right
    # thing on its own.  Python's ``f"{0.05:.2%}"`` already renders "5.00%", so
    # ".2%" must be left alone.  But ".2f%" / ".0f%" are "format the raw number
    # then append %" — Python doesn't grok those, so we strip the % and tack
    # it on after.  The decision rule is "is the char before % an integer?",
    # which is what indicates a d3-style ``.<n>%`` spec.
    if spec.endswith("%") and len(spec) >= 2 and spec[-2] in "fFeEgGd,":
        spec, suffix = spec[:-1], "%"
    return f"{prefix}{val:{spec}}{suffix}"


# ---------------------------------------------------------------------------
# JSON-safe records (NaN/Inf -> None)
# ---------------------------------------------------------------------------

def json_safe(records: list[dict]) -> list[dict]:
    """Replace NaN/Inf with ``None`` for embed-in-JSON safety."""
    out = []
    for rec in records:
        row = {}
        for k, v in rec.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                row[k] = None
            else:
                row[k] = v
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# KPI grid
# ---------------------------------------------------------------------------

def kpi_grid(items: list[tuple]) -> str:
    """Render KPI cards as a CSS grid.

    Each item is ``(label, value, sub)`` where ``sub`` may be None.
    """
    parts = ['<div class="kpi-grid">']
    for label, value, sub in items:
        sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
        parts.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'{sub_html}'
            f'</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# DataFrame -> HTML table
# ---------------------------------------------------------------------------

# Standard column formatters for input-stats tables
TABLE_FMT = {
    "term": ",.0f",
    "Count": ",.0f",
    "Balance": "$,.0f",
    "Bal %": ".2f%",
    "Avg Bal": "$,.0f",
    "RATE": ".2%",
    "FICO": ",.0f",
    "DTI": ".2%",
}


def df_to_html_table(
    df: pd.DataFrame,
    fmt: dict | None = None,
    *,
    gradient_cols: list[str] | None = None,
) -> str:
    """Render a DataFrame as a styled HTML table.

    Rows whose first cell contains ``"(TOTAL)"`` get the ``total-row`` class.
    Columns named in *gradient_cols* receive per-cell heatmap backgrounds
    (TOTAL rows excluded from the colour ramp); the ``data-gradient`` attribute
    lets the page-level "Heatmap On/Off" toggle switch them off in bulk.
    """
    fmt = fmt or {}
    gradient_cols = gradient_cols or []

    # Per-column (min, max) for the heatmap, computed from non-TOTAL rows only.
    col_ranges: dict[str, tuple[float, float]] = {}
    if gradient_cols:
        non_total = strip_total_rows(df)
        for col in gradient_cols:
            if col not in non_total.columns:
                continue
            vals = pd.to_numeric(non_total[col], errors="coerce").dropna()
            if len(vals) > 0 and vals.min() != vals.max():
                col_ranges[col] = (float(vals.min()), float(vals.max()))

    rows = ['<table class="stats">']
    rows.append("<tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr>")
    for _, row in df.iterrows():
        first = str(row.iloc[0])
        is_total = "(TOTAL)" in first.upper()
        cls = ' class="total-row"' if is_total else ""
        cells: list[str] = []
        for c in df.columns:
            val = row[c]
            attrs = ""
            if not is_total and c in col_ranges:
                cmin, cmax = col_ranges[c]
                bg = gradient_bg(val, cmin, cmax, c)
                if bg:
                    attrs = f' data-gradient="1" style="{bg}"'
            cells.append(f'<td{attrs}>{fmt_cell(val, fmt.get(c))}</td>')
        rows.append(f"<tr{cls}>{''.join(cells)}</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def strip_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop ``(TOTAL)`` rows from a stats DataFrame."""
    first = df.columns[0]
    return df[~df[first].astype(str).str.contains(r"\(TOTAL\)", case=False, na=False)].copy()


# ---------------------------------------------------------------------------
# Heatmap gradient (per-cell background colour for stats tables)
# ---------------------------------------------------------------------------

def gradient_bg(val, col_min: float, col_max: float, metric: str) -> str:
    """Return inline ``background:rgb(r,g,b);`` for a heatmap cell.

    The hue ramp depends on the metric — RATE / FICO have semantically meaningful
    "good"/"bad" directions.  Returns ``""`` for non-numeric or NaN values.
    """
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if np.isnan(v) or np.isinf(v) or col_max == col_min:
        return ""

    t = max(0.0, min(1.0, (v - col_min) / (col_max - col_min)))

    if metric == "RATE":
        if t < 0.5:
            r, g, b = int(140 + t * 230), int(200 - t * 60), int(140 - t * 200)
        else:
            r, g, b = 255, int(170 - (t - 0.5) * 240), 40
    elif metric == "FICO":
        if t < 0.5:
            r, g, b = 255, int(50 + t * 240), 40
        else:
            r, g, b = int(255 - (t - 0.5) * 230), int(170 + (t - 0.5) * 60), int(40 + (t - 0.5) * 200)
    else:
        r, g, b = int(255 - t * 135), int(255 - t * 105), int(255 - t * 40)

    return f"background:rgb({r},{g},{b});"
