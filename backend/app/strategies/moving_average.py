"""Moving Average Crossover (SMA).

Go long when the short SMA is above the long SMA; flat otherwise. The
signal is shifted by one bar so trades execute on the *next* bar's
open/close, avoiding look-ahead bias.
"""
from __future__ import annotations

import pandas as pd

from app.models.schemas import StrategyParams


def ma_crossover_signals(df: pd.DataFrame, params: StrategyParams) -> pd.Series:
    short = params.short_window
    long = params.long_window

    close = df["Close"]
    sma_short = close.rolling(window=short, min_periods=short).mean()
    sma_long = close.rolling(window=long, min_periods=long).mean()

    raw = (sma_short > sma_long).astype(float)
    # Shift by 1: we can only act on a signal the bar *after* it forms.
    signals = raw.shift(1).fillna(0.0)
    signals.name = "position"
    return signals
