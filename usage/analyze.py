"""
Cursor API Usage Analysis

Generates a self-contained interactive HTML report from a Cursor usage-events CSV export.

Usage:
    python usage/analyze.py <csv_path> [options]

Examples:
    python usage/analyze.py ~/Downloads/usage-events-2026-04-09.csv
    python usage/analyze.py usage.csv --since 2026-01-01
    python usage/analyze.py usage.csv --name Yiming --out report.html
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent))
from cost_estimate import compute_costs, map_model

# ── Helpers ─────────────────────────────────────────────────────────────────

def fmt_num(n: float) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def fig_to_div(fig: go.Figure, fig_id: str = "") -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=fig_id)


MODEL_FAMILY_RULES = [
    (lambda m: "claude" in m and "opus" in m,   "Claude Opus"),
    (lambda m: "claude" in m and "sonnet" in m, "Claude Sonnet"),
    (lambda m: "claude" in m and "haiku" in m,  "Claude Haiku"),
    (lambda m: "claude" in m,                   "Claude (Other)"),
    (lambda m: "gpt" in m,                      "GPT"),
    (lambda m: "gemini" in m or "grok" in m,    "Gemini/Grok"),
    (lambda m: "cursor" in m or "composer" in m,"Cursor Built-in"),
    (lambda m: m in ("auto", ""),               "Auto"),
]

FAMILY_COLORS = {
    "Claude Opus": "#7C3AED", "Claude Sonnet": "#2563EB",
    "Claude Haiku": "#06B6D4", "Claude (Other)": "#8B5CF6",
    "GPT": "#10B981", "Gemini/Grok": "#F59E0B",
    "Cursor Built-in": "#6B7280", "Auto": "#9CA3AF", "Other": "#D1D5DB",
}

KIND_COLORS = {
    "User API Key": "#7C3AED", "Included": "#10B981",
    "pro-free-trial": "#F59E0B", "usage-based": "#EF4444",
    "Aborted, Not Charged": "#9CA3AF", "Errored, No Charge": "#D1D5DB",
}

CHART_LAYOUT = dict(template="plotly_white", margin=dict(l=50, r=30, t=30, b=50))
LEGEND_H = dict(orientation="h", y=-0.18)


def classify_model(name: str) -> str:
    ml = name.lower()
    for test, family in MODEL_FAMILY_RULES:
        if test(ml):
            return family
    return "Other"


# ── Data loading ────────────────────────────────────────────────────────────

def load_data(csv_path: str, since: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])

    if since:
        df = df[df["Date"] >= since].copy()

    df["date"] = df["Date"].dt.date
    df["hour"] = df["Date"].dt.hour
    df["weekday"] = df["Date"].dt.day_name()
    df["week"] = df["Date"].dt.isocalendar().week.astype(int)
    df["year_month"] = df["Date"].dt.to_period("M").astype(str)

    for col in ["Input (w/ Cache Write)", "Input (w/o Cache Write)",
                "Cache Read", "Output Tokens", "Total Tokens"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Raw `Cost` column from CSV is $0 for everything (always Included / Free /
    # User API Key), so we replace it with a token-based imputed cost using
    # Cursor's published API rates. Included events stay at $0.
    df["Cost"] = compute_costs(df)
    df["model_family"] = df["Model"].map(classify_model)
    df["base_model"] = df["Model"].fillna("").map(lambda m: map_model(m)[0])
    return df


# ── Charts ──────────────────────────────────────────────────────────────────

def chart_daily_volume(df, family_counts, daily_agg):
    """Stacked daily requests by model family + 7-day rolling-average line overlay."""
    daily = df.groupby(["date", "model_family"]).size().reset_index(name="requests")
    fig = go.Figure()
    for fam in family_counts.index:
        sub = daily[daily["model_family"] == fam]
        fig.add_trace(go.Bar(
            x=sub["date"], y=sub["requests"], name=fam,
            marker_color=FAMILY_COLORS.get(fam, "#999"),
        ))
    fig.add_trace(go.Scatter(
        x=daily_agg["date"], y=daily_agg["req_7d"], name="7-day avg",
        mode="lines", line=dict(color="#111827", width=2.5),
    ))
    fig.update_layout(
        barmode="stack", xaxis_title="", yaxis_title="Requests",
        height=420, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


def chart_model_pies(family_counts, family_tokens):
    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["By Request Count", "By Total Tokens"],
    )
    pie_kwargs = dict(hole=0.45, textposition="outside", textinfo="label+percent",
                      insidetextorientation="horizontal")
    fig.add_trace(go.Pie(
        labels=family_counts.index, values=family_counts.values,
        marker_colors=[FAMILY_COLORS.get(f, "#999") for f in family_counts.index],
        **pie_kwargs,
    ), row=1, col=1)
    fig.add_trace(go.Pie(
        labels=family_tokens["model_family"], values=family_tokens["Total Tokens"],
        marker_colors=[FAMILY_COLORS.get(f, "#999") for f in family_tokens["model_family"]],
        **pie_kwargs,
    ), row=1, col=2)
    fig.update_layout(
        template="plotly_white", height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )
    return fig


_HEATMAP_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]


def _localize(df: pd.DataFrame, tz_offset: int = -4) -> pd.DataFrame:
    """Attach `local_hour` and `local_weekday` columns for a given UTC offset."""
    df_local = df.copy()
    df_local["local_hour"] = (df_local["hour"] + tz_offset) % 24
    day_map = {d: i for i, d in enumerate(_HEATMAP_DAYS)}
    inv_map = {i: d for d, i in day_map.items()}
    df_local["local_weekday"] = df_local.apply(
        lambda r: inv_map.get((day_map.get(r["weekday"], 0) - 1) % 7)
        if (r["hour"] + tz_offset) < 0 else r["weekday"],
        axis=1,
    )
    return df_local


def chart_heatmap(df, tz_offset: int = -4):
    """Activity heatmap: request count by weekday × local hour."""
    df_local = _localize(df, tz_offset)
    heat = df_local.groupby(["local_weekday", "local_hour"]).size().reset_index(name="count")
    pivot = heat.pivot(index="local_weekday", columns="local_hour", values="count").fillna(0)
    pivot = pivot.reindex(_HEATMAP_DAYS).reindex(columns=range(24), fill_value=0)

    tz_label = f"UTC{tz_offset:+d}" if tz_offset != 0 else "UTC"
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index, colorscale="Purples",
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Requests: %{z}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title=f"Hour ({tz_label})", yaxis_title="",
        template="plotly_white", height=360,
        margin=dict(l=90, r=30, t=30, b=60),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def chart_cost_heatmap(df, tz_offset: int = -4):
    """Spend heatmap: paid USD by weekday × local hour (User API Key only)."""
    paid = df[df["Kind"] == "User API Key"]
    if paid.empty:
        return go.Figure()
    df_local = _localize(paid, tz_offset)
    heat = (df_local.groupby(["local_weekday", "local_hour"])["Cost"]
            .sum().reset_index(name="cost"))
    pivot = (heat.pivot(index="local_weekday", columns="local_hour", values="cost")
             .fillna(0))
    pivot = pivot.reindex(_HEATMAP_DAYS).reindex(columns=range(24), fill_value=0)

    tz_label = f"UTC{tz_offset:+d}" if tz_offset != 0 else "UTC"
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index, colorscale="Reds",
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>$%{z:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title=f"Hour ({tz_label})", yaxis_title="",
        template="plotly_white", height=360,
        margin=dict(l=90, r=30, t=30, b=60),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def chart_cache(df):
    daily = df.groupby("date").agg(
        total_input=("Input (w/ Cache Write)", "sum"),
        input_no_cache=("Input (w/o Cache Write)", "sum"),
        cache_read=("Cache Read", "sum"),
    ).reset_index()
    denom = (daily["total_input"] + daily["input_no_cache"] + daily["cache_read"]).replace(0, 1)
    daily["cache_pct"] = daily["cache_read"] / denom * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["cache_pct"],
        mode="lines+markers", name="Cache Hit %",
        line=dict(color="#06B6D4", width=2), marker=dict(size=3),
        fill="tozeroy", fillcolor="rgba(6,182,212,0.1)",
    ))
    fig.update_layout(
        xaxis_title="Date", yaxis_title="Cache Hit %",
        height=360, **CHART_LAYOUT,
    )
    return fig


def chart_monthly(monthly):
    """Bar: requests per month (left axis). Line: paid cost (right axis)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["requests"], name="Requests",
        marker_color="rgba(124,58,237,0.6)",
        hovertemplate="%{x}<br>%{y:,} requests<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=monthly["month_label"], y=monthly["cost"], name="Paid Spend (USD)",
        line=dict(color="#EF4444", width=2.5), mode="lines+markers",
        hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(height=380, legend=LEGEND_H, **CHART_LAYOUT)
    fig.update_yaxes(title_text="Requests", secondary_y=False)
    fig.update_yaxes(title_text="Paid Spend (USD)", secondary_y=True)
    return fig


