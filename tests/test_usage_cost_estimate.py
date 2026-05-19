import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "usage" / "cost_estimate.py"
_SPEC = importlib.util.spec_from_file_location("cost_estimate", _MODULE_PATH)
cost_estimate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cost_estimate)

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


def test_gpt_55_long_context_doubles_cached_input_not_output() -> None:
    cost = price_row(
        input_with_cw=0,
        input_wo_cw=10_000,
        cache_read=300_000,
        output=10_000,
        base_key="gpt-5.5",
        is_fast=False,
        max_mode=False,
    )

    assert cost == 0.01 * 10.00 + 0.30 * 1.00 + 0.01 * 30.00
