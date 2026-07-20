"""Page builders for the deal report."""
from .aggregate import build_aggregate_page
from .pool_composition import build_pool_composition_page

__all__ = ["build_aggregate_page", "build_pool_composition_page"]
