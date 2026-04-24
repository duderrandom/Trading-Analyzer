# Trading Strategy Analyzer — Frontend

Single-page, vanilla JS + HTML + CSS, charts via Chart.js. No build
step, no framework, no npm.

## Layout

```
frontend/
├── index.html     # form + results scaffold, loads Chart.js from CDN
├── styles.css     # dark dashboard theme
├── app.js         # API calls, form handling, chart rendering
└── README.md
```

## Run

The backend must be running first (defaults to `http://localhost:8000`):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Then serve the frontend from any static server. Python's built-in works:

```bash
cd frontend
python3 -m http.server 5173
```

Open <http://localhost:5173>. The "connected/offline" badge in the top
right tells you whether the frontend is talking to the backend.

To point the frontend at a non-default backend URL, add `?api=...`:

```
http://localhost:5173/?api=http://my-backend:8080
```

## Features

- **Config panel** (left): ticker, date range, initial capital,
  strategy checkboxes, collapsible strategy-parameter group, and an
  optional trading-costs group (commission per trade / per share,
  slippage in bps).
- **Performance summary table** with the best strategy highlighted.
- **Equity curves chart** — all selected strategies overlaid so you
  can compare them at a glance.
- **Price chart with trade markers** — pick which strategy's trades to
  overlay on the price series; green up-triangles for buys, red
  down-triangles for sells.
- **Trade log table** for the selected strategy.
- **Export CSV** of aligned equity curves for offline analysis.
- **Educational accordion** explaining each strategy and the
  limitations of backtesting.

## Smoke test

1. Start the backend.
2. Start the static server and open the page.
3. Default ticker `AAPL`, 3-year date range. Click **Run backtest**.
4. You should see metrics for all three strategies, the equity-curve
   chart with three lines, and the price chart with buy/sell markers.
5. Change the price chart's strategy dropdown — the trade markers
   and trade log update.
6. Click **Export CSV** — a CSV with aligned equity curves downloads.

## Notes

- Chart.js is loaded from a CDN; an air-gapped environment would need
  to vendor it locally.
- CORS is open on the backend (`allow_origins=["*"]`) for the MVP —
  tighten this in a real deployment.
- The frontend is intentionally framework-free. Swapping to React or
  similar is straightforward — `app.js` is a thin client over the
  `/api/backtest` and `/api/backtest/export` endpoints.
