"""Broker — turns orders into fills, applying slippage and commission.

Cost models:
  * slippage_bps: adverse, in basis points. Buys pay more, sells get less.
  * commission: per-trade flat fee + per-share fee. Either can be zero.

Defaults to a frictionless broker so the engine matches the
textbook-simple case until the user opts in to costs.
"""
from __future__ import annotations

from dataclasses import dataclass

from .orders import Order, Trade
from .portfolio import Portfolio


@dataclass
class Broker:
    commission_per_trade: float = 0.0
    commission_per_share: float = 0.0
    slippage_bps: float = 0.0  # 1 bp = 0.01%

    def _fill_price(self, raw_price: float, action: str) -> float:
        adj = raw_price * (self.slippage_bps / 10_000.0)
        return raw_price + adj if action == "BUY" else raw_price - adj

    def _commission(self, shares: float) -> float:
        return self.commission_per_trade + self.commission_per_share * shares

    def execute(self, order: Order, raw_price: float, portfolio: Portfolio) -> Trade | None:
        """Execute `order` at `raw_price`. Returns a Trade, or None if
        the order is a no-op (e.g., BUY when already long)."""
        fill_price = self._fill_price(raw_price, order.action)

        if order.action == "BUY":
            if portfolio.is_long:
                return None
            # Size so gross cost + commission <= cash:
            #   shares * fill_price + fee_trade + fee_share * shares = cash
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
