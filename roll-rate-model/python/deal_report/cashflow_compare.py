"""Cashflow Comparison page.

Runs ``cashflow_engine`` in-process using period curves derived from this
deal's roll-rate ``metrics_portfolio``, then overlays both engines'
per-period series. Never reads cashflow_engine's own outputs.

Optional integration: if ``cashflow_engine`` is not importable, or the deal
has no matching CF config under ``S:/QR/jli/Cashflow_Engine/deals/<deal>/``,
``build_cf_comparison_html`` returns ``None`` and the deal report omits the
tab.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd

CF_ENGINE_ROOT = Path("S:/QR/jli/Cashflow_Engine")


# ── Engine resolution ────────────────────────────────────────────────────

def _try_import_cf_engine() -> ModuleType | None:
    """Import ``cashflow_engine``; fall back to a sys.path append if needed."""
    try:
        import cashflow_engine  # type: ignore[import-not-found]
        return cashflow_engine
    except ImportError:
        pass
    if CF_ENGINE_ROOT.is_dir() and str(CF_ENGINE_ROOT) not in sys.path:
        sys.path.insert(0, str(CF_ENGINE_ROOT))
        try:
            import cashflow_engine  # type: ignore[import-not-found]
            return cashflow_engine
        except ImportError:
            return None
    return None


def _load_cf_deal_config(deal: str, scenario: str) -> dict | None:
    cfg_path = CF_ENGINE_ROOT / "deals" / deal / "configs" / f"{scenario}.json"
    if not cfg_path.is_file():
        return None
    return json.loads(cfg_path.read_text())


def _resolve_cf_path(path_str: str | None) -> Path | None:
    if path_str is None:
        return None
    p = Path(path_str)
    return p if p.is_absolute() else CF_ENGINE_ROOT / p


# ── Curves derived from roll-rate metrics ────────────────────────────────
#
# Cashflow projections are always period-indexed. The cashflow_engine looks
# up CDR/CPR by projection ``period`` (not ``loan_age``), so we feed it from
# the period-indexed sheets:
#
#   - ``metrics_grouped_period`` (term × grade × period) — preferred,
#     matches the standalone CF runner's input shape.
#   - ``metrics_portfolio`` (period only) — fallback when grouped is empty.
#
# ``metrics_grouped`` (which is indexed by ``loan_age``) is intentionally
# not used here: for seasoned pools, ``loan_age`` ≠ ``period``, and feeding
# loan-age curves to a period-keyed engine miscompares cohorts.

_COHORT_COLS = ("term", "grade")


def _curves_from_rr(
    metrics_grouped_period_df: pd.DataFrame,
    metrics_portfolio_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a (cohort, period, cdr, cpr) curves DataFrame from RR metrics.

    Falls back from grouped-period to portfolio-flat when needed.
    Returns an empty DataFrame when neither source is usable.
    """
    if _has_curves(metrics_grouped_period_df):
        cohort_cols = [c for c in _COHORT_COLS
                       if c in metrics_grouped_period_df.columns]
        if cohort_cols:
            return _emit_curves(metrics_grouped_period_df, cohort_cols)

    if _has_curves(metrics_portfolio_df):
        return _emit_curves(metrics_portfolio_df, [])

    return pd.DataFrame()


def _has_curves(df: pd.DataFrame) -> bool:
    return not df.empty and {"period", "cdr", "cpr"}.issubset(df.columns)


def _emit_curves(df: pd.DataFrame, cohort_cols: list[str]) -> pd.DataFrame:
    out = df[[*cohort_cols, "period", "cdr", "cpr"]].copy()
    out["period"] = out["period"].astype(int)
    out = out[out["period"] >= 1].dropna(subset=["cdr", "cpr"])
    return out.sort_values([*cohort_cols, "period"]).reset_index(drop=True)


def _severity_array(sev_path: Path | None, *, avg_start_age: int, horizon: int):
    if sev_path is None or not sev_path.is_file():
        return 1.0
    sev_df = pd.read_csv(sev_path, sep="\t")
    sev_curve = sev_df.set_index("loan_age")["severity"].to_dict()
    max_age = max(sev_curve.keys())
    return np.array(
        [sev_curve.get(min(avg_start_age + t, max_age), sev_curve[max_age])
         for t in range(horizon)]
    )


