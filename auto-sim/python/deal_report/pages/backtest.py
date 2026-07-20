"""Sim Performance vs Actual page — projected (sim) vs realized (flat-file tapes).

Inline page fragment (rendered in the shared shell by ``builder``, like the
Aggregate and Pool-Composition pages), built from the sim's ``sim_results.xlsx``
and the realized CSVs ``realized.py`` writes from the monthly tapes. Appends its
Vega specs to the shared ``specs`` list; the shell renders them. No external
engine, no DB.

Sections: KPI cards, transition matrices (realized vs modeled), pool & credit
curves, and conditional transition rates tabbed by from-state.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..render.formatters import fmt_dollars, fmt_pct, kpi_grid
from ..metrics.kpis import pool_horizon

FROM_STATES = ["C", "D1M", "D2M", "D3M", "D4M"]
TO_STATES = ["C", "D1M", "D2M", "D3M", "D4M", "PIF", "LIQ"]
_STAY = "stay"

_SERIES = ["Projected", "Actual"]
_DASH = [[5, 4], [1, 0]]
# Rolling-Forecast overlay: Projected dashed, Actual solid, Rolling Forecast
# dashed in a distinct red. "Rolling Forecast" = the model re-seeded from each
# actual monthly panel (one step), vs the compounding multi-step "Projected".
_OS_LABEL = "Rolling Forecast"
_SERIES_OS = ["Projected", "Actual", _OS_LABEL]
_DASH_OS = [[5, 4], [1, 0], [6, 4]]
_OS_COLOR = "#d62728"
_RULE_COLOR = "#adb5bd"

# Match the report shell's sans-serif stack so Vega text isn't the default serif.
_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


# ── transition rates from the sim's prob keys (fromX_Y / fromX_stay) ─────────
#
# The sim stores fromX_Y as P(X→Y) × (X-balance / total-balance) — normalized by
# the whole pool, not conditional on X. Balance-weight Σ(fromX_Y·begin_bal) then
# row-normalize by the X-row total to recover the conditional P(X→Y).

def modeled_matrix(metrics_grouped_df: pd.DataFrame) -> pd.DataFrame:
    """Deal-level conditional Markov matrix (from×to), collapsed over the sim's
    (cohort, loan_age) grid. NaN where the topology has no such transition."""
    mg = metrics_grouped_df
    out = pd.DataFrame(index=FROM_STATES, columns=TO_STATES, dtype=float)
    if mg is None or mg.empty or "begin_bal" not in mg.columns:
        return out
    w = pd.to_numeric(mg["begin_bal"], errors="coerce").fillna(0.0)
    for fs in FROM_STATES:
        for ts in TO_STATES:
            col = f"from{fs}_{_STAY}" if ts == fs else f"from{fs}_{ts}"
            if col in mg.columns:
                v = pd.to_numeric(mg[col], errors="coerce").fillna(0.0)
                out.loc[fs, ts] = float((v * w).sum())
        row_sum = out.loc[fs].sum(skipna=True)          # X's balance exposure
        if row_sum > 0:
            out.loc[fs] = out.loc[fs] / row_sum          # → conditional P(X→·)
    return out


def realized_matrix(actuals_matrix_df: pd.DataFrame) -> pd.DataFrame:
    """Realized conditional Markov matrix (from×to) from the tapes."""
    out = pd.DataFrame(index=FROM_STATES, columns=TO_STATES, dtype=float)
    if actuals_matrix_df is None or actuals_matrix_df.empty:
        return out
    piv = actuals_matrix_df.pivot(index="from_status", columns="to_status",
                                  values="prob")
    return out.combine_first(piv).reindex(index=FROM_STATES, columns=TO_STATES)


def modeled_transitions_by_period(mgp: pd.DataFrame | None) -> pd.DataFrame:
    """Modeled conditional P(from→to) by period — same balance-weight +
    row-normalize as ``modeled_matrix``, kept per period.
    Long form: period, from_status, to_status, rate."""
    cols = [c for c in (mgp.columns if mgp is not None else []) if c.startswith("from")]
    if mgp is None or mgp.empty or "period" not in mgp.columns \
            or "begin_bal" not in mgp.columns or not cols:
        return pd.DataFrame(columns=["period", "from_status", "to_status", "rate"])
    keymap = {}                                          # prob-key col → (from, to)
    for c in cols:
        rest = c[4:]
        fs = next((s for s in FROM_STATES if rest == s or rest.startswith(s + "_")), None)
        if fs is None:
            continue
        suff = rest[len(fs) + 1:] if rest != fs else _STAY
        keymap[c] = (fs, fs if suff == _STAY else suff)
    rows = []
    for per, g in mgp.groupby(mgp["period"].astype(int)):
        ww = pd.to_numeric(g["begin_bal"], errors="coerce").fillna(0.0)
        agg, tot = {}, {}
        for c, (fs, to) in keymap.items():
            v = float((pd.to_numeric(g[c], errors="coerce").fillna(0.0) * ww).sum())
            agg[(fs, to)] = agg.get((fs, to), 0.0) + v
            tot[fs] = tot.get(fs, 0.0) + v
        for (fs, to), v in agg.items():
            if tot.get(fs, 0.0) > 0:
                rows.append({"period": int(per), "from_status": fs,
                             "to_status": to, "rate": v / tot[fs]})
    return pd.DataFrame(rows)


# ── single-value heatmap matrix (one per Realized / Modeled, shown side by side) ─

def _mtx_panel(cid: str, title: str, sub: str) -> str:
    """One matrix panel: an HTML header (title + subtitle, report font) above the
    natural-size Vega grid ``#cid``."""
    return (
        '<div class="mtx-panel">'
        f'<div class="mtx-head"><span class="mtx-title">{title}</span>'
        f'<span class="mtx-sub">{sub}</span></div>'
        f'<div id="{cid}" class="mtx-chart"></div>'
        '</div>'
    )


