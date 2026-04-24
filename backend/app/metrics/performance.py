"""Performance metrics.

All metrics operate on two inputs:
  * an equity curve (portfolio value indexed by date)
  * a list of trades (paired BUY/SELL)

These are intentionally simplified textbook definitions — production
analytics would account for risk-free rates, benchmark-relative stats,
trade costs, tax drag, etc.
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
    # Use calendar span rather than bar count — handles weekends/holidays.
    span_days = (equity.index[-1] - equity.index[0]).days
    if span_days <= 0:
        return 0.0
    years = span_days / 365.25
    growth = equity.iloc[-1] / equity.iloc[0]
    if growth <= 0:
        return -1.0
    return float(growth ** (1.0 / years) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough decline, returned as a negative fraction."""
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdowns = (equity - running_max) / running_max
    return float(drawdowns.min())


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float | None:
    """Annualized Sharpe ratio using daily returns.

    Returns None if there isn't enough variance to compute meaningfully.
    """
    if returns is None or len(returns) < 2:
        return None
    rf_per_period = risk_free_rate / periods_per_year
    excess = returns - rf_per_period
    std = excess.std(ddof=1)
    # Guard against degenerate (constant or near-constant) series: pandas
    # can return a tiny non-zero std due to floating-point noise.
    if std is None or np.isnan(std) or std < 1e-12:
        return None
    return float((excess.mean() / std) * np.sqrt(periods_per_year))


def win_rate(trades) -> float | None:
    """Win rate over *completed* round-trip trades (a BUY paired with a SELL).

    Returns None if there are no completed trades.
    """
    completed_pairs: list[tuple[float, float]] = []
    entry_price: float | None = None
    for t in trades:
        if t.action == "BUY":
            entry_price = t.price
        elif t.action == "SELL" and entry_price is not None:
            completed_pairs.append((entry_price, t.price))
            entry_price = None

    if not completed_pairs:
        return None
    wins = sum(1 for entry, exit_ in completed_pairs if exit_ > entry)
    return float(wins / len(completed_pairs))


def compute_all(equity: pd.Series, returns: pd.Series, trades, initial_capital: float) -> MetricsResult:
    tr = total_return(equity)
    ar = annualized_return(equity)
    mdd = max_drawdown(equity)
    sr = sharpe_ratio(returns)
    wr = win_rate(trades)

    return MetricsResult(
        total_return_pct=round(tr * 100.0, 4),
        annualized_return_pct=round(ar * 100.0, 4),
        max_drawdown_pct=round(mdd * 100.0, 4),
        win_rate_pct=round(wr * 100.0, 4) if wr is not None else None,
        sharpe_ratio=round(sr, 4) if sr is not None else None,
        num_trades=len(trades),
        final_value=round(float(equity.iloc[-1]) if len(equity) else initial_capital, 2),
    )
