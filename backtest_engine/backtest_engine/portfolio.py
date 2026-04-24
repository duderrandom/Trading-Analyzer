"""Portfolio state — cash, shares, mark-to-market equity."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Portfolio:
    cash: float
    shares: float = 0.0

    @property
    def is_long(self) -> bool:
        return self.shares > 0.0

    def equity(self, price: float) -> float:
        return self.cash + self.shares * price

    def allocate(self, price: float, shares: float, commission: float) -> None:
        cost = shares * price + commission
        if cost > self.cash + 1e-9:
            raise ValueError(
                f"Insufficient cash: need {cost:.2f}, have {self.cash:.2f}"
            )
        self.cash -= cost
        self.shares += shares

    def liquidate(self, price: float, commission: float) -> float:
        shares_sold = self.shares
        self.cash += shares_sold * price - commission
        self.shares = 0.0
        return shares_sold