# ── Engine invocation ────────────────────────────────────────────────────

def _run_cf_engine(
    deal: str,
    scenario: str,
    rr_metrics_portfolio: pd.DataFrame,
    rr_metrics_grouped_period: pd.DataFrame,
) -> tuple[Any, int] | None:
    """Run cashflow_engine for the deal with RR-derived curves.

    Returns ``(ProjectionResult, max_orig_term)`` or ``None`` if any
    precondition is missing. ``max_orig_term`` is the largest original term
    found in the CF tape — used downstream to cap the x-axis on the
    comparison charts to a portfolio-meaningful horizon.
    """
    ce = _try_import_cf_engine()
    if ce is None:
        return None
    cf_cfg = _load_cf_deal_config(deal, scenario)
    if cf_cfg is None:
        return None

    tape_path = _resolve_cf_path(cf_cfg["tape"]["path"])
    if tape_path is None or not tape_path.is_file():
        return None

    curves_df = _curves_from_rr(rr_metrics_grouped_period, rr_metrics_portfolio)
    if curves_df.empty:
        return None

    tape_df = pd.read_csv(tape_path)
    fields = cf_cfg["tape"].get("fields", {})
    lf_kwargs = {
        "balance_col":     fields.get("balance",     "current_balance"),
        "rate_col":        fields.get("rate",        "interest_rate"),
        "rem_term_col":    fields.get("rem_term",    "remaining_term"),
        "term_col":        fields.get("term",        "original_term"),
        "grade_col":       fields.get("grade",       "loan_grade"),
        "monthly_pmt_col": fields.get("monthly_pmt", "scheduled_payment"),
        "loan_id_col":     fields.get("loan_id",     "loan_id"),
        "loan_age_col":    fields.get("loan_age",    "loan_age"),
    }
    tape = ce.LoanFrame.from_dataframe(tape_df, **lf_kwargs)

    horizon = int(tape.rem_term.max())
    avg_start_age = int(round((tape.term_orig - tape.rem_term).mean()))
    severity = _severity_array(
        _resolve_cf_path(cf_cfg.get("severity")),
        avg_start_age=avg_start_age, horizon=horizon,
    )

    engine_cfg = cf_cfg.get("engine", {})
    result, _ = ce.run_scenario(
        tape, curves_df,
        dials_df=None,
        severity=severity,
        full_prepay_int_factor=engine_cfg.get("full_prepay_int_factor", 1.0),
        cpr_excludes_defaults=engine_cfg.get("cpr_excludes_defaults", False),
    )
    max_orig_term = int(np.asarray(tape.term_orig).max())
    return result, max_orig_term


# ── Series alignment + KPI computation ───────────────────────────────────

def _rr_series(
    rr_portfolio_df: pd.DataFrame,
    rr_metrics_portfolio_df: pd.DataFrame,
) -> pd.DataFrame:
    """Per-period series from roll-rate sim outputs.

    Note: RR ``prin_pmt`` already includes both scheduled principal and
    full-prepayment (``pif_bal``) flows — do not add ``pif_bal`` separately.

    The ``cgl`` series is taken from ``Metrics_Portfolio.cgl`` (the canonical
    sim metric) rather than recomputed from ``Portfolio.loss`` — they can
    differ slightly because metrics_portfolio is balance-weighted from
    metrics_grouped, while the raw loss column is the unweighted sum.
    """
    df = rr_portfolio_df.copy().sort_values("period").reset_index(drop=True)
    initial = float(df["begin_bal"].iloc[0]) if not df.empty else 0.0
    recovery = df["net_recov"] if "net_recov" in df.columns else pd.Series(0.0, index=df.index)
    interest = df["int_pmt"]
    principal = df["prin_pmt"]
    net_cf = interest + principal + recovery

    cgl = _merge_metrics_cgl(df["period"], rr_metrics_portfolio_df)
    if cgl is None:
        cgl = df["loss"].cumsum() / initial if initial > 0 else 0.0

    return pd.DataFrame({
        "period":       df["period"].astype(int),
        "balance_eop":  df["end_bal"],
        "pool_factor":  df["end_bal"] / initial if initial > 0 else 0.0,
        "interest":     interest,
        "cum_interest": interest.cumsum(),
        "cgl":          cgl,
        "net_cf":       net_cf,
        "cum_net_cf":   net_cf.cumsum(),
    })


