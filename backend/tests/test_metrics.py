from __future__ import annotations

import numpy as np
import pandas as pd

from app.backtest.engine import Trade
from app.metrics.performance import (
    compute_all,
    max_drawdown,
    sharpe_ratio,
    total_return,
    win_rate,
)


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def test_total_return_basic():
    eq = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.date_range("2023-01-02", periods=3, freq="B"),
    )
    assert abs(total_return(eq) - 0.21) < 1e-9


def test_max_drawdown_known_case():
    # Peak at 120, trough at 80 → -33.33%
    eq = pd.Series(
        [100, 120, 90, 80, 95],
        index=pd.date_range("2023-01-02", periods=5, freq="B"),
        dtype=float,
    )
    mdd = max_drawdown(eq)
    assert abs(mdd - (-40.0 / 120.0)) < 1e-9


def test_sharpe_on_constant_returns_is_none():
    ret = pd.Series([0.01] * 30)
    # Zero std → undefined Sharpe.
    assert sharpe_ratio(ret) is None


def test_sharpe_positive_on_noisy_positive_drift():
    np.random.seed(0)
    ret = pd.Series(np.random.normal(0.001, 0.01, 252))
    sr = sharpe_ratio(ret)
    assert sr is not None and sr > 0


def test_win_rate_counts_pairs():
    trades = [
        Trade(_ts("2023-01-02"), "BUY", 100.0, 1, 0.0, 100.0),
        Trade(_ts("2023-01-05"), "SELL", 110.0, 1, 0.0, 110.0),   # win
        Trade(_ts("2023-01-10"), "BUY", 115.0, 1, 0.0, 115.0),
        Trade(_ts("2023-01-12"), "SELL", 105.0, 1, 0.0, 105.0),   # loss
    ]
    assert win_rate(trades) == 0.5


def test_win_rate_none_when_no_completed_trades():
    trades = [Trade(_ts("2023-01-02"), "BUY", 100.0, 1, 0.0, 100.0)]
    assert win_rate(trades) is None


def test_compute_all_shape():
    eq = pd.Series(
        np.linspace(10_000, 11_000, 252),
        index=pd.date_range("2023-01-02", periods=252, freq="B"),
    )
    ret = eq.pct_change().fillna(0.0)
    m = compute_all(eq, ret, trades=[], initial_capital=10_000.0)
    assert m.total_return_pct > 0
    assert m.num_trades == 0
    assert m.win_rate_pct is None