def _matrix_heatmap_spec(mat: pd.DataFrame) -> dict:
    """Vega-Lite heatmap of the from→to matrix (values in %) — grid ONLY: no
    title, subtitle or colour legend (those live in HTML around the chart, at the
    report's font sizes, so nothing scales up when the page is wide). YlGnBu on a
    shared 0-100 domain with in-cell labels + hover. Grey cell = no transition."""
    recs = []
    for fs in FROM_STATES:
        for ts in TO_STATES:
            v = mat.loc[fs, ts] if (fs in mat.index and ts in mat.columns) else np.nan
            ok = isinstance(v, (int, float)) and np.isfinite(v)
            recs.append({"from": fs, "to": ts,
                         "value": round(float(v) * 100, 2) if ok else None,
                         "label": f"{v * 100:.2f}" if ok else ""})   # 2 dp: from-C rates are small
    ax = {"labelFontSize": 11, "titleFontSize": 10, "labelFont": _FONT, "titleFont": _FONT,
          "labelColor": "#1b2733", "titleColor": "#8a95a1", "domain": False,
          "ticks": False, "labelAngle": 0, "labelPadding": 4, "titleFontWeight": 500}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        # width:"container" → Vega lays the grid out at the column width and draws
        # text at its TRUE px size (no CSS scale-up). Cells fill horizontally (wide
        # rectangles); height is step-based so it stays compact. Titles live in HTML
        # (see _mtx_panel), so this is just the grid.
        "width": "container", "height": {"step": 42}, "background": None,
        "autosize": {"type": "fit", "contains": "padding", "resize": True},
        "data": {"values": recs},
        "encoding": {
            "y": {"field": "from", "type": "nominal", "sort": FROM_STATES,
                  "title": "from", "axis": ax},
            "x": {"field": "to", "type": "nominal", "sort": TO_STATES,
                  "title": "to", "axis": {**ax, "orient": "bottom"}},
        },
        "layer": [
            {"mark": {"type": "rect", "stroke": "#ffffff", "strokeWidth": 2},
             "encoding": {
                 "color": {"field": "value", "type": "quantitative",
                           "scale": {"scheme": "yellowgreenblue", "domain": [0, 100]},
                           "legend": None},
                 "tooltip": [{"field": "from", "title": "from"},
                             {"field": "to", "title": "to"},
                             {"field": "value", "type": "quantitative", "title": "P (%)",
                              "format": ".2f"}]}},
            {"mark": {"type": "text", "font": _FONT, "fontSize": 10, "fontWeight": 600},
             "encoding": {"text": {"field": "label"},
                          "color": {"condition": {"test": "datum.value >= 45", "value": "#ffffff"},
                                    "value": "#11202b"}}},
        ],
        "config": {"font": _FONT, "view": {"stroke": None}, "axis": {"grid": False}},
    }


