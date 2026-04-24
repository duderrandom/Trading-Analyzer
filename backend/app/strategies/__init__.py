"""Strategy registry.

Each strategy is a pure function from an OHLC DataFrame + params to a
Series of target positions: 1.0 = fully long, 0.0 = flat. This keeps the
backtest engine completely decoupled from strategy internals.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from app.models.schemas import StrategyParams

from .buy_hold import buy_hold_signals
from .moving_average import ma_crossover_signals
from .rsi import rsi_signals

SignalFn = Callable[[pd.DataFrame, StrategyParams], pd.Series]

REGISTRY: dict[str, tuple[str, SignalFn, str]] = {
    "buy_hold": (
        "Buy & Hold",
        buy_hold_signals,
        "Enter on day one and hold to the end. Baseline for comparison.",
    ),
    "ma_crossover": (
        "Moving Average Crossover",
        ma_crossover_signals,
        "Go long when the short SMA crosses above the long SMA; exit on "
        "the reverse cross.",
    ),
    "rsi": (
        "RSI Mean Reversion",
        rsi_signals,
        "Go long when RSI falls below the oversold threshold; exit when "
        "RSI rises above the overbought threshold.",
    ),
}


def get_strategy(name: str) -> tuple[str, SignalFn, str]:
    if name not in REGISTRY:
        raise KeyError(f"Unknown strategy: {name}")
    return REGISTRY[name]


__all__ = ["REGISTRY", "get_strategy", "SignalFn"]
