# Trading Strategy Analyzer — Backend

An **educational** backtesting service for classic rule-based trading
strategies. It is **not** a prediction engine and it does **not** use
machine learning. The goal is to help you *see* how strategies behave
on real data and build intuition for risk/return trade-offs.

## What it does

- Pulls daily OHLC prices from Yahoo Finance (or loads a local CSV)
- Runs three strategies on the same window so you can compare them:
  - **Buy & Hold** — baseline
  - **Moving Average Crossover** — short SMA vs long SMA (trend following)
  - **RSI Mean Reversion** — enter on oversold, exit on overbought
- Returns per-strategy equity curves, trade logs, and performance metrics
- Exports a combined equity-curve CSV for offline analysis

## Project structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── data/fetcher.py      # Yahoo Finance + CSV loader
│   ├── strategies/          # Signal-generating strategies
│   │   ├── buy_hold.py
│   │   ├── moving_average.py
│   │   └── rsi.py
│   ├── backtest/engine.py   # Trade simulation + equity curve
│   ├── metrics/performance.py  # Return, drawdown, Sharpe, win rate
│   └── models/schemas.py    # Pydantic request/response models
├── tests/                   # Offline unit + API tests
└── requirements.txt
```

## Running locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> for the interactive API docs.

## API

### `GET /api/strategies`
List available strategies with human-readable descriptions.

### `POST /api/backtest`
Run one or more strategies on a ticker / date range.

```json
{
  "ticker": "AAPL",
  "start_date": "2020-01-02",
  "end_date": "2024-12-31",
  "strategies": ["buy_hold", "ma_crossover", "rsi"],
  "initial_capital": 10000,
  "params": {
    "short_window": 20,
    "long_window": 50,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  }
}
```

Returns the raw price series, per-strategy equity curves, trade logs,
metrics, and the ID of the best-performing strategy on total return.

### `POST /api/backtest/export`
Same body as `/api/backtest`; returns a CSV of aligned equity curves.

### `GET /api/health?ticker=AAPL&start=...&end=...`
Smoke-checks that the data provider is reachable.

## How the strategies work

### Buy & Hold
Go long on the first bar and never sell. Our benchmark — an active
strategy that loses to buy-and-hold is not adding value.

### Moving Average Crossover
Compute a short SMA (default 20) and a long SMA (default 50). Position
is `1` when short > long, else `0`. Works well in trending markets;
gets whipsawed in choppy ones.

### RSI Mean Reversion
Compute Wilder's RSI (default period 14). Enter long when RSI drops
below `oversold` (default 30), exit when it rises above `overbought`
(default 70). The opposite assumption of the MA strategy — mean
reversion instead of trend.

## How backtesting works

1. Fetch OHLC prices for the ticker and date range.
2. Strategy function takes the price DataFrame + params, returns a
   `position` series of `0.0` / `1.0`.
3. Signals are **shifted by one bar** so decisions based on today's
   close only act on tomorrow — avoiding look-ahead bias.
4. The engine walks the series: on a `0 → 1` transition, buy at that
   bar's close with all cash; on `1 → 0`, sell to cash.
5. Portfolio value is tracked every bar, producing an equity curve.
6. Metrics are computed on the equity curve + trade log.

## Interpreting the metrics

Every metric the API returns tells a partial truth. The productive way
to read them is *together* — each one covers a blind spot of the others.

### Total return — `total_return_pct`

```
total_return = final_equity / initial_equity - 1
```

Cumulative gain over the window. Easy to compare, easy to cherry-pick.
Ignores *how long* it took and *how bumpy* the ride was. +50% over 10
years is worse than cash; +50% over 1 year is great. Same number.

### Annualized return (CAGR) — `annualized_return_pct`

```
years = (end_date - start_date) / 365.25
CAGR  = (final_equity / initial_equity) ^ (1 / years) - 1
```

The constant yearly growth rate that would produce the same final
equity. The right metric for comparing strategies over *different
window lengths*. We use calendar days so weekends/holidays don't
distort the denominator.

Past CAGR is a *description*, not a *forecast*. Extrapolating it
forward is the single most common mistake in this domain.

### Max drawdown — `max_drawdown_pct`

```
running_max = equity.cummax()
drawdown[t] = (equity[t] - running_max[t]) / running_max[t]
max_drawdown = min(drawdown)
```

Largest peak-to-trough equity decline. A **risk** metric, not a return
metric. Answers: "If I'd bought at the worst moment, how deep would I
have been under before recovering?"

Rules of thumb:

| Max drawdown   | How it feels                                     |
| -------------- | ------------------------------------------------ |
| 0% to −10%     | Comfortable                                      |
| −10% to −25%   | Pressures discipline                             |
| −25% to −50%   | Most people abandon the strategy here            |
| < −50%         | Needs +100% just to break even                   |

Captures only the *worst* drawdown — a strategy with five −15% drops
scores better than one with a single −20%, though the former may be
harder to live with. Also ignores duration; a 6-month drawdown and a
6-year drawdown of equal depth score identically.

### Sharpe ratio — `sharpe_ratio`

```
excess[t] = daily_return[t] - (risk_free_rate / 252)
sharpe    = mean(excess) / stdev(excess) × √252
```

Return per unit of volatility, annualized. We default
`risk_free_rate = 0` — a simplification that flatters all strategies
in a high-rate environment.

| Sharpe     | Rough read                                          |
| ---------- | --------------------------------------------------- |
| < 0        | Lost money on a risk-adjusted basis                |
| 0.0 – 0.5  | Weak; not obviously better than random             |
| 0.5 – 1.0  | Decent; most equity buy-and-hold falls here        |
| 1.0 – 2.0  | Good; rare over long windows                       |
| > 2.0      | Suspicious in a backtest — usually overfitting     |

Treats upside volatility as risk (most investors don't). Assumes
roughly normal returns — real returns have fat tails, so Sharpe
*understates* tail risk. Returns `null` when std is ~0 or there's too
little data.

### Win rate — `win_rate_pct`

```
pairs = [(entry, exit) from BUY→SELL pairs]
win_rate = count(exit > entry) / count(pairs)
```

Fraction of completed round-trip trades that were profitable. **This
metric tells you nothing about profitability on its own.** A 30%-win
trend strategy with winners 5× the losers is very profitable; a
90%-win strategy that occasionally blows up is a losing strategy.

Returns `null` when no round-trip has closed (e.g., buy-and-hold that
never sells — there's no "win/loss" pair to score).

**Treat win rate as descriptive, not evaluative.**

### Number of trades — `num_trades`

Count of fills (BUYs + SELLs). A proxy for **turnover**.

- Under ~20 round-trips, the result is mostly luck — too few samples
  to say anything statistically.
- High turnover magnifies the real-world costs we omit by default
  (spread, commission, taxes). A strategy that trades 200 times a
  year can look great here and lose money in practice.

"More trades = more robust" is wrong: more trades in the same window
often means reacting to noise. "Fewer trades = better" is also wrong:
if buy-and-hold beats you with 1 trade, you're not adding value.

### Final value — `final_value`

```
final_value = cash + shares × last_close
```

Dollar value at the end of the window. Intuitive, but a pure function
of `total_return × initial_capital` — conveys no new information.
Good for presenting to non-quants; don't let a big number disguise a
small risk-adjusted edge.

### Reading them *together*

1. **Drawdown first.** If you couldn't live through it, the return is
   irrelevant.
2. **Then CAGR.** Normalizes across window lengths and strategies.
3. **Then Sharpe.** Did the return justify the volatility?
4. **Glance at trade count.** Under ~20 round-trips, most conclusions
   are premature.
5. **Win rate is for curiosity, not decisions.**

And the uncomfortable truth this tool is designed to surface: across
most tickers and windows, **buy-and-hold is very hard to beat**,
especially once costs enter the picture. When an active strategy wins
on a specific window, the usual reason is that the window happened to
favor its regime (trending for MA crossover, mean-reverting for RSI).
Shift the window by a few months and the "winner" often changes.

## Limitations (be honest with yourself)

- **No transaction costs, slippage, or taxes.** Real trading has all
  three and they often erase paper edges, especially for high-frequency
  rules like RSI.
- **All-in / all-out sizing.** No position sizing, no risk targeting,
  no stops. These can significantly change outcomes.
- **Survivorship bias.** Single-ticker tests on companies that still
  trade today systematically overstate returns — delisted names are
  invisible.
- **Look-ahead-free but parameter-biased.** We fix `short=20, long=50`
  etc. — these defaults were chosen because they are famous, not
  because they are optimal, but *any* fixed choice is a form of
  hindsight when tested on history.
- **Free data quality.** Yahoo Finance is convenient, not canonical.
  Splits/dividends are mostly handled (`auto_adjust=True`), but data
  gaps and errors exist.
- **In-sample performance is not evidence.** A strategy looking good
  on a specific window tells you very little about the next window.

Consistent profits are hard. This tool exists so you can *feel* why.

## Testing

```bash
cd backend
pytest -q
```

The suite uses synthetic data and `monkeypatch` to stub the data
fetcher, so it runs fully offline.

## Example usage (curl)

```bash
# List strategies
curl http://localhost:8000/api/strategies | jq

# Run a 3-strategy comparison on SPY
curl -X POST http://localhost:8000/api/backtest \
  -H 'Content-Type: application/json' \
  -d '{
    "ticker": "SPY",
    "start_date": "2018-01-02",
    "end_date": "2023-12-29",
    "strategies": ["buy_hold", "ma_crossover", "rsi"],
    "initial_capital": 10000
  }' | jq '.results[] | {label, metrics}'
```
