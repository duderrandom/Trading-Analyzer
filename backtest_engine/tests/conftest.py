from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def trending_ohlc() -> pd.DataFrame:
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    trend = np.linspace(100.0, 150.0, n)
    noise = np.random.normal(0, 1.5, n)
    close = trend + noise
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.5,
            "Low": close - 0.5,
            "Close": close,
            "Volume": np.full(n, 1_000_000.0),
        },
        index=dates,
    )


@pytest.fixture
def flat_ohlc() -> pd.DataFrame:
    dates = pd.date_range("2023-01-02", periods=50, freq="B")
    close = np.full(50, 100.0)
    return pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": close},
        index=dates,
    )
