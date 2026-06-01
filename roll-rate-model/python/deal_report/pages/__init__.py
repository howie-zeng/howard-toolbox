"""Page builders for the deal report."""
from .aggregate import build_aggregate_page
from .summary import build_summary_page

__all__ = ["build_aggregate_page", "build_summary_page"]
