"""
Compute imputed Cursor usage cost from a usage-events CSV.

Pricing sourced from https://cursor.com/docs/models-and-pricing
All prices are USD per 1M tokens. Max Mode = Yes adds 20% upcharge on
individual plans. Sonnet/Grok get 2x when input exceeds 200k tokens.
Fast variants (OpenAI/Anthropic) price at 2x the base model.
"""

import argparse
import re
from pathlib import Path

import pandas as pd

# Base API pricing per 1M tokens: (input, cache_write, cache_read, output)
# cache_write=None means same as input (no separate cache-write rate in docs)
BASE_PRICES = {
    "claude-4-sonnet":     (3.00, 3.75, 0.30, 15.00),
    "claude-4-sonnet-1m":  (6.00, 7.50, 0.60, 22.50),
    "claude-4.5-haiku":    (1.00, 1.25, 0.10, 5.00),
    "claude-4.5-opus":     (5.00, 6.25, 0.50, 25.00),
    "claude-4.5-sonnet":   (3.00, 3.75, 0.30, 15.00),
    "claude-4.6-opus":     (5.00, 6.25, 0.50, 25.00),
    "claude-4.6-opus-fast":(30.00, 37.50, 3.00, 150.00),
    "claude-4.6-sonnet":   (3.00, 3.75, 0.30, 15.00),
    "claude-4.7-opus":     (5.00, 6.25, 0.50, 25.00),
    "composer-1":          (1.25, None, 0.125, 10.00),
    "composer-1.5":        (3.50, None, 0.35, 17.50),
    "composer-2":          (0.50, None, 0.20, 2.50),
    "gemini-2.5-flash":    (0.30, None, 0.03, 2.50),
    "gemini-3-flash":      (0.50, None, 0.05, 3.00),
    "gemini-3-pro":        (2.00, None, 0.20, 12.00),
    "gemini-3.1-pro":      (2.00, None, 0.20, 12.00),
    "gpt-5":               (1.25, None, 0.125, 10.00),
    "gpt-5-fast":          (2.50, None, 0.25, 20.00),
    "gpt-5-mini":          (0.25, None, 0.025, 2.00),
    "gpt-5-codex":         (1.25, None, 0.125, 10.00),
    "gpt-5.1-codex":       (1.25, None, 0.125, 10.00),
    "gpt-5.1-codex-max":   (1.25, None, 0.125, 10.00),
    "gpt-5.1-codex-mini":  (0.25, None, 0.025, 2.00),
    "gpt-5.2":             (1.75, None, 0.175, 14.00),
    "gpt-5.2-codex":       (1.75, None, 0.175, 14.00),
    "gpt-5.3-codex":       (1.75, None, 0.175, 14.00),
    "gpt-5.4":             (2.50, None, 0.25, 15.00),
    "gpt-5.4-mini":        (0.75, None, 0.075, 4.50),
    "gpt-5.4-nano":        (0.20, None, 0.02, 1.25),
    "grok-4.20":           (2.00, None, 0.20, 6.00),
    "kimi-k2.5":           (0.60, None, 0.10, 3.00),
    "auto":                (1.25, 1.25, 0.25, 6.00),  # Auto pool rates
}

# Sonnet variants and Grok: 2x when input > 200k tokens
LONG_CONTEXT_2X = {"claude-4-sonnet-1m", "claude-4.5-sonnet", "claude-4.6-sonnet", "grok-4.20"}


def map_model(raw: str) -> tuple[str, bool]:
    """Map a CSV model string to (base_key, is_fast)."""
    m = (raw or "").strip().lower()
    if not m:
        return ("auto", False)

    is_fast = m.endswith("-fast") or "-fast" in m
    m_clean = m.replace("-fast", "")

    # Strip reasoning-effort / thinking suffixes (high, medium, xhigh, thinking, preview)
    for suffix in ("-xhigh-thinking", "-max-thinking", "-high-thinking",
                   "-xhigh", "-high", "-medium", "-low", "-thinking",
                   "-preview"):
        if m_clean.endswith(suffix):
            m_clean = m_clean[: -len(suffix)]

    # Cursor-specific labels
    if m_clean == "auto":
        return ("auto", False)
    if m_clean == "agent_review":
        return ("auto", False)  # treat as auto pool
    if m_clean.startswith("premium"):
        # "Premium (Codex 5.3)" → gpt-5.3-codex
        if "5.3" in m_clean and "codex" in m_clean:
            return ("gpt-5.3-codex", is_fast)
        return ("auto", False)

    # Claude Opus Fast is its own line item in the docs (10x pricier)
    if m_clean.startswith("claude-4.6-opus") and is_fast:
        return ("claude-4.6-opus-fast", False)  # fast already baked in

    # Normalize claude-4.x-opus / sonnet / haiku
    if re.match(r"claude-\d\.\d+-(opus|sonnet|haiku)", m_clean):
        return (m_clean, is_fast)

    # Composer
    if m_clean.startswith("composer"):
        return (m_clean, is_fast)

    # Gemini
    if m_clean.startswith("gemini"):
        return (m_clean, is_fast)

    # GPT families — normalize to base keys present in BASE_PRICES
    if m_clean in BASE_PRICES:
        return (m_clean, is_fast)

    # Try progressively shorter prefixes
    candidates = [m_clean]
    parts = m_clean.split("-")
    for i in range(len(parts) - 1, 0, -1):
        candidates.append("-".join(parts[:i]))
    for c in candidates:
        if c in BASE_PRICES:
            return (c, is_fast)

    return ("auto", False)  # safe fallback