def chart_maxmode(df):
    daily = df.groupby(["date", "Max Mode"]).size().reset_index(name="count")
    fig = go.Figure()
    for mode in ["Yes", "No"]:
        sub = daily[daily["Max Mode"] == mode]
        fig.add_trace(go.Bar(
            x=sub["date"], y=sub["count"], name=f"Max Mode: {mode}",
            marker_color="#7C3AED" if mode == "Yes" else "#D1D5DB",
        ))
    fig.update_layout(
        barmode="stack", xaxis_title="Date", yaxis_title="Requests",
        height=380, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


def chart_daily_cost(df):
    """Daily paid spend (bars) with 7-day rolling-average line overlay."""
    paid = df[df["Kind"] == "User API Key"]
    if paid.empty:
        return go.Figure()
    daily = (
        paid.groupby("date")["Cost"].sum().reset_index()
        .sort_values("date")
    )
    daily["cost_7d"] = daily["Cost"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["Cost"], name="Daily Spend",
        marker_color="rgba(124,58,237,0.35)",
        hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["cost_7d"], name="7-day avg",
        mode="lines", line=dict(color="#7C3AED", width=2.5),
        hovertemplate="%{x}<br>7d avg: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="", yaxis_title="Paid Spend (USD)",
        height=360, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


def chart_cumulative_cost(df):
    """Cumulative paid spend over time (area)."""
    paid = df[df["Kind"] == "User API Key"]
    if paid.empty:
        return go.Figure()
    daily = paid.groupby("date")["Cost"].sum().reset_index().sort_values("date")
    daily["cumulative"] = daily["Cost"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["cumulative"], mode="lines",
        line=dict(color="#7C3AED", width=2.5),
        fill="tozeroy", fillcolor="rgba(124,58,237,0.15)",
        hovertemplate="%{x}<br>Cumulative: $%{y:,.2f}<extra></extra>",
        name="Cumulative Spend",
    ))
    fig.update_layout(
        xaxis_title="", yaxis_title="Cumulative Paid Spend (USD)",
        height=360, showlegend=False, **CHART_LAYOUT,
    )
    return fig


def chart_monthly_cost(df):
    """Bar chart of paid spend (User API Key events) by month."""
    paid = df[df["Kind"] == "User API Key"].copy()
    if paid.empty:
        return go.Figure()
    monthly = paid.groupby("year_month")["Cost"].sum().reset_index()
    monthly["month_label"] = monthly["year_month"].apply(
        lambda ym: pd.Timestamp(ym).strftime("%b %Y")
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["Cost"],
        marker_color="#7C3AED",
        text=[f"${v:,.0f}" for v in monthly["Cost"]],
        textposition="outside",
        hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Month", yaxis_title="Paid Spend (USD)",
        height=380, **CHART_LAYOUT,
    )
    return fig


def chart_cost_by_model(df, top_n: int = 10):
    """Horizontal bar: top-N base models by paid spend."""
    paid = df[df["Kind"] == "User API Key"]
    if paid.empty:
        return go.Figure()
    by_model = (
        paid.groupby("base_model")["Cost"].sum()
        .sort_values(ascending=True).tail(top_n)
    )
    fig = go.Figure(go.Bar(
        y=by_model.index, x=by_model.values,
        orientation="h",
        marker_color="#7C3AED",
        text=[f"${v:,.0f}" for v in by_model.values],
        textposition="outside",
        hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Paid Spend (USD)", yaxis_title="",
        template="plotly_white", height=max(320, 28 * len(by_model) + 80),
        margin=dict(l=220, r=60, t=20, b=50),
    )
    return fig


def chart_cost_breakdown(df):
    """Pie: where the paid spend goes (cache write / input / cache read / output).

    Approximation: uses overall effective rates by weighting each token type's
    sum by its average price across paid events.
    """
    paid = df[df["Kind"] == "User API Key"].copy()
    if paid.empty:
        return go.Figure()
    # Attribute each row's cost to its token components using the per-row
    # effective rates implied by map_model.
    from cost_estimate import BASE_PRICES  # local import to avoid top-level churn
    labels = ["Cache Write (input cached)", "Input (uncached)", "Cache Read", "Output"]
    totals = [0.0, 0.0, 0.0, 0.0]
    for _, r in paid.iterrows():
        base, is_fast = map_model(r["Model"])
        p_in, p_cw, p_cr, p_out = BASE_PRICES.get(base, BASE_PRICES["auto"])
        if p_cw is None:
            p_cw = p_in
        if is_fast and base != "claude-4.6-opus-fast":
            p_in, p_cw, p_cr, p_out = p_in*2, p_cw*2, p_cr*2, p_out*2
        totals[0] += r["Input (w/ Cache Write)"] / 1e6 * p_cw
        totals[1] += r["Input (w/o Cache Write)"] / 1e6 * p_in
        totals[2] += r["Cache Read"] / 1e6 * p_cr
        totals[3] += r["Output Tokens"] / 1e6 * p_out
    colors = ["#7C3AED", "#4F46E5", "#06B6D4", "#10B981"]
    fig = go.Figure(go.Pie(
        labels=labels, values=totals,
        marker_colors=colors, hole=0.45,
        textinfo="label+percent",
        texttemplate="%{label}<br>$%{value:,.0f} (%{percent})",
        textposition="outside",
        hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=380,
        margin=dict(l=20, r=20, t=30, b=20), showlegend=False,
    )
    return fig


def chart_billing_kind(df):
    daily = df.groupby(["date", "Kind"]).size().reset_index(name="count")
    fig = go.Figure()
    for kind in df["Kind"].unique():
        sub = daily[daily["Kind"] == kind]
        fig.add_trace(go.Bar(
            x=sub["date"], y=sub["count"], name=kind,
            marker_color=KIND_COLORS.get(kind, "#999"),
        ))
    fig.update_layout(
        barmode="stack", xaxis_title="Date", yaxis_title="Requests",
        height=380, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


# ── Report assembly ─────────────────────────────────────────────────────────

def build_report(df: pd.DataFrame, name: str = "Howard") -> str:
    # ── Core volume metrics ────────────────────────────────────────────────
    total_events = len(df)
    date_range_start = df["Date"].min().strftime("%b %d, %Y")
    date_range_end = df["Date"].max().strftime("%b %d, %Y")
    n_active_days = df["date"].nunique()
    total_tokens = df["Total Tokens"].sum()
    total_input = df["Input (w/ Cache Write)"].sum() + df["Input (w/o Cache Write)"].sum()
    total_output = df["Output Tokens"].sum()
    total_cache_read = df["Cache Read"].sum()
    avg_daily_events = total_events / max(n_active_days, 1)
    avg_tokens_per_req = total_tokens / max(total_events, 1)

    family_counts = df["model_family"].value_counts()

    daily_agg = df.groupby("date").agg(
        requests=("Date", "count"), total_tokens=("Total Tokens", "sum"),
    ).reset_index().sort_values("date")
    daily_agg["req_7d"] = daily_agg["requests"].rolling(7, min_periods=1).mean()

    family_tokens = df.groupby("model_family")["Total Tokens"].sum().reset_index()
    family_tokens = family_tokens.sort_values("Total Tokens", ascending=False)

    monthly = df.groupby("year_month").agg(
        requests=("Date", "count"), total_tokens=("Total Tokens", "sum"),
        output_tokens=("Output Tokens", "sum"), cost=("Cost", "sum"),
    ).reset_index().sort_values("year_month")
    monthly["month_label"] = monthly["year_month"].apply(
        lambda ym: pd.Timestamp(ym).strftime("%b %Y")
    )

    # ── Cost metrics (User API Key only) ───────────────────────────────────
    paid_df = df[df["Kind"] == "User API Key"]
    total_paid = float(paid_df["Cost"].sum())
    n_paid_events = len(paid_df)
    paid_active_days = paid_df["date"].nunique()
    avg_paid_per_day = total_paid / max(paid_active_days, 1)
    avg_paid_per_event = total_paid / max(n_paid_events, 1)

    top_cost_model = (
        paid_df.groupby("base_model")["Cost"].sum().sort_values(ascending=False)
        if not paid_df.empty else pd.Series(dtype=float)
    )
    if len(top_cost_model):
        top_cost_model_name = top_cost_model.index[0]
        top_cost_model_val = float(top_cost_model.iloc[0])
        top_cost_model_pct = top_cost_model_val / max(total_paid, 1e-9) * 100
    else:
        top_cost_model_name, top_cost_model_val, top_cost_model_pct = "n/a", 0.0, 0.0

    monthly_paid = paid_df.groupby("year_month")["Cost"].sum().sort_index()
    max_date = df["Date"].max()

    # MoM comparison — if the latest month is only partially elapsed, annualize
    # it to a full-month equivalent so the comparison is apples-to-apples.
    latest_month_is_partial = False
    latest_month_days_elapsed = 0
    latest_month_days_in_month = 0
    if len(monthly_paid) >= 2:
        latest_ym = pd.Timestamp(monthly_paid.index[-1])
        month_end = (latest_ym + pd.offsets.MonthEnd(0)).date()
        latest_month_days_in_month = month_end.day
        latest_month_days_elapsed = min(max_date.date().day, month_end.day)
        latest_month_is_partial = max_date.date() < month_end
        latest_month_cost = float(monthly_paid.iloc[-1])
        prior_month_cost = float(monthly_paid.iloc[-2])
        if latest_month_is_partial and latest_month_days_elapsed > 0:
            latest_month_projected = (latest_month_cost
                                      / latest_month_days_elapsed
                                      * latest_month_days_in_month)
        else:
            latest_month_projected = latest_month_cost
        mom_pct = ((latest_month_projected - prior_month_cost)
                   / max(prior_month_cost, 1e-9) * 100)
    else:
        latest_month_cost = float(monthly_paid.iloc[-1]) if len(monthly_paid) else 0.0
        prior_month_cost, mom_pct, latest_month_projected = 0.0, 0.0, latest_month_cost

    # Burn-rate projection: average daily paid spend over the last 14 days × 30
    recent_14 = paid_df[paid_df["Date"] >= (max_date - timedelta(days=14))]
    recent_14_days = max(recent_14["date"].nunique(), 1)
    burn_daily = recent_14["Cost"].sum() / recent_14_days
    projected_monthly = burn_daily * 30

    # ── Cache savings: tokens served from cache at cache-read rate vs input rate ─
    from cost_estimate import BASE_PRICES
    cache_savings = 0.0
    cache_read_cost_total = 0.0
    for _, r in paid_df.iterrows():
        base, is_fast = map_model(r["Model"])
        p_in, p_cw, p_cr, p_out = BASE_PRICES.get(base, BASE_PRICES["auto"])
        if p_cw is None:
            p_cw = p_in
        if is_fast and base != "claude-4.6-opus-fast":
            p_in, p_cr = p_in * 2, p_cr * 2
        cr_tokens = r["Cache Read"] or 0
        cache_read_cost_total += cr_tokens / 1e6 * p_cr
        cache_savings += cr_tokens / 1e6 * (p_in - p_cr)

    # ── General stats ──────────────────────────────────────────────────────
    busiest = daily_agg.loc[daily_agg["requests"].idxmax()]
    busiest_str = pd.Timestamp(busiest["date"]).strftime("%b %d, %Y")
    busiest_count = int(busiest["requests"])
    top_model = top_cost_model_name if top_cost_model_name != "n/a" else df["Model"].value_counts().index[0]
    cache_overall = total_cache_read / max(total_input + total_cache_read, 1) * 100
    max_mode_pct = (df["Max Mode"] == "Yes").sum() / total_events * 100
    median_output = df[df["Output Tokens"] > 0]["Output Tokens"].median()
    avg_output_per_req = total_output / max(total_events, 1)

    recent_30 = df[df["Date"] >= (max_date - timedelta(days=30))]
    older = df[(df["Date"] < (max_date - timedelta(days=30))) &
               (df["Date"] >= (max_date - timedelta(days=60)))]
    recent_daily = len(recent_30) / max(recent_30["date"].nunique(), 1)
    older_daily = len(older) / max(older["date"].nunique(), 1)
    trend_pct = ((recent_daily - older_daily) / max(older_daily, 1)) * 100
    trend_arrow = "&#9650;" if trend_pct > 0 else "&#9660;" if trend_pct < 0 else "&#9644;"
    trend_color = "#10B981" if trend_pct > 0 else "#EF4444" if trend_pct < 0 else "#6B7280"
    mom_color = "#EF4444" if mom_pct > 0 else "#10B981" if mom_pct < 0 else "#6B7280"

    # ── Charts ─────────────────────────────────────────────────────────────
    figs = {
        "daily_vol":       chart_daily_volume(df, family_counts, daily_agg),
        "pie":             chart_model_pies(family_counts, family_tokens),
        "heat":            chart_heatmap(df),
        "cost_heat":       chart_cost_heatmap(df),
        "cache":           chart_cache(df),
        "monthly":         chart_monthly(monthly),
        "maxmode":         chart_maxmode(df),
        "kind":            chart_billing_kind(df),
        "cost_daily":      chart_daily_cost(df),
        "cost_cumulative": chart_cumulative_cost(df),
        "cost_monthly":    chart_monthly_cost(df),
        "cost_by_model":   chart_cost_by_model(df),
        "cost_breakdown":  chart_cost_breakdown(df),
    }
    divs = {k: fig_to_div(v, k) for k, v in figs.items()}

    # Tables
    monthly_rows = ""
    for _, r in monthly.iterrows():
        monthly_rows += (
            f"<tr><td>{r['month_label']}</td><td>{int(r['requests']):,}</td>"
            f"<td>{fmt_num(r['total_tokens'])}</td><td>{fmt_num(r['output_tokens'])}</td>"
            f"<td>${r['cost']:,.2f}</td></tr>"
        )

    # Paid-spend model table (User API Key only, top 10)
    cost_model_rows = ""
    if not paid_df.empty:
        cm = (
            paid_df.groupby("base_model").agg(
                events=("Date", "count"),
                tokens=("Total Tokens", "sum"),
                cost=("Cost", "sum"),
            ).reset_index().sort_values("cost", ascending=False).head(10)
        )
        for _, r in cm.iterrows():
            pct = r["cost"] / max(total_paid, 1e-9) * 100
            cost_model_rows += (
                f"<tr><td>{r['base_model']}</td><td>{int(r['events']):,}</td>"
                f"<td>{fmt_num(r['tokens'])}</td>"
                f"<td>${r['cost']:,.2f}</td><td>{pct:.1f}%</td></tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name}'s Cursor Usage Report</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
    :root {{
        --purple-600: #7C3AED; --purple-50: #F5F3FF;
        --gray-50: #F9FAFB; --gray-100: #F3F4F6; --gray-200: #E5E7EB;
        --gray-500: #6B7280; --gray-700: #374151; --gray-900: #111827;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--gray-50); color: var(--gray-900); line-height: 1.6;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
    header {{
        background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
        color: white; padding: 32px 0; margin-bottom: 28px;
    }}
    header h1 {{ font-size: 2rem; font-weight: 700; }}
    header p {{ opacity: 0.85; margin-top: 6px; font-size: 1rem; }}
    .kpi-grid {{
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 16px; margin-bottom: 32px;
    }}
    .kpi-card {{
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid var(--gray-200);
    }}
    .kpi-card .label {{ font-size: 0.8rem; color: var(--gray-500); text-transform: uppercase;
        letter-spacing: 0.05em; font-weight: 600; }}
    .kpi-card .value {{ font-size: 1.75rem; font-weight: 700; color: var(--purple-600); margin-top: 4px; }}
    .kpi-card .sub {{ font-size: 0.8rem; color: var(--gray-500); margin-top: 2px; }}
    .kpi-card.highlight {{
        background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
        border-color: transparent;
    }}
    .kpi-card.highlight .label,
    .kpi-card.highlight .sub {{ color: rgba(255,255,255,0.85); }}
    .kpi-card.highlight .value {{ color: white; }}
    .card-title {{
        font-weight: 600; margin-bottom: 10px; color: var(--gray-700);
        font-size: 0.95rem;
    }}
    .section {{ margin-bottom: 36px; }}
    .section h2 {{
        font-size: 1.25rem; font-weight: 700; color: var(--gray-900);
        margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid var(--gray-200);
    }}
    .chart-card {{
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid var(--gray-200);
        margin-bottom: 24px;
    }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    @media (max-width: 1024px) {{
        .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 768px) {{
        .two-col {{ grid-template-columns: 1fr; }}
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .cost-note {{
        font-size: 0.8rem; color: var(--gray-500); margin-top: 8px;
        font-style: italic;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th {{ text-align: left; padding: 10px 14px; background: var(--gray-100);
        font-weight: 600; color: var(--gray-700); border-bottom: 2px solid var(--gray-200); }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--gray-200); }}
    tr:hover td {{ background: var(--purple-50); }}
    .insight-grid {{
        display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    }}
    @media (max-width: 900px) {{
        .insight-grid {{ grid-template-columns: 1fr; }}
    }}
    .insight-box {{
        background: var(--purple-50); border-left: 4px solid var(--purple-600);
        border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 0;
    }}
    .insight-box h3 {{ font-size: 0.95rem; font-weight: 700; color: var(--purple-600); margin-bottom: 6px; }}
    .insight-box p {{ font-size: 0.9rem; color: var(--gray-700); }}
    footer {{ text-align: center; padding: 24px; color: var(--gray-500); font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
    <div class="container">
        <h1>{name}&rsquo;s Cursor Usage Report</h1>
        <p>{date_range_start} &ndash; {date_range_end} &middot; Generated {datetime.now().strftime("%b %d, %Y %H:%M")}</p>
    </div>
</header>
<div class="container">

<!-- KPI grid: headline cost metrics first, then volume, then efficiency -->
<div class="kpi-grid">
    <div class="kpi-card highlight">
        <div class="label">Paid Spend</div>
        <div class="value">${total_paid:,.0f}</div>
        <div class="sub">{n_paid_events:,} API-key events &middot; ${avg_paid_per_event:.2f}/req</div>
    </div>
    <div class="kpi-card">
        <div class="label">Avg Daily Spend</div>
        <div class="value">${avg_paid_per_day:,.0f}</div>
        <div class="sub">across {paid_active_days} paid days</div>
    </div>
    <div class="kpi-card">
        <div class="label">Projected Monthly</div>
        <div class="value">${projected_monthly:,.0f}</div>
        <div class="sub">@ {burn_daily:,.0f}/day (last 14d)</div>
    </div>
    <div class="kpi-card">
        <div class="label">MoM Change</div>
        <div class="value" style="color:{mom_color}">{mom_pct:+.0f}%</div>
        <div class="sub">{
            f"proj ${latest_month_projected:,.0f} vs ${prior_month_cost:,.0f}"
            if latest_month_is_partial
            else f"${latest_month_cost:,.0f} vs ${prior_month_cost:,.0f}"
        }</div>
    </div>
    <div class="kpi-card">
        <div class="label">Total Requests</div>
        <div class="value">{total_events:,}</div>
        <div class="sub">{n_active_days} active days &middot; {avg_daily_events:.0f}/day</div>
    </div>
    <div class="kpi-card">
        <div class="label">Total Tokens</div>
        <div class="value">{fmt_num(total_tokens)}</div>
        <div class="sub">{fmt_num(total_output)} output &middot; avg {fmt_num(avg_output_per_req)}/req</div>
    </div>
    <div class="kpi-card">
        <div class="label">Cache Hit Rate</div>
        <div class="value">{cache_overall:.1f}%</div>
        <div class="sub">{fmt_num(total_cache_read)} tokens cached</div>
    </div>
    <div class="kpi-card">
        <div class="label">Max Mode Usage</div>
        <div class="value">{max_mode_pct:.0f}%</div>
        <div class="sub">of all requests</div>
    </div>
</div>

<!-- Executive summary: lead with cost, arranged as 2x2 grid -->
<div class="section">
    <h2>Executive Summary</h2>
    <div class="insight-grid">
        <div class="insight-box">
            <h3>Spend Concentration</h3>
            <p>You spent <strong>${total_paid:,.2f}</strong> out-of-pocket over {paid_active_days} active days
               via your own API key. <strong>{top_cost_model_name}</strong> alone accounts for
               <strong>${top_cost_model_val:,.2f}</strong> ({top_cost_model_pct:.0f}% of spend).</p>
        </div>
        <div class="insight-box">
            <h3>Burn Rate &amp; Projection</h3>
            <p>Your last-14-day average is <strong>${burn_daily:,.0f}/day</strong>, projecting to
               <strong>${projected_monthly:,.0f}/month</strong> at this pace.
               {pd.Timestamp(monthly_paid.index[-1]).strftime("%b %Y") if len(monthly_paid) else "n/a"}{
                   f" (day {latest_month_days_elapsed}/{latest_month_days_in_month}, projected ${latest_month_projected:,.0f} for full month)"
                   if latest_month_is_partial else ""
               } is running <strong style="color:{mom_color}">{mom_pct:+.0f}%</strong>
               vs the prior month (${prior_month_cost:,.0f}).</p>
        </div>
        <div class="insight-box">
            <h3>Cache Savings</h3>
            <p>Prompt caching served <strong>{fmt_num(total_cache_read)}</strong> tokens
               ({cache_overall:.0f}% of all input). At cache-read rates that cost
               <strong>${cache_read_cost_total:,.2f}</strong>; at full input rates the same
               tokens would have cost <strong>${cache_read_cost_total + cache_savings:,.2f}</strong>
               &mdash; caching saved about
               <strong style="color:#10B981">${cache_savings:,.2f}</strong>.</p>
        </div>
        <div class="insight-box">
            <h3>Activity Snapshot</h3>
            <p>Busiest day: <strong>{busiest_str}</strong> ({busiest_count:,} requests).
               Median output size is {fmt_num(median_output)} tokens per request.
               Comparing the last 30 days to the prior 30, daily request volume changed by
               <strong style="color:{trend_color}">{trend_pct:+.0f}%</strong>
               ({recent_daily:.0f} vs {older_daily:.0f} req/day).</p>
        </div>
    </div>
</div>

<!-- SECTION 1: SPEND -->
<div class="section">
    <h2>1. Spend Trajectory</h2>
    <p class="cost-note">
        Pricing imputed from <a href="https://cursor.com/docs/models-and-pricing" target="_blank">Cursor's published API rates</a>.
        Only <code>User API Key</code> events are charged &mdash; <code>Included</code>,
        <code>Aborted</code>, and <code>Errored</code> events are $0. Max Mode 20% upcharge is
        <em>not</em> applied since you pay the provider directly.
    </p>
    <div class="two-col">
        <div class="chart-card">
            <div class="card-title">Daily Paid Spend (7-day avg overlay)</div>
            {divs["cost_daily"]}
        </div>
        <div class="chart-card">
            <div class="card-title">Cumulative Paid Spend</div>
            {divs["cost_cumulative"]}
        </div>
    </div>
    <div class="two-col">
        <div class="chart-card">
            <div class="card-title">Monthly Paid Spend</div>
            {divs["cost_monthly"]}
        </div>
        <div class="chart-card">
            <div class="card-title">Where the Money Goes</div>
            {divs["cost_breakdown"]}
        </div>
    </div>
    <div class="chart-card">
        <div class="card-title">Paid Spend by Base Model (top 10)</div>
        {divs["cost_by_model"]}
    </div>
    <div class="chart-card" style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th>Base Model</th><th>Events</th><th>Tokens</th>
                    <th>Paid Spend</th><th>% of Total</th>
                </tr>
            </thead>
            <tbody>{cost_model_rows}</tbody>
        </table>
    </div>
</div>

<!-- SECTION 2: VOLUME -->
<div class="section">
    <h2>2. Usage Volume</h2>
    <div class="chart-card">
        <div class="card-title">Daily Requests by Model Family (black line = 7-day avg)</div>
        {divs["daily_vol"]}
    </div>
    <div class="chart-card">
        <div class="card-title">Model Family Distribution</div>
        {divs["pie"]}
    </div>
    <div class="chart-card">
        <div class="card-title">Monthly Summary</div>
        {divs["monthly"]}
    </div>
    <div class="chart-card" style="overflow-x:auto;">
        <table>
            <thead><tr>
                <th>Month</th><th>Requests</th><th>Total Tokens</th>
                <th>Output Tokens</th><th>Paid Spend</th>
            </tr></thead>
            <tbody>{monthly_rows}</tbody>
        </table>
    </div>
</div>

<!-- SECTION 3: PATTERNS -->
<div class="section">
    <h2>3. Usage Patterns</h2>
    <div class="two-col">
        <div class="chart-card">
            <div class="card-title">Activity Heatmap (request count, ET)</div>
            {divs["heat"]}
        </div>
        <div class="chart-card">
            <div class="card-title">Spend Heatmap (paid $, ET)</div>
            {divs["cost_heat"]}
        </div>
    </div>
    <div class="two-col">
        <div class="chart-card">
            <div class="card-title">Cache Hit Rate Over Time</div>
            {divs["cache"]}
        </div>
        <div class="chart-card">
            <div class="card-title">Max Mode Adoption</div>
            {divs["maxmode"]}
        </div>
    </div>
    <div class="chart-card">
        <div class="card-title">Billing Kind (Included vs Paid vs Errored)</div>
        {divs["kind"]}
    </div>
</div>

</div>
<footer>{name}&rsquo;s Cursor Usage Report &middot; Auto-generated from usage-events export</footer>
</body>
</html>"""


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML report from a Cursor usage-events CSV.",
    )
    parser.add_argument("csv", help="Path to the usage-events CSV file")
    parser.add_argument("--since", default=None,
                        help="Only include events on or after this date (e.g. 2026-01-01)")
    parser.add_argument("--out", "-o", default=None,
                        help="Output HTML path (default: <csv_dir>/<name>_cursor_usage.html)")
    parser.add_argument("--name", "-n", default="Howard",
                        help="Name for the report title (default: Howard)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found", file=sys.stderr)
        sys.exit(1)

    name = args.name
    out_path = (Path(args.out) if args.out
                else csv_path.parent / f"{name.lower()}_cursor_usage.html")

    print(f"Loading {csv_path} ...")
    df = load_data(str(csv_path), since=args.since)
    print(f"  {len(df):,} events, {df['date'].nunique()} active days, "
          f"{df['Model'].nunique()} models, {fmt_num(df['Total Tokens'].sum())} tokens")

    print(f"Building report for {name} ...")
    html = build_report(df, name=name)

    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
