from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_engine import metrics, run_backtest
from backtest_engine.orders import Trade


def test_total_return():
    eq = pd.Series([100.0, 110.0, 121.0], index=pd.date_range("2023-01-02", periods=3, freq="B"))
    assert abs(metrics.total_return(eq) - 0.21) < 1e-9


def test_max_drawdown_known_case():
    eq = pd.Series([100, 120, 90, 80, 95], index=pd.date_range("2023-01-02", periods=5, freq="B"), dtype=float)
    assert abs(metrics.max_drawdown(eq) - (-40.0 / 120.0)) < 1e-9


def test_sharpe_none_on_constant():
    assert metrics.sharpe_ratio(pd.Series([0.01] * 30)) is None


def test_win_rate_pairs():
    ts = pd.Timestamp
    trades = [
        Trade(ts("2023-01-02"), "BUY",  100.0, 1, 0.0, 100.0),
        Trade(ts("2023-01-05"), "SELL", 110.0, 1, 0.0, 110.0),
        Trade(ts("2023-01-10"), "BUY",  115.0, 1, 0.0, 115.0),
        Trade(ts("2023-01-12"), "SELL", 105.0, 1, 0.0, 105.0),
    ]
    assert metrics.win_rate(trades) == 0.5


def test_compute_all_integration(trending_ohlc):
    sig = pd.Series(1.0, index=trending_ohlc.index)
    result = run_backtest(trending_ohlc, sig, initial_capital=10_000.0)
    m = metrics.compute_all(result)
    assert m.num_trades == 1
    assert m.total_return_pct > 0
    # Only one open BUY, no round-trip closed → win_rate undefined.
    assert m.win_rate_pct is None
