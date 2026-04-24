"""Pure-pandas indicator library used by the custom-strategy evaluator.

Each function takes a price DataFrame (or Series) and returns a Series
aligned to the input index. Warmup periods surface as leading NaNs —
the evaluator and backtest engine already handle NaN → flat position.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _source(df: pd.DataFrame, source: str) -> pd.Series:
    col = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}.get(source.lower())
    if col is None or col not in df.columns:
        raise ValueError(f"Unknown price source: {source}")
    return df[col]


def sma(df: pd.DataFrame, period: int, source: str = "close") -> pd.Series:
    return _source(df, source).rolling(window=period, min_periods=period).mean()


def ema(df: pd.DataFrame, period: int, source: str = "close") -> pd.Series:
    return _source(df, source).ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(df: pd.DataFrame, period: int, source: str = "close") -> pd.Series:
    """Wilder-smoothed RSI. Matches existing app.strategies.rsi.compute_rsi."""
    close = _source(df, source)
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(100.0).where(avg_gain.notna(), np.nan)


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    source: str = "close",
) -> dict[str, pd.Series]:
    price = _source(df, source)
    fast_ema = price.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = price.ewm(span=slow, adjust=False, min_periods=slow).mean()
    line = fast_ema - slow_ema
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return {"line": line, "signal": sig, "hist": line - sig}


def bollinger(
    df: pd.DataFrame,
    period: int = 20,
    stddev: float = 2.0,
    source: str = "close",
) -> dict[str, pd.Series]:
    price = _source(df, source)
    mid = price.rolling(window=period, min_periods=period).mean()
    std = price.rolling(window=period, min_periods=period).std(ddof=0)
    return {"upper": mid + stddev * std, "middle": mid, "lower": mid - stddev * std}
