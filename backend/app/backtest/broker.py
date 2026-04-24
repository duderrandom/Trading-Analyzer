"""Broker: turns orders into fills, applying slippage and commission.

Two cost models, combined:

  * Slippage — expressed as a fraction of price. Adverse by convention:
    we pay a higher price on buys and receive a lower price on sells.
  * Commission — per-trade dollar fee plus a per-share fee. Either can
    be zero. Defaults to zero on both so the engine behaves identically
    to the "frictionless" MVP unless the caller opts in.

All fills occur at the close of the signal bar. This is a deliberate
simplification — real execution at the open or via VWAP would change
results, sometimes materially.
"""
from __future__ import annotations

from dataclasses import dataclass

from .orders import Order, Trade
from .portfolio import Portfolio


@dataclass
class Broker:
    commission_per_trade: float = 0.0
    commission_per_share: float = 0.0
    slippage_bps: float = 0.0  # basis points (1 bp = 0.01%)

    def _fill_price(self, raw_price: float, action: str) -> float:
        adj = raw_price * (self.slippage_bps / 10_000.0)
        return raw_price + adj if action == "BUY" else raw_price - adj

    def _commission(self, shares: float) -> float:
        return self.commission_per_trade + self.commission_per_share * shares

    def execute(self, order: Order, raw_price: float, portfolio: Portfolio) -> Trade | None:
        """Execute `order` against `portfolio` at `raw_price`.

        Returns the realized Trade, or None if the order is a no-op
        (e.g., "SELL" when already flat).
        """
        fill_price = self._fill_price(raw_price, order.action)

        if order.action == "BUY":
            if portfolio.is_long:
                return None  # already at target
            # Size so that gross cost + commission <= cash.
            # Solve: shares * fill_price + fee_trade + fee_share * shares = cash
            # => shares * (fill_price + fee_share) = cash - fee_trade
            budget = portfolio.cash - self.commission_per_trade
            denom = fill_price + self.commission_per_share
            if denom <= 0 or budget <= 0:
                return None
            shares = budget / denom
            commission = self._commission(shares)
            portfolio.allocate(fill_price, shares, commission)
            return Trade(
                date=order.date,
                action="BUY",
                price=fill_price,
                shares=shares,
                commission=commission,
                portfolio_value=portfolio.equity(raw_price),
            )

        # SELL
        if not portfolio.is_long:
            return None
        shares = portfolio.shares
        commission = self._commission(shares)
        sold = portfolio.liquidate(fill_price, commission)
        return Trade(
            date=order.date,
            action="SELL",
            price=fill_price,
            shares=sold,
            commission=commission,
            portfolio_value=portfolio.equity(raw_price),
        )
