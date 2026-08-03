"""Vega-Lite spec builders for the deal report charts.

All builders return plain dicts (JSON-serialisable) following the
Vega-Lite v5 schema.  Specs are accumulated in a list during page assembly
and embedded as a single ``<script type="application/json">`` payload that
the page-level JS picks up and renders client-side.
"""
from __future__ import annotations

from .theme import (
    ACCENT, BORDER, CARD_BG, CURVE_PALETTE, TEXT, TEXT_DIM,
    CHART_HALF_WIDTH, CHART_FULL_WIDTH, CHART_HEIGHT,
)


# ---------------------------------------------------------------------------
# Shared Vega-Lite config (theme tokens applied to every spec)
# ---------------------------------------------------------------------------

VEGA_CONFIG = {
    "view": {"stroke": None},
    "background": CARD_BG,
    "axis": {
        "labelColor": TEXT, "titleColor": TEXT,
        "gridColor": "#eef1f5", "gridOpacity": 0.9,
        "domainColor": "#ced4da", "tickColor": "#ced4da",
    },
    "legend": {"labelColor": TEXT, "titleColor": TEXT},
    "title": {"color": TEXT, "subtitleColor": TEXT_DIM},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _x_scale(x_domain_max: int | None) -> dict:
    scale = {"nice": False}
    if x_domain_max is not None:
        scale["domain"] = [0, x_domain_max]
        scale["clamp"] = True
    return scale


def _fold_with_relabel(y_fields: list[str], y_labels: list[str] | None) -> list[dict]:
    """Build the ``transform`` list to fold y_fields and optionally relabel them."""
    transforms: list[dict] = [{"fold": y_fields, "as": ["metric", "value"]}]
    if y_labels and y_labels != y_fields:
        cases = " : ".join(
            f"datum.metric === '{f}' ? '{l}'" for f, l in zip(y_fields, y_labels)
        ) + " : datum.metric"
        transforms.append({"calculate": cases, "as": "metric"})
    return transforms


# ---------------------------------------------------------------------------
# Line chart with hover tooltip
# ---------------------------------------------------------------------------

def _clip_ymax(records: list[dict], y_fields: list[str], pct: float) -> float | None:
    """y-axis cap = the `pct`-th percentile of the values, +50% headroom.

    Used to keep the meaningful body of a curve readable when a few runoff-tail
    points spike (e.g. CDR/CPR -> ~100% as the pool drains). Points above the cap
    are clipped by the line mark instead of compressing the whole axis.
    """
    vals = sorted(float(r[f]) for r in records
                  for f in y_fields if isinstance(r.get(f), (int, float)))
    if not vals:
        return None
    k = (len(vals) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(vals) - 1)
    p = vals[lo] + (vals[hi] - vals[lo]) * (k - lo)
    ymax = p * 1.5
    return ymax if ymax > 0 else None


def line_spec(
    records: list[dict], x: str, y_fields: list[str], *,
    title: str = "",
    y_format: str = ",.0f",
    width: int = CHART_FULL_WIDTH,
    height: int = CHART_HEIGHT,
    colors: list[str] | None = None,
    x_domain_max: int | None = None,
    y_labels: list[str] | None = None,
    y_clip_pct: float | None = None,
) -> dict:
    """Multi-series line chart with nearest-point tooltip.

    `y_clip_pct` caps the y-axis at that percentile (+headroom) so runoff-tail
    spikes don't squash the meaningful range; the line clips past the cap.
    """
    colors = colors or CURVE_PALETTE
    display = y_labels if y_labels and len(y_labels) == len(y_fields) else y_fields
    color_range = [colors[i % len(colors)] for i in range(len(y_fields))]

    ymax = _clip_ymax(records, y_fields, y_clip_pct) if y_clip_pct is not None else None
    line_y = {"field": "value", "type": "quantitative", "title": "",
              "axis": {"grid": True, "format": y_format, "gridDash": [2, 4]}}
    circle_y = {"field": "value", "type": "quantitative"}
    if ymax is not None:
        line_y["scale"] = {"domain": [0, ymax]}
        circle_y["scale"] = {"domain": [0, ymax]}

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": width, "height": height, "title": title,
        "data": {"values": records},
        "transform": _fold_with_relabel(y_fields, y_labels),
        "layer": [
            {
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.5},
                "encoding": {
                    "x": {"field": x, "type": "quantitative", "title": "Period",
                          "axis": {"grid": True, "format": "d", "gridDash": [2, 4]},
                          "scale": _x_scale(x_domain_max)},
                    "y": line_y,
                    "color": {"field": "metric", "type": "nominal", "title": "",
                              "scale": {"domain": display, "range": color_range},
                              "legend": {"orient": "top", "labelLimit": 200,
                                         "symbolType": "stroke",
                                         "symbolStrokeWidth": 2.5,
                                         "symbolSize": 200}},
                },
            },
            {
                "mark": {"type": "circle", "size": 60, "opacity": 0, "clip": True},
                "selection": {
                    "hover": {"type": "single", "nearest": True,
                              "on": "pointerover", "encodings": ["x"], "empty": "none"}
                },
                "encoding": {
                    "x": {"field": x, "type": "quantitative"},
                    "y": circle_y,
                    # Pass the SAME color scale as the line layer; without it,
                    # Vega-Lite makes an independent scale for the hover circle
                    # using the default category palette, so dots don't match.
                    "color": {"field": "metric", "type": "nominal", "legend": None,
                              "scale": {"domain": display, "range": color_range}},
                    "opacity": {"condition": {"selection": "hover", "value": 1}, "value": 0},
                    "tooltip": [
                        {"field": x, "type": "quantitative", "title": "Period", "format": "d"},
                        {"field": "metric", "type": "nominal", "title": "Series"},
                        {"field": "value", "type": "quantitative", "format": y_format},
                    ],
                },
            },
            {
                "mark": {"type": "rule", "color": "#adb5bd", "strokeDash": [4, 4]},
                "encoding": {"x": {"field": x, "type": "quantitative"}},
                "transform": [{"filter": {"selection": "hover"}}],
            },
        ],
        "config": VEGA_CONFIG,
    }


