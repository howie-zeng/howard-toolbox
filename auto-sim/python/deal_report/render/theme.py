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

# Backtest overlay series: realized curve + one projection per scenario.
ACTUAL_COLOR = "#212529"
SCEN_COLOR = {
    "PRIME_BASE": "#3b6ea5", "PRIME_BASE_HISTORY": "#8a6d9e",
    "PRIME_STACKED": "#c97b3c", "SUBPRIME_BASE": "#3b6ea5",
    "SUBPRIME_STACKED": "#c97b3c",
}

# Platform accents — same palette as the trans_model ctd1 explorers.
PLATFORM_COLOR = {
    "CarMax": "#e8590c", "Carvana": "#0e7490", "Hyundai": "#1d4ed8",
    "Toyota": "#2f9e44", "Drive": "#eab308", "Exeter": "#b5179e",
    "Santander Drive": "#d00000",
}

# Per-metric accent colours (single-series charts) — semantic & muted:
# blue = balance/size, green = prepay, amber/red = default & loss, teal = interest.
METRIC_COLORS = {
    "begin_bal":    "#3b6ea5",  # balance — slate blue
    "pool_factor":  "#5b8bb5",  # balance % — lighter slate blue
    "cpr":          "#4c956c",  # prepay — green
    "cdr":          "#c97b3c",  # default rate — amber
    "cgl":          "#b3543d",  # cumulative loss — brick red
    "cum_interest": "#3d7d8a",  # interest — teal
    "ctd1":         "#8a6d9e",  # roll to delinquency — muted purple
    "ctp":          "#4c956c",  # prepay — green
}

# Stacked-area palettes
DQ_COLORS = ["#e9c46a", "#e08a4f", "#c25b3f", "#8c2f25"]   # severity: gold -> deep red
PMT_COLORS = ["#3d7d8a", "#4c956c", "#8fa6c2"]             # interest / principal / PIF

# Multi-source palette (Deal + per-quarter comparisons in summary tables)
SOURCE_COLORS = ["#3b6ea5", "#c97b3c", "#4c956c", "#8a6d9e", "#d9a441"]

# Ordered sequential blues for ranked buckets (FICO / rate) — light = low, dark
# = high, so a bucket's colour reads as its position in the ordering.
BUCKET_PALETTE = ["#cfe1f2", "#9ec9e2", "#6baed6", "#4292c6", "#2171b5", "#08519c"]

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
