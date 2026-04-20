# Polymarket Copy-Trade Monitor — Plan

Status: **DRAFT, awaiting approval. No code written yet.**

> **Scope for first delivery (Phase 1a):** historical data download and
> win-rate calculation only. See Section 1.5 for the narrowed spec.
> Other phases remain in this doc for context and future sequencing.

## 1. Goal and scope

Build a **read-only** system that:

1. Discovers skilled Polymarket traders using the public leaderboard.
2. Downloads their full trade history.
3. Computes our own skill metrics (not just Polymarket's PnL display).
4. Ranks traders and produces a shortlist.
5. Polls the shortlist and alerts on new trades in near real time.

Explicitly **out of scope** for v1: placing orders, any authenticated CLOB
usage, KYC, pUSD funding, wallet management, Kalshi or any execution venue.
Those are a separate future project if the analytics prove there is edge.

## 2. Success criteria

A v1 is done when all of these are true:

- `fetch_leaderboard.py` runs on a schedule and populates a persistent store
  with daily snapshots across all `(category, timePeriod, orderBy)` slices.
- `fetch_user_trades.py` can backfill and incrementally update trade history
  for an arbitrary wallet address, with no duplicates and safe to rerun.
- `rank_traders.py` produces a shortlist CSV plus an HTML report showing
  each trader's custom metrics (not just PnL).
- `watch_live.py` polls a shortlist every N seconds and emits new trades
  to a sink (stdout + file for v1; Slack/email later).
- A notebook exists that answers the question: "if I had paper-copied the
  top N traders with a T-second lag, what would my PnL curve look like?"

## 1.5 Phase 1a — Historical download & win rate (FIRST DELIVERY)

The narrowest useful first step: get a local dataset rich enough to answer
"who is actually good, and what is their win rate?" Everything downstream
(ranking, monitoring, backtesting) depends on this data existing.

### 1.5.1 Reference feature parity

Trackers like [Polywhaler](https://www.polywhaler.com/),
PolymarketFlow, and PolyWhale all surface the same column set, so we know
the target shape:

| Column | Computed from |
|---|---|
| Win rate | resolved markets / trades per wallet |
| 30-day P&L | `trade` + `market.resolved_outcome` or `/value` series |
| All-time P&L | same |
| Trading volume (notional USD) | sum of `size * price` across trades |
| Top markets / categories | trade count and volume bucketed by market |
| Last activity timestamp | max(trade.timestamp) |
| ROI | P&L / capital deployed |
| Trade count, avg trade size | trade table aggregates |
| Avg holding period | exit_ts - entry_ts per resolved position |

Polywhaler and peers also display a "Smart Money Score" (PolymarketFlow's
version is 0-100 combining volume, consistency, diversification, recency).
We will compute our own version in Phase 2 (see Section 6) — **not** in
Phase 1a. Phase 1a just makes sure the underlying data exists.

### 1.5.2 Wallet universe for backfill

Three options, pick one:

**Option A — Leaderboard union (recommended for v1)**
Everyone who has appeared at any `rank <= 500` in any
`(category, timePeriod, orderBy)` slice over our leaderboard history.
Expected size: ~2,000-5,000 wallets. Manageable.

**Option B — Whale threshold**
Every wallet with at least one single trade of `notional >= $10k` in the
last 12 months. Requires scanning `/trades` market-by-market, which is
much more expensive (we have to walk every market). Polywhaler-style.

**Option C — Both, union**
Most thorough, most expensive. Defer to v2.

Plan assumption: **Option A for Phase 1a**. Option B added in v2 when we
care about whales who never made a leaderboard.

### 1.5.3 Win-rate definition (must choose one)

Prediction-market win rate is ambiguous — three competing definitions:

| Definition | Formula | Pros | Cons |
|---|---|---|---|
| **Per-market** | markets where realized PnL > 0 / total resolved markets traded | Matches Polywhaler / how humans read "86.9% win rate" | Dilutes: one big win = one small loss |
| **Per-trade (fill)** | fills that were profitable vs. final settle / total fills | Fine-grained | Noisy; re-entries look like separate wins |
| **Per-position** | entry-to-exit round trips with PnL > 0 / total round trips | Best semantic match for "did this bet work out" | Requires FIFO position reconstruction |

**Recommendation: compute all three, default-display per-market** (matches
external trackers so numbers are comparable). Each is a distinct metric in
`trader_metric`:

```
win_rate_by_market
win_rate_by_trade
win_rate_by_position
```

Realized/unrealized split is separate and also computed.

### 1.5.4 What "resolved" means

A trade counts toward win-rate denominator **only when its market has
resolved** (`market.resolved = 1`). Open positions are excluded. This means
`fetch_markets.py` (Section 5.5) must run before `rank_traders.py` and
hydrate `market.resolved_outcome` from Gamma API.

For a binary YES/NO market, realized PnL on a closed position:

```
entry_side = BUY outcome_index=k at price p, size s
settle price = 1.0 if resolved_outcome == k else 0.0
realized_pnl = (settle - p) * s
```

For positions closed before resolution (sold on CLOB), PnL is just
`(exit_price - entry_price) * size` summed over FIFO-matched fills.

### 1.5.5 Phase 1a deliverables

Only these scripts plus a validation notebook:

1. `client.py` + `db.py` + `config.py` (shared infra)
2. `fetch_leaderboard.py` — daily snapshot, seeds wallet universe
3. `fetch_user_trades.py` — per-wallet trade backfill, incremental-safe
4. `fetch_markets.py` — resolve `condition_id` -> title + resolution outcome
5. `compute_win_rate.py` — new, Phase 1a-specific CLI:
   ```
   python polymarket/compute_win_rate.py [--wallet 0x...] [--min-resolved 10] [--out stats.csv]
   ```
   Writes `trader_metric` rows for: `win_rate_by_market`,
   `win_rate_by_trade`, `win_rate_by_position`, `pnl_realized_all_time`,
   `pnl_realized_30d`, `volume_usd_all_time`, `n_resolved_markets`,
   `last_active_ts`, `avg_hold_days`.
6. Notebook `notebooks/01_validate_win_rate.ipynb` — spot-check against
   Polymarket profile pages and Polywhaler for 5-10 known wallets.

### 1.5.6 Volume and runtime estimates

- Leaderboard: 10 categories × 4 periods × 2 order_by × up to 1,050 wallets
  = ~84k rows per snapshot. One HTTP call per 50 rows = ~1,680 calls.
  At 4 req/s rate limit = ~7 minutes per full snapshot.
- Trade backfill for Option A (3,000 wallets, avg ~500 trades each):
  ~1.5M trades. At limit=500 per call (safe) = ~3,000 calls, ~13 min.
  The long tail (whales with 10k+ trades) dominates; cap per wallet at
  10k most recent fills for v1, expose `--full` for specific wallets.
- Market metadata: ~10k unique condition_ids, one call each (or batch
  when Gamma supports it) = ~2,500 calls, ~10 min.
- Total one-time backfill: **~30 minutes**. Daily incremental: **<5 min**.

SQLite size: ~500 MB for 1.5M trades + metadata. Comfortably handleable.

### 1.5.7 Validation plan

Before declaring Phase 1a done:

1. Pick 5 wallets with publicly visible profile pages on polymarket.com.
2. Confirm our `volume_usd_all_time` and `n_trades` match the profile
   page within ~1% (allow for in-flight trades).
3. Cross-check `win_rate_by_market` against Polywhaler's win rate for
   3 wallets that appear on both.
4. Confirm `pnl_realized_30d` matches Polymarket's "30-day P&L" on the
   profile page for 5 wallets within ~2%.

Deltas larger than that mean either our resolution hydration is wrong or
our position-reconstruction is wrong — both are fixable but must be caught
here, not after ranking and monitoring build on top.

## 3. API endpoints used (all public, no auth)

Base: `https://data-api.polymarket.com` unless noted.

| Purpose | Endpoint | Key params |
|---|---|---|
| Leaderboard snapshot | `GET /v1/leaderboard` | `category`, `timePeriod`, `orderBy`, `limit<=50`, `offset<=1000` |
| User trade history | `GET /trades` | `user`, `limit<=10000`, `offset`, `takerOnly` |
| User current positions | `GET /positions` | `user` |
| User portfolio value | `GET /value` | `user` |
| User activity feed | `GET /activity` | `user` (mixes trades + splits/merges/redeems) |
| User public profile | `GET /profile/:wallet` (Gamma) | — |
| Market metadata | Gamma `/markets`, `/events` | resolve `conditionId` -> title, outcomes, liquidity, resolution |
| Historical market prices | `GET /prices-history` | for backtest pricing |

No CLOB, no Gamma auth, no WebSocket in v1. Rate limits honored via client
throttle (see `client.py` below).

## 4. Data model (SQLite, DuckDB upgrade path)

SQLite is sufficient for v1 — trade history for top 1k wallets is at most
a few GB. Switch to DuckDB/Parquet only if a query gets slow.

### Tables

```sql
-- One row per (snapshot_ts, category, time_period, order_by, rank).
-- Primary key lets us track rank changes over time.
CREATE TABLE leaderboard_snapshot (
  snapshot_ts     INTEGER NOT NULL,      -- unix seconds
  category        TEXT    NOT NULL,
  time_period     TEXT    NOT NULL,      -- DAY, WEEK, MONTH, ALL
  order_by        TEXT    NOT NULL,      -- PNL, VOL
  rank            INTEGER NOT NULL,
  proxy_wallet    TEXT    NOT NULL,
  user_name       TEXT,
  vol             REAL,
  pnl             REAL,
  verified_badge  INTEGER,
  PRIMARY KEY (snapshot_ts, category, time_period, order_by, rank)
);

CREATE INDEX idx_leaderboard_wallet ON leaderboard_snapshot(proxy_wallet);

-- Set of wallets we care about. Flagged manually or by rank_traders.py.
CREATE TABLE tracked_wallet (
  proxy_wallet    TEXT PRIMARY KEY,
  user_name       TEXT,
  first_seen_ts   INTEGER,
  last_refresh_ts INTEGER,               -- last time we pulled trades
  notes           TEXT                    -- optional manual tag
);

-- One row per fill. tx_hash uniquely identifies a trade.
-- Upsert on (proxy_wallet, tx_hash, asset) so incremental refresh is idempotent.
CREATE TABLE trade (
  proxy_wallet    TEXT    NOT NULL,
  tx_hash         TEXT    NOT NULL,
  timestamp       INTEGER NOT NULL,
  condition_id    TEXT    NOT NULL,
  asset           TEXT    NOT NULL,      -- token id inside the market
  side            TEXT    NOT NULL,      -- BUY, SELL
  size            REAL    NOT NULL,
  price           REAL    NOT NULL,
  outcome         TEXT,
  outcome_index   INTEGER,
  title           TEXT,
  slug            TEXT,
  event_slug      TEXT,
  PRIMARY KEY (proxy_wallet, tx_hash, asset)
);

CREATE INDEX idx_trade_wallet_ts ON trade(proxy_wallet, timestamp);
CREATE INDEX idx_trade_condition ON trade(condition_id);

-- Market metadata snapshot (refreshed lazily when a new condition_id appears).
CREATE TABLE market (
  condition_id     TEXT PRIMARY KEY,
  title            TEXT,
  slug             TEXT,
  event_slug       TEXT,
  category         TEXT,
  end_date_ts      INTEGER,
  resolved         INTEGER,              -- 0/1
  resolved_outcome INTEGER,              -- 0 or 1 on binary markets
  resolved_ts      INTEGER,
  last_refresh_ts  INTEGER
);

-- Positions snapshot, used for tracking current exposure.
CREATE TABLE position_snapshot (
  snapshot_ts    INTEGER NOT NULL,
  proxy_wallet   TEXT    NOT NULL,
  condition_id   TEXT    NOT NULL,
  asset          TEXT    NOT NULL,
  size           REAL,
  avg_price      REAL,
  current_value  REAL,
  realized_pnl   REAL,
  unrealized_pnl REAL,
  PRIMARY KEY (snapshot_ts, proxy_wallet, asset)
);

-- One row per (wallet, metric) from rank_traders.py. Overwritten each run.
CREATE TABLE trader_metric (
  compute_ts      INTEGER NOT NULL,
  proxy_wallet    TEXT    NOT NULL,
  metric          TEXT    NOT NULL,
  value           REAL,
  PRIMARY KEY (compute_ts, proxy_wallet, metric)
);
```

### File layout for data

```
polymarket/
  data/
    polymarket.sqlite          # all tables above
    snapshots/
      leaderboard_YYYYMMDD.parquet  # optional cold archive
    logs/
      collector.log
      watcher.log
```

`data/` is gitignored.

## 5. Component breakdown

### 5.1 `client.py` — API wrapper

- `PolymarketClient` class.
- `requests.Session` with retry (`urllib3.Retry`) on 429/5xx.
- Token-bucket rate limiter, default 4 req/s, configurable.
- One method per endpoint we use. Return parsed JSON, not raw response.
- Pagination helpers that yield pages lazily.
- `timeout=(5, 30)` on every call.
- Respects `POLYMARKET_USER_AGENT` env var.

### 5.2 `db.py` — SQLite layer

- `connect(path) -> sqlite3.Connection` with `PRAGMA journal_mode=WAL`,
  `foreign_keys=ON`, `synchronous=NORMAL`.
- `init_schema(conn)` idempotent.
- Upsert helpers per table:
  - `upsert_leaderboard_rows(conn, rows)`
  - `upsert_trades(conn, rows)` — uses `INSERT OR IGNORE` on PK.
  - `upsert_markets(conn, rows)`
- No ORM. Plain SQL + named placeholders.

### 5.3 `fetch_leaderboard.py` — CLI

```
python polymarket/fetch_leaderboard.py [--categories all] [--time-periods all] [--order-by both] [--db path] [--dry-run]
```

- Loops over `(category, timePeriod, orderBy)` slices.
- Paginates offset 0 -> 1000.
- Writes to `leaderboard_snapshot` with a single `snapshot_ts`.
- Also upserts any newly seen wallets into `tracked_wallet` with
  `first_seen_ts` (so later phases can query "who has ever been top-ranked").
- Exits non-zero if any slice fully failed.
- Runs in ~1 min.

### 5.4 `fetch_user_trades.py` — CLI

```
python polymarket/fetch_user_trades.py --wallet 0x... [--since-ts N] [--full] [--db path]
```

Two modes:
- Default (incremental): look up `max(timestamp)` for that wallet and pull
  only newer trades, paging until we hit that cutoff.
- `--full`: wipe and backfill from epoch 0. Used rarely.

Bulk variant:
```
python polymarket/fetch_user_trades.py --from-tracked [--top-n 100]
```
Iterates `tracked_wallet` ordered by most recent `first_seen_ts`, calls
the single-wallet path for each.

### 5.5 `fetch_markets.py` — CLI

```
python polymarket/fetch_markets.py --missing [--db path]
```

Finds `condition_id`s referenced in `trade` but not in `market`, calls
Gamma API, populates `market` table. Runs after each trade pull.

### 5.6 `rank_traders.py` — CLI

```
python polymarket/rank_traders.py [--min-markets 30] [--min-days 60] [--top-n 50] [--out shortlist.csv]
```

Computes the metrics in Section 6, writes them to `trader_metric`, then
emits a shortlist CSV and an HTML report similar to `usage/analyze.py`
(self-contained Plotly).

### 5.7 `watch_live.py` — long-running poller

```
python polymarket/watch_live.py --wallets shortlist.csv [--interval 30] [--sink stdout,file,slack] [--slack-webhook $URL]
```

- Loads wallets.
- Every `--interval` seconds, for each wallet, calls `/trades?user=<>&limit=50`.
- Dedupes against the `trade` table.
- For each new trade, enriches with market metadata + current midpoint
  (`GET /midpoint`) + computed slippage estimate.
- Emits to configured sinks.
- Graceful shutdown on SIGINT, saves last-seen timestamp per wallet.
- File sink rotates daily.

### 5.8 Notebook: `notebooks/01_copy_backtest.ipynb`

- Load trades for shortlist wallets.
- Simulate: for each trade, construct a synthetic fill at `trade.price *
  (1 + slippage)` where slippage is a tunable bps cost.
- Follow exits the same way.
- Plot equity curve per wallet, aggregate portfolio, Sharpe, max DD.
- Sensitivity to `slippage_bps` and `lag_seconds` (we approximate lag
  by pushing entry price toward the next recorded fill).

## 6. Ranking methodology — the research question

The leaderboard's raw PnL is heavily survivorship-biased. We compute our
own metrics from the trade history we own. All metrics are computed per
wallet and stored in `trader_metric`. Shortlist is a weighted rank across
these.

### 6.1 Skill metrics (compute all, score on subset)

| Metric | Definition | Why |
|---|---|---|
| `n_trades` | count(`trade`) | Sample size floor |
| `n_resolved_markets` | count distinct `condition_id` that has resolved | Real skill needs resolved outcomes |
| `days_active` | `max(ts) - min(ts)` in days | Filters one-week wonders |
| `pnl_realized` | sum over resolved markets of `(settle_price - avg_entry) * size`, signed by side | Independent of leaderboard |
| `win_rate` | fraction of resolved markets with positive realized PnL | Basic skill proxy |
| `avg_edge_bps` | mean of `(settle - entry_price)` in bps, signed | Per-trade edge |
| `sharpe_daily` | daily PnL mean / std from `/value` series | Risk-adjusted |
| `max_drawdown` | peak-to-trough on `/value` series | Risk character |
| `bet_size_kelly_corr` | Spearman(`size`, `abs(edge)`) | Does bet sizing track conviction |
| `category_hhi` | Herfindahl of traded market categories | Specialist vs generalist |
| `exit_timing_bps` | mean of `(exit_price - mid_at_exit_time)` | Good exits are half the edge |
| `rank_persistence` | fraction of daily leaderboard snapshots in last 30 days where rank <= 100 in any (category, timePeriod, ALL) | Stability; computed from our own `leaderboard_snapshot` |
| `wallet_cluster_id` | optional: cluster wallets that co-trade same markets within short windows | Avoid counting same human twice |

### 6.2 Filters (hard gates before ranking)

- `n_resolved_markets >= 30`
- `days_active >= 60`
- `pnl_realized > 0`
- `rank_persistence >= 0.1` (showed up in the top 100 at least 10% of days)

### 6.3 Composite score (v1 — simple, tunable)

```
score = 0.35 * zscore(sharpe_daily)
      + 0.25 * zscore(avg_edge_bps)
      + 0.15 * zscore(win_rate)
      + 0.15 * zscore(rank_persistence)
      + 0.10 * zscore(exit_timing_bps)
```

Z-scores computed over the filtered cohort. Tunable via CLI flag in v2.
Shortlist = top N by `score` after filters, deduped by `wallet_cluster_id`.

## 7. Monitoring design

### 7.1 Latency budget

From when the trader's fill is visible via `/trades` to when our alert fires:

- API response time: ~200-500 ms.
- Our poll cadence: 30 s default (tunable down to 5 s for small shortlists).
- Enrichment (market lookup, midpoint): ~300 ms.
- **End-to-end median: ~15 s after their fill hits the Data API.**

The Data API itself is not tick-by-tick; it aggregates. Our bound is
whatever Polymarket's internal aggregation lag is. For v1 monitor-only,
this is fine. If/when we ever move to execution, sub-second freshness
would require the CLOB market WebSocket keyed off known market ids.

### 7.2 Dedup and state

- `watch_live.py` keeps an in-memory `last_seen_ts[wallet]`.
- On startup it seeds from `SELECT max(timestamp) FROM trade WHERE proxy_wallet=?`.
- On every poll, new trades are those with `timestamp > last_seen_ts[wallet]`.
- Trades are also inserted into `trade` via `upsert_trades` so a restart is
  lossless.

### 7.3 Sinks (pluggable)

- `stdout`: human-readable single-line per trade.
- `file`: append JSONL to `data/logs/alerts-YYYYMMDD.jsonl`.
- `slack`: webhook POST with a compact block.
- `email`: later, via existing `emailer/` (optional reuse).

### 7.4 Alert shape (JSON)

```json
{
  "alert_ts": 1713630420,
  "trade_ts": 1713630410,
  "trader": { "wallet": "0x...", "user_name": "abc", "rank_percentile": 0.98 },
  "market": { "title": "...", "slug": "...", "category": "SPORTS",
              "resolves": "2026-05-01", "liquidity_usd": 124500 },
  "fill": { "side": "BUY", "outcome": "Yes", "price": 0.63, "size": 8400 },
  "context": { "mid_now": 0.635, "copy_slippage_bps": 8,
               "trader_position_after": 18200 }
}
```

## 8. Tech stack and dependencies

Additions to `requirements.txt`:

```
# polymarket monitor
requests
tenacity           # retry decorator
python-dateutil
tqdm               # progress during backfill
rich               # pretty CLI output
```

Already present and reused: `pandas`, `numpy`, `plotly`.

No async in v1. We're I/O-bound but the volumes are modest (low single-digit
req/s). If polling tightens, migrate `watch_live.py` to `httpx` + `asyncio`.

## 9. File layout

```
polymarket/
  PLAN.md                       # this file
  README.md                     # written after v1 ships
  __init__.py
  client.py
  db.py
  config.py                     # endpoint URLs, category enums, defaults
  fetch_leaderboard.py
  fetch_user_trades.py
  fetch_markets.py
  rank_traders.py
  watch_live.py
  sinks/
    __init__.py
    stdout.py
    file.py
    slack.py
  notebooks/
    01_explore_leaderboard.ipynb
    02_copy_backtest.ipynb
  data/                         # gitignored
    polymarket.sqlite
    snapshots/
    logs/
tests/
  test_polymarket_client.py     # smoke + mocked pagination
  test_polymarket_db.py         # schema + upsert idempotency
```

## 10. Implementation milestones

| M | Deliverable | Rough effort |
|---|---|---|
| M1 | `client.py`, `db.py`, `config.py`, smoke tests | 0.5 day |
| M2 | `fetch_leaderboard.py` + scheduled run (Windows Task Scheduler or cron on SG VPS later) | 0.5 day |
| M3 | `fetch_user_trades.py` + `fetch_markets.py` + backfill for everyone ever in top 100 | 0.5 day |
| M4 | `rank_traders.py` + HTML report | 1 day |
| M5 | Notebook backtest | 1 day |
| M6 | `watch_live.py` stdout + file sinks | 0.5 day |
| M7 | Slack sink + deploy to SG VPS | 0.5 day |

Total: ~4.5 working days, checkpoints after each milestone.

## 11. Open decisions — want your input before I code

### Phase 1a questions (blocking — need answers before coding)

1. **Wallet universe**: Option A (leaderboard union, ~3k wallets) vs
   Option B (whale $10k threshold, market-walking) vs Option C (both).
   My recommendation: **A now, B later**.
2. **Win rate definition to headline**: per-market (Polywhaler style),
   per-trade, or per-position? My recommendation: **compute all 3,
   display per-market as default**.
3. **Store**: SQLite (simple, single-file) vs DuckDB (faster analytic
   queries, Parquet-native). My recommendation: **SQLite** — switch
   later if notebook queries get slow.
4. **Where does `data/` live**: `polymarket/data/` on the S drive (easy
   sync, DFS lock risk with SQLite WAL) vs local
   `C:\Users\hzeng\.polymarket\` (no lock risk, not synced). My
   recommendation: **local** for SQLite, sync Parquet archives to S.
5. **Historical lookback for trade backfill**: all time, last 24 months,
   or last 12 months? My recommendation: **all time, capped at 10k most
   recent fills per wallet** (with `--full` to override for interesting
   wallets).
6. **Category focus**: OVERALL only, or all 10 categories in parallel?
   Per-category adds ~10x API calls (still well under rate limits) and
   gives us specialist signal which is probably where real edge lives.
   My recommendation: **all categories from day one**.

### Phase 2+ questions (can decide later)

7. **Schedule runner**: Windows Task Scheduler locally vs cron on the
   SG VPS. My recommendation: **local Task Scheduler for dev, VPS
   cron once watcher is proven**.
8. **Alert sink for v1 monitor**: stdout + file only, or include Slack
   and/or reuse existing `emailer/`?
9. **Shortlist size**: 20, 50, 100? Affects polling load and alert volume.
10. **Backtest slippage assumption**: fixed bps default (I propose 20 bps),
    or depth-model derived from orderbook snapshots (much heavier)?
11. **Wallet clustering** (same human, multiple wallets): ship in v1 or
    defer? Non-trivial; I recommend **defer to v2**.

## 12. Non-goals / deferred

- Order placement, CLOB auth, `py-clob-client`, wallet management.
- Kalshi integration.
- Web dashboard (report is static HTML for v1).
- Multi-user / multi-account.
- Historical market price backtesting beyond the simple slippage model
  (requires `/prices-history` for every market, expensive).
- Real-time WebSocket ingestion.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Polymarket adds auth to Data API | `PolymarketClient` has a single auth hook; swap in headers then |
| Rate limits tighten | Token-bucket already configurable; backoff on 429 |
| Leaderboard changes schema | Pydantic models (or dataclasses) validate and log on drift |
| Survivorship bias dominates | Hard filters + rank persistence + out-of-sample backtest |
| One good trader runs many wallets | Wallet clustering (v2) |
| SQLite lock on DFS share | Move `data/` to local disk if issues appear |
| Polymarket ToS prohibits scraping | Data API is documented public API, not scraping. Use a proper `User-Agent`, respect rate limits |
