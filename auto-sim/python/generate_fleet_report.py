#!/usr/bin/env python
"""Fleet report — per-deal CGL and CNL panels, actual vs every scenario.

Each deal gets a row of two panels (CGL left, CNL right): the actual curve
solid dark, each scenario's projection dashed in its scenario hue, capped at
the deal's last observed month. Panels carry the platform's accent colour
(matching the trans_model ctd1 explorer palette) on the card strip and title.
Sections are grouped by modelling shelf, with a lean fit table underneath.

    python python/generate_fleet_report.py            # all deals
    python python/generate_fleet_report.py --deals EART_2023_1 CMAX_2022_1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
ROOT = os.path.dirname(_HERE)
OUTPUT = os.path.join(ROOT, "output")

import realized  # noqa: E402
from deal_meta import resolve  # noqa: E402
from deal_report.render.assets import CSS, JS, VEGA_CDN  # noqa: E402
from deal_report.render.formatters import fmt_pct, kpi_grid  # noqa: E402
from deal_report.render.theme import ACTUAL_COLOR, PLATFORM_COLOR, SCEN_COLOR  # noqa: E402

METRICS = [("cgl", "CGL"), ("cnl", "CNL")]


def _chip(ratio) -> str:
    """Fit-ratio chip, thresholded at 10% and 25% absolute deviation from 1."""
    if ratio is None or not np.isfinite(ratio):
        return '<span class="chip na">—</span>'
    dev = abs(ratio - 1.0)
    cls = "ok" if dev <= 0.10 else ("warn" if dev <= 0.25 else "bad")
    return f'<span class="chip {cls}">{ratio:.2f}×</span>'


def _at(df: pd.DataFrame, per: int, col: str):
    row = df.loc[df["period"] == per, col]
    return float(row.iloc[0]) if len(row) and pd.notna(row.iloc[0]) else None


def _combos(want: set[str]) -> list[tuple[str, str]]:
    out = []
    for deal in sorted(os.listdir(OUTPUT)):
        ddir = os.path.join(OUTPUT, deal)
        if not os.path.isdir(ddir) or deal.startswith("_") or (want and deal not in want):
            continue
        for scen in sorted(os.listdir(ddir)):
            if os.path.isfile(os.path.join(ddir, scen, "sim_results.xlsx")):
                out.append((deal, scen))
    return out


def _curve_records(df: pd.DataFrame, metric: str, series: str, horizon: int) -> list[dict]:
    return [{"x": int(r.period), "v": float(getattr(r, metric)), "series": series}
            for r in df.itertuples()
            if pd.notna(getattr(r, metric)) and r.period <= horizon]


def collect(want: set[str]):
    """Return (fit rows DataFrame, {(deal, metric): curve records})."""
    rows, curves, realized_cache = [], {}, {}
    for deal, scen in _combos(want):
        meta = resolve(deal)
        if meta is None or not os.path.isdir(meta["tape_dir"]):
            print(f"  SKIP {deal}: unmapped or tape dir missing", flush=True)
            continue
        prepped = os.path.join(ROOT, "input", "deals", deal, "loans_prepped.json")
        if deal not in realized_cache:            # realized is scenario-independent
            with open(os.path.join(ROOT, meta["config"])) as f:
                lag_path = json.load(f).get("lag_dist_path",
                                            "input/severity/recovery_lag_dist.tsv")
            res = realized.compute_realized(meta["tape_dir"], prepped,
                                            lag_dist_path=lag_path)
            realized_cache[deal] = (res["portfolio"],
                                    realized._orig_pool_and_asof(prepped)[1])
        act, snap = realized_cache[deal]
        horizon = int(act["period"].max())

        proj = pd.ExcelFile(os.path.join(OUTPUT, deal, scen, "sim_results.xlsx")) \
            .parse("Metrics_Portfolio")
        for metric, _ in METRICS:
            key = (deal, metric)
            if key not in curves:
                curves[key] = _curve_records(act, metric, "Actual", horizon)
            curves[key] += _curve_records(proj, metric, scen, horizon)

        r_cgl, p_cgl = _at(act, horizon, "cgl"), _at(proj, horizon, "cgl")
        r_cnl, p_cnl = _at(act, horizon, "cnl"), _at(proj, horizon, "cnl")
        rows.append({
            "deal": deal, "scenario": scen,
            "platform": meta["platform"], "shelf": meta["shelf"],
            "group": "Prime" if meta["shelf"] == "Prime" else "Subprime",
            "snapshot": str(snap)[:10], "months": horizon,
            "real_cgl": r_cgl, "proj_cgl": p_cgl,
            "cgl_ratio": (p_cgl / r_cgl) if (p_cgl and r_cgl) else None,
            "real_cnl": r_cnl, "proj_cnl": p_cnl,
            "cnl_ratio": (p_cnl / r_cnl) if (p_cnl and r_cnl) else None,
            "link": f"{deal}/{deal}_{scen}_deal_report.html",
        })
        print(f"  {deal:15s} {scen:20s} CGL {p_cgl and f'{p_cgl:.1%}'} / "
              f"{r_cgl and f'{r_cgl:.1%}'}", flush=True)
    return pd.DataFrame(rows), curves


def _panel_spec(deal: str, metric_label: str, recs: list[dict],
                scens: list[str], accent: str) -> dict:
    """One panel with a shared-crosshair hover: nearest x highlights a dot per
    series and the tooltip lists every series' value at that period."""
    series = ["Actual"] + scens
    colors = [ACTUAL_COLOR] + [SCEN_COLOR.get(s, "#888") for s in scens]
    dashes = [[1, 0]] + [[6, 4]] * len(scens)
    color_scale = {"domain": series, "range": colors}
    transform = [{"calculate": f"datum.series === '{s}' ? datum.v : null",
                  "as": f"_s{i}"} for i, s in enumerate(series)]
    transform.append({"joinaggregate": [{"op": "max", "field": f"_s{i}", "as": s}
                                        for i, s in enumerate(series)],
                      "groupby": ["x"]})
    tooltip = [{"field": "x", "type": "quantitative", "title": "period", "format": "d"}]
    tooltip += [{"field": s, "type": "quantitative", "format": ".2%"} for s in series]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container", "height": 240,
        "title": {"text": f"{deal} — {metric_label}", "anchor": "start",
                  "fontSize": 13, "offset": 6, "color": accent},
        "autosize": {"type": "fit", "contains": "padding"},
        "data": {"values": recs},
        "transform": transform,
        "layer": [
            {"mark": {"type": "line", "clip": True, "strokeWidth": 2},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative", "title": None,
                       "axis": {"format": "d", "grid": True, "gridDash": [2, 4]},
                       "scale": {"nice": False}},
                 "y": {"field": "v", "type": "quantitative", "title": None,
                       "axis": {"format": ".1%", "grid": True, "gridDash": [2, 4]}},
                 "color": {"field": "series", "type": "nominal", "legend": None,
                           "scale": color_scale},
                 "strokeDash": {"field": "series", "type": "nominal", "legend": None,
                                "scale": {"domain": series, "range": dashes}}}},
            {"mark": {"type": "circle", "size": 48, "clip": True},
             "selection": {"hov": {"type": "single", "nearest": True,
                                   "on": "pointerover", "encodings": ["x"],
                                   "empty": "none"}},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative"},
                 "y": {"field": "v", "type": "quantitative"},
                 "color": {"field": "series", "type": "nominal",
                           "scale": color_scale, "legend": None},
                 "opacity": {"condition": {"selection": "hov", "value": 1}, "value": 0},
                 "tooltip": tooltip}},
            {"mark": {"type": "rule", "color": "#9aa5b1", "strokeDash": [4, 4]},
             "encoding": {"x": {"field": "x", "type": "quantitative"}},
             "transform": [{"filter": {"selection": "hov"}}]},
        ],
        "config": {
            "view": {"stroke": None}, "background": "#f8f9fa",
            "axis": {"labelColor": "#212529", "gridColor": "#eef1f5",
                     "domainColor": "#ced4da", "tickColor": "#ced4da"},
            "title": {"color": accent},
        },
    }


