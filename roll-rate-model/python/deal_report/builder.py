"""Top-level orchestrator: load data + assemble the multi-page HTML report.

Page layout:
  - Aggregate Overview    — KPIs + portfolio time-series charts
  - Summary Statistics    — input-tape breakdowns
  - Cashflow Comparison   — cashflow_engine run with RR-derived curves
                            (omitted when cashflow_engine isn't available
                            or the deal has no matching CF config)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .assets import CSS, JS
from .cashflow_compare import build_cf_comparison_html
from .input_stats import compute_deal_input_stats
from .kpis import compute_aggregate_metrics, enrich_portfolio_with_transition_rates
from .loader import load_deal_input, load_sim_results, model_root
from .pages import build_aggregate_page, build_summary_page

VEGA_CDN = (
    '<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>'
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_html(
    deal: str,
    scenario: str = "base",
    *,
    output_dir: Path | None = None,
    input_dir: Path | None = None,
) -> tuple[str, Path]:
    """Build the full HTML report and write it to disk.

    Reads ``output/<deal>/<scenario>/sim_results.xlsx`` and the deal's input
    CSV (when available), assembles the report, and writes it to
    ``output/<deal>/<deal>_deal_report.html`` (overwritten on each run).

    Returns ``(html_string, output_path)``.
    """
    # ── Load ────────────────────────────────────────────────────────────
    sim = load_sim_results(deal, scenario, output_dir=output_dir)
    portfolio_df = sim["portfolio"]
    metrics_portfolio_df = enrich_portfolio_with_transition_rates(
        sim["metrics_portfolio"], sim["metrics_grouped"]
    )
    metrics_grouped_period_df = sim["metrics_grouped_period"]
    input_df = load_deal_input(deal, input_dir=input_dir)

    kpi = compute_aggregate_metrics(portfolio_df, metrics_portfolio_df)
    input_stats = compute_deal_input_stats(input_df) if not input_df.empty else {}

    # ── Build pages ────────────────────────────────────────────────────
    specs: list[dict] = []
    plot_id = 0

    aggregate_html, plot_id = build_aggregate_page(
        portfolio_df, metrics_portfolio_df, kpi,
        specs=specs, plot_id=plot_id,
    )
    if input_stats:
        summary_html, plot_id = build_summary_page(
            input_stats, specs=specs, plot_id=plot_id,
        )
    else:
        summary_html = ""

    # CF comparison is a self-contained HTML document (iframe srcdoc).
    cf_compare_html = build_cf_comparison_html(
        deal, scenario, portfolio_df, metrics_portfolio_df,
        metrics_grouped_period_df,
    )

    # ── Compose ────────────────────────────────────────────────────────
    html = _compose_document(
        deal=deal, scenario=scenario, kpi=kpi,
        aggregate_html=aggregate_html,
        summary_html=summary_html,
        cf_compare_html=cf_compare_html,
        specs=specs,
    )

    # ── Write ──────────────────────────────────────────────────────────
    out_root = Path(output_dir) if output_dir else (model_root() / "output")
    out_dir = out_root / deal
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{deal}_deal_report.html"
    out_path.write_text(html, encoding="utf-8")
    return html, out_path


# ---------------------------------------------------------------------------
# Document composition
# ---------------------------------------------------------------------------

def _iframe_page(page_id: str, srcdoc_html: str) -> str:
    """Wrap a self-contained HTML document in an iframe page panel."""
    escaped = srcdoc_html.replace("&", "&amp;").replace('"', "&quot;")
    return (
        f'<div id="{page_id}" class="report-page">'
        f'<iframe srcdoc="{escaped}" '
        f'style="width:100%; height:calc(100vh - 120px); border:none;"></iframe>'
        f'</div>'
    )


def _compose_document(
    *,
    deal: str,
    scenario: str,
    kpi: dict,
    aggregate_html: str,
    summary_html: str,
    cf_compare_html: str | None,
    specs: list[dict],
) -> str:
    """Wrap page bodies in the shared shell (head, header, page nav, JS)."""
    nav_links = ['<a href="#" data-page="page-aggregate" class="active">Aggregate Overview</a>']
    if summary_html:
        nav_links.append('<a href="#" data-page="page-summary">Summary Statistics</a>')
    if cf_compare_html:
        nav_links.append('<a href="#" data-page="page-cf-compare">Cashflow Comparison</a>')

    final_period = kpi.get("final_period", "N/A")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pages = [
        f'<div id="page-aggregate" class="report-page active">'
        f'<div class="content">{aggregate_html}</div></div>'
    ]
    if summary_html:
        pages.append(
            f'<div id="page-summary" class="report-page">'
            f'<div class="content">{summary_html}</div></div>'
        )
    if cf_compare_html:
        pages.append(_iframe_page("page-cf-compare", cf_compare_html))

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