def _merge_metrics_cgl(
    period_series: pd.Series,
    metrics_portfolio_df: pd.DataFrame,
) -> pd.Series | None:
    """Align ``Metrics_Portfolio.cgl`` onto the Portfolio period axis.

    Returns the cgl series re-indexed to the Portfolio's period order
    (forward-filled across any gaps), or ``None`` if metrics aren't usable.
    """
    if metrics_portfolio_df.empty or "cgl" not in metrics_portfolio_df.columns:
        return None
    mp = metrics_portfolio_df[["period", "cgl"]].dropna()
    if mp.empty:
        return None
    aligned = (
        pd.DataFrame({"period": period_series.astype(int)})
        .merge(mp, on="period", how="left")
    )
    return aligned["cgl"].ffill().fillna(0.0)


def _cf_series(cf_ts: pd.DataFrame) -> pd.DataFrame:
    """Per-period series from cashflow_engine portfolio_ts."""
    df = cf_ts.copy().sort_values("period").reset_index(drop=True)
    initial = float(df["base"].iloc[0]) if not df.empty else 0.0
    interest = df["interest"]
    sched_prin = df["sched_prin"]
    prepay_prin = df["prepay_prin"]
    recovery = df["recovery"] if "recovery" in df.columns else pd.Series(0.0, index=df.index)
    net_cf = interest + sched_prin + prepay_prin + recovery
    return pd.DataFrame({
        "period":       df["period"].astype(int),
        "balance_eop":  df["balance_eop"],
        "pool_factor":  df["pool_factor"] if "pool_factor" in df.columns
                        else (df["balance_eop"] / initial if initial > 0 else 0.0),
        "interest":     interest,
        "cum_interest": df["cum_interest"],
        "cgl":          df["cgl"] if "cgl" in df.columns
                        else df["default_prin"].cumsum() / initial,
        "net_cf":       net_cf,
        "cum_net_cf":   net_cf.cumsum(),
    })


def _fmt_money(v: float) -> str:
    if v is None or not np.isfinite(v):
        return "-"
    return f"${v:,.0f}"


def _fmt_pct_of(num: float, denom: float) -> str:
    if denom is None or denom == 0 or not np.isfinite(denom):
        return "-"
    return f"{num/denom*100:.1f}% of CF projection"


def _fmt_pct(v: float, digits: int = 2) -> str:
    if v is None or not np.isfinite(v):
        return "-"
    return f"{v*100:.{digits}f}%"


# ── HTML rendering ───────────────────────────────────────────────────────

_HEAD = """\
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Cashflow Comparison</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       margin: 0; padding: 20px 32px; background: #ffffff; color: #212529; font-size: 13px; }
h1 { color: #212529; border-bottom: 2px solid #2b7ab5; padding-bottom: 8px; font-size: 20px; }
h2 { color: #212529; margin: 24px 0 8px 0; font-size: 16px; }
.kpi-row { display: flex; gap: 16px; margin: 16px 0 20px 0; flex-wrap: wrap; }
.kpi-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px;
             padding: 12px 16px; min-width: 150px; flex: 1; }
.kpi-card .label { font-size: 10px; font-weight: 600; color: #6c757d;
                     text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 3px; }
.kpi-card .value { font-size: 20px; font-weight: 700; color: #212529; }
.kpi-card .sub { font-size: 10px; color: #6c757d; margin-top: 2px; }
.kpi-card.highlight { border-color: #2b7ab5; }
.kpi-card.highlight .value { color: #2b7ab5; }
.note { font-size: 12px; color: #6c757d; margin: 8px 0 16px 0; line-height: 1.5; }
.chart-row { display: flex; gap: 16px; flex-wrap: wrap; }
.chart-box { background: #f8f9fa; padding: 14px; margin: 8px 0; border-radius: 6px;
              border: 1px solid #dee2e6; overflow: visible; flex: 1; min-width: 45%; }
.chart-box .vega-embed { overflow: visible !important; }
.chart-box .vega-embed summary { display: none !important; }
</style>
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
</head><body>
"""


