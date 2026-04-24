"""Standalone backtesting engine.

Event-driven, single-asset, long-only. Designed to be small enough to
read end-to-end — roughly 200 lines of code — while still producing
realistic equity curves, trade logs, and performance metrics.

Public surface:

    from backtest_engine import (
        run_backtest,     # run a strategy, get a BacktestResult
        Broker,           # configure commission / slippage
        Portfolio,        # cash + shares state
        Order, Trade,     # order intent / realized fill
        BacktestResult,   # equity curve + trades + metrics
        metrics,          # module: total_return, max_drawdown, sharpe, win_rate
    )
"""
from .broker import Broker
from .engine import run_backtest
from .orders import Order, Trade
from .portfolio import Portfolio
from .results import BacktestResult
from . import metrics

__version__ = "0.1.0"

__all__ = [
    "Broker",
    "Order",
    "Portfolio",
    "Trade",
    "BacktestResult",
    "run_backtest",
    "metrics",
    "__version__",
]
