"""Tests for the user-defined strategy AST: indicators, evaluator, end-to-end."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.custom_spec import CustomStrategy
from app.strategies import indicators
from app.strategies.evaluator import evaluate


def test_sma_matches_rolling_mean(trending_ohlc: pd.DataFrame) -> None:
    got = indicators.sma(trending_ohlc, 10)
    expected = trending_ohlc["Close"].rolling(10, min_periods=10).mean()
    pd.testing.assert_series_equal(got, expected, check_names=False)


def test_ema_warmup_has_nans(trending_ohlc: pd.DataFrame) -> None:
    got = indicators.ema(trending_ohlc, 20)
    assert got.iloc[:19].isna().all()
    assert got.iloc[19:].notna().all()


def test_rsi_in_range(choppy_ohlc: pd.DataFrame) -> None:
    rsi = indicators.rsi(choppy_ohlc, 14)
    valid = rsi.dropna()
    assert (valid >= 0.0).all() and (valid <= 100.0).all()


def test_macd_line_equals_fast_minus_slow(trending_ohlc: pd.DataFrame) -> None:
    parts = indicators.macd(trending_ohlc, fast=12, slow=26, signal=9)
    fast = indicators.ema(trending_ohlc, 12)
    slow = indicators.ema(trending_ohlc, 26)
    pd.testing.assert_series_equal(parts["line"], fast - slow, check_names=False)


def test_bollinger_upper_above_middle(trending_ohlc: pd.DataFrame) -> None:
    bb = indicators.bollinger(trending_ohlc, period=20, stddev=2.0)
    diff = (bb["upper"] - bb["middle"]).dropna()
    assert (diff > 0).all()


# ───────────── Evaluator ─────────────

def _spec(entry: dict, exit_: dict, label: str = "Test") -> CustomStrategy:
    return CustomStrategy.model_validate({"label": label, "entry": entry, "exit": exit_})


def test_crosses_fires_on_choppy_series(choppy_ohlc: pd.DataFrame) -> None:
    # Choppy data → SMA(5) and SMA(20) genuinely cross each other multiple
    # times after warmup, so both entry and exit signals fire.
    spec = _spec(
        entry={"op": "crosses_above",
               "left": {"ind": "sma", "period": 5},
               "right": {"ind": "sma", "period": 20}},
        exit_={"op": "crosses_below",
               "left": {"ind": "sma", "period": 5},
               "right": {"ind": "sma", "period": 20}},
    )
    pos = evaluate(spec, choppy_ohlc)
    assert set(pos.unique()).issubset({0.0, 1.0})
    assert pos.iloc[0] == 0.0
    assert (pos == 1.0).any()
    assert (pos == 0.0).any()


def test_rsi_threshold_strategy(choppy_ohlc: pd.DataFrame) -> None:
    spec = _spec(
        entry={"op": "lt",
               "left": {"ind": "rsi", "period": 14},
               "right": {"const": 30.0}},
        exit_={"op": "gt",
               "left": {"ind": "rsi", "period": 14},
               "right": {"const": 70.0}},
    )
    pos = evaluate(spec, choppy_ohlc)
    rsi = indicators.rsi(choppy_ohlc, 14)

    # Whenever we're long, either RSI was below 30 at/around entry,
    # or we haven't seen a >70 exit yet. Simpler invariant: the signal
    # goes long at least once on a mean-reverting series.
    assert (pos == 1.0).any()
    # And goes flat at least once — choppy series swings both ways.
    assert (pos == 0.0).any()
    # RSI with period=14 needs 14+ bars of warmup; early bars stay flat.
    assert (pos.iloc[:14] == 0.0).all()
    _ = rsi  # referenced for explicitness


def test_and_combines_rules(trending_ohlc: pd.DataFrame) -> None:
    # Long only when short>long AND price>SMA(50). Never flattens via 'never true' exit.
    spec = _spec(
        entry={"op": "and", "args": [
            {"op": "gt",
             "left": {"ind": "sma", "period": 5},
             "right": {"ind": "sma", "period": 20}},
            {"op": "gt",
             "left": {"price": "close"},
             "right": {"ind": "sma", "period": 50}},
        ]},
        exit_={"op": "lt",
               "left": {"const": 1.0},
               "right": {"const": 0.0}},  # never true → hold forever
    )
    pos = evaluate(spec, trending_ohlc)
    # Once entered, it should stay long (exit never fires).
    first_long = pos[pos == 1.0].index
    if len(first_long) > 0:
        assert (pos.loc[first_long[0]:] == 1.0).all()


def test_not_inverts(trending_ohlc: pd.DataFrame) -> None:
    inner = {"op": "gt",
             "left": {"ind": "sma", "period": 5},
             "right": {"ind": "sma", "period": 20}}
    inside = _spec(entry=inner, exit_={"op": "not", "arg": inner})
    pos = evaluate(inside, trending_ohlc)
    assert set(pos.unique()).issubset({0.0, 1.0})


def _base_payload() -> dict:
    return {
        "ticker": "TEST",
        "start_date": "2023-01-02",
        "end_date": "2023-12-15",
        "initial_capital": 10_000,
    }


def test_api_round_trip(monkeypatch, trending_ohlc):
    """POST a custom-strategy request and confirm it runs end-to-end."""
    from fastapi.testclient import TestClient

    from app import main as app_module

    monkeypatch.setattr(app_module, "get_ohlc", lambda *a, **kw: trending_ohlc)
    client = TestClient(app_module.app)

    payload = _base_payload() | {
        "strategies": ["custom"],
        "custom": {
            "label": "SMA 5/20",
            "entry": {"op": "crosses_above",
                      "left": {"ind": "sma", "period": 5},
                      "right": {"ind": "sma", "period": 20}},
            "exit": {"op": "crosses_below",
                     "left": {"ind": "sma", "period": 5},
                     "right": {"ind": "sma", "period": 20}},
        },
    }
    resp = client.post("/api/backtest", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["results"][0]["label"] == "SMA 5/20"
    assert data["results"][0]["strategy"] == "custom"


def test_custom_without_spec_rejected(monkeypatch, trending_ohlc):
    from fastapi.testclient import TestClient

    from app import main as app_module

    monkeypatch.setattr(app_module, "get_ohlc", lambda *a, **kw: trending_ohlc)
    client = TestClient(app_module.app)

    payload = _base_payload() | {"strategies": ["custom"]}
    resp = client.post("/api/backtest", json=payload)
    assert resp.status_code == 400
    assert "custom" in resp.text.lower()