# Per-chart palette — colors match the reference HTMLs in C:/Users/jasonli/Downloads.
_CHARTS = [
    # (id_suffix, title, series_field, y_format, color)
    ("cf_comp_0", "Cumulative Interest",         "cum_interest", "$,.0f", "#a0e426"),
    ("cf_comp_1", "Periodic Interest",           "interest",     "$,.0f", "#5bc0eb"),
    ("cf_comp_2", "Cumulative Gross Loss (CGL)", "cgl",          ".2%",   "#fa7921"),
    ("cf_comp_3", "Pool Factor",                 "pool_factor",  ".2%",   "#9bc53d"),
    ("cf_comp_4", "Net Cash Flow (per period)",  "net_cf",       "$,.0f", "#8b5cf6"),
    ("cf_comp_5", "Cumulative Net Cash Flow",    "cum_net_cf",   "$,.0f", "#e55934"),
]


def _build_long_records(rr: pd.DataFrame, cf: pd.DataFrame, field: str) -> list[dict]:
    """Long-form (period, value, series) records for one metric."""
    out: list[dict] = []
    for _, row in rr.iterrows():
        out.append({"period": int(row["period"]), "value": float(row[field]),
                    "series": "Roll-Rate Model"})
    for _, row in cf.iterrows():
        out.append({"period": int(row["period"]), "value": float(row[field]),
                    "series": "Cashflow Projection"})
    return out


def _chart_spec(title: str, color: str, y_format: str,
                values: list[dict], max_period: int) -> dict:
    """Vega-Lite spec mirroring the reference HTMLs exactly:

    - Width 680 × Height 350
    - Both series share one color; line style (solid vs. dashed) distinguishes them
    - joinaggregate transform builds per-period tooltip columns
    - Three-layer composition: line, invisible hover circles, vertical hover rule
    """
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width":   680,
        "height":  350,
        "title":   title,
        "data":    {"values": values},
        "transform": [
            {"calculate": "datum.series === 'Roll-Rate Model' ? datum.value : null",
             "as": "_s0"},
            {"calculate": "datum.series === 'Cashflow Projection' ? datum.value : null",
             "as": "_s1"},
            {"joinaggregate": [
                {"op": "max", "field": "_s0", "as": "Roll-Rate Model"},
                {"op": "max", "field": "_s1", "as": "Cashflow Projection"},
             ], "groupby": ["period"]},
        ],
        "layer": [
            {
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.5},
                "encoding": {
                    "x": {"field": "period", "type": "quantitative", "title": "Period",
                          "axis": {"grid": True, "format": "d", "gridDash": [2, 4]},
                          "scale": {"nice": False, "domain": [0, max_period],
                                    "clamp": True}},
                    "y": {"field": "value", "type": "quantitative", "title": "",
                          "axis": {"grid": True, "format": y_format,
                                   "gridDash": [2, 4]}},
                    "color": {"field": "series", "type": "nominal", "title": "",
                              "scale": {"domain": ["Roll-Rate Model",
                                                   "Cashflow Projection"],
                                        "range": [color, color]},
                              "legend": {"orient": "right", "labelLimit": 200,
                                         "symbolType": "stroke",
                                         "symbolStrokeWidth": 2.5,
                                         "symbolSize": 200}},
                    "strokeDash": {"field": "series", "type": "nominal",
                                   "scale": {"domain": ["Roll-Rate Model",
                                                        "Cashflow Projection"],
                                             "range": [[1, 0], [6, 4]]},
                                   "legend": None},
                },
            },
            {
                "mark": {"type": "circle", "size": 60, "opacity": 0},
                "selection": {"hover": {"type": "single", "nearest": True,
                                        "on": "pointerover",
                                        "encodings": ["x"], "empty": "none"}},
                "encoding": {
                    "x": {"field": "period", "type": "quantitative"},
                    "y": {"field": "value",  "type": "quantitative"},
                    "color": {"field": "series", "type": "nominal"},
                    "opacity": {"condition": {"selection": "hover", "value": 1},
                                "value": 0},
                    "tooltip": [
                        {"field": "period", "type": "quantitative",
                         "title": "Period", "format": "d"},
                        {"field": "Roll-Rate Model", "type": "quantitative",
                         "title": "Roll-Rate Model", "format": y_format},
                        {"field": "Cashflow Projection", "type": "quantitative",
                         "title": "Cashflow Projection", "format": y_format},
                    ],
                },
            },
            {
                "mark": {"type": "rule", "color": "#adb5bd",
                         "strokeDash": [4, 4]},
                "encoding": {"x": {"field": "period", "type": "quantitative"}},
                "transform": [{"filter": {"selection": "hover"}}],
            },
        ],
        "config": {
            "view": {"stroke": None},
            "background": "#f8f9fa",
            "axis": {"labelColor": "#212529", "titleColor": "#212529",
                     "gridColor": "#e0e0e0", "domainColor": "#ced4da",
                     "tickColor": "#ced4da"},
            "legend": {"labelColor": "#212529", "titleColor": "#212529"},
            "title":  {"color": "#212529", "subtitleColor": "#6c757d"},
        },
    }


