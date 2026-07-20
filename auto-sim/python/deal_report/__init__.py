"""Deal report HTML generator for roll-rate-model simulation outputs.

Public entry point: ``build_html`` — orchestrates loaders + page builders
to produce a self-contained, multi-page HTML report from
``output/<deal>/<scenario>/sim_results.xlsx`` and
``input/deals/<deal>/*.csv``.
"""
from .builder import build_html

__all__ = ["build_html"]
