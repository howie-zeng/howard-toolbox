"""Interactive HTML model report using Vega-Lite.

Generates a self-contained HTML with:
  - Top-level tabs per from-status (from C, from D1M, ...)
  - Sub-tabs per transition model (from C -> D1M, from C -> PIF, ...)
  - Categorical coefficient table
  - Interactive smooth curves with hover crosshair, clickable legends
  - Expand button -> modal with zoom/pan
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from .data_prep import (
    ModelLink,
    load_all_coef,
    build_all_models,
    DEFAULT_STATUS_TO_ROLL,
)


def generate_model_report_html(
    coef_dir: str,
    config: Dict[str, Any],
    output_path: str = None,
) -> None:
    status_to_roll = config.get("status_to_roll", DEFAULT_STATUS_TO_ROLL)
    from_statuses = list(status_to_roll.keys())
    coef_by_from = load_all_coef(coef_dir, from_statuses)
    all_models = build_all_models(coef_by_from)
    if output_path is None:
        output_path = os.path.join(coef_dir, "model_report.html")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    coef_version = os.path.basename(coef_dir)
    html = _build_html(status_to_roll, all_models, coef_version)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Model report: {output_path}")


def _build_html(status_to_roll, all_models, coef_version):
    from_statuses = list(status_to_roll.keys())
    top_tabs_html, pages_html = [], []
    all_specs = {}

    for fi, from_s in enumerate(from_statuses):
        to_list = [s for s in status_to_roll[from_s] if s != from_s]
        page_id = f"page-{from_s}"
        active = " active" if fi == 0 else ""
        top_tabs_html.append(
            f'<a href="#" data-page="{page_id}" class="{active.strip()}">from {from_s}</a>')
        sub_tabs, sub_pages = [], []
        for ti, to_s in enumerate(to_list):
            model_name = f"from{from_s}_{to_s}"
            link = all_models.get(model_name)
            if link is None:
                continue
            sub_id = f"sub-{from_s}-{to_s}"
            sa = " active" if ti == 0 else ""
            sub_tabs.append(
                f'<a href="#" data-sub="{sub_id}" data-parent="{page_id}" '
                f'class="sub-tab{sa}">{from_s} &rarr; {to_s}</a>')
            cat_html = _build_cat_table(link, model_name)
            smooth_html, specs = _build_smooth_charts(link, model_name, from_s, to_s)
            all_specs.update(specs)
            sub_pages.append(f'<div id="{sub_id}" class="sub-page{sa}">\n{cat_html}\n{smooth_html}\n</div>')
        pages_html.append(
            f'<div id="{page_id}" class="report-page{active}"><div class="content">\n'
            f'<div class="sub-nav">{"".join(sub_tabs)}</div>\n'
            f'{"".join(sub_pages)}\n</div></div>')

    return _TEMPLATE.format(
        coef_version=coef_version,
        top_tabs="\n".join(top_tabs_html),
        pages="\n".join(pages_html),
        specs_json=json.dumps(all_specs, separators=(",", ":")))


# ---------------------------------------------------------------------------
# Categorical table
# ---------------------------------------------------------------------------

def _build_cat_table(link: ModelLink, model_name: str) -> str:
    rows = [f'<tr class="total-row"><td>(Intercept)</td><td></td>'
            f'<td class="{"pos" if link.intercept >= 0 else "neg"}">'
            f'{link.intercept:+.6f}</td></tr>']
    for items in [
        [(k, v) for k, v in link.lookups.items() if "|" not in k],
        [(k, v) for k, v in link.lookups.items() if "|" in k],
    ]:
        for var_name, lookup in items:
            for i, (level, val) in enumerate(lookup.table.items()):
                label = var_name if i == 0 else ""
                cls = "pos" if val >= 0 else "neg"
                rows.append(f'<tr><td class="var-name">{label}</td>'
                            f'<td>{level}</td><td class="{cls}">{val:+.6f}</td></tr>')
    return (
        f'<h2>{model_name} &mdash; Coefficients</h2>\n'
        f'<div class="table-box"><table class="coef-table">\n'
        f'<thead><tr><th>Variable</th><th>Level</th><th>Coefficient</th></tr></thead>\n'
        f'<tbody>{"".join(rows)}</tbody></table></div>')


# ---------------------------------------------------------------------------
# Smooth charts
# ---------------------------------------------------------------------------

def _build_smooth_charts(link, model_name, from_s, to_s):
    specs = {}
    parts = []
    smooth_items = list(link.smooths.items())
    sbf_items = list(link.smooth_by_factors.items())
    sbn_items = list(link.smooth_by_nums.items())
    if not smooth_items and not sbf_items and not sbn_items:
        return "", {}

    parts.append(f'<h2>{model_name} &mdash; Smooths</h2>\n<div class="chart-grid">')

    for var_name, smooth in smooth_items:
        did = f"chart-{from_s}-{to_s}-{var_name}".replace(" ", "_")
        data = _smooth_to_data(smooth)
        trimmed = _trim_outliers(data)
        specs[did] = {
            "thumb": _line_spec(trimmed, var_name, f"s({var_name})", 420, 240),
            "full":  _line_spec(data, var_name, f"s({var_name})", 900, 500, zoom=True),
        }
        parts.append(_chart_div(did))

    for (sv, fv), sbf in sbf_items:
        did = f"chart-{from_s}-{to_s}-{sv}-by-{fv}".replace(" ", "_")
        data = []
        for fval, smooth in sbf.smooths.items():
            data.extend(_smooth_to_data(smooth, factor=fval))
        trimmed = _trim_outliers(data)
        specs[did] = {
            "thumb": _multi_spec(trimmed, sv, f"s({sv}):{fv}", fv, 420, 260),
            "full":  _multi_spec(data, sv, f"s({sv}):{fv}", fv, 900, 500, zoom=True),
        }
        parts.append(_chart_div(did))

    for (sv, wv), sbn in sbn_items:
        if sbn.smooth:
            did = f"chart-{from_s}-{to_s}-{sv}-by-{wv}".replace(" ", "_")
            data = _smooth_to_data(sbn.smooth)
            trimmed = _trim_outliers(data)
            specs[did] = {
                "thumb": _line_spec(trimmed, sv, f"s({sv})*{wv}", 420, 240),
                "full":  _line_spec(data, sv, f"s({sv})*{wv}", 900, 500, zoom=True),
            }
            parts.append(_chart_div(did))

    parts.append('</div>')
    return "\n".join(parts), specs


def _chart_div(div_id):
    return (f'<div class="chart-box">'
            f'<span class="expand-btn" onclick="openModal(\'{div_id}\')" title="Expand">&#x26F6;</span>'
            f'<div id="{div_id}" class="vega-chart"></div></div>')


def _smooth_to_data(smooth, factor=None, n_pts=200):
    data = []
    step = (smooth.xmax - smooth.xmin) / (n_pts - 1) if n_pts > 1 else 0
    for i in range(n_pts):
        x = smooth.xmin + step * i
        y = smooth.eval(x)
        row = {"x": round(x, 6), "y": round(y, 6)}
        if factor is not None:
            row["factor"] = str(factor)
        data.append(row)
    return data


def _x_axis_cfg(data):
    """Return (format_str, axis_dict) that avoids commas, .0, and duplicate ticks."""
    xs = [d["x"] for d in data]
    if all(x == int(x) for x in xs):
        return "d", {"format": "d", "tickMinStep": 1}
    return ".4~g", {"format": ".4~g"}


def _trim_outliers(data, pct_lo=2, pct_hi=98):
    ys = sorted(d["y"] for d in data)
    if len(ys) < 10:
        return data
    lo = ys[int(len(ys) * pct_lo / 100)]
    hi = ys[int(len(ys) * pct_hi / 100)]
    margin = (hi - lo) * 0.05
    return [d for d in data if lo - margin <= d["y"] <= hi + margin]


# ---------------------------------------------------------------------------
# Vega-Lite specs  (v4 selection API for compat)
# ---------------------------------------------------------------------------

# Hand-picked palette: distinct, muted, professional
_COLORS = ["#1d4ed8", "#e97320", "#059669", "#9333ea", "#dc2626",
           "#0891b2", "#ca8a04", "#be185d", "#4f46e5", "#65a30d"]

_VEGA_CFG = {
    "view": {"stroke": None},
    "background": "#f8f9fa",
    "axis": {"labelColor": "#212529", "titleColor": "#212529",
             "gridColor": "#e0e0e0", "gridDash": [2, 4],
             "domainColor": "#ced4da", "tickColor": "#ced4da",
             "labelFontSize": 10, "titleFontSize": 11},
    "legend": {"labelColor": "#212529", "titleColor": "#212529",
               "labelFontSize": 10, "titleFontSize": 11,
               "symbolType": "stroke", "symbolStrokeWidth": 3, "symbolSize": 200},
    "title": {"color": "#212529"},
}


def _line_spec(data, x_label, y_label, w, h, zoom=False):
    """Single-series line with tooltip."""
    xfmt, x_axis = _x_axis_cfg(data)
    tooltip = [
        {"field": "x", "type": "quantitative", "title": x_label, "format": xfmt},
        {"field": "y", "type": "quantitative", "title": y_label, "format": ".4f"},
    ]
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": w, "height": h,
        "data": {"values": data},
        "mark": {"type": "line", "color": _COLORS[0], "strokeWidth": 2.5,
                 "point": False},
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "title": x_label,
                   "scale": {"zero": False}, "axis": x_axis},
            "y": {"field": "y", "type": "quantitative", "title": y_label},
            "tooltip": tooltip,
        },
        "config": _VEGA_CFG,
    }
    if zoom:
        spec["params"] = [{"name": "grid", "select": "interval", "bind": "scales"}]
    return spec


def _multi_spec(data, x_label, y_label, factor_label, w, h, zoom=False):
    """Multi-series line with clickable legend."""
    xfmt, x_axis = _x_axis_cfg(data)
    tooltip = [
        {"field": "x", "type": "quantitative", "title": x_label, "format": xfmt},
        {"field": "y", "type": "quantitative", "title": y_label, "format": ".4f"},
        {"field": "factor", "type": "nominal", "title": factor_label},
    ]
    legend_orient = "right" if zoom else "bottom"
    legend_cols = None if zoom else {"columns": 4}
    color_enc = {"field": "factor", "type": "nominal", "title": factor_label,
                 "scale": {"range": _COLORS},
                 "legend": {"orient": legend_orient, "labelLimit": 200,
                            **(legend_cols or {})}}
    params = [
        {"name": "legend_sel", "select": {"type": "point", "fields": ["factor"]},
         "bind": "legend"},
    ]
    if zoom:
        params.append({"name": "grid", "select": "interval", "bind": "scales"})

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": w, "height": h,
        "data": {"values": data},
        "params": params,
        "mark": {"type": "line", "strokeWidth": 2.5, "point": False},
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "title": x_label,
                   "scale": {"zero": False}, "axis": x_axis},
            "y": {"field": "y", "type": "quantitative", "title": y_label},
            "color": color_enc,
            "opacity": {"condition": {"param": "legend_sel", "value": 1},
                        "value": 0.08},
            "tooltip": tooltip,
        },
        "config": _VEGA_CFG,
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_TEMPLATE = """\
<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <title>Model Report - {coef_version}</title>
  <style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       margin: 0; padding: 0; background: #ffffff; color: #212529; font-size: 13px; }}
