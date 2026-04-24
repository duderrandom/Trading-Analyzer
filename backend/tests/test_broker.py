from __future__ import annotations

import pandas as pd
import pytest

from app.backtest.broker import Broker
from app.backtest.engine import run_backtest
from app.backtest.orders import Order
from app.backtest.portfolio import Portfolio


def test_frictionless_broker_matches_baseline(trending_ohlc):
    """Default broker is zero-cost — buy-and-hold should match
    (final_close / first_close) * initial capital within tolerance."""
    sig = pd.Series(1.0, index=trending_ohlc.index)
    result = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)

    first = float(trending_ohlc["Close"].iloc[0])
    last = float(trending_ohlc["Close"].iloc[-1])
    expected = 10_000.0 * (last / first)

    assert abs(result.final_value - expected) / expected < 0.01
    assert result.total_commission == 0.0


def test_commission_reduces_final_value(trending_ohlc):
    sig = pd.Series(1.0, index=trending_ohlc.index)

    free = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    with_fee = run_backtest(
        trending_ohlc,
        sig,
        initial_capital=10_000.0,
        broker=Broker(commission_per_trade=1.0),
    )
    assert with_fee.final_value < free.final_value
    assert with_fee.total_commission > 0


def test_slippage_buy_pays_more():
    pf = Portfolio(cash=10_000.0)
    broker = Broker(slippage_bps=50.0)  # 0.5%
    order = Order(pd.Timestamp("2023-01-02"), "BUY", target_fraction=1.0)
    trade = broker.execute(order, raw_price=100.0, portfolio=pf)
    assert trade is not None
    assert trade.price == pytest.approx(100.5)


def test_redundant_order_is_noop():
    """Trying to BUY when already long, or SELL when flat, returns None."""
    pf = Portfolio(cash=0.0, shares=10.0)
    broker = Broker()
    order = Order(pd.Timestamp("2023-01-02"), "BUY", target_fraction=1.0)
    assert broker.execute(order, raw_price=100.0, portfolio=pf) is None

    pf2 = Portfolio(cash=10_000.0, shares=0.0)
    sell = Order(pd.Timestamp("2023-01-02"), "SELL", target_fraction=0.0)
    assert broker.execute(sell, raw_price=100.0, portfolio=pf2) is None
