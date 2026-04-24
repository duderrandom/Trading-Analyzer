"""Portfolio state: cash, shares, mark-to-market equity.

Single-asset by design — this MVP trades one ticker at a time. Extending
to multi-asset would replace `shares: float` with a `dict[str, float]`
and require a price lookup per symbol.
"""
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
        """Mark-to-market equity at a given price."""
        return self.cash + self.shares * price

    def allocate(self, price: float, shares: float, commission: float) -> None:
        """Buy `shares` at `price`, paying `commission` from cash."""
        cost = shares * price + commission
        if cost > self.cash + 1e-9:
            raise ValueError(
                f"Insufficient cash: need {cost:.2f}, have {self.cash:.2f}"
            )
        self.cash -= cost
        self.shares += shares

    def liquidate(self, price: float, commission: float) -> float:
        """Sell entire position at `price`, paying `commission`.
        Returns shares sold."""
        shares_sold = self.shares
        proceeds = shares_sold * price - commission
        self.cash += proceeds
        self.shares = 0.0
        return shares_sold
