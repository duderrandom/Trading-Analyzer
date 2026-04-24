"""Pydantic models describing a user-defined strategy as an AST.

Shape at a glance:

    Strategy:
        entry: BoolExpr     # when flat, go long if this is true
        exit:  BoolExpr     # when long, go flat if this is true

    NumExpr  = Indicator | Price | Constant
    BoolExpr = Comparison(num, num) | Logical(bool, …) | Not(bool)

    Indicator kinds: sma, ema, rsi, macd_line, macd_signal, macd_hist,
                     bb_upper, bb_middle, bb_lower

The schema is validated at the API boundary; the evaluator trusts it.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


# ───────────── Numeric expressions ─────────────

class IndicatorSMA(BaseModel):
    ind: Literal["sma"]
    period: int = Field(ge=2, le=400)
    source: Literal["open", "high", "low", "close"] = "close"


class IndicatorEMA(BaseModel):
    ind: Literal["ema"]
    period: int = Field(ge=2, le=400)
    source: Literal["open", "high", "low", "close"] = "close"


class IndicatorRSI(BaseModel):
    ind: Literal["rsi"]
    period: int = Field(default=14, ge=2, le=100)
    source: Literal["open", "high", "low", "close"] = "close"


class IndicatorMACD(BaseModel):
    ind: Literal["macd_line", "macd_signal", "macd_hist"]
    fast: int = Field(default=12, ge=2, le=200)
    slow: int = Field(default=26, ge=3, le=400)
    signal: int = Field(default=9, ge=2, le=200)
    source: Literal["open", "high", "low", "close"] = "close"


class IndicatorBB(BaseModel):
    ind: Literal["bb_upper", "bb_middle", "bb_lower"]
    period: int = Field(default=20, ge=2, le=400)
    stddev: float = Field(default=2.0, gt=0.0, le=10.0)
    source: Literal["open", "high", "low", "close"] = "close"


class Price(BaseModel):
    price: Literal["open", "high", "low", "close"]


class Constant(BaseModel):
    const: float


NumExpr = Annotated[
    Union[
        IndicatorSMA,
        IndicatorEMA,
        IndicatorRSI,
        IndicatorMACD,
        IndicatorBB,
        Price,
        Constant,
    ],
    Field(discriminator=None),
]


# ───────────── Boolean expressions ─────────────

class Comparison(BaseModel):
    op: Literal["gt", "lt", "gte", "lte", "crosses_above", "crosses_below"]
    left: NumExpr
    right: NumExpr


class LogicalAnd(BaseModel):
    op: Literal["and"]
    args: list["BoolExpr"] = Field(min_length=1, max_length=16)


class LogicalOr(BaseModel):
    op: Literal["or"]
    args: list["BoolExpr"] = Field(min_length=1, max_length=16)


class LogicalNot(BaseModel):
    op: Literal["not"]
    arg: "BoolExpr"


BoolExpr = Annotated[
    Union[Comparison, LogicalAnd, LogicalOr, LogicalNot],
    Field(discriminator="op"),
]


LogicalAnd.model_rebuild()
LogicalOr.model_rebuild()
LogicalNot.model_rebuild()


class CustomStrategy(BaseModel):
    label: str = Field(default="Custom Strategy", min_length=1, max_length=80)
    entry: BoolExpr
    exit: BoolExpr