# ── two-series (projected solid / actual dashed) curve spec ──────────────────

def _long_records(proj: pd.DataFrame, act: pd.DataFrame, x: str,
                  col: str, max_x: int | None = None) -> list[dict]:
    """Long-form (x, value, series) records — finite-only, within the chart's
    x-range. Runoff CDR/CPR divide by ~0 balance → inf that would poison vega's
    y-extent and blank the chart, so drop non-finite values."""
    out = []
    for df, series in ((proj, "Projected"), (act, "Actual")):
        if col not in df.columns:
            continue
        for _, r in df.iterrows():
            xi, v = int(r[x]), r.get(col)
            if max_x is not None and xi > max_x:
                continue
            if pd.notna(v) and np.isfinite(v):
                out.append({"x": xi, "value": float(v), "series": series})
    return out


# Rate charts (CDR/CPR/severity) size the y-axis to show the projected body while
# clipping the end-of-life runoff. Generosity is the pct percentile of both series
# over the full horizon, but BOUNDED at `mult × realized range` so a broad tail
# ramp (e.g. CPR → ~100% at maturity) can't balloon the axis and squash the body.
# Bigger pct / mult = more generous.  headroom = padding above the chosen top.
_RATE_YMAX_PCT = 0.98
_RATE_YMAX_MULT = 2.0
_YMAX_HEADROOM = 1.15


def _ymax(proj: pd.DataFrame, act: pd.DataFrame, col: str,
          horizon: int, window: int | None,
          pct: float = _RATE_YMAX_PCT, mult: float = _RATE_YMAX_MULT) -> float | None:
    """Padded y-axis top.

    ``window is None`` (balance, pool factor, cumulative CGL/CNL): the true max
    over the full horizon — these are monotone/bounded, so fit everything.

    Otherwise (rate charts CDR/CPR/severity, ``window`` = last realized period):
    top = max(realized range, min(pct-percentile over the full horizon,
    mult × realized range)). The percentile reveals the projected body past
    ``last_actual`` and clips only the extreme tail; the ``mult`` cap keeps a broad
    runoff ramp from blowing the axis up; the realized floor always shows actuals."""
    def finite(df, hi):
        if col not in df.columns:
            return pd.Series(dtype=float)
        s = pd.to_numeric(df.loc[df["x"] <= hi, col], errors="coerce")
        return s[np.isfinite(s)]                          # drop NaN and inf

    full = pd.concat([finite(proj, horizon), finite(act, horizon)])
    if full.empty:
        return None
    if window is None:
        top = full.max()
    else:
        realized = pd.concat([finite(proj, window), finite(act, window)])
        realized_max = float(realized.max()) if not realized.empty else 0.0
        generous = min(float(full.quantile(pct)), realized_max * mult)
        top = max(realized_max, generous)
    return float(top) * _YMAX_HEADROOM