def price_row(
    input_with_cw: int,
    input_wo_cw: int,
    cache_read: int,
    output: int,
    base_key: str,
    is_fast: bool,
    max_mode: bool,
) -> float:
    """Return USD cost for a single event."""
    p_in, p_cw, p_cr, p_out = BASE_PRICES.get(base_key, BASE_PRICES["auto"])
    if p_cw is None:
        p_cw = p_in  # cache write == input rate for non-Anthropic models

    # Fast multiplier (2x) for OpenAI/Anthropic fast variants
    # (Claude 4.6 Opus Fast is already a separate, much-more-expensive line item)
    if is_fast and base_key != "claude-4.6-opus-fast":
        p_in *= 2
        p_cw *= 2
        p_cr *= 2
        p_out *= 2

    # Long-context surcharge for Sonnet/Grok when input > 200k
    total_input = (input_with_cw or 0) + (input_wo_cw or 0)
    if base_key in LONG_CONTEXT_2X and total_input > 200_000:
        p_in *= 2
        p_cw *= 2
        p_cr *= 2
        p_out *= 2

    cost = (
        (input_wo_cw or 0) / 1e6 * p_in
        + (input_with_cw or 0) / 1e6 * p_cw
        + (cache_read or 0) / 1e6 * p_cr
        + (output or 0) / 1e6 * p_out
    )

    if max_mode:
        cost *= 1.20  # Max Mode 20% upcharge on individual plans

    return cost


def compute_costs(df: pd.DataFrame) -> pd.Series:
    """Return a per-row USD cost series. Only `User API Key` events are charged;
    `Included` / `Aborted` / `Errored` events cost $0.

    Expects the usual Cursor CSV columns: `Kind`, `Model`, `Max Mode`,
    `Input (w/ Cache Write)`, `Input (w/o Cache Write)`, `Cache Read`,
    `Output Tokens`.
    """
    token_cols = ("Input (w/ Cache Write)", "Input (w/o Cache Write)",
                  "Cache Read", "Output Tokens")
    tok = {c: pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
           for c in token_cols}

    mapping = df["Model"].fillna("").map(map_model)
    base = mapping.map(lambda t: t[0])
    fast = mapping.map(lambda t: t[1])

    is_paid = df["Kind"] == "User API Key"
    costs = pd.Series(0.0, index=df.index)
    if is_paid.any():
        sub_idx = df.index[is_paid]
        costs.loc[sub_idx] = [
            price_row(
                tok["Input (w/ Cache Write)"].loc[i],
                tok["Input (w/o Cache Write)"].loc[i],
                tok["Cache Read"].loc[i],
                tok["Output Tokens"].loc[i],
                base.loc[i],
                bool(fast.loc[i]),
                max_mode=False,  # user pays provider directly, no Cursor upcharge
            )
            for i in sub_idx
        ]
    return costs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--plan-fee", type=float, default=0.0,
                        help="Monthly plan fee in USD to add to totals")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")

    for c in ("Input (w/ Cache Write)", "Input (w/o Cache Write)",
              "Cache Read", "Output Tokens"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["max_mode_bool"] = df["Max Mode"].str.lower().eq("yes")
    mapping = df["Model"].fillna("").map(map_model)
    df["base_model"] = mapping.map(lambda t: t[0])
    df["is_fast"] = mapping.map(lambda t: t[1])

    # Real out-of-pocket cost:
    #   - Included events: $0 (covered by plan)
    #   - Aborted/Errored:  $0
    #   - User API Key:     provider's API rate, no Cursor upcharge
    is_paid = df["Kind"] == "User API Key"
    df["cost_usd"] = 0.0
    df.loc[is_paid, "cost_usd"] = df[is_paid].apply(
        lambda r: price_row(
            r["Input (w/ Cache Write)"],
            r["Input (w/o Cache Write)"],
            r["Cache Read"],
            r["Output Tokens"],
            r["base_model"],
            r["is_fast"],
            max_mode=False,  # provider rate, no Cursor 20% upcharge
        ),
        axis=1,
    )

    df["ym"] = df["Date"].dt.to_period("M").astype(str)

    print(f"Source: {args.csv}")
    print(f"Rows: {len(df):,}")
    print(f"Date range: {df['Date'].min()}  to  {df['Date'].max()}")
    print()

    print("=== Events by Kind ===")
    by_kind = df.groupby("Kind").agg(
        events=("cost_usd", "size"),
        cost_usd=("cost_usd", "sum"),
    ).round(2)
    print(by_kind.to_string())
    print()

    paid = df[is_paid]
    print("=== Paid spend by base model (User API Key only) ===")
    by_model = (
        paid.groupby("base_model")["cost_usd"]
        .agg(["count", "sum"]).round(2)
        .sort_values("sum", ascending=False)
    )
    by_model.columns = ["events", "cost_usd"]
    print(by_model.to_string())
    print()

    print("=== Monthly paid spend (User API Key only) ===")
    monthly = paid.groupby("ym")["cost_usd"].agg(["count", "sum"]).round(2)
    monthly.columns = ["events", "cost_usd"]
    print(monthly.to_string())
    print()

    total_paid = paid["cost_usd"].sum()
    months = max(1, df["ym"].nunique())
    print("=== Summary ===")
    print(f"  User API Key spend (paid to provider): ${total_paid:,.2f}")
    print(f"  Included events:                       {(df['Kind']=='Included').sum():,} (covered by Cursor plan, $0)")
    if args.plan_fee > 0:
        print(f"  Plan fees ({months} months x ${args.plan_fee:.0f}):                  ${months * args.plan_fee:,.2f}")
        print(f"  TOTAL out-of-pocket:                   ${total_paid + months * args.plan_fee:,.2f}")


if __name__ == "__main__":
    main()