def _legend_html(scens: list[str], platforms: list[str]) -> str:
    line = ('<span style="display:inline-block;width:22px;height:0;'
            'border-top:3px {style} {color};vertical-align:middle;"></span>')
    dot = ('<span style="display:inline-block;width:10px;height:10px;'
           'border-radius:50%;background:{color};vertical-align:middle;"></span>')
    items = [f'<span class="cl-item">{line.format(style="solid", color=ACTUAL_COLOR)}'
             f'&nbsp;Actual</span>']
    items += [f'<span class="cl-item">{line.format(style="dashed", color=SCEN_COLOR.get(s, "#888"))}'
              f'&nbsp;{s}</span>' for s in scens]
    items += [f'<span class="cl-item">{dot.format(color=PLATFORM_COLOR.get(p, "#888"))}'
              f'&nbsp;{p}</span>' for p in platforms]
    return ('<div class="cohort-legend visible" style="justify-content:flex-start;'
            'margin:2px 0 10px;">' + "".join(items) + "</div>")


def _table(df: pd.DataFrame) -> str:
    head = ("<tr><th>Deal</th><th>Scenario</th><th>Platform</th><th>Shelf</th>"
            "<th>Snapshot</th><th>Obs mo</th>"
            "<th>CGL proj / act</th><th>Fit</th>"
            "<th>CNL proj / act</th><th>Fit</th></tr>")
    dot = ('<span style="display:inline-block;width:9px;height:9px;'
           'border-radius:50%;background:{c};margin-right:7px;"></span>')
    body = []
    for r in df.itertuples():
        pair = lambda p, a: (f"{fmt_pct(p)} / {fmt_pct(a)}"
                             if p is not None and a is not None else "—")
        body.append(
            f'<tr><td>{dot.format(c=PLATFORM_COLOR.get(r.platform, "#888"))}'
            f'<a href="{r.link}">{r.deal}</a></td>'
            f"<td>{r.scenario}</td><td>{r.platform}</td><td>{r.shelf}</td>"
            f"<td>{r.snapshot}</td><td>{r.months}</td>"
            f"<td>{pair(r.proj_cgl, r.real_cgl)}</td><td>{_chip(r.cgl_ratio)}</td>"
            f"<td>{pair(r.proj_cnl, r.real_cnl)}</td><td>{_chip(r.cnl_ratio)}</td></tr>")
    return (f'<div class="table-box"><table class="stats">{head}'
            f'{"".join(body)}</table></div>')