def _lag_bar_spec(records: list[dict], sort: list[str], projected_only: bool = False,
                  w: int = 670, h: int = 380) -> dict:
    """Grouped bar: P(recovery-lag bucket | charge-off), Projected vs Actual."""
    series = ["Projected"] if projected_only else ["Projected", "Actual"]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": w, "height": h, "autosize": {"type": "fit", "contains": "padding"},
        "title": {"text": "Recovery Lag Profile (share of charge-offs)", "anchor": "middle"},
        "data": {"values": [r for r in records if r["series"] in series]},
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "bucket", "type": "nominal", "sort": sort, "title":
                  "recovery lag (months after charge-off)", "axis": {"labelAngle": 0}},
            "xOffset": {"field": "series", "sort": series},
            "y": {"field": "value", "type": "quantitative", "title": "share",
                  "axis": {"format": ".0%"}},
            # Actual = a light tint of the projected purple so the two bars read
            # as one family (same hue) rather than clashing purple-vs-blue.
            "color": {"field": "series", "type": "nominal",
                      "scale": {"domain": ["Projected", "Actual"], "range": ["#8b5cf6", "#c9bcee"]},
                      "legend": None if projected_only else {"orient": "top", "title": None}},
            "tooltip": [{"field": "bucket", "type": "nominal", "title": "lag"},
                        {"field": "series", "type": "nominal"},
                        {"field": "value", "type": "quantitative", "format": ".1%"}],
        },
        "config": {
            "view": {"stroke": None}, "background": "#f8f9fa",
            "axis": {"labelColor": "#212529", "titleColor": "#212529",
                     "gridColor": "#eef1f5", "domainColor": "#ced4da",
                     "tickColor": "#ced4da"},
            "legend": {"labelColor": "#212529"}, "title": {"color": "#212529"},
        },
    }


def _curve_spec(title: str, color: str, y_fmt: str, values: list[dict],
                x_title: str, max_x: int, ymax: float | None,
                w: int = 670, h: int = 380, onestep: bool = False) -> dict:
    """Projected + Actual line chart in one colour with a shared hover crosshair
    + tooltip. With ``onestep`` the values also carry a 'One-step' series (model
    re-seeded from the realized pool each month), drawn as a distinct dotted line
    and shown/hidden by the ``showOS`` param (driven by the section toggle)."""
    yscale = {"domain": [0, ymax]} if ymax is not None else {"zero": True}
    series = _SERIES_OS if onestep else _SERIES
    dash = _DASH_OS if onestep else _DASH
    color_scale = {"domain": series,
                   "range": ([color, color, _OS_COLOR] if onestep else [color, color])}
    transform = [
        {"calculate": "datum.series === 'Projected' ? datum.value : null", "as": "_p"},
        {"calculate": "datum.series === 'Actual' ? datum.value : null", "as": "_a"},
    ]
    joinagg = [{"op": "max", "field": "_p", "as": "Projected"},
               {"op": "max", "field": "_a", "as": "Actual"}]
    tooltip = [{"field": "x", "type": "quantitative", "title": x_title, "format": "d"},
               {"field": "Projected", "type": "quantitative", "format": y_fmt},
               {"field": "Actual", "type": "quantitative", "format": y_fmt}]
    if onestep:
        transform.append({"calculate": f"datum.series === '{_OS_LABEL}' ? datum.value : null", "as": "_o"})
        joinagg.append({"op": "max", "field": "_o", "as": "rf_val"})
        tooltip.append({"field": "rf_val", "type": "quantitative", "format": y_fmt,
                        "title": _OS_LABEL})
    transform.append({"joinaggregate": joinagg, "groupby": ["x"]})
    # line-layer opacity: hide the One-step line when the toggle (showOS) is off.
    line_enc = {
        "x": {"field": "x", "type": "quantitative", "title": x_title,
              "axis": {"grid": True, "format": "d", "gridDash": [2, 4]},
              "scale": {"nice": False, "domain": [0, max_x], "clamp": True}},
        "y": {"field": "value", "type": "quantitative", "title": "",
              "axis": {"grid": True, "format": y_fmt, "gridDash": [2, 4]},
              "scale": yscale},
        "color": {"field": "series", "type": "nominal", "title": "",
                  "scale": color_scale,
                  "legend": {"orient": "top", "symbolType": "stroke",
                             "symbolStrokeWidth": 2.5, "symbolSize": 200}},
        "strokeDash": {"field": "series", "type": "nominal",
                       "scale": {"domain": series, "range": dash}, "legend": None}}
    if onestep:
        line_enc["opacity"] = {"condition": {"test": f"datum.series !== '{_OS_LABEL}' || showOS",
                                             "value": 1}, "value": 0}
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        # fit axes/legend inside w×h so every SVG is exactly w×h — CSS width:100%
        # then scales all charts uniformly (matches the aggregate tab).
        "width": w, "height": h, "title": {"text": title, "fontSize": 14},
        "autosize": {"type": "fit", "contains": "padding"},
        "data": {"values": values},
        "transform": transform,
        "layer": [
            {"mark": {"type": "line", "clip": True, "strokeWidth": 2.5},
             "encoding": line_enc},
            # invisible hover targets — each dot adopts ITS OWN series colour on
            # hover (via the same scale as the line), so the Rolling Forecast dot
            # reads red while Projected/Actual keep the base chart colour.
            {"mark": {"type": "circle", "size": 55, "clip": True},
             "selection": {"hov": {"type": "single", "nearest": True,
                                   "on": "pointerover", "encodings": ["x"],
                                   "empty": "none"}},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative"},
                 "y": {"field": "value", "type": "quantitative"},
                 "color": {"field": "series", "type": "nominal",
                           "scale": color_scale, "legend": None},
                 "opacity": {"condition": {"selection": "hov", "value": 1}, "value": 0},
                 "tooltip": tooltip}},
            {"mark": {"type": "rule", "color": _RULE_COLOR, "strokeDash": [4, 4]},
             "encoding": {"x": {"field": "x", "type": "quantitative"}},
             "transform": [{"filter": {"selection": "hov"}}]},
        ],
        "config": {
            "view": {"stroke": None}, "background": "#f8f9fa",
            "axis": {"labelColor": "#212529", "titleColor": "#212529",
                     "gridColor": "#eef1f5", "domainColor": "#ced4da",
                     "tickColor": "#ced4da"},
            "legend": {"labelColor": "#212529"}, "title": {"color": "#212529"},
        },
    }
    if onestep:
        spec["params"] = [{"name": "showOS", "value": True}]   # toggle-driven
    return spec



