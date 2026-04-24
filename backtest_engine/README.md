# backtest-engine

A small, readable event-driven backtesting engine for single-asset,
long-only rule-based strategies. No web server, no data provider, no
strategies bundled — just the simulation core.

Roughly 200 lines of code across five files. Designed to be read
end-to-end in 10 minutes.

## Install

From source (editable):

```bash
cd backtest_engine
pip install -e .
```

Dependencies: `numpy`, `pandas`. That's it.

## Concepts

```
signals (0.0 / 1.0)  ──►  Engine loop
                              │  on 0→1 : Order(BUY)
                              │  on 1→0 : Order(SELL)
                              ▼
                            Broker  ── slippage + commission ──►  Trade
                              │
                              ▼
                          Portfolio  ── cash + shares ──────────►  equity[t]
                              │
                              ▼
                        BacktestResult
```

| Module         | What it does                                          |
| -------------- | ----------------------------------------------------- |
| `orders.py`    | `Order` (intent) and `Trade` (realized fill)          |
| `portfolio.py` | `Portfolio`: cash, shares, mark-to-market             |
| `broker.py`    | `Broker`: fills orders, applies costs                 |
| `engine.py`    | `run_backtest`: the loop                              |
| `results.py`   | `BacktestResult`: equity curve + trade log            |
| `metrics.py`   | total return, max drawdown, Sharpe, win rate          |

## Quick start

```python
import pandas as pd
from backtest_engine import Broker, metrics, run_backtest

# prices: DataFrame with 'Close' column + DatetimeIndex
# signals: Series of 0.0/1.0 aligned to prices.index
#          (shift(1) it yourself to avoid look-ahead bias)

result = run_backtest(
    prices,
    signals,
    initial_capital=10_000.0,
    broker=Broker(commission_per_trade=1.0, slippage_bps=5.0),
)

m = metrics.compute_all(result)
print(m.total_return_pct, m.max_drawdown_pct, m.sharpe_ratio)
```

See `examples/moving_average_example.py` for a runnable walkthrough.

## Signal convention

- `1.0` at bar *t* → be fully invested at the **close** of bar *t*
- `0.0` at bar *t* → be flat at the close of bar *t*
- The caller is responsible for `shift(1)`. A signal computed from bar
  *t*'s close can only realistically be acted on at bar *t+1*.

## Cost model

Two opt-in knobs on `Broker`:

| Parameter              | Effect                                                      |
| ---------------------- | ----------------------------------------------------------- |
| `commission_per_trade` | Flat dollar fee per fill                                    |
| `commission_per_share` | Per-share dollar fee                                        |
| `slippage_bps`         | Adverse slippage in basis points (buys up, sells down)     |

All default to zero — the broker is frictionless unless you opt in.

## What's intentionally missing

This is a teaching tool. These are missing on purpose:

- No shorting, no leverage, no margin
- No partial position sizing (position is 0 or 1)
- No limit / stop / bracket orders
- No multi-asset portfolios
- No intraday fills (all fills at the signal bar's close)
- No corporate actions beyond what your data source bakes in
- No benchmark-relative metrics

Each of these is a deliberate simplification. If you need them, this
engine is not the right starting point.

## Testing

```bash
pip install -e ".[dev]"
pytest -q
```

The test suite uses synthetic data — no network calls.

## Why "educational"?

Reading 200 lines of a real engine teaches far more than black-boxing a
library. Every simplification in here is one you will eventually have
to think about in a serious system. The goal is to see the shape of
the problem clearly.
