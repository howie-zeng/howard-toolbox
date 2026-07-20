"""Top-level orchestrator: load data + assemble the multi-page HTML report.

Page layout:
  - Aggregate Overview          — KPIs + projected portfolio time-series charts
  - Sim Performance vs Actual   — projected curves overlaid on realized tapes
                                  (omitted when no actuals are available)
  - Pool Composition            — input-tape collateral breakdowns
  - Cashflow Comparison         — cashflow_engine run with RR-derived curves
                                  (omitted when cashflow_engine isn't available
                                  or the deal has no matching CF config)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .render.assets import CSS, JS, VEGA_CDN
from .pages.backtest import build_backtest_html
from .pages.cashflow_compare import build_cf_comparison_html
from .metrics.input_stats import compute_deal_input_stats
from .metrics.kpis import compute_aggregate_metrics, enrich_portfolio_with_transition_rates
from .loader import load_deal_input, load_sim_results, model_root
from .pages import build_aggregate_page, build_pool_composition_page




# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_html(
    deal: str,
    scenario: str = "base",
    *,
    output_dir: Path | None = None,
    input_dir: Path | None = None,
    actuals: dict | None = None,
    onestep: "pd.DataFrame | None" = None,
) -> tuple[str, Path]:
    """Build the full HTML report and write it to disk.

    Reads ``output/<deal>/<scenario>/sim_results.xlsx`` and the deal's input
    CSV (when available), assembles the report, and writes it to
    ``output/<deal>/<deal>_<scenario>_deal_report.html`` (overwritten on each
    run).

    Returns ``(html_string, output_path)``.
    """
    # ── Load ────────────────────────────────────────────────────────────
    sim = load_sim_results(deal, scenario, output_dir=output_dir)
    portfolio_df = sim["portfolio"]
    metrics_portfolio_df = enrich_portfolio_with_transition_rates(
        sim["metrics_portfolio"], sim["metrics_grouped"]
    )
    # Projected delinquency shares (30+ and % current) from the Portfolio sheet,
    # merged onto the metrics so the backtest page can overlay them vs actual.
    _pf = portfolio_df
    _dq = [c for c in ("dq30_bal", "dq60_bal", "dq90_bal", "dq120_bal") if c in _pf.columns]
    if _dq and "begin_bal" in _pf.columns and "period" in _pf.columns:
        _d = pd.DataFrame({"period": _pf["period"]})
        _d["dq30p"] = _pf[_dq].sum(axis=1) / _pf["begin_bal"]
        _d60 = [c for c in ("dq60_bal", "dq90_bal", "dq120_bal") if c in _pf.columns]
        _d["dq60p"] = _pf[_d60].sum(axis=1) / _pf["begin_bal"]
        _init = float(_pf["begin_bal"].iloc[0]) if len(_pf) else 0.0
        _d["dq30_orig"] = _pf[_dq].sum(axis=1) / _init if _init > 0 else float("nan")  # 30+ ÷ original
        metrics_portfolio_df = metrics_portfolio_df.merge(_d, on="period", how="left")
    metrics_grouped_period_df = sim["metrics_grouped_period"]
    input_df = load_deal_input(deal, input_dir=input_dir)

    kpi = compute_aggregate_metrics(portfolio_df, metrics_portfolio_df)
    input_stats = compute_deal_input_stats(input_df) if not input_df.empty else {}

    # ── Build pages ────────────────────────────────────────────────────
    specs: list[dict] = []
    plot_id = 0

    # Realized overlay (computed in memory by the caller, or CSV fallback).
    out_root = Path(output_dir) if output_dir else (model_root() / "output")
    if actuals is None:
        actuals = _load_actuals(out_root / deal)
    lag_profile = actuals.get("lag_profile") if isinstance(actuals, dict) else None

    aggregate_html, plot_id = build_aggregate_page(
        portfolio_df, metrics_portfolio_df, kpi,
        specs=specs, plot_id=plot_id,
        metrics_grouped_period_df=metrics_grouped_period_df,
        lag_profile=lag_profile,
    )
    if input_stats:
        summary_html, plot_id = build_pool_composition_page(
            input_stats, specs=specs, plot_id=plot_id,
        )
    else:
        summary_html = ""

    # CF comparison — inline page (like the others): appends specs to the shared list.
    cf_compare_html, plot_id = build_cf_comparison_html(
        deal, scenario, portfolio_df, metrics_portfolio_df,
        metrics_grouped_period_df, specs=specs, plot_id=plot_id,
    )

    # Backtest vs Actual — overlays the realized tapes onto the sim. Inline page
    # (like Aggregate/Pool Composition): appends its specs to the shared list.
    if actuals["portfolio"] is not None:
        backtest_html, plot_id = build_backtest_html(
            deal, scenario, metrics_portfolio_df, sim["metrics_grouped"],
            actuals["portfolio"], actuals["transitions"], actuals["matrix"],
            metrics_grouped_period_df=metrics_grouped_period_df,
            lag_profile=lag_profile, onestep_df=onestep, specs=specs, plot_id=plot_id,
        )
    else:
        backtest_html = None

    # ── Compose ────────────────────────────────────────────────────────
    html = _compose_document(
        deal=deal, scenario=scenario, kpi=kpi,
        aggregate_html=aggregate_html,
        summary_html=summary_html,
        cf_compare_html=cf_compare_html,
        backtest_html=backtest_html,
        specs=specs,
    )

    # ── Write ──────────────────────────────────────────────────────────
    out_dir = out_root / deal
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{deal}_{scenario}_deal_report.html"
    out_path.write_text(html, encoding="utf-8")
    return html, out_path


def _load_actuals(deal_dir: Path) -> dict:
    """Load the realized CSVs written by realized.py (None each if absent)."""
    out = {}
    for key, name in (("portfolio", "actuals_portfolio.csv"),
                      ("transitions", "actuals_transitions.csv"),
                      ("matrix", "actuals_matrix.csv")):
        p = deal_dir / name
        out[key] = pd.read_csv(p) if p.is_file() else None
    return out


# ---------------------------------------------------------------------------
# Document composition
# ---------------------------------------------------------------------------

def _compose_document(
    *,
    deal: str,
    scenario: str,
    kpi: dict,
    aggregate_html: str,
    summary_html: str,
    cf_compare_html: str | None,
    backtest_html: str | None,
    specs: list[dict],
) -> str:
    """Wrap page bodies in the shared shell (head, header, page nav, JS)."""
    nav_links = ['<a href="#" data-page="page-aggregate" class="active">Aggregate Overview</a>']
    if backtest_html:
        nav_links.append('<a href="#" data-page="page-backtest">Sim Performance vs Actual</a>')
    if summary_html:
        nav_links.append('<a href="#" data-page="page-summary">Pool Composition</a>')
    if cf_compare_html:
        nav_links.append('<a href="#" data-page="page-cf-compare">Cashflow Comparison</a>')

    final_period = kpi.get("final_period", "N/A")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pages = [
        f'<div id="page-aggregate" class="report-page active">'
        f'<div class="content">{aggregate_html}</div></div>'
    ]
    if backtest_html:
        pages.append(
            f'<div id="page-backtest" class="report-page">'
            f'<div class="content">{backtest_html}</div></div>'
        )
    if summary_html:
        pages.append(
            f'<div id="page-summary" class="report-page">'
            f'<div class="content">{summary_html}</div></div>'
        )
    if cf_compare_html:
        pages.append(
            f'<div id="page-cf-compare" class="report-page">'
            f'<div class="content">{cf_compare_html}</div></div>'
        )

    specs_json = json.dumps(specs, default=str, separators=(",", ":"))

    return (
        '<!DOCTYPE html>\n'
        '<html><head>\n'
        '  <meta charset="utf-8">\n'
        f'  <title>Deal Report — {deal}</title>\n'
        f'  <style>{CSS}</style>\n'
        f'  {VEGA_CDN}\n'
        '</head><body>\n'
        f'<div class="header">'
        f'<h1>Deal Report: {deal}</h1>'
        f'<div class="meta">'
        f'<p><strong>Scenario:</strong> {scenario}</p>'
        f'<p><strong>Generated:</strong> {generated}</p>'
        f'<p><strong>Active Periods:</strong> {final_period}</p>'
        f'</div></div>\n'
        f'<div class="page-nav">{"".join(nav_links)}</div>\n'
        + "\n".join(pages) + "\n"
        f'<script id="vega-specs" type="application/json">{specs_json}</script>\n'
        f'<script>{JS}</script>\n'
        '</body></html>\n'
    )