# ---------------------------------------------------------------------------
# Rate chart with toggleable per-cohort overlay
# ---------------------------------------------------------------------------

def rate_cohort_spec(
    agg_records: list[dict], cohort_records: list[dict], *,
    title: str, y_format: str, color: str,
    series_label: str | None = None,
    x_domain_max: int | None = None,
    width: int = CHART_HALF_WIDTH, height: int = CHART_HEIGHT,
) -> dict:
    """A bold aggregate rate line with faint per-cohort lines behind it.

    A native checkbox (Vega param ``show_cohorts``) toggles the cohort layer's
    opacity. The y-axis auto-fits all data (aggregate + cohorts). Cohorts get a
    right-side legend.
    `agg_records`: [{period, value, series}], `cohort_records`: [{period, cohort, value}].
    """
    series_label = series_label or title
    x_scale = _x_scale(x_domain_max)
    cohort_domain = sorted({r["cohort"] for r in cohort_records})
    # Combined point set for ONE consistent nearest-hover (aggregate + cohorts),
    # matching the tooltip-bubble + rule hover used on the other charts.
    hover_records = (
        [{"period": r["period"], "value": r["value"], "series": series_label, "kind": "agg"}
         for r in agg_records]
        + [{"period": r["period"], "value": r["value"], "series": r["cohort"],
            "cohort": r["cohort"], "kind": "cohort"}
           for r in cohort_records]
    )
    # Explicit combined domain keeps hover-dot colours matching the lines.
    # The hover-dot range must enumerate each cohort's palette colour explicitly,
    # cycling the palette by modulo against `len(cohort_domain)` to match the
    # cohort line layer. Otherwise: when cohorts exceed palette size, Vega cycles
    # `[color] + CURVE_PALETTE` (length 1 + N_palette) by a DIFFERENT modulo than
    # the cohort line cycles `CURVE_PALETTE` (length N_palette), and the colours
    # shift by 1 starting at the (N_palette)-th cohort.
    cohort_range = [CURVE_PALETTE[i % len(CURVE_PALETTE)] for i in range(len(cohort_domain))]
    hover_color = {"field": "series", "type": "nominal", "legend": None,
                   "scale": {"domain": [series_label] + cohort_domain,
                             "range": [color] + cohort_range}}

    def y_enc(axis):
        e = {"field": "value", "type": "quantitative", "title": ""}
        if axis:
            e["axis"] = {"grid": True, "format": y_format, "gridDash": [2, 4]}
        return e

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": width, "height": height, "title": title,
        "padding": {"left": 5, "top": 5, "right": 8, "bottom": 5},
        # Keep each layer's colour scale separate: cohort lines use the palette
        # (no legend); the aggregate line keeps its single semantic colour + legend.
        "resolve": {"scale": {"color": "independent"},
                    "legend": {"color": "independent"}},
        "params": [
            {"name": "show_cohorts", "value": False,
             "bind": {"input": "checkbox", "name": "Show cohort curves  "}},
            # highlighted cohort label — set by the HTML legend's click handler
            {"name": "hl_cohort", "value": None},
        ],
        "layer": [
            {   # faint per-cohort lines — filtered by the toggle (data removed when off,
                # so the y-axis still auto-resizes). The colour scale uses an EXPLICIT
                # domain so it stays valid even with no rows — an empty nominal colour
                # scale otherwise corrupts the SVG viewBox (charts become giant squares).
                "data": {"values": cohort_records},
                "transform": [{"filter": "show_cohorts"}],
                "mark": {"type": "line", "clip": True},
                "encoding": {
                    "x": {"field": "period", "type": "quantitative", "title": "Period",
                          "axis": {"grid": True, "format": "d", "gridDash": [2, 4]},
                          "scale": x_scale},
                    "y": y_enc(True),
                    # No Vega legend — a dynamic HTML legend (toggled by show_cohorts)
                    # is rendered alongside the chart instead. A Vega legend here would
                    # need an empty colour domain to be dynamic, which breaks the viewBox.
                    "color": {"field": "cohort", "type": "nominal",
                              "scale": {"domain": cohort_domain, "range": CURVE_PALETTE},
                              "legend": None},
                    "opacity": {"condition": {"test": "hl_cohort === datum.cohort", "value": 0.95},
                                "value": 0.3},
                    "strokeWidth": {"condition": {"test": "hl_cohort === datum.cohort", "value": 3},
                                    "value": 1.2},
                },
            },
            {   # bold portfolio aggregate line
                "data": {"values": agg_records},
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.5},
                "encoding": {
                    "x": {"field": "period", "type": "quantitative", "scale": x_scale},
                    "y": y_enc(False),
                    "color": {"field": "series", "type": "nominal", "title": "",
                              "scale": {"domain": [series_label], "range": [color]},
                              "legend": {"orient": "top", "symbolType": "stroke",
                                         "symbolStrokeWidth": 2.5, "symbolSize": 200}},
                },
            },
            {   # vertical guide at the hovered period (matches the other charts)
                "data": {"values": hover_records},
                "transform": [{"filter": {"param": "hpt", "empty": False}}],
                "mark": {"type": "rule", "color": "#868e96", "strokeDash": [4, 4]},
                "encoding": {"x": {"field": "period", "type": "quantitative", "scale": x_scale}},
            },
            {   # nearest-point hover — colored dot + standard tooltip bubble, consistent
                # with the rest of the report. Only the aggregate and the BOLDED
                # (legend-clicked) cohorts are hover targets — faint/unselected cohorts
                # don't respond.
                "data": {"values": hover_records},
                "transform": [{"filter": "datum.kind === 'agg' || (show_cohorts && datum.cohort === hl_cohort)"}],
                "params": [{"name": "hpt",
                            "select": {"type": "point", "nearest": True,
                                       "on": "pointerover", "clear": "pointerout"}}],
                "mark": {"type": "circle", "size": 55, "clip": True},
                "encoding": {
                    "x": {"field": "period", "type": "quantitative", "scale": x_scale},
                    "y": y_enc(False),
                    "color": hover_color,
                    "opacity": {"condition": {"param": "hpt", "empty": False, "value": 1}, "value": 0},
                    "tooltip": [{"field": "series", "type": "nominal", "title": ""},
                                {"field": "period", "type": "quantitative", "title": "Period", "format": "d"},
                                {"field": "value", "type": "quantitative", "title": title, "format": y_format}],
                },
            },
        ],
        "config": VEGA_CONFIG,
    }


