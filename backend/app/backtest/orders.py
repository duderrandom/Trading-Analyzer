"""Order and Trade value objects.

An `Order` is an intent: "buy/sell at the next bar's close". A `Trade`
is the realized fill: price, shares, resulting portfolio value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


Action = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Order:
    """A pending instruction. Engines turn signals into Orders, the
    Broker turns Orders into Trades."""

    date: pd.Timestamp
    action: Action
    # `target_fraction` is the *target position* after this order fills,
    # expressed as a fraction of equity. 1.0 = fully long, 0.0 = flat.
    target_fraction: float


@dataclass
class Trade:
    """A realized fill."""

    date: pd.Timestamp
    action: Action
    price: float          # fill price (post-slippage)
    shares: float         # shares transacted
    commission: float     # cost paid for this fill
    portfolio_value: float  # equity immediately after the fill
