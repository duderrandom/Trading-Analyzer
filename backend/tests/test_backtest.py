from __future__ import annotations

import pandas as pd

from app.backtest.engine import run_backtest
from app.models.schemas import StrategyParams
from app.strategies.buy_hold import buy_hold_signals
from app.strategies.moving_average import ma_crossover_signals


def test_buy_hold_equity_tracks_price(trending_ohlc):
    sig = buy_hold_signals(trending_ohlc, StrategyParams())
    bt = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)

    first_close = trending_ohlc["Close"].iloc[0]
    last_close = trending_ohlc["Close"].iloc[-1]
    expected = 10_000.0 * (last_close / first_close)

    # Allow small tolerance since buy is at close of day 0.
    assert abs(bt.final_value - expected) / expected < 0.01
    assert len(bt.trades) == 1
    assert bt.trades[0].action == "BUY"


def test_flat_signal_preserves_capital(trending_ohlc):
    sig = pd.Series(0.0, index=trending_ohlc.index)
    bt = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    assert bt.final_value == 10_000.0
    assert bt.trades == []
    assert (bt.equity == 10_000.0).all()


def test_completed_trade_pair(trending_ohlc):
    # Force one entry and one exit.
    sig = pd.Series(0.0, index=trending_ohlc.index)
    sig.iloc[10:20] = 1.0
    bt = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)

    actions = [t.action for t in bt.trades]
    assert actions == ["BUY", "SELL"]


def test_ma_crossover_runs_end_to_end(trending_ohlc):
    params = StrategyParams(short_window=10, long_window=30)
    sig = ma_crossover_signals(trending_ohlc, params)
    bt = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    assert bt.final_value > 0
    assert len(bt.equity) == len(trending_ohlc)