# ---------------------------------------------------------------------------
# Stacked area
# ---------------------------------------------------------------------------

def area_spec(
    records: list[dict], x: str, y_fields: list[str], *,
    title: str = "",
    y_format: str = ",.0f",
    width: int = CHART_FULL_WIDTH,
    height: int = CHART_HEIGHT,
    colors: list[str] | None = None,
    x_domain_max: int | None = None,
    y_labels: list[str] | None = None,
) -> dict:
    """Stacked area chart with hover tooltips."""
    colors = colors or CURVE_PALETTE
    display = y_labels if y_labels and len(y_labels) == len(y_fields) else y_fields
    color_range = [colors[i % len(colors)] for i in range(len(y_fields))]

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": width, "height": height, "title": title,
        "data": {"values": records},
        "transform": _fold_with_relabel(y_fields, y_labels),
        "mark": {"type": "area", "clip": True, "opacity": 0.65, "line": True},
        "encoding": {
            "x": {"field": x, "type": "quantitative", "title": "Period",
                  "axis": {"grid": True, "format": "d", "gridDash": [2, 4]},
                  "scale": _x_scale(x_domain_max)},
            "y": {"field": "value", "type": "quantitative", "title": "",
                  "axis": {"grid": True, "format": y_format, "gridDash": [2, 4]},
                  "stack": True},
            "color": {"field": "metric", "type": "nominal", "title": "",
                      "scale": {"domain": display, "range": color_range},
                      "legend": {"orient": "top", "labelLimit": 200,
                                 "symbolType": "stroke",
                                 "symbolStrokeWidth": 2.5,
                                 "symbolSize": 200}},
            "tooltip": [
                {"field": x, "type": "quantitative", "title": "Period", "format": "d"},
                {"field": "metric", "type": "nominal", "title": "Series"},
                {"field": "value", "type": "quantitative", "format": y_format},
            ],
        },
        "config": VEGA_CONFIG,
    }


