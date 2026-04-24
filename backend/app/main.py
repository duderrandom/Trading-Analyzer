"""FastAPI application exposing the backtest endpoints."""
from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.backtest import Broker, run_backtest
from app.data.fetcher import DataFetchError, get_ohlc
from app.metrics.performance import compute_all
from app.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    EquityPoint,
    Metrics,
    PricePoint,
    StrategyResult,
    Trade,
)
from app.strategies import REGISTRY, get_strategy
from app.strategies.evaluator import evaluate as evaluate_custom


app = FastAPI(
    title="Trading Strategy Analyzer",
    description=(
        "An educational backtesting tool. Compare classic rule-based "
        "trading strategies on historical price data. This is not a "
        "prediction engine — it is a tool for understanding risk, "
        "return, and the difficulty of consistent outperformance."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: frontend served from a different port
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "name": "Trading Strategy Analyzer",
        "version": "0.1.0",
        "docs": "/docs",
        "disclaimer": (
            "Educational tool. Backtests ignore commissions, slippage, "
            "and taxes. Past performance does not predict future results."
        ),
    }


@app.get("/api/strategies")
def list_strategies() -> list[dict]:
    return [
        {"id": key, "label": label, "description": desc}
        for key, (label, _fn, desc) in REGISTRY.items()
    ]


def _run_single(req: BacktestRequest, strategy_id: str, prices):
    if strategy_id == "custom":
        if req.custom is None:
            raise HTTPException(
                status_code=400,
                detail="Strategy 'custom' requires a 'custom' spec in the request.",
            )
        label = req.custom.label
        signals = evaluate_custom(req.custom, prices)
    else:
        label, signal_fn, _desc = get_strategy(strategy_id)
        signals = signal_fn(prices, req.params)
    broker = Broker(
        commission_per_trade=req.broker.commission_per_trade,
        commission_per_share=req.broker.commission_per_share,
        slippage_bps=req.broker.slippage_bps,
    )
    bt = run_backtest(prices, signals, initial_capital=req.initial_capital, broker=broker)
    metrics = compute_all(bt.equity, bt.returns, bt.trades, req.initial_capital)

    return StrategyResult(
        strategy=strategy_id,  # type: ignore[arg-type]
        label=label,
        metrics=Metrics(
            total_return_pct=metrics.total_return_pct,
            annualized_return_pct=metrics.annualized_return_pct,
            max_drawdown_pct=metrics.max_drawdown_pct,
            win_rate_pct=metrics.win_rate_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            num_trades=metrics.num_trades,
            final_value=metrics.final_value,
        ),
        trades=[
            Trade(
                date=t.date.strftime("%Y-%m-%d"),
                action=t.action,  # type: ignore[arg-type]
                price=round(t.price, 4),
                shares=round(t.shares, 6),
                portfolio_value=round(t.portfolio_value, 2),
            )
            for t in bt.trades
        ],
        equity_curve=[
            EquityPoint(date=d.strftime("%Y-%m-%d"), value=round(float(v), 2))
            for d, v in bt.equity.items()
        ],
    )


@app.post("/api/backtest", response_model=BacktestResponse)
def backtest(req: BacktestRequest) -> BacktestResponse:
    try:
        prices = get_ohlc(req.ticker, req.start_date, req.end_date)
    except DataFetchError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover — provider-side failures
        raise HTTPException(status_code=502, detail=f"Data provider error: {e}") from e

    if len(prices) < 5:
        raise HTTPException(
            status_code=400,
            detail="Not enough price data in the requested range to run a backtest.",
        )

    results: list[StrategyResult] = []
    for strat in req.strategies:
        try:
            results.append(_run_single(req, strat, prices))
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    best = max(results, key=lambda r: r.metrics.total_return_pct).strategy

    price_points = [
        PricePoint(
            date=idx.strftime("%Y-%m-%d"),
            open=round(float(row.Open), 4),
            high=round(float(row.High), 4),
            low=round(float(row.Low), 4),
            close=round(float(row.Close), 4),
            volume=float(row.Volume),
        )
        for idx, row in prices.iterrows()
    ]

    return BacktestResponse(
        ticker=req.ticker,
        start_date=str(prices.index[0].date()),
        end_date=str(prices.index[-1].date()),
        initial_capital=req.initial_capital,
        prices=price_points,
        results=results,
        best_strategy=best,
    )


@app.post("/api/backtest/export")
def export_csv(req: BacktestRequest) -> StreamingResponse:
    """Return a CSV comparing the equity curves of each requested strategy."""
    response = backtest(req)

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["date"] + [r.label for r in response.results]
    writer.writerow(header)

    # Align equity curves by date.
    by_date: dict[str, list] = {}
    for r in response.results:
        for pt in r.equity_curve:
            by_date.setdefault(pt.date, [None] * len(response.results))
    label_to_idx = {r.label: i for i, r in enumerate(response.results)}
    for r in response.results:
        for pt in r.equity_curve:
            by_date[pt.date][label_to_idx[r.label]] = pt.value

    for d in sorted(by_date):
        writer.writerow([d] + by_date[d])

    buf.seek(0)
    filename = f"backtest_{req.ticker}_{req.start_date}_{req.end_date}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/health")
def health(
    ticker: str = Query(default="AAPL"),
    start: date = Query(default=date(2023, 1, 1)),
    end: date = Query(default=date(2023, 3, 1)),
) -> dict:
    """Smoke-check the data provider without running a full backtest."""
    try:
        df = get_ohlc(ticker, start, end)
        return {"ok": True, "rows": int(len(df)), "ticker": ticker.upper()}
    except DataFetchError as e:
        return {"ok": False, "error": str(e)}
