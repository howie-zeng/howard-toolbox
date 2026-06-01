"""Load simulation outputs and input loan tape for the deal report.

Conventions:
- Sim output:  ``output/<deal>/<scenario>/sim_results.xlsx``
- Loan input:  ``input/deals/<deal>/<deal>.csv`` (or first CSV in folder)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SIM_RESULTS_FILENAME = "sim_results.xlsx"
SHEET_PORTFOLIO = "Portfolio"
SHEET_METRICS_PORTFOLIO = "Metrics_Portfolio"
SHEET_METRICS_GROUPED = "Metrics_Grouped"
SHEET_METRICS_GROUPED_PERIOD = "Metrics_Grouped_Period"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def model_root() -> Path:
    """Root of the roll-rate-model checkout (parent of ``python/``)."""
    return Path(__file__).resolve().parent.parent.parent


def resolve_sim_path(deal: str, scenario: str = "base", *, output_dir: Path | None = None) -> Path:
    """Path to ``sim_results.xlsx`` for a deal/scenario."""
    output_dir = Path(output_dir) if output_dir else model_root() / "output"
    return output_dir / deal / scenario / SIM_RESULTS_FILENAME


def resolve_input_csv(deal: str, *, input_dir: Path | None = None) -> Path | None:
    """Find the loan-tape CSV for a deal.

    Prefers ``<deal>.csv`` and falls back to the first CSV in the folder.
    Returns None when the input directory or CSV is missing.
    """
    input_dir = Path(input_dir) if input_dir else model_root() / "input" / "deals"
    deal_dir = input_dir / deal
    if not deal_dir.is_dir():
        return None
    preferred = deal_dir / f"{deal}.csv"
    if preferred.is_file():
        return preferred
    csvs = sorted(deal_dir.glob("*.csv"))
    return csvs[0] if csvs else None


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_sim_results(deal: str, scenario: str = "base", *, output_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the four sim_results sheets into a dict.

    ``metrics_grouped`` is indexed by ``loan_age``; ``metrics_grouped_period``
    is indexed by projection ``period``. Cashflow projections must use the
    period-indexed sheet.
    """
    xlsx_path = resolve_sim_path(deal, scenario, output_dir=output_dir)
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"sim_results not found: {xlsx_path}")

    out: dict[str, pd.DataFrame] = {}
    with pd.ExcelFile(xlsx_path) as xls:
        for key, sheet in [
            ("portfolio",              SHEET_PORTFOLIO),
            ("metrics_portfolio",      SHEET_METRICS_PORTFOLIO),
            ("metrics_grouped",        SHEET_METRICS_GROUPED),
            ("metrics_grouped_period", SHEET_METRICS_GROUPED_PERIOD),
        ]:
            out[key] = pd.read_excel(xls, sheet_name=sheet) if sheet in xls.sheet_names else pd.DataFrame()
    return out


def load_deal_input(deal: str, *, input_dir: Path | None = None) -> pd.DataFrame:
    """Load the raw loan-tape CSV; returns an empty DataFrame if absent."""
    csv_path = resolve_input_csv(deal, input_dir=input_dir)
    if csv_path is None:
        return pd.DataFrame()
    return pd.read_csv(csv_path)


