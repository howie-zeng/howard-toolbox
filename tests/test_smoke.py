"""Smoke tests: verify each module imports without error."""

import importlib
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "emailer.render",
        "emailer.generate_diagram",
        "dial.dial_utils",
        "dial.update_dials",
        "formatter.format_excel",
    ],
)
def test_module_imports(module):
    if sys.platform != "win32" and module == "emailer.render":
        pytest.skip("emailer.render requires win32clipboard")
    importlib.import_module(module)