def _render_html(deal: str, rr: pd.DataFrame, cf: pd.DataFrame, max_period: int) -> str:
    initial = float(rr["balance_eop"].iloc[0] / rr["pool_factor"].iloc[0]) \
              if not rr.empty and rr["pool_factor"].iloc[0] > 0 else 0.0
    rr_cum_int = float(rr["cum_interest"].iloc[-1]) if not rr.empty else 0.0
    cf_cum_int = float(cf["cum_interest"].iloc[-1]) if not cf.empty else 0.0
    rr_cum_cf  = float(rr["cum_net_cf"].iloc[-1]) if not rr.empty else 0.0
    cf_cum_cf  = float(cf["cum_net_cf"].iloc[-1]) if not cf.empty else 0.0
    rr_cgl     = float(rr["cgl"].iloc[-1]) if not rr.empty else 0.0
    cf_cgl     = float(cf["cgl"].iloc[-1]) if not cf.empty else 0.0
    int_leak   = cf_cum_int - rr_cum_int
    cf_gap     = cf_cum_cf - rr_cum_cf
    cgl_gap    = rr_cgl - cf_cgl

    kpis = (
        '<div class="kpi-row">'
        f'  <div class="kpi-card"><div class="label">Initial Balance</div>'
        f'    <div class="value">{_fmt_money(initial)}</div></div>'
        f'  <div class="kpi-card"><div class="label">Roll-Rate Cum. Interest</div>'
        f'    <div class="value">{_fmt_money(rr_cum_int)}</div></div>'
        f'  <div class="kpi-card"><div class="label">Cashflow Cum. Interest</div>'
        f'    <div class="value">{_fmt_money(cf_cum_int)}</div></div>'
        f'  <div class="kpi-card highlight"><div class="label">Interest Leakage</div>'
        f'    <div class="value">{_fmt_money(int_leak)}</div>'
        f'    <div class="sub">{_fmt_pct_of(int_leak, cf_cum_int)}</div></div>'
        '</div>'
        '<div class="kpi-row">'
        f'  <div class="kpi-card"><div class="label">Cum. Cash Flow Gap</div>'
        f'    <div class="value">{_fmt_money(cf_gap)}</div>'
        f'    <div class="sub">CF - RR total</div></div>'
        f'  <div class="kpi-card"><div class="label">Roll-Rate CGL</div>'
        f'    <div class="value">{_fmt_pct(rr_cgl)}</div>'
        f'    <div class="sub">Metrics_Portfolio.cgl (sim)</div></div>'
        f'  <div class="kpi-card"><div class="label">Cashflow CGL</div>'
        f'    <div class="value">{_fmt_pct(cf_cgl)}</div>'
        f'    <div class="sub">CF projection lifetime</div></div>'
        f'  <div class="kpi-card highlight"><div class="label">CGL Gap (RR − CF)</div>'
        f'    <div class="value">{_fmt_pct(cgl_gap)}</div>'
        f'    <div class="sub">tail loss CF misses</div></div>'
        '</div>'
    )

    specs: list[dict] = []
    chart_divs: list[str] = []
    for chart_id, title, field, y_format, color in _CHARTS:
        values = _build_long_records(rr, cf, field)
        spec = _chart_spec(title, color, y_format, values, max_period)
        specs.append({"id": chart_id, "spec": spec})
        chart_divs.append(
            f'<div class="chart-box"><div id="{chart_id}"></div></div>'
        )

    rows_html = (
        '<h2>Interest</h2>'
        f'<div class="chart-row">{chart_divs[0]}{chart_divs[1]}</div>'
        '<h2>Credit &amp; Balance</h2>'
        f'<div class="chart-row">{chart_divs[2]}{chart_divs[3]}</div>'
        '<h2>Net Cash Flow</h2>'
        f'<div class="chart-row">{chart_divs[4]}{chart_divs[5]}</div>'
    )

    specs_json = json.dumps(specs, default=str, separators=(",", ":"))
    embed_script = (
        '<script>(function() {\n'
        f'  var specs = {specs_json};\n'
        '  specs.forEach(function(entry) {\n'
        "    vegaEmbed('#' + entry.id, entry.spec, "
        "{ actions: false, renderer: 'svg' })\n"
        '      .catch(function(e) { console.error(entry.id, e); });\n'
        '  });\n'
        '})();</script>'
    )

    return (
        _HEAD
        + '<h1>Cashflow Projection vs Roll-Rate Model</h1>'
        + '<p class="note">'
          '<strong>Roll-Rate Model</strong> (solid) accounts for delinquent loans not '
          'making interest payments. '
          '<strong>Cashflow Projection</strong> (dashed) assumes all performing loans '
          'pay interest until default or prepayment.'
          '</p>'
        + kpis
        + rows_html
        + embed_script
        + '</body></html>'
    )