# from-state → to-state charts for the tabbed Transition Rates section
_RATE_TABS = [
    ("C",   "From C",   [("D1M", "C → D1M  (ctd1)"), ("PIF", "C → PIF  (prepay)")]),
    ("D1M", "From D1M", [("C", "D1M → C  (cure)"), ("D2M", "D1M → D2M  (roll)"),
                         ("PIF", "D1M → PIF  (prepay)")]),
    ("D2M", "From D2M", [("C", "D2M → C  (cure)"), ("D1M", "D2M → D1M  (cure 1 bkt)"),
                         ("D3M", "D2M → D3M  (roll)"), ("LIQ", "D2M → LIQ  (charge-off)")]),
    ("D3M", "From D3M", [("C", "D3M → C  (cure)"), ("D2M", "D3M → D2M  (cure 1 bkt)"),
                         ("D4M", "D3M → D4M  (roll)"), ("LIQ", "D3M → LIQ  (charge-off)")]),
    ("D4M", "From D4M", [("C", "D4M → C  (cure)"), ("D3M", "D4M → D3M  (cure 1 bkt)"),
                         ("LIQ", "D4M → LIQ  (charge-off)")]),
]
_TO_COLOR = {"C": "#2c7a4b", "D1M": "#8a6d9e", "D2M": "#c98a2b",
             "D3M": "#b3543d", "D4M": "#7a3b52", "PIF": "#4c956c", "LIQ": "#b3543d"}

_X_TITLE = "Period (months from snapshot)"

# Only these transitions are worth plotting. Everything else — deep-bucket rolls
# and cures (D2M/D3M/D4M) — rides tiny loan counts late in the deal, so its
# realized rate is dominated by small-denominator noise (single loans spiking to
# 100%). The four below all originate in the well-populated C / D1M buckets.
_RATE_PLOT = frozenset({("C", "D1M"), ("C", "PIF"),
                        ("D1M", "C"), ("D1M", "D2M")})