.header {{ padding: 24px 32px 0 32px; }}
h1 {{ color: #212529; text-align: center; border-bottom: 2px solid #2b7ab5;
     padding-bottom: 10px; font-size: 22px; margin: 0 0 16px 0; }}
h2 {{ color: #212529; margin-top: 24px; margin-bottom: 12px; border-left: 4px solid #2b7ab5;
     padding-left: 10px; font-size: 16px; }}
.content {{ padding: 0 32px 64px 32px; }}

.page-nav {{ position: sticky; top: 0; z-index: 999; background: #ffffff;
            border-bottom: 2px solid #dee2e6; padding: 10px 32px 0 32px;
            display: flex; gap: 4px; }}
.page-nav a {{ display: inline-block; padding: 8px 24px; background: #f8f9fa;
              color: #6c757d; text-decoration: none; border-radius: 4px 4px 0 0;
              font-size: 13px; font-weight: 600; border: 1px solid #dee2e6;
              border-bottom: 2px solid #dee2e6; margin-bottom: -2px;
              cursor: pointer; user-select: none; transition: all 0.15s; }}
.page-nav a.active {{ background: #2b7ab5; color: #fff; border-color: #2b7ab5;
                     border-bottom-color: #ffffff; }}
.page-nav a:hover:not(.active) {{ background: #e9ecef; color: #212529; }}
.report-page {{ display: none; }}
.report-page.active {{ display: block; }}

.sub-nav {{ display: flex; gap: 6px; padding: 20px 0 12px 0; flex-wrap: wrap;
           margin-bottom: 8px; border-bottom: 1px solid #dee2e6; }}
.sub-nav a {{ display: inline-block; padding: 6px 16px; background: #f8f9fa;
             color: #6c757d; text-decoration: none; border-radius: 3px;
             font-size: 12px; font-weight: 600; border: 1px solid #dee2e6;
             cursor: pointer; user-select: none; transition: all 0.15s; }}
.sub-nav a.active {{ background: #2b7ab5; color: #fff; border-color: #2b7ab5; }}
.sub-nav a:hover:not(.active) {{ background: #e9ecef; color: #212529; }}
.sub-page {{ display: none; }}
.sub-page.active {{ display: block; }}

.table-box {{ background: #f8f9fa; padding: 14px; margin: 12px 0;
             border-radius: 6px; border: 1px solid #dee2e6; overflow-x: auto; }}
.coef-table {{ width: 100%; border-collapse: collapse; font-size: 12px;
              font-family: Consolas, 'Courier New', monospace; }}
.coef-table th {{ background: #2C3E50; color: #fff; padding: 8px 12px;
                 text-align: left; font-weight: 600; }}
.coef-table td {{ padding: 6px 12px; border-bottom: 1px solid #dee2e6; }}
.coef-table td.var-name {{ font-weight: 600; }}
.coef-table td.pos {{ color: #27AE60; font-weight: 500; }}
.coef-table td.neg {{ color: #C0392B; font-weight: 500; }}
.coef-table tr:nth-child(even) {{ background: #f1f3f5; }}
.coef-table tr:nth-child(odd) {{ background: #ffffff; }}
.coef-table tr.total-row td {{ font-weight: 700; background: #e9ecef;
                               border-top: 2px solid #2b7ab5; }}

.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
              gap: 16px; margin: 16px 0; }}
.chart-box {{ background: #f8f9fa; padding: 14px; border-radius: 6px;
             border: 1px solid #dee2e6; overflow: visible; position: relative; }}
.chart-box .vega-embed {{ overflow: visible !important; }}
.chart-box .vega-embed summary {{ display: none !important; }}

.expand-btn {{ position: absolute; top: 6px; right: 8px; z-index: 5;
              cursor: pointer; font-size: 16px; color: #6c757d; opacity: 0.4;
              transition: opacity 0.15s; user-select: none; }}
.expand-btn:hover {{ opacity: 1; color: #2b7ab5; }}

.modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                 background: rgba(0,0,0,0.6); z-index: 10000; justify-content: center;
                 align-items: center; }}
.modal-overlay.open {{ display: flex; }}
.modal-content {{ background: #fff; border-radius: 8px; padding: 24px; max-width: 95vw;
                 max-height: 92vh; overflow: auto; position: relative;
                 box-shadow: 0 8px 32px rgba(0,0,0,0.3); }}
.modal-close {{ position: absolute; top: 8px; right: 14px; font-size: 22px; cursor: pointer;
               color: #6c757d; font-weight: 700; z-index: 1; }}
.modal-close:hover {{ color: #212529; }}
.modal-hint {{ font-size: 11px; color: #6c757d; margin-top: 8px; text-align: center; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
</head><body>
<div class="header">
  <h1>Model Report: {coef_version}</h1>
</div>
<div class="page-nav">
{top_tabs}
</div>
{pages}

<div class="modal-overlay" id="chartModal">
  <div class="modal-content">
    <span class="modal-close" onclick="closeModal()">&times;</span>
    <div id="modalChart"></div>
    <div class="modal-hint">Scroll to zoom &middot; Drag to pan &middot; Double-click to reset</div>
  </div>
</div>

<script>
var SPECS = {specs_json};
var rendered = {{}};

function renderChartsIn(container) {{
  if (typeof vegaEmbed === 'undefined') {{
    setTimeout(function() {{ renderChartsIn(container); }}, 200); return;
  }}
  setTimeout(function() {{
    container.querySelectorAll('.vega-chart').forEach(function(el) {{
      var id = el.id;
      if (!id || rendered[id] || !SPECS[id]) return;
      rendered[id] = true;
      vegaEmbed('#' + id, SPECS[id].thumb, {{actions: false, renderer: 'svg'}}).catch(function(err) {{
        el.innerHTML = '<p style="color:red;font-size:11px">Chart error: ' + err.message + '</p>';
      }});
    }});
  }}, 50);
}}

function openModal(chartId) {{
  var spec = SPECS[chartId];
  if (!spec || !spec.full) return;
  var modal = document.getElementById('chartModal');
  var target = document.getElementById('modalChart');
  target.innerHTML = '';
  modal.classList.add('open');
  vegaEmbed(target, spec.full, {{actions: false, renderer: 'svg'}}).catch(function(err) {{
    target.innerHTML = '<p style="color:red">Error: ' + err.message + '</p>';
  }});
}}
function closeModal() {{
  document.getElementById('chartModal').classList.remove('open');
  document.getElementById('modalChart').innerHTML = '';
}}
document.getElementById('chartModal').addEventListener('click', function(e) {{
  if (e.target === this) closeModal();
}});
document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') closeModal(); }});

function activatePage(pageId) {{
  document.querySelectorAll('.page-nav a').forEach(function(t) {{ t.classList.remove('active'); }});
  document.querySelectorAll('.report-page').forEach(function(p) {{ p.classList.remove('active'); }});
  var tab = document.querySelector('.page-nav a[data-page="' + pageId + '"]');
  var page = document.getElementById(pageId);
  if (tab) tab.classList.add('active');
  if (page) {{ page.classList.add('active');
    var sub = page.querySelector('.sub-page.active');
    if (sub) renderChartsIn(sub);
  }}
}}
function activateSub(parentId, subId) {{
  var parent = document.getElementById(parentId);
  if (!parent) return;
  parent.querySelectorAll('.sub-nav a').forEach(function(t) {{ t.classList.remove('active'); }});
  parent.querySelectorAll('.sub-page').forEach(function(p) {{ p.classList.remove('active'); }});
  var tab = parent.querySelector('.sub-nav a[data-sub="' + subId + '"]');
  var sub = document.getElementById(subId);
  if (tab) tab.classList.add('active');
  if (sub) {{ sub.classList.add('active'); renderChartsIn(sub); }}
}}

document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('.page-nav a').forEach(function(tab) {{
    tab.addEventListener('click', function(e) {{
      e.preventDefault(); activatePage(this.getAttribute('data-page'));
    }});
  }});
  document.querySelectorAll('.sub-nav a').forEach(function(tab) {{
    tab.addEventListener('click', function(e) {{
      e.preventDefault(); activateSub(this.getAttribute('data-parent'), this.getAttribute('data-sub'));
    }});
  }});
  var initPage = document.querySelector('.report-page.active');
  if (initPage) {{
    var initSub = initPage.querySelector('.sub-page.active');
    if (initSub) renderChartsIn(initSub);
  }}
}});
</script>
</body></html>
"""