# ── Public entry point ───────────────────────────────────────────────────

def build_cf_comparison_html(
    deal: str,
    scenario: str,
    rr_portfolio_df: pd.DataFrame,
    rr_metrics_portfolio_df: pd.DataFrame,
    rr_metrics_grouped_period_df: pd.DataFrame,
) -> str | None:
    """Run cashflow_engine with RR-derived curves and render a comparison HTML.

    Curves are drawn from ``metrics_grouped_period`` (term × grade × period)
    when available — matching the standalone CF runner's input granularity —
    and fall back to ``metrics_portfolio`` (portfolio-flat) otherwise.

    Returns ``None`` when cashflow_engine is unavailable, the deal has no CF
    config, the CF tape is missing, or the RR metrics are insufficient — so
    the caller can simply skip the tab.
    """
    if rr_portfolio_df.empty or (
        rr_metrics_portfolio_df.empty and rr_metrics_grouped_period_df.empty
    ):
        return None
    run = _run_cf_engine(
        deal, scenario, rr_metrics_portfolio_df, rr_metrics_grouped_period_df,
    )
    if run is None:
        return None
    cf_result, max_orig_term = run
    if cf_result.portfolio_ts.empty:
        return None
    rr = _rr_series(rr_portfolio_df, rr_metrics_portfolio_df)
    cf = _cf_series(cf_result.portfolio_ts)
    horizon = _chart_horizon(rr_portfolio_df, max_orig_term)
    rr = rr[rr["period"] <= horizon].reset_index(drop=True)
    cf = _extend_cf_to_horizon(cf, horizon)
    return _render_html(deal, rr, cf, max_period=horizon)


def _chart_horizon(rr_portfolio_df: pd.DataFrame, max_orig_term: int) -> int:
    """X-axis cap: the last period RR records a nonzero loss, floored at the
    longest original term. The floor guarantees CF's full lifecycle is shown;
    the loss-event ceiling exposes any RR tail chargeoff past loan maturity
    (a current loan at term-end can still roll dq30 → dq60 → dq90 → LIQ).
    """
    loss_periods = rr_portfolio_df.loc[rr_portfolio_df["loss"] > 0, "period"]
    last_loss = int(loss_periods.max()) if not loss_periods.empty else 0
    return max(max_orig_term, last_loss)


def _extend_cf_to_horizon(cf: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Forward-fill CF past its own horizon so charts show a flat tail.

    CF projects only to ``max(rem_term)``; anything past that has no engine
    output. We add zero-flow rows that hold the cumulative series at its
    final value, so the dashed CF line continues horizontally to the chart
    edge instead of dropping out.
    """
    if cf.empty:
        return cf
    last_period = int(cf["period"].max())
    if last_period >= horizon:
        return cf
    last = cf.iloc[-1]
    tail = pd.DataFrame([
        {
            "period":       p,
            "balance_eop":  0.0,
            "pool_factor":  0.0,
            "interest":     0.0,
            "cum_interest": float(last["cum_interest"]),
            "cgl":          float(last["cgl"]),
            "net_cf":       0.0,
            "cum_net_cf":   float(last["cum_net_cf"]),
        }
        for p in range(last_period + 1, horizon + 1)
    ])
    return pd.concat([cf, tail], ignore_index=True)
