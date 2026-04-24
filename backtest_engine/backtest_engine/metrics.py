"""Performance metrics.

Textbook definitions — useful for comparison, not for reporting to a
portfolio manager. Production analytics would account for benchmarks,
risk-free curves, tax drag, etc.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


@dataclass
class MetricsResult:
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float | None
    sharpe_ratio: float | None
    num_trades: int
    final_value: float


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def annualized_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    span_days = (equity.index[-1] - equity.index[0]).days
    if span_days <= 0:
        return 0.0
    years = span_days / 365.25
    growth = equity.iloc[-1] / equity.iloc[0]
    if growth <= 0:
        return -1.0
    return float(growth ** (1.0 / years) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough decline (negative fraction)."""
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    return float(dd.min())


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float | None:
    if returns is None or len(returns) < 2:
        return None
    rf = risk_free_rate / periods_per_year
    excess = returns - rf
    std = excess.std(ddof=1)
    if std is None or np.isnan(std) or std < 1e-12:
        return None
    return float((excess.mean() / std) * np.sqrt(periods_per_year))


def win_rate(trades) -> float | None:
    """Win rate over completed round-trip trades."""
    pairs: list[tuple[float, float]] = []
    entry: float | None = None
    for t in trades:
        if t.action == "BUY":
            entry = t.price
        elif t.action == "SELL" and entry is not None:
            pairs.append((entry, t.price))
            entry = None
    if not pairs:
        return None
    wins = sum(1 for a, b in pairs if b > a)
    return float(wins / len(pairs))


def compute_all(result) -> MetricsResult:
    """Compute the full metrics bundle from a `BacktestResult`."""
    eq = result.equity
    ret = result.returns
    trades = result.trades

    tr = total_return(eq)
    ar = annualized_return(eq)
    mdd = max_drawdown(eq)
    sr = sharpe_ratio(ret)
    wr = win_rate(trades)

    return MetricsResult(
        total_return_pct=round(tr * 100.0, 4),
        annualized_return_pct=round(ar * 100.0, 4),
        max_drawdown_pct=round(mdd * 100.0, 4),
        win_rate_pct=round(wr * 100.0, 4) if wr is not None else None,
        sharpe_ratio=round(sr, 4) if sr is not None else None,
        num_trades=len(trades),
        final_value=round(float(eq.iloc[-1]) if len(eq) else result.initial_capital, 2),
    )
