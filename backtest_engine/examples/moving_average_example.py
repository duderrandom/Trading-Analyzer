"""Example: moving average crossover on synthetic prices.

Run: python examples/moving_average_example.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_engine import Broker, metrics, run_backtest


def generate_prices(seed: int = 0, n: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-02", periods=n, freq="B")
    trend = np.linspace(100.0, 160.0, n)
    noise = rng.normal(0, 2.0, n)
    close = trend + noise
    return pd.DataFrame(
        {
            "Open": close, "High": close + 0.5, "Low": close - 0.5,
            "Close": close, "Volume": np.full(n, 1e6),
        },
        index=dates,
    )


def ma_crossover(prices: pd.DataFrame, short: int = 20, long: int = 50) -> pd.Series:
    close = prices["Close"]
    sma_s = close.rolling(short, min_periods=short).mean()
    sma_l = close.rolling(long, min_periods=long).mean()
    # shift(1) to avoid look-ahead
    return (sma_s > sma_l).astype(float).shift(1).fillna(0.0)


def main() -> None:
    prices = generate_prices()
    signals = ma_crossover(prices, short=20, long=50)

    for label, broker in [
        ("frictionless", Broker()),
        ("with costs", Broker(commission_per_trade=1.0, slippage_bps=5.0)),
    ]:
        result = run_backtest(prices, signals, initial_capital=10_000.0, broker=broker)
        m = metrics.compute_all(result)
        print(f"\n=== {label} ===")
        print(f"  final value:      ${m.final_value:,.2f}")
        print(f"  total return:     {m.total_return_pct:.2f}%")
        print(f"  annualized:       {m.annualized_return_pct:.2f}%")
        print(f"  max drawdown:     {m.max_drawdown_pct:.2f}%")
        print(f"  sharpe (daily):   {m.sharpe_ratio}")
        print(f"  trades:           {m.num_trades}")
        print(f"  win rate:         {m.win_rate_pct}")
        print(f"  total commission: ${result.total_commission:,.2f}")


if __name__ == "__main__":
    main()
