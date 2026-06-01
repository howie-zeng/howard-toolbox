"""Theme constants — colours and chart dimensions."""
from __future__ import annotations

# Base palette
BG = "#ffffff"
CARD_BG = "#f8f9fa"
BORDER = "#dee2e6"
TEXT = "#212529"
TEXT_DIM = "#6c757d"
ACCENT = "#2b7ab5"

# Chart dimensions
CHART_HALF_WIDTH = 670
CHART_FULL_WIDTH = 1400
CHART_SIMPLE_WIDTH = 900
CHART_HEIGHT = 380

# Per-metric accent colours (single-series charts)
METRIC_COLORS = {
    "cpr": "#5bc0eb",
    "cdr": "#e55934",
    "cgl": "#fa7921",
    "begin_bal": "#5bc0eb",
    "pool_factor": "#9bc53d",
    "cum_interest": "#a0e426",
    "ctd1": "#8b5cf6",
    "ctp": "#16a34a",
}

# Stacked-area palettes
DQ_COLORS = ["#fde74c", "#fa7921", "#e55934", "#9b1d20"]
PMT_COLORS = ["#5bc0eb", "#9bc53d", "#c3a5e0"]

# Multi-source palette (Deal + per-quarter comparisons in summary tables)
SOURCE_COLORS = ["#4a90d9", "#e8734a", "#5cc07a", "#b07cd8", "#f0b429"]

# Multi-line palette for curve charts (one colour per cohort series)
CURVE_PALETTE = [
    "#4e79a7", "#59a14f", "#edc949", "#af7aa1", "#ff9da7",
    "#9c755f", "#bab0ab", "#76b7b2", "#8cd17d", "#b6992d",
    "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#393b79",
]

# FICO / rate bucket definitions — applied to the input loan tape
FICO_BUCKET_BINS = [0, 650, 700, 750, 800]
FICO_BUCKET_LABELS = ["0-649", "650-699", "700-749", "750-799", "800+"]

RATE_BUCKET_BINS = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 1.0]
RATE_BUCKET_LABELS = ["0-5%", "5-10%", "10-15%", "15-20%", "20-25%", "25%+"]
