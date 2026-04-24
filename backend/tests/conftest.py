"""Shared fixtures. A synthetic OHLC series with a known shape lets us
test strategy + backtest + metrics behavior deterministically, without
hitting the network.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def trending_ohlc() -> pd.DataFrame:
    """250 trading days of a gently upward-drifting series with noise."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    trend = np.linspace(100.0, 150.0, n)
    noise = np.random.normal(0, 1.5, n)
    close = trend + noise
    df = pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.5,
            "Low": close - 0.5,
            "Close": close,
            "Volume": np.full(n, 1_000_000.0),
        },
        index=dates,
    )
    df.index.name = "Date"
    return df


@pytest.fixture
def choppy_ohlc() -> pd.DataFrame:
    """A mean-reverting series good for RSI testing."""
    np.random.seed(7)
    n = 200
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    base = 100 + 5 * np.sin(np.linspace(0, 12 * np.pi, n))
    noise = np.random.normal(0, 0.8, n)
    close = base + noise
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close + 0.3,
            "Low": close - 0.3,
            "Close": close,
            "Volume": np.full(n, 500_000.0),
        },
        index=dates,
    )
    df.index.name = "Date"
    return df
