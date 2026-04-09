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

    df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce").fillna(0)
    df["model_family"] = df["Model"].map(classify_model)
    return df


# ── Charts ──────────────────────────────────────────────────────────────────

def chart_daily_volume(df, family_counts):
    daily = df.groupby(["date", "model_family"]).size().reset_index(name="requests")
    fig = go.Figure()
    for fam in family_counts.index:
        sub = daily[daily["model_family"] == fam]
        fig.add_trace(go.Bar(
            x=sub["date"], y=sub["requests"], name=fam,
            marker_color=FAMILY_COLORS.get(fam, "#999"),
        ))
    fig.update_layout(
        barmode="stack", xaxis_title="Date", yaxis_title="Requests",
        height=420, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


def chart_daily_tokens(df):
    """Stacked area: input (new) + cache read + output so components sum to total."""
    daily = df.groupby("date").agg(
        input_new=("Input (w/ Cache Write)", "sum"),
        input_no_cache=("Input (w/o Cache Write)", "sum"),
        cache_read=("Cache Read", "sum"),
        output_tokens=("Output Tokens", "sum"),
    ).reset_index()
    daily["input_total"] = daily["input_new"] + daily["input_no_cache"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["cache_read"], name="Cache Read",
        stackgroup="one", line=dict(width=0),
        fillcolor="rgba(6,182,212,0.45)",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["input_total"], name="Input (New)",
        stackgroup="one", line=dict(width=0),
        fillcolor="rgba(124,58,237,0.45)",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["output_tokens"], name="Output",
        stackgroup="one", line=dict(width=0),
        fillcolor="rgba(16,185,129,0.45)",
    ))
    fig.update_layout(
        xaxis_title="Date", yaxis_title="Tokens",
        height=400, legend=LEGEND_H, **CHART_LAYOUT,
    )
    return fig


def chart_trend(daily_agg):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=daily_agg["date"], y=daily_agg["requests"], name="Daily Requests",
        marker_color="rgba(124,58,237,0.25)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=daily_agg["date"], y=daily_agg["req_7d"], name="7-Day Avg Requests",
        line=dict(color="#7C3AED", width=2.5),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=daily_agg["date"], y=daily_agg["tok_7d"], name="7-Day Avg Tokens",
        line=dict(color="#10B981", width=2, dash="dash"),
    ), secondary_y=True)
    fig.update_layout(height=420, legend=LEGEND_H, **CHART_LAYOUT)
    fig.update_yaxes(title_text="Requests", secondary_y=False)
    fig.update_yaxes(title_text="Tokens", secondary_y=True)
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


def chart_heatmap(df, tz_offset: int = -4):
    """Heatmap with hours converted from UTC to local (default ET, UTC-4)."""
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df_local = df.copy()
    df_local["local_hour"] = (df_local["hour"] + tz_offset) % 24
    day_map = {d: i for i, d in enumerate(order)}
    inv_map = {i: d for d, i in day_map.items()}
    df_local["local_weekday"] = df_local.apply(
        lambda r: inv_map.get((day_map.get(r["weekday"], 0) - 1) % 7) if (r["hour"] + tz_offset) < 0 else r["weekday"],
        axis=1,
    )
    heat = df_local.groupby(["local_weekday", "local_hour"]).size().reset_index(name="count")
    pivot = heat.pivot(index="local_weekday", columns="local_hour", values="count").fillna(0)
    pivot = pivot.reindex(order).reindex(columns=range(24), fill_value=0)

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
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["requests"], name="Requests",
        marker_color="#7C3AED",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=monthly["month_label"], y=monthly["total_tokens"], name="Total Tokens",
        line=dict(color="#10B981", width=2.5), mode="lines+markers",
    ), secondary_y=True)
    fig.update_layout(height=400, legend=LEGEND_H, **CHART_LAYOUT)
    fig.update_yaxes(title_text="Requests", secondary_y=False)
    fig.update_yaxes(title_text="Total Tokens", secondary_y=True)
    return fig


def chart_top_models(df):
    top = df.groupby("Model").agg(
        requests=("Date", "count"),
    ).reset_index().sort_values("requests", ascending=True).tail(15)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top["Model"], x=top["requests"],
        orientation="h", marker_color="#7C3AED",
    ))
    fig.update_layout(
        xaxis_title="Requests", yaxis_title="",
        template="plotly_white", height=450,
        margin=dict(l=280, r=30, t=30, b=50),
    )
    return fig


