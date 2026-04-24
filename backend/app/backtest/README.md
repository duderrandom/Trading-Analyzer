# Backtesting Engine

A small, readable event-driven backtester. Built for the Trading Strategy
Analyzer, but has no dependency on FastAPI, Yahoo Finance, or any
specific strategy — it can be imported and used on its own.

## Components

| File           | Responsibility                                             |
| -------------- | ---------------------------------------------------------- |
| `orders.py`    | `Order` (intent) and `Trade` (realized fill) value objects |
| `portfolio.py` | `Portfolio`: cash + shares bookkeeping, mark-to-market     |
| `broker.py`    | `Broker`: turns orders into trades, applies costs          |
| `engine.py`    | `run_backtest`: drives the simulation loop                 |
| `results.py`   | `BacktestResult`: equity curve, returns, trade log         |

## Data flow

```
signals (0.0 / 1.0)  ──►  Engine loop
                              │
                              │  on 0→1 : Order(BUY)
                              │  on 1→0 : Order(SELL)
                              ▼
                            Broker  ── applies slippage + commission ──►  Trade
                              │
                              ▼
                          Portfolio  ── cash / shares updated ──────────►  equity[t]
                              │
                              ▼
                        BacktestResult
```

## Usage

```python
import pandas as pd
from app.backtest import Broker, run_backtest

# prices: DataFrame with columns Open/High/Low/Close/Volume, DatetimeIndex
# signals: Series of 0.0/1.0 aligned to prices.index

result = run_backtest(
    prices,
    signals,
    initial_capital=10_000.0,
    broker=Broker(
        commission_per_trade=1.0,   # $1 per fill
        commission_per_share=0.0,
        slippage_bps=5.0,           # 5 bps adverse slippage
    ),
)

print(result.final_value, len(result.trades), result.total_commission)
result.equity.plot()  # matplotlib
```

## Design choices & simplifications

- **All-in / all-out sizing.** Position is either 0.0 (cash) or 1.0
  (fully invested). No partial sizing. This is the single biggest
  simplification — real strategies use risk-based sizing.
- **Fills at the signal bar's close.** No intraday fills, no
  open-of-next-bar fills, no VWAP. Switching this would require a small
  change in `engine.py` and a more careful look-ahead story.
- **Signals are expected to be shift(1)'d by the caller** so that a
  signal computed from bar *t*'s close only acts on bar *t+1*. The
  bundled strategies already do this; home-grown signals must do it too.
- **Slippage is symmetric and adverse.** Buys pay `price * (1 +
  slippage_bps/1e4)`, sells receive `price * (1 - slippage_bps/1e4)`.
  Fine as a first approximation; real slippage depends on size, spread,
  volatility, and participation rate.
- **Commission is `per_trade + per_share * shares`.** Covers both
  flat-fee retail brokers and the older per-share model.
- **No shorting, no leverage, no margin.** Extending to shorts would
  require `target_fraction` to support negative values in `Order` and a
  sign in `Portfolio.shares`.
- **Single asset.** Multi-asset would replace `shares: float` with a
  dict and require per-symbol prices in `Portfolio.equity()`.

## Extending

Adding a new cost model — e.g., percentage-of-notional commission —
means one new field on `Broker` and one line in `_commission()`. The
rest of the engine is unaffected.

Adding a new order type — e.g., fractional position sizing — means
teaching `Broker.execute()` to interpret `order.target_fraction` rather
than treating BUY as "use all cash".