# ---------------------------------------------------------------------------
# Bar chart (used by summary stats)
# ---------------------------------------------------------------------------

def bar_spec(
    records: list[dict], x: str, y: str, *,
    color: str | None = None,
    title: str = "",
    y_format: str = ",.0f",
    width: int = CHART_FULL_WIDTH,
    height: int = CHART_HEIGHT,
    colors: list[str] | None = None,
    x_sort: list | None = None,
) -> dict:
    """Vertical bar chart, optionally grouped by a colour dimension."""
    colors = colors or CURVE_PALETTE
    enc_x: dict = {"field": x, "type": "nominal", "title": x, "axis": {"labelAngle": 0}}
    if x_sort is not None:
        enc_x["sort"] = x_sort
    encoding: dict = {
        "x": enc_x,
        "y": {"field": y, "type": "quantitative", "title": "",
              "axis": {"format": y_format}},
        "tooltip": [
            {"field": x, "type": "nominal"},
            {"field": y, "type": "quantitative", "format": y_format},
        ],
    }
    selection: dict = {}
    if color:
        color_vals = sorted({r[color] for r in records if r.get(color) is not None})
        color_range = [colors[i % len(colors)] for i in range(len(color_vals))]
        encoding["color"] = {"field": color, "type": "nominal", "title": color,
                             "scale": {"domain": color_vals, "range": color_range},
                             "legend": {"orient": "top", "labelLimit": 200}}
        encoding["xOffset"] = {"field": color, "type": "nominal"}
        encoding["tooltip"].append({"field": color, "type": "nominal"})
        selection["legend_sel"] = {"type": "multi", "fields": [color], "bind": "legend"}
        encoding["opacity"] = {"condition": {"selection": "legend_sel", "value": 1}, "value": 0.15}

    spec: dict = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": width, "height": height, "title": title,
        "data": {"values": records},
        "mark": {"type": "bar", "cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3},
        "encoding": encoding,
        "config": VEGA_CONFIG,
    }
    if selection:
        spec["selection"] = selection
    return spec


def faceted_bar_spec(
    records: list[dict], dim_col: str, y: str, y_format: str,
    source_order: list[str], source_colors: list[str],
    term_order: list[str], dim_order: list[str],
    facet_w: int, height: int, *, title: str = "",
) -> dict:
    """Faceted bar chart: one panel per term, x = dimension, colour = source."""
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": title,
        "data": {"values": records},
        "columns": len(term_order),
        "spacing": 5,
        "resolve": {"scale": {"y": "shared"}},
        "facet": {
            "field": "term", "type": "nominal", "title": None,
            "header": {"labelFontWeight": "bold", "labelFontSize": 13, "title": None},
            "sort": term_order,
        },
        "spec": {
            "width": facet_w, "height": height,
            "selection": {"legend_sel": {"type": "multi", "fields": ["Source"], "bind": "legend"}},
            "mark": {"type": "bar", "cornerRadiusTopLeft": 2, "cornerRadiusTopRight": 2},
            "encoding": {
                "x": {"field": dim_col, "type": "nominal", "title": None,
                      "sort": dim_order, "axis": {"labelAngle": 0, "labelLimit": 80}},
                "y": {"field": y, "type": "quantitative", "title": y,
                      "axis": {"format": y_format}},
                "color": {"field": "Source", "type": "nominal",
                          "scale": {"domain": source_order, "range": source_colors},
                          "legend": {"orient": "top"}},
                "xOffset": {"field": "Source", "type": "nominal"},
                "opacity": {"condition": {"selection": "legend_sel", "value": 1}, "value": 0.15},
                "tooltip": [
                    {"field": "term", "type": "nominal", "title": "Term"},
                    {"field": dim_col, "type": "nominal"},
                    {"field": "Source", "type": "nominal"},
                    {"field": y, "type": "quantitative", "format": y_format},
                ],
            },
        },
        "autosize": {"type": "fit", "contains": "padding"},
        "config": VEGA_CONFIG,
    }