def _kpi_section(init_bal: float, last_actual: int,
                 proj: pd.DataFrame, act: pd.DataFrame) -> str:
    """Simple projected-vs-actual KPI cards, read at the last reported month so
    the two are apples-to-apples (the projection runs past the actuals)."""
    def at(df: pd.DataFrame, col: str):
        if col not in df.columns:
            return None
        s = df.loc[df["x"] == last_actual, col]
        if not len(s) or pd.isna(s.iloc[0]):
            return None
        return float(s.iloc[0])

    # Actual pool factor = realized balance ÷ realized starting balance.
    apf = None
    if "balance" in act.columns and len(act):
        a = act.sort_values("x")
        b0 = a["balance"].iloc[0]
        bl = at(act, "balance")
        if bl is not None and b0 and b0 > 0:
            apf = bl / b0

    sub = f"@ period {last_actual}"
    items = [
        ("Snapshot Pool",         fmt_dollars(init_bal),         "original balance"),
        ("Actual CGL",            fmt_pct(at(act, "cgl")),       sub),
        ("Projected CGL",         fmt_pct(at(proj, "cgl")),      sub),
        ("Actual CNL",            fmt_pct(at(act, "cnl")),       sub),
        ("Projected CNL",         fmt_pct(at(proj, "cnl")),      sub),
        ("Actual Pool Factor",    fmt_pct(apf),                  sub),
        ("Projected Pool Factor", fmt_pct(at(proj, "pool_factor")), sub),
    ]
    return kpi_grid(items)


