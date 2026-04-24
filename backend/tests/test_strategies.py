from __future__ import annotations

import numpy as np

from app.models.schemas import StrategyParams
from app.strategies.buy_hold import buy_hold_signals
from app.strategies.moving_average import ma_crossover_signals
from app.strategies.rsi import compute_rsi, rsi_signals


def test_buy_hold_always_long(trending_ohlc):
    sig = buy_hold_signals(trending_ohlc, StrategyParams())
    assert (sig == 1.0).all()
    assert sig.index.equals(trending_ohlc.index)


def test_ma_crossover_no_lookahead(trending_ohlc):
    params = StrategyParams(short_window=10, long_window=30)
    sig = ma_crossover_signals(trending_ohlc, params)
    # First `long_window` bars cannot have a valid signal.
    assert sig.iloc[:30].sum() == 0.0
    # In an uptrend we should end up long.
    assert sig.iloc[-1] == 1.0


def test_ma_crossover_values_are_binary(trending_ohlc):
    params = StrategyParams(short_window=10, long_window=30)
    sig = ma_crossover_signals(trending_ohlc, params)
    assert set(np.unique(sig.values)).issubset({0.0, 1.0})


def test_rsi_bounds():
    import pandas as pd

    close = pd.Series(np.linspace(100, 120, 50))
    rsi = compute_rsi(close, period=14)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_rsi_signals_change_position_on_extremes(choppy_ohlc):
    params = StrategyParams(rsi_period=14, rsi_oversold=30, rsi_overbought=70)
    sig = rsi_signals(choppy_ohlc, params)
    # A mean-reverting series should trigger both entries and exits.
    assert (sig == 1.0).any()
    assert (sig == 0.0).any()
