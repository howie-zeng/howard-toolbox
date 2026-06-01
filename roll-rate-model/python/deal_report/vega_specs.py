"""Vega-Lite spec builders for the deal report charts.

All builders return plain dicts (JSON-serialisable) following the
Vega-Lite v5 schema.  Specs are accumulated in a list during page assembly
and embedded as a single ``<script type="application/json">`` payload that
the page-level JS picks up and renders client-side.
"""
from __future__ import annotations

from .theme import (
    CARD_BG,
    CHART_FULL_WIDTH,
    CHART_HEIGHT,
    CURVE_PALETTE,
    TEXT,
    TEXT_DIM,
)

# ---------------------------------------------------------------------------
# Shared Vega-Lite config (theme tokens applied to every spec)
# ---------------------------------------------------------------------------

VEGA_CONFIG = {
    "view": {"stroke": None},
    "background": CARD_BG,
    "axis": {
        "labelColor": TEXT, "titleColor": TEXT,
        "gridColor": "#e0e0e0", "domainColor": "#ced4da", "tickColor": "#ced4da",
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
            f"datum.metric === '{field}' ? '{label}'"
            for field, label in zip(y_fields, y_labels, strict=True)
        ) + " : datum.metric"
        transforms.append({"calculate": cases, "as": "metric"})
    return transforms


# ---------------------------------------------------------------------------
# Line chart with hover tooltip
# ---------------------------------------------------------------------------

def line_spec(
    records: list[dict], x: str, y_fields: list[str], *,
    title: str = "",
    y_format: str = ",.0f",
    width: int = CHART_FULL_WIDTH,
    height: int = CHART_HEIGHT,
    colors: list[str] | None = None,
    x_domain_max: int | None = None,
    y_labels: list[str] | None = None,
) -> dict:
    """Multi-series line chart with nearest-point tooltip."""
    colors = colors or CURVE_PALETTE
    display = y_labels if y_labels and len(y_labels) == len(y_fields) else y_fields
    color_range = [colors[i % len(colors)] for i in range(len(y_fields))]

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
                    "y": {"field": "value", "type": "quantitative", "title": "",
                          "axis": {"grid": True, "format": y_format, "gridDash": [2, 4]}},
                    "color": {"field": "metric", "type": "nominal", "title": "",
                              "scale": {"domain": display, "range": color_range},
                              "legend": {"orient": "right", "labelLimit": 200,
                                         "symbolType": "stroke",
                                         "symbolStrokeWidth": 2.5,
                                         "symbolSize": 200}},
                },
            },
            {
                "mark": {"type": "circle", "size": 60, "opacity": 0},
                "selection": {
                    "hover": {"type": "single", "nearest": True,
                              "on": "pointerover", "encodings": ["x"], "empty": "none"}
                },
                "encoding": {
                    "x": {"field": x, "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                    "color": {"field": "metric", "type": "nominal"},
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
                      "legend": {"orient": "right", "labelLimit": 200,
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
                             "legend": {"orient": "right", "labelLimit": 200}}
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
