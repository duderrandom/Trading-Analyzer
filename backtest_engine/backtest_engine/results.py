"""Backtest output container."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .orders import Trade


@dataclass
class BacktestResult:
    equity: pd.Series          # portfolio value indexed by date
    returns: pd.Series         # bar-over-bar equity returns
    trades: list[Trade] = field(default_factory=list)
    initial_capital: float = 0.0
    final_value: float = 0.0
    total_commission: float = 0.0

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({"equity": self.equity, "returns": self.returns})

    def trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(
                columns=["date", "action", "price", "shares", "commission", "portfolio_value"]
            )
        return pd.DataFrame([t.__dict__ for t in self.trades])
