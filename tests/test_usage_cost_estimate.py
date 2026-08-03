import importlib.util
from pathlib import Path

import pandas as pd

_MODULE_PATH = Path(__file__).resolve().parents[1] / "usage" / "cost_estimate.py"
_SPEC = importlib.util.spec_from_file_location("cost_estimate", _MODULE_PATH)
cost_estimate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cost_estimate)

BASE_PRICES = cost_estimate.BASE_PRICES
compute_cost_estimates = cost_estimate.compute_cost_estimates
map_model = cost_estimate.map_model
price_row = cost_estimate.price_row
rates_for_event = cost_estimate.rates_for_event


def test_new_gpt_56_export_labels_map_to_correct_base_models() -> None:
    assert map_model("gpt-5.6-sol-max") == ("gpt-5.6-sol", False)
    assert map_model("gpt-5.6-terra-max") == ("gpt-5.6-terra", False)
    assert map_model("gpt-5.6-terra-medium") == ("gpt-5.6-terra", False)


def test_current_official_model_prices_are_available() -> None:
    expected = {
        "claude-4.7-opus-fast": (30.00, 37.50, 3.00, 150.00),
        "claude-4.8-opus": (5.00, 6.25, 0.50, 25.00),
        "claude-5-sonnet": (3.00, 3.75, 0.30, 15.00),
        "claude-fable-5": (10.00, 12.50, 1.00, 50.00),
        "composer-2.5": (0.50, None, 0.20, 2.50),
        "gemini-3-pro-image": (2.00, None, 0.20, 12.00),
        "gemini-3.5-flash": (1.50, None, 0.15, 9.00),
        "glm-5.2": (1.40, None, 0.26, 4.40),
        "gpt-5.6-luna": (1.00, 1.25, 0.10, 6.00),
        "gpt-5.6-sol": (5.00, 6.25, 0.50, 30.00),
        "gpt-5.6-terra": (2.50, 3.125, 0.25, 15.00),
        "grok-4.5": (2.00, None, 0.50, 6.00),
        "kimi-k2.7-code": (0.95, None, 0.19, 4.00),
    }

    assert {model: BASE_PRICES[model] for model in expected} == expected


def test_current_official_export_labels_map_to_supported_models() -> None:
    assert map_model("claude-opus-4-7-fast") == ("claude-4.7-opus-fast", False)
    assert map_model("claude-opus-4-8-thinking-max") == ("claude-4.8-opus", False)
    assert map_model("claude-sonnet-5-thinking-max") == ("claude-5-sonnet", False)
    assert map_model("claude-fable-5-thinking-max") == ("claude-fable-5", False)
    assert map_model("composer-2.5-fast")[0] == "composer-2.5"
    assert map_model("gemini-3-pro-image-preview") == ("gemini-3-pro-image", False)
    assert map_model("gemini-3.5-flash") == ("gemini-3.5-flash", False)


def test_composer_25_fast_label_uses_documented_base_rates() -> None:
    base_key, is_fast = map_model("composer-2.5-fast")

    assert rates_for_event(0, 0, 0, base_key, is_fast) == (0.50, 0.50, 0.20, 2.50)


def test_gpt_56_sol_row_threshold_doubles_input_rates_not_output() -> None:
    conservative = rates_for_event(
        0,
        10_000,
        300_000,
        "gpt-5.6-sol",
        False,
    )
    high = rates_for_event(
        0,
        10_000,
        300_000,
        "gpt-5.6-sol",
        False,
        gpt_long_context_policy=cost_estimate.GPT_LONG_CONTEXT_ROW_THRESHOLD,
    )

    assert conservative == (5.00, 6.25, 0.50, 30.00)
    assert high == (10.00, 12.50, 1.00, 30.00)


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
