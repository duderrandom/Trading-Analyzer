"""Backtesting engine — public surface."""
from .broker import Broker
from .engine import run_backtest
from .orders import Order, Trade
from .portfolio import Portfolio
from .results import BacktestResult

# Back-compat alias for earlier callers that imported the typed output
# class as `BacktestOutput`.
BacktestOutput = BacktestResult

__all__ = [
    "Broker",
    "Order",
    "Portfolio",
    "Trade",
    "BacktestResult",
    "BacktestOutput",
    "run_backtest",
]
