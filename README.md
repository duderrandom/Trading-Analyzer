# Trading Strategy Analyzer

An **educational** tool for backtesting and comparing classic rule-based
trading strategies on historical market data. Not a prediction engine.
No machine learning. The goal is to build intuition for risk, return,
and the difficulty of consistent outperformance.

## Repository layout

```
trading-analyzer/
├── backend/           # FastAPI service (data, strategies, backtest, metrics, API)
├── frontend/          # Vanilla HTML/CSS/JS single-page UI (Chart.js via CDN)
└── backtest_engine/   # Standalone, pip-installable backtest engine (no web deps)
```

Each folder has its own README with details. A short summary:

| Piece                | What it is                                                         |
| -------------------- | ------------------------------------------------------------------ |
| **`backend/`**       | REST API: strategies registry, `/api/backtest`, `/api/backtest/export`, health. Uses Yahoo Finance for data. |
| **`frontend/`**      | Single page: config form, metrics table, equity curves, price chart with buy/sell markers, CSV export. |
| **`backtest_engine/`** | Standalone engine (~200 LOC) — can be installed and used independently of the web app. |

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Browse <http://localhost:8000/docs> for interactive API docs.

### 2. Frontend

In a second terminal:

```bash
cd frontend
python3 -m http.server 5173
```

Open <http://localhost:5173>. The "connected/offline" badge in the top
right shows the backend status.

To point the UI at a non-default backend URL:

```
http://localhost:5173/?api=http://my-backend:8080
```

### 3. (Optional) Standalone engine

Use the engine without the web app:

```bash
cd backtest_engine
pip install -e ".[dev]"
pytest -q
python examples/moving_average_example.py
```

## Features

- **Data ingestion** — daily OHLC from Yahoo Finance, or CSV.
- **Strategies** — Buy & Hold baseline, SMA crossover, RSI mean-reversion.
- **Backtesting engine** — all-in/all-out, fills at the signal bar's
  close, optional commission + slippage costs. Signals are shifted by
  one bar to avoid look-ahead bias.
- **Metrics** — total/annualized return, max drawdown, Sharpe ratio,
  win rate, trade count, final value.
- **Visualization** — price chart with buy/sell markers, combined
  equity curves across selected strategies.
- **Comparison** — side-by-side metrics table with best performer
  highlighted. CSV export of aligned equity curves.
- **Parameterized** — MA windows, RSI period/thresholds, initial
  capital, and cost knobs are all exposed in the UI.

## How the strategies work

- **Buy & Hold** — go long on day 1, hold to the end. A reference: any
  active strategy unable to beat this on the chosen window is not
  adding value here.
- **Moving Average Crossover** — long when the short SMA is above the
  long SMA, flat otherwise. Trend-following.
- **RSI Mean Reversion** — long when Wilder's RSI drops below
  `oversold`, flat when it rises above `overbought`. Opposite
  assumption from the MA strategy.

## How backtesting works

1. Fetch OHLC prices for the ticker and date range.
2. Each strategy produces a `position` series: `1.0` = invested,
   `0.0` = cash.
3. Signals are shifted by one bar, so a signal computed from bar *t*'s
   close only acts on bar *t+1*.
4. The engine walks bar by bar: on a `0 → 1` transition, buy at that
   bar's close; on `1 → 0`, sell.
5. Portfolio value is marked-to-market every bar → the equity curve.
6. Metrics are computed from the equity curve and the trade log.

## Limitations

Honest, because the point of this tool is to see them clearly:

- **No taxes. Default no commissions / slippage** (opt in through the
  UI or broker config).
- **All-in / all-out sizing.** No risk targeting, no position sizing,
  no stops.
- **Single ticker.** Survivorship bias: a name that still trades today
  is a selection in itself.
- **Parameters as hindsight.** Any fixed window (`short=20`,
  `long=50`, ...) was chosen with knowledge of what worked historically.
- **Free-data quality.** Yahoo Finance is convenient, not canonical.
- **In-sample results are not predictive.** Good performance on one
  window tells you little about the next.

Consistent profits are hard. This tool exists so you can see and feel
why — not to convince you otherwise.

## Testing

```bash
# Backend (25 tests)
cd backend && source .venv/bin/activate && pytest -q

# Standalone engine (12 tests)
cd backtest_engine && source .venv/bin/activate && pytest -q
```

Both suites are fully offline (monkey-patched data fetcher / synthetic
price fixtures).

## Example: end-to-end via curl

```bash
curl -X POST http://localhost:8000/api/backtest \
  -H 'Content-Type: application/json' \
  -d '{
    "ticker": "SPY",
    "start_date": "2018-01-02",
    "end_date": "2023-12-29",
    "strategies": ["buy_hold", "ma_crossover", "rsi"],
    "initial_capital": 10000,
    "params": {"short_window": 20, "long_window": 50},
    "broker": {"commission_per_trade": 1.0, "slippage_bps": 5.0}
  }' | jq '.results[] | {label, metrics}'
```
