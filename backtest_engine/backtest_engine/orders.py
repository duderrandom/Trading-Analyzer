"""Order and Trade value objects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


Action = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Order:
    """A pending instruction: 'after this fill, be at `target_fraction`
    of equity invested'. Engines turn signals into Orders, the Broker
    turns Orders into Trades."""

    date: pd.Timestamp
    action: Action
    target_fraction: float  # 1.0 = fully long, 0.0 = flat


@dataclass
class Trade:
    """A realized fill."""

    date: pd.Timestamp
    action: Action
    price: float            # fill price (post-slippage)
    shares: float
    commission: float
    portfolio_value: float  # equity immediately after the fill
