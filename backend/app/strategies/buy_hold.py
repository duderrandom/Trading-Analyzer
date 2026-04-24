"""Buy-and-hold baseline.

Buy at the first available close and hold to the end. Useful as a
reference for whether an active strategy is actually adding value
versus simply being long the market.
"""
from __future__ import annotations

import pandas as pd

from app.models.schemas import StrategyParams


def buy_hold_signals(df: pd.DataFrame, params: StrategyParams) -> pd.Series:
    signals = pd.Series(1.0, index=df.index, name="position")
    return signals
