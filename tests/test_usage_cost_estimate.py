import importlib.util
from pathlib import Path

import pandas as pd

_MODULE_PATH = Path(__file__).resolve().parents[1] / "usage" / "cost_estimate.py"
_SPEC = importlib.util.spec_from_file_location("cost_estimate", _MODULE_PATH)
cost_estimate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cost_estimate)

compute_cost_estimates = cost_estimate.compute_cost_estimates
price_row = cost_estimate.price_row


def test_claude_45_sonnet_does_not_double_for_long_context() -> None:
    cost = price_row(
        input_with_cw=0,
        input_wo_cw=250_000,
        cache_read=0,
        output=10_000,
        base_key="claude-4.5-sonnet",
        is_fast=False,
        max_mode=False,
    )

    assert cost == 0.25 * 3.00 + 0.01 * 15.00


def test_gpt_55_conservative_policy_does_not_double_aggregate_row() -> None:
    cost = price_row(
        input_with_cw=0,
        input_wo_cw=10_000,
        cache_read=300_000,
        output=10_000,
        base_key="gpt-5.5",
        is_fast=False,
        max_mode=False,
    )

    assert cost == 0.01 * 5.00 + 0.30 * 0.50 + 0.01 * 30.00


def test_gpt_55_row_threshold_policy_doubles_cached_input_not_output() -> None:
    cost = price_row(
        input_with_cw=0,
        input_wo_cw=10_000,
        cache_read=300_000,
        output=10_000,
        base_key="gpt-5.5",
        is_fast=False,
        max_mode=False,
        gpt_long_context_policy=cost_estimate.GPT_LONG_CONTEXT_ROW_THRESHOLD,
    )

    assert cost == 0.01 * 10.00 + 0.30 * 1.00 + 0.01 * 30.00


def test_compute_cost_estimates_returns_primary_and_high_for_gpt_aggregate_row() -> None:
    df = pd.DataFrame(
        {
            "Kind": ["User API Key", "Included"],
            "Model": ["gpt-5.5-extra-high", "gpt-5.5-extra-high"],
            "Max Mode": ["Yes", "Yes"],
            "Input (w/ Cache Write)": [0, 0],
            "Input (w/o Cache Write)": [10_000, 10_000],
            "Cache Read": [300_000, 300_000],
            "Output Tokens": [10_000, 10_000],
        }
    )

    estimates = compute_cost_estimates(df)

    assert estimates.loc[0, "Cost Primary"] == 0.01 * 5.00 + 0.30 * 0.50 + 0.01 * 30.00
    assert estimates.loc[0, "Cost High"] == 0.01 * 10.00 + 0.30 * 1.00 + 0.01 * 30.00
    assert estimates.loc[0, "Cost Delta"] == estimates.loc[0, "Cost High"] - estimates.loc[0, "Cost Primary"]
    assert estimates.loc[1, "Cost Primary"] == 0.0
    assert estimates.loc[1, "Cost High"] == 0.0
