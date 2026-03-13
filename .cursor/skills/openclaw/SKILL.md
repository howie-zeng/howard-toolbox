---
name: openclaw
description: >-
  Knowledge of the OpenClaw Personal Cognitive OS. Use when the user asks about 
  openclaw, the cognitive OS, daily briefings, the monthly pipeline, or tasks 
  running in the C:\Users\Howard\.openclaw environment.
---

# OpenClaw Personal Cognitive OS

OpenClaw is a personal cognitive OS running on the local desktop, located at `C:\Users\Howard\.openclaw`. It handles daily intelligence, monitoring, and long-term memory.

## Architecture & File Structure
- **Config**: `openclaw.json` defines models (`zai/glm-5`), API keys, channels (Discord), hooks, and agent properties.
- **Python Scripts**: `workspace/scripts/` (Requires Python 3.11+)
  - `common.py`: shared utilities (paths, load_json, save_json, load_tickers, OAuth).
  - `run_all.py`: daily pipeline (parallel fetch -> archive).
  - `run_maintenance.py`: self-maintenance queue + one safe fix per run.
  - `run_monthly.py`: monthly stock selection -> ChatGPT recommendation.
  - `morning_dashboard.py`: 10-line overnight summary.
  - `sentinel.py`: hourly anomaly watchdog.
  - `fetch_*.py`: individual data fetchers (weather, market, tech, etc.).
- **Data**: `workspace/data/` contains JSON outputs from fetchers (gitignored). Also contains `portfolio.txt` and `watchlist.txt` for the monthly pipeline.
- **Config**: `workspace/config/` holds scoring configs, issuer map, allowlists.
- **Knowledge**: `workspace/knowledge/` holds journals, monthly archives, and user profiles.

## Key Workflows

### Daily Pipeline
- Full data refresh: `python workspace/scripts/run_all.py`
- Quick 10-line summary: `python workspace/scripts/morning_dashboard.py`

### Self-Maintenance
- Build queue: `python workspace/scripts/run_maintenance.py`
- Apply one safe task: `python workspace/scripts/run_maintenance.py --apply` (lighter pass: `--skip-smoke`)

### Monthly Pipeline
- First time: add tickers to `workspace/data/portfolio.txt`
- Generate recommendation: `python workspace/scripts/run_monthly.py --refresh --with-prices`
- Track monthly picks: `python workspace/scripts/monthly_track.py --prices`

## Gateway & Dashboard
- Gateway listens on `127.0.0.1:18789`.
- The dashboard can be accessed via `http://localhost:18789/__openclaw__/canvas/`.

## No-Auth Integrations
- Weather (Open-Meteo), Market Context (CNN/yfinance), Tech Trends (HN/GitHub), Sentinel (disk/mem).

## Setup-Required Integrations
- Gmail, Google Calendar, Oura Ring, Portfolio News, IB Portfolio, SEC Filings, Tasks.
