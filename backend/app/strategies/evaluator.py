"""Evaluate a CustomStrategy AST against a price DataFrame."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.custom_spec import (
    BoolExpr,
    Comparison,
    Constant,
    CustomStrategy,
    IndicatorBB,
    IndicatorEMA,
    IndicatorMACD,
    IndicatorRSI,
    IndicatorSMA,
    LogicalAnd,
    LogicalNot,
    LogicalOr,
    NumExpr,
    Price,
)

from . import indicators


def _eval_num(node: NumExpr, df: pd.DataFrame) -> pd.Series:
    if isinstance(node, IndicatorSMA):
        return indicators.sma(df, node.period, node.source)
    if isinstance(node, IndicatorEMA):
        return indicators.ema(df, node.period, node.source)
    if isinstance(node, IndicatorRSI):
        return indicators.rsi(df, node.period, node.source)
    if isinstance(node, IndicatorMACD):
        parts = indicators.macd(df, node.fast, node.slow, node.signal, node.source)
        return parts[node.ind.removeprefix("macd_")]
    if isinstance(node, IndicatorBB):
        parts = indicators.bollinger(df, node.period, node.stddev, node.source)
        return parts[node.ind.removeprefix("bb_")]
    if isinstance(node, Price):
        col = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}[node.price]
        return df[col].astype(float)
    if isinstance(node, Constant):
        return pd.Series(node.const, index=df.index, dtype=float)
    raise TypeError(f"Unsupported numeric node: {type(node).__name__}")


def _eval_bool(node: BoolExpr, df: pd.DataFrame) -> pd.Series:
    if isinstance(node, Comparison):
        left = _eval_num(node.left, df)
        right = _eval_num(node.right, df)
        if node.op == "gt":
            out = left > right
        elif node.op == "lt":
            out = left < right
        elif node.op == "gte":
            out = left >= right
        elif node.op == "lte":
            out = left <= right
        elif node.op == "crosses_above":
            out = (left > right) & (left.shift(1) <= right.shift(1))
        elif node.op == "crosses_below":
            out = (left < right) & (left.shift(1) >= right.shift(1))
        else:
            raise ValueError(f"Unknown comparison op: {node.op}")
        valid = left.notna() & right.notna()
        if node.op in ("crosses_above", "crosses_below"):
            valid &= left.shift(1).notna() & right.shift(1).notna()
        return (out & valid).fillna(False)

    if isinstance(node, LogicalAnd):
        args = [_eval_bool(a, df) for a in node.args]
        out = args[0]
        for a in args[1:]:
            out = out & a
        return out.fillna(False)

    if isinstance(node, LogicalOr):
        args = [_eval_bool(a, df) for a in node.args]
        out = args[0]
        for a in args[1:]:
            out = out | a
        return out.fillna(False)

    if isinstance(node, LogicalNot):
        return (~_eval_bool(node.arg, df)).fillna(False)

    raise TypeError(f"Unsupported boolean node: {type(node).__name__}")


def evaluate(strategy: CustomStrategy, df: pd.DataFrame) -> pd.Series:
    """Return a position Series (0.0 / 1.0) for the given strategy.

    Position stays flat until `entry` first fires, then holds until `exit`
    fires. Signals are shifted by one bar to avoid look-ahead — a signal
    computed from bar t's close only acts from bar t+1.
    """
    entry = _eval_bool(strategy.entry, df)
    exit_ = _eval_bool(strategy.exit, df)

    position = 0.0
    out: list[float] = []
    for is_entry, is_exit in zip(entry.values, exit_.values):
        if position == 0.0 and is_entry:
            position = 1.0
        elif position == 1.0 and is_exit:
            position = 0.0
        out.append(position)

    series = pd.Series(out, index=df.index, name="position", dtype=float)
    return series.shift(1).fillna(0.0)
