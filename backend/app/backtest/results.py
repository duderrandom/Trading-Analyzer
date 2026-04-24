"""Backtest output aggregation."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .orders import Trade


@dataclass
class BacktestResult:
    equity: pd.Series              # portfolio value indexed by date
    returns: pd.Series             # bar-over-bar equity returns
    trades: list[Trade] = field(default_factory=list)
    initial_capital: float = 0.0
    final_value: float = 0.0
    total_commission: float = 0.0

    def to_frame(self) -> pd.DataFrame:
        """Convenience: equity + returns aligned as a DataFrame."""
        return pd.DataFrame({"equity": self.equity, "returns": self.returns})