def build_backtest_html(
    deal: str,
    scenario: str,
    metrics_portfolio_df: pd.DataFrame,
    metrics_grouped_df: pd.DataFrame,
    actuals_portfolio_df: pd.DataFrame,
    actuals_transitions_df: pd.DataFrame,
    actuals_matrix_df: pd.DataFrame,
    metrics_grouped_period_df: pd.DataFrame | None = None,
    lag_profile: pd.DataFrame | None = None,
    onestep_df: pd.DataFrame | None = None,
    *,
    specs: list[dict],
    plot_id: int = 0,
) -> tuple[str | None, int]:
    """Render the Sim-Performance-vs-Actual page as an inline fragment.

    Appends Vega specs to *specs* (mutated in place, shell renders them) and
    returns ``(html, next_plot_id)``. ``html`` is None if inputs are insufficient.
    """
    if actuals_portfolio_df is None or actuals_portfolio_df.empty:
        return None, plot_id
    mp = metrics_portfolio_df.copy()
    if mp.empty:
        return None, plot_id
    mp = mp.sort_values("period").reset_index(drop=True)

    # ---- projected period curves from the sim ----
    init_bal = float(mp["begin_bal"].iloc[0]) if "begin_bal" in mp else 0.0
    proj = pd.DataFrame({"x": mp["period"].astype(int)})
    proj["pool_factor"] = mp["begin_bal"] / init_bal if init_bal > 0 else np.nan
    proj["balance"] = pd.to_numeric(mp["begin_bal"], errors="coerce")   # $ outstanding (match aggregate)
    for c in ("cpr", "cdr", "cgl", "cnl"):
        proj[c] = mp[c] if c in mp.columns else np.nan
    act = actuals_portfolio_df.rename(columns={"period": "x"}).copy()
    act["balance"] = pd.to_numeric(act["begin_bal"], errors="coerce") if "begin_bal" in act else np.nan
    last_actual = int(act["x"].max())

    # Per-period loss severity = period net loss ÷ period gross charge-off, from
    # the cumulative columns: 1 - Δ(recovery share)/Δ(gross-loss share), where
    # recovery share = cgl - cnl. Marginal (not cumulative) LGD; noisier because
    # recoveries lag their charge-off month.
    def _severity(df):
        if {"cgl", "cnl"} <= set(df.columns):
            cgl = pd.to_numeric(df["cgl"], errors="coerce")
            recov = cgl - pd.to_numeric(df["cnl"], errors="coerce")
            dco = cgl.diff(); drec = recov.diff()
            return (1 - drec / dco).where(dco > 0)
        return np.nan
    proj = proj.sort_values("x")
    proj["severity"] = _severity(proj)
    act = act.sort_values("x")
    act["severity"] = _severity(act)

    # One x-horizon shared with the aggregate page: last period with >=
    # POOL_CUTOFF of the original pool (see kpis.pool_horizon). CDR/CPR get a
    # y-window (below) so the runoff spike is clamped, not the x-axis.
    horizon = max(pool_horizon(mp["begin_bal"], mp["period"]) or int(proj["x"].max()),
                  last_actual)

    # ---- 0. KPI cards — projected vs actual at the last reported month ----
    kpi_html = _kpi_section(init_bal, last_actual, proj, act)

    # ---- 1. transition matrices (Realized | Modeled heatmaps, side by side) ----
    # Titles/subtitles are HTML (report font, fixed size); the Vega chart is the
    # bare grid rendered at natural size (.mtx-chart), so it never scales up.
    specs.append({"id": "bt_mtx_real",
                  "spec": _matrix_heatmap_spec(realized_matrix(actuals_matrix_df))})
    specs.append({"id": "bt_mtx_mod",
                  "spec": _matrix_heatmap_spec(modeled_matrix(metrics_grouped_df))})
    mtx_html = (
        '<div class="mtx-row">'
        + _mtx_panel("bt_mtx_real", "Realized", "from tapes · monthly P(from→to)")
        + _mtx_panel("bt_mtx_mod", f"Modeled ({scenario})", "sim · monthly P(from→to)")
        + '</div>'
    )

    # ---- 2. pool & credit curves (2-up pairs, grouped by sub-head) ----
    # window bounds the y-domain (None = full horizon).
    perf = [
        ("bt_bal", "Outstanding Balance",         "balance",     "$,.0f", "#3b6ea5", None),
        ("bt_pf",  "Pool Factor",                 "pool_factor", ".2%",   "#5b8bb5", None),
        ("bt_cdr", "CDR (annualized)",            "cdr",         ".2%", "#b3543d", last_actual),
        ("bt_cpr", "CPR (annualized)",            "cpr",         ".1%", "#2b7ab5", last_actual),
        ("bt_cgl", "Cumulative Gross Loss (CGL)", "cgl",         ".2%", "#b3543d", None),
        ("bt_cnl", "Cumulative Net Loss (CNL)",   "cnl",         ".2%", "#2c7a4b", None),
        ("bt_sev", "Loss Severity (per-period net ÷ gross charge-off)",
                                                  "severity",    ".1%", "#8b5cf6", last_actual),
    ]
    box = {}
    for cid, title, col, yfmt, color, window in perf:
        chart_h = horizon                       # unified cutoff; window still clamps CDR/CPR y-axis
        vals = _long_records(proj, act, "x", col, max_x=chart_h)
        ymax = _ymax(proj, act, col, chart_h, window)
        specs.append({"id": cid, "spec": _curve_spec(
            title, color, yfmt, vals, _X_TITLE, chart_h, ymax)})
        box[col] = f'<div class="chart-box"><div id="{cid}"></div></div>'

    # Severity's companion: recovery-lag profile (projected vs actual) — 2-up.
    if lag_profile is not None and not lag_profile.empty:
        recs = lag_profile.to_dict("records")
        order = list(dict.fromkeys(lag_profile["bucket"]))
        specs.append({"id": "bt_lag", "spec": _lag_bar_spec(recs, order)})
        box["lag"] = '<div class="chart-box"><div id="bt_lag"></div></div>'
    else:
        box["lag"] = ""

    perf_html = (
        f'<div class="sub-head">Pool Runoff</div>'
        f'<div class="chart-row">{box["balance"]}{box["pool_factor"]}</div>'
        f'<div class="sub-head">Prepay &amp; Default Rates</div>'
        f'<div class="chart-row">{box["cdr"]}{box["cpr"]}</div>'
        f'<div class="sub-head">Cumulative Losses</div>'
        f'<div class="chart-row">{box["cgl"]}{box["cnl"]}</div>'
        f'<div class="sub-head">Severity &amp; Recovery Timing</div>'
        f'<div class="chart-row">{box["severity"]}{box["lag"]}</div>')

    # ---- 3. transition rates, tabbed by from-state ----
    mod_tr = modeled_transitions_by_period(metrics_grouped_period_df)
    rea_tr = actuals_transitions_df if actuals_transitions_df is not None \
        else pd.DataFrame(columns=["period", "from_status", "to_status", "rate"])

    def _trans_pair(fs, to):
        cols = {"period": "x", "rate": "v"}
        p = mod_tr[(mod_tr.from_status == fs) & (mod_tr.to_status == to)][["period", "rate"]].rename(columns=cols)
        a = rea_tr[(rea_tr.from_status == fs) & (rea_tr.to_status == to)][["period", "rate"]].rename(columns=cols)
        return p, a

    # one-step overlay applies only to ctd1 (C->D1M) and ctp (C->PIF)
    _OS_COL = {("C", "D1M"): "ctd1", ("C", "PIF"): "ctp"}
    have_os = onestep_df is not None and not onestep_df.empty

    def _onestep_records(fs, to, max_x):
        col = _OS_COL.get((fs, to))
        if not have_os or col is None or col not in onestep_df.columns:
            return []
        out = []
        for _, r in onestep_df.iterrows():
            xi, v = int(r["period"]), r[col]
            if xi <= max_x and pd.notna(v) and np.isfinite(v):
                out.append({"x": xi, "value": float(v), "series": _OS_LABEL})
        return out

    tab_btns, tab_panels = [], []
    kept_tabs = 0                         # first surviving tab is the active one
    onestep_shown = False
    for fs, label, tos in _RATE_TABS:
        boxes = []
        for to, clabel in tos:
            if (fs, to) not in _RATE_PLOT:
                continue                  # not a worth-plotting transition
            p, a = _trans_pair(fs, to)
            cid = f"bt_{fs}_{to}"
            vals = _long_records(p, a, "x", "v", max_x=horizon)
            os_recs = _onestep_records(fs, to, horizon)
            vals += os_recs
            use_os = bool(os_recs)
            onestep_shown = onestep_shown or use_os
            ymax = _ymax(p, a, "v", horizon, last_actual)
            specs.append({"id": cid, "spec": _curve_spec(
                clabel, _TO_COLOR.get(to, "#555"), ".2%", vals,
                _X_TITLE, horizon, ymax, onestep=use_os)})
            boxes.append(f'<div class="chart-box"><div id="{cid}"></div></div>')
        if not boxes:
            continue                      # every transition pruned — drop the tab
        active = " active" if kept_tabs == 0 else ""
        kept_tabs += 1
        tab_btns.append(f'<button class="l2-btn{active}" data-tab="tab_{fs}">{label}</button>')
        tab_panels.append(f'<div class="l2-panel{active}" id="tab_{fs}">'
                          f'<div class="chart-row">{"".join(boxes)}</div></div>')
    os_toggle = (
        '<div class="os-toggle"><label><input type="checkbox" id="os-toggle-chk" checked> '
        '<b>Rolling Forecast</b> overlay (red, dashed) — the model re-seeded from each '
        'actual monthly panel (one step). Gap vs <b>Projected</b> = compounding drift; '
        'gap vs <b>Actual</b> = per-step model error.</label></div>'
    ) if onestep_shown else ""
    transitions_html = (f'<div class="tabs">{"".join(tab_btns)}</div>'
                        f'{"".join(tab_panels)}{os_toggle}')

    return _compose(last_actual, kpi_html, mtx_html, perf_html,
                    transitions_html), plot_id


_MTX_LEGEND = (
    '<div class="mtx-legend">Balance-weighted monthly P(from→to), %. '
    'Darker = higher; grey = no such transition. Hover for exact values.</div>'
)


def _compose(last_actual, kpi_html, mtx_html, perf_html, transitions_html):
    """Inline page fragment. Specs are rendered by the shell; L2 tabs are wired
    by the shell's initL2Tabs(). Fixed-width transition specs render even inside
    a display:none tab panel."""
    return (
        kpi_html
        + '<p class="note"><b>Projected</b> — dashed · <b>Actual</b> — solid '
        f'(realized tapes, through period {last_actual}).</p>'
        '<h2>Transition Matrix</h2>' + _MTX_LEGEND + mtx_html
        + '<h2>Pool &amp; Credit Performance</h2>' + perf_html
        + '<h2>Transition Rates</h2>'
        '<p class="note">Conditional monthly P(from→to) by period.</p>'
        + transitions_html
    )
