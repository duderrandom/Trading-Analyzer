"""RSI (Relative Strength Index) mean-reversion strategy.

Classic Wilder's RSI. Enter long when RSI crosses below `oversold`,
exit when RSI crosses above `overbought`. Between those, we carry the
previous position forward.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.schemas import StrategyParams


def compute_rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder-smoothed RSI."""
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    # Wilder's smoothing is an EMA with alpha = 1/period.
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # If avg_loss is zero we have only gains — treat that as RSI = 100.
    rsi = rsi.fillna(100.0)
    return rsi


def rsi_signals(df: pd.DataFrame, params: StrategyParams) -> pd.Series:
    rsi = compute_rsi(df["Close"], params.rsi_period)

    position = 0.0
    out: list[float] = []
    for value in rsi.values:
        if np.isnan(value):
            out.append(0.0)
            continue
        if value < params.rsi_oversold:
            position = 1.0
        elif value > params.rsi_overbought:
            position = 0.0
        out.append(position)

    signals = pd.Series(out, index=df.index, name="position")
    # Shift by 1 bar to avoid look-ahead: the signal based on today's
    # close is only actionable tomorrow.
    return signals.shift(1).fillna(0.0)
