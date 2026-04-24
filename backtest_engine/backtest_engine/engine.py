"""Engine — the core simulation loop.

Takes a price DataFrame and a 0.0/1.0 signal series, walks them bar by
bar, and produces a `BacktestResult`. The engine itself is ~40 lines;
almost all behavior lives in `Portfolio` and `Broker`.

Signal convention:
  * 1.0 means "be fully long at the close of this bar"
  * 0.0 means "be flat at the close of this bar"
  * The caller is responsible for `shift(1)` to avoid look-ahead bias
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .broker import Broker
from .orders import Order, Trade
from .portfolio import Portfolio
from .results import BacktestResult


def _require_close(prices: pd.DataFrame) -> np.ndarray:
    if "Close" not in prices.columns:
        raise ValueError("prices DataFrame must contain a 'Close' column")
    return prices["Close"].astype(float).values


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float = 10_000.0,
    broker: Broker | None = None,
) -> BacktestResult:
    """Run a single-asset backtest.

    Args:
        prices: OHLC DataFrame with a `Close` column and a DatetimeIndex.
        signals: target position per bar (0.0 or 1.0). Reindexed to
            `prices.index` if needed.
        initial_capital: starting cash.
        broker: execution model; defaults to zero-cost.

    Returns:
        BacktestResult with equity curve, returns, and trade log.
    """
    if prices.empty:
        raise ValueError("prices is empty")
    if broker is None:
        broker = Broker()

    close = _require_close(prices)
    if not prices.index.equals(signals.index):
        signals = signals.reindex(prices.index).fillna(0.0)
    sig = np.clip(signals.astype(float).values, 0.0, 1.0)
    dates = prices.index

    portfolio = Portfolio(cash=float(initial_capital))
    trades: list[Trade] = []
    equity = np.empty(len(close), dtype=float)

    for i in range(len(close)):
        price = close[i]
        target = sig[i]

        order: Order | None = None
        if target > 0.5 and not portfolio.is_long:
            order = Order(dates[i], "BUY", target_fraction=1.0)
        elif target < 0.5 and portfolio.is_long:
            order = Order(dates[i], "SELL", target_fraction=0.0)

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
        final_value=float(equity_series.iloc[-1]),
        total_commission=float(sum(t.commission for t in trades)),
    )