def build_html(df: pd.DataFrame, curves: dict) -> str:
    med = lambda c: (float(df[c].dropna().median()) if df[c].notna().any() else None)
    worst = df.assign(dev=(df["cgl_ratio"] - 1).abs()).sort_values("dev").iloc[-1] \
        if df["cgl_ratio"].notna().any() else None
    kpis = kpi_grid([
        ("Deals",           str(df["deal"].nunique()),  "with sim + tapes"),
        ("Reports",         str(len(df)),               "deal × scenario"),
        ("Median CGL fit",  f"{med('cgl_ratio'):.2f}×" if med("cgl_ratio") else "—",
         "projected ÷ actual"),
        ("Median CNL fit",  f"{med('cnl_ratio'):.2f}×" if med("cnl_ratio") else "—",
         "projected ÷ actual"),
        ("Widest CGL miss", worst["deal"] if worst is not None else "—",
         f"{worst['cgl_ratio']:.2f}×  ({worst['scenario']})" if worst is not None else ""),
    ])

    specs, sections = [], []
    for group in ("Prime", "Subprime"):
        gdf = df[df["group"] == group]
        if gdf.empty:
            continue
        gscens = sorted(gdf["scenario"].unique())
        gplats = sorted(gdf["platform"].unique())
        boxes = []
        for deal in sorted(gdf["deal"].unique()):
            dsub = gdf[gdf["deal"] == deal]
            dscens = sorted(dsub["scenario"].unique())
            accent = PLATFORM_COLOR.get(dsub["platform"].iloc[0], "#888")
            for metric, label in METRICS:
                cid = f"pnl_{deal}_{metric}"
                specs.append({"id": cid, "spec": _panel_spec(
                    deal, label, curves[(deal, metric)], dscens, accent)})
                boxes.append(f'<div class="chart-box" style="border-top-color:{accent};">'
                             f'<div id="{cid}"></div></div>')
        sections.append(
            f"<h2>{group} — Cumulative Losses, actual vs scenarios</h2>"
            + _legend_html(gscens, gplats)
            + f'<div class="chart-row" style="grid-template-columns:'
              f'repeat(auto-fit, minmax(560px, 1fr));">{"".join(boxes)}</div>')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Auto ABS — Fleet CGL / CNL</title>
{VEGA_CDN}
<style>{CSS}</style></head>
<body>
<div class="header"><h1>Auto ABS — Fleet Loss Backtest</h1></div>
<div class="content">
{kpis}
{"".join(sections)}
<h2>Fit table</h2>
<p class="note">Projected ÷ actual at each deal's last reported month.
Chips: green ≤ 10% deviation, amber ≤ 25%, red beyond. Click a deal for its
full report.</p>
{_table(df)}
</div>
<script type="application/json" id="vega-specs">{json.dumps(specs)}</script>
<script>{JS}</script>
</body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deals", nargs="*", default=[],
                    help="Restrict to these deal names (default: all).")
    ap.add_argument("--out", default=os.path.join(OUTPUT, "fleet_report.html"))
    args = ap.parse_args(argv)
    df, curves = collect(set(args.deals))
    if df.empty:
        print("No (deal, scenario) results found."); return 1
    df = df.sort_values(["group", "platform", "deal", "scenario"]).reset_index(drop=True)
    html = build_html(df, curves)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nWrote {args.out}  ({len(html) / 1024:.1f} KB, {len(df)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