def chart_distribution(df):
    """Log-scale x-axis histogram for heavily skewed token distribution."""
    nonzero = df[df["Total Tokens"] > 0]["Total Tokens"]
    log_vals = np.log10(nonzero)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=log_vals, nbinsx=60,
        marker_color="rgba(124,58,237,0.6)",
        hovertemplate="log₁₀(tokens)=%{x:.1f}<br>Count=%{y}<extra></extra>",
    ))
    tick_vals = list(range(int(log_vals.min()), int(log_vals.max()) + 2))
    tick_text = [fmt_num(10**v) for v in tick_vals]
    fig.update_layout(
        xaxis=dict(title="Tokens per Request", tickvals=tick_vals, ticktext=tick_text),
        yaxis_title="Count",
        height=360, **CHART_LAYOUT,
    )
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

    model_counts = df["Model"].value_counts()
    family_counts = df["model_family"].value_counts()

    # Aggregations
    daily_agg = df.groupby("date").agg(
        requests=("Date", "count"), total_tokens=("Total Tokens", "sum"),
    ).reset_index().sort_values("date")
    daily_agg["req_7d"] = daily_agg["requests"].rolling(7, min_periods=1).mean()
    daily_agg["tok_7d"] = daily_agg["total_tokens"].rolling(7, min_periods=1).mean()

    family_tokens = df.groupby("model_family")["Total Tokens"].sum().reset_index()
    family_tokens = family_tokens.sort_values("Total Tokens", ascending=False)

    monthly = df.groupby("year_month").agg(
        requests=("Date", "count"), total_tokens=("Total Tokens", "sum"),
        output_tokens=("Output Tokens", "sum"), cost=("Cost", "sum"),
    ).reset_index().sort_values("year_month")
    monthly["month_label"] = monthly["year_month"].apply(
        lambda ym: pd.Timestamp(ym).strftime("%b %Y")
    )

    # Stats
    busiest = daily_agg.loc[daily_agg["requests"].idxmax()]
    busiest_str = pd.Timestamp(busiest["date"]).strftime("%b %d, %Y")
    busiest_count = int(busiest["requests"])
    peak_hour = df.groupby("hour").size().idxmax()
    peak_hour_count = int(df.groupby("hour").size().max())
    top_model = model_counts.index[0]
    top_model_pct = model_counts.values[0] / total_events * 100
    cache_overall = total_cache_read / max(total_input + total_cache_read, 1) * 100
    max_mode_pct = (df["Max Mode"] == "Yes").sum() / total_events * 100
    median_tokens = df[df["Total Tokens"] > 0]["Total Tokens"].median()
    p95_tokens = df[df["Total Tokens"] > 0]["Total Tokens"].quantile(0.95)

    recent_30 = df[df["Date"] >= (df["Date"].max() - timedelta(days=30))]
    older = df[(df["Date"] < (df["Date"].max() - timedelta(days=30))) &
               (df["Date"] >= (df["Date"].max() - timedelta(days=60)))]
    recent_daily = len(recent_30) / max(recent_30["date"].nunique(), 1)
    older_daily = len(older) / max(older["date"].nunique(), 1)
    trend_pct = ((recent_daily - older_daily) / max(older_daily, 1)) * 100
    trend_arrow = "&#9650;" if trend_pct > 0 else "&#9660;" if trend_pct < 0 else "&#9644;"
    trend_color = "#10B981" if trend_pct > 0 else "#EF4444" if trend_pct < 0 else "#6B7280"

    # Charts
    figs = {
        "daily_vol":  chart_daily_volume(df, family_counts),
        "daily_tok":  chart_daily_tokens(df),
        "trend":      chart_trend(daily_agg),
        "pie":        chart_model_pies(family_counts, family_tokens),
        "heat":       chart_heatmap(df),
        "cache":      chart_cache(df),
        "monthly":    chart_monthly(monthly),
        "top_models": chart_top_models(df),
        "dist":       chart_distribution(df),
        "maxmode":    chart_maxmode(df),
        "kind":       chart_billing_kind(df),
    }
    divs = {k: fig_to_div(v, k) for k, v in figs.items()}

    # Tables
    monthly_rows = ""
    for _, r in monthly.iterrows():
        monthly_rows += (
            f"<tr><td>{r['month_label']}</td><td>{int(r['requests']):,}</td>"
            f"<td>{fmt_num(r['total_tokens'])}</td><td>{fmt_num(r['output_tokens'])}</td>"
            f"<td>${r['cost']:.2f}</td></tr>"
        )

    model_detail = df.groupby("Model").agg(
        requests=("Date", "count"), total_tokens=("Total Tokens", "sum"),
        avg_tokens=("Total Tokens", "mean"),
    ).reset_index().sort_values("requests", ascending=False).head(10)
    model_rows = ""
    for _, r in model_detail.iterrows():
        model_rows += (
            f"<tr><td>{r['Model']}</td><td>{int(r['requests']):,}</td>"
            f"<td>{fmt_num(r['total_tokens'])}</td><td>{fmt_num(r['avg_tokens'])}</td></tr>"
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
        display: grid; grid-template-columns: repeat(3, 1fr);
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
    @media (max-width: 768px) {{
        .two-col {{ grid-template-columns: 1fr; }}
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th {{ text-align: left; padding: 10px 14px; background: var(--gray-100);
        font-weight: 600; color: var(--gray-700); border-bottom: 2px solid var(--gray-200); }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--gray-200); }}
    tr:hover td {{ background: var(--purple-50); }}
    .insight-box {{
        background: var(--purple-50); border-left: 4px solid var(--purple-600);
        border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 16px;
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

<div class="kpi-grid">
    <div class="kpi-card">
        <div class="label">Total Requests</div>
        <div class="value">{total_events:,}</div>
        <div class="sub">{n_active_days} active days</div>
    </div>
    <div class="kpi-card">
        <div class="label">Total Tokens</div>
        <div class="value">{fmt_num(total_tokens)}</div>
        <div class="sub">Avg {fmt_num(avg_tokens_per_req)}/request</div>
    </div>
    <div class="kpi-card">
        <div class="label">Output Tokens</div>
        <div class="value">{fmt_num(total_output)}</div>
        <div class="sub">Median {fmt_num(median_tokens)}/req</div>
    </div>
    <div class="kpi-card">
        <div class="label">Cache Hit Rate</div>
        <div class="value">{cache_overall:.1f}%</div>
        <div class="sub">{fmt_num(total_cache_read)} tokens cached</div>
    </div>
    <div class="kpi-card">
        <div class="label">Avg Daily Requests</div>
        <div class="value">{avg_daily_events:.0f}</div>
        <div class="sub">30-Day Trend: <span style="color:{trend_color}">{trend_arrow} {abs(trend_pct):.0f}%</span></div>
    </div>
    <div class="kpi-card">
        <div class="label">Max Mode Usage</div>
        <div class="value">{max_mode_pct:.0f}%</div>
        <div class="sub">of all requests</div>
    </div>
</div>

<div class="section">
    <h2>Key Insights</h2>
    <div class="insight-box">
        <h3>Primary Model</h3>
        <p>Your most-used model is <strong>{top_model}</strong>, accounting for {top_model_pct:.1f}% of all requests.
           The 95th percentile request size is {fmt_num(p95_tokens)} tokens, with a median of {fmt_num(median_tokens)}.</p>
    </div>
    <div class="insight-box">
        <h3>Peak Activity</h3>
        <p>Busiest day: <strong>{busiest_str}</strong> with {busiest_count:,} requests.
           Peak hour is <strong>{peak_hour}:00 UTC</strong> ({peak_hour_count:,} total requests at that hour).</p>
    </div>
    <div class="insight-box">
        <h3>Usage Trend</h3>
        <p>Comparing the last 30 days to the prior 30 days, your daily request volume changed by
           <strong style="color:{trend_color}">{trend_pct:+.0f}%</strong>
           ({recent_daily:.0f} vs {older_daily:.0f} requests/day).</p>
    </div>
</div>

<div class="section">
    <h2>Daily Request Volume</h2>
    <div class="chart-card">{divs["daily_vol"]}</div>
</div>

<div class="section">
    <h2>Usage Trend (7-Day Rolling Average)</h2>
    <div class="chart-card">{divs["trend"]}</div>
</div>

<div class="section">
    <h2>Daily Token Volume</h2>
    <div class="chart-card">{divs["daily_tok"]}</div>
</div>

<div class="section">
    <h2>Model Family Distribution</h2>
    <div class="chart-card">{divs["pie"]}</div>
</div>

<div class="section">
    <h2>Top 15 Models by Request Count</h2>
    <div class="chart-card">{divs["top_models"]}</div>
</div>

<div class="section">
    <h2>Activity Patterns</h2>
    <div class="chart-card">{divs["heat"]}</div>
</div>

<div class="section">
    <h2>Cache Efficiency &amp; Max Mode</h2>
    <div class="two-col">
        <div class="chart-card">{divs["cache"]}</div>
        <div class="chart-card">{divs["maxmode"]}</div>
    </div>
</div>

<div class="section">
    <h2>Billing Kind Breakdown</h2>
    <div class="chart-card">{divs["kind"]}</div>
</div>

<div class="section">
    <h2>Request Size Distribution</h2>
    <div class="chart-card">{divs["dist"]}</div>
</div>

<div class="section">
    <h2>Monthly Summary</h2>
    <div class="chart-card">{divs["monthly"]}</div>
    <div class="chart-card" style="overflow-x:auto;">
        <table>
            <thead><tr><th>Month</th><th>Requests</th><th>Total Tokens</th><th>Output Tokens</th><th>Cost</th></tr></thead>
            <tbody>{monthly_rows}</tbody>
        </table>
    </div>
</div>

<div class="section">
    <h2>Top 10 Models (Detailed)</h2>
    <div class="chart-card" style="overflow-x:auto;">
        <table>
            <thead><tr><th>Model</th><th>Requests</th><th>Total Tokens</th><th>Avg Tokens/Req</th></tr></thead>
            <tbody>{model_rows}</tbody>
        </table>
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
