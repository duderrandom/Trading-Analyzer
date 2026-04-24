from __future__ import annotations

import pandas as pd
import pytest

from backtest_engine import Broker, run_backtest
from backtest_engine.orders import Order
from backtest_engine.portfolio import Portfolio


def test_buy_hold_tracks_price(trending_ohlc):
    sig = pd.Series(1.0, index=trending_ohlc.index)
    result = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)

    first = float(trending_ohlc["Close"].iloc[0])
    last = float(trending_ohlc["Close"].iloc[-1])
    expected = 10_000.0 * (last / first)

    assert abs(result.final_value - expected) / expected < 0.01
    assert len(result.trades) == 1
    assert result.trades[0].action == "BUY"


def test_flat_signal_preserves_capital(flat_ohlc):
    sig = pd.Series(0.0, index=flat_ohlc.index)
    result = run_backtest(flat_ohlc, sig, initial_capital=5_000.0)
    assert result.final_value == 5_000.0
    assert result.trades == []


def test_flat_price_with_long_signal_is_flat(flat_ohlc):
    sig = pd.Series(1.0, index=flat_ohlc.index)
    result = run_backtest(flat_ohlc, sig, initial_capital=5_000.0)
    # No price movement → equity stays at initial capital.
    assert abs(result.final_value - 5_000.0) < 1e-6


def test_commission_eats_return(trending_ohlc):
    sig = pd.Series(1.0, index=trending_ohlc.index)
    free = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    costly = run_backtest(
        trending_ohlc,
        sig,
        initial_capital=10_000.0,
        broker=Broker(commission_per_trade=10.0),
    )
    assert costly.final_value < free.final_value
    assert costly.total_commission > 0


def test_reindex_on_misaligned_signals(trending_ohlc):
    # Signal only covers part of the range; missing bars should be flat.
    sig = pd.Series(1.0, index=trending_ohlc.index[:10])
    result = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    assert len(result.equity) == len(trending_ohlc)


def test_broker_slippage_direction():
    pf = Portfolio(cash=10_000.0)
    b = Broker(slippage_bps=100.0)  # 1%
    t = b.execute(Order(pd.Timestamp("2023-01-02"), "BUY", 1.0), raw_price=100.0, portfolio=pf)
    assert t is not None
    assert t.price == pytest.approx(101.0)
    t2 = b.execute(Order(pd.Timestamp("2023-01-03"), "SELL", 0.0), raw_price=100.0, portfolio=pf)
    assert t2 is not None
    assert t2.price == pytest.approx(99.0)


def test_empty_prices_raises():
    with pytest.raises(ValueError):
        run_backtest(pd.DataFrame({"Close": []}), pd.Series([], dtype=float))
