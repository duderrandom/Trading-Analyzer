"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.custom_spec import CustomStrategy


StrategyName = Literal["buy_hold", "ma_crossover", "rsi", "custom"]


class StrategyParams(BaseModel):
    """Per-strategy parameters. Only the fields relevant to the selected
    strategy are read; others are ignored."""

    # Moving Average Crossover
    short_window: int = Field(default=20, ge=2, le=200)
    long_window: int = Field(default=50, ge=5, le=400)

    # RSI
    rsi_period: int = Field(default=14, ge=2, le=100)
    rsi_oversold: float = Field(default=30.0, ge=1.0, le=49.0)
    rsi_overbought: float = Field(default=70.0, ge=51.0, le=99.0)

    @field_validator("long_window")
    @classmethod
    def _long_gt_short(cls, v: int, info) -> int:  # type: ignore[no-untyped-def]
        short = info.data.get("short_window")
        if short is not None and v <= short:
            raise ValueError("long_window must be greater than short_window")
        return v


class BrokerConfig(BaseModel):
    commission_per_trade: float = Field(default=0.0, ge=0.0)
    commission_per_share: float = Field(default=0.0, ge=0.0)
    slippage_bps: float = Field(default=0.0, ge=0.0, le=1000.0)


class BacktestRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=15)
    start_date: date
    end_date: date
    strategies: list[StrategyName] = Field(..., min_length=1)
    initial_capital: float = Field(default=10_000.0, gt=0)
    params: StrategyParams = Field(default_factory=StrategyParams)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    custom: Optional[CustomStrategy] = None

    @field_validator("ticker")
    @classmethod
    def _upper_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, v: date, info) -> date:  # type: ignore[no-untyped-def]
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date")
        return v


class Trade(BaseModel):
    date: str
    action: Literal["BUY", "SELL"]
    price: float
    shares: float
    portfolio_value: float


class EquityPoint(BaseModel):
    date: str
    value: float


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class Metrics(BaseModel):
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: Optional[float]
    sharpe_ratio: Optional[float]
    num_trades: int
    final_value: float


class StrategyResult(BaseModel):
    strategy: StrategyName
    label: str
    metrics: Metrics
    trades: list[Trade]
    equity_curve: list[EquityPoint]


class BacktestResponse(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    prices: list[PricePoint]
    results: list[StrategyResult]
    best_strategy: str
