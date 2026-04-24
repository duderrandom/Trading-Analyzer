"""Backtest engine — turns a signal series into trades and an equity curve.

The engine is intentionally thin. The heavy lifting lives in:

  * `Portfolio` — cash + shares bookkeeping
  * `Broker`    — order execution, slippage, commission
  * `Order` / `Trade` — value objects

Simplifications kept for pedagogical clarity:
  * Single asset, all-in / all-out sizing (position = 0 or 1)
  * Fills at the signal bar's close
  * No intraday fills, no limit/stop orders
  * No dividends beyond what `auto_adjust=True` bakes into close prices
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .broker import Broker
from .orders import Order, Trade
from .portfolio import Portfolio
from .results import BacktestResult


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float = 10_000.0,
    broker: Broker | None = None,
) -> BacktestResult:
    """Simulate a strategy.

    Args:
        prices: OHLC DataFrame indexed by date. Only `Close` is read.
        signals: target position per bar (0.0 or 1.0), aligned to `prices.index`.
        initial_capital: starting cash.
        broker: optional pre-configured Broker. Defaults to a frictionless
            broker (zero commission, zero slippage).
    """
    if broker is None:
        broker = Broker()

    if not prices.index.equals(signals.index):
        signals = signals.reindex(prices.index).fillna(0.0)

    close = prices["Close"].astype(float).values
    sig = np.clip(signals.astype(float).values, 0.0, 1.0)
    dates = prices.index

    portfolio = Portfolio(cash=float(initial_capital))
    trades: list[Trade] = []
    equity = np.empty(len(close), dtype=float)

    for i in range(len(close)):
        price = close[i]
        target = sig[i]

        # Detect a transition and submit a single order.
        if target > 0.5 and not portfolio.is_long:
            order = Order(dates[i], "BUY", target_fraction=1.0)
        elif target < 0.5 and portfolio.is_long:
            order = Order(dates[i], "SELL", target_fraction=0.0)
        else:
            order = None

        if order is not None:
            trade = broker.execute(order, raw_price=price, portfolio=portfolio)
            if trade is not None:
                trades.append(trade)

        equity[i] = portfolio.equity(price)

    equity_series = pd.Series(equity, index=dates, name="equity")
    returns = equity_series.pct_change().fillna(0.0)

    return BacktestResult(
        equity=equity_series,
        returns=returns,
        trades=trades,
        initial_capital=float(initial_capital),
        final_value=float(equity_series.iloc[-1]) if len(equity_series) else float(initial_capital),
        total_commission=float(sum(t.commission for t in trades)),
    )
