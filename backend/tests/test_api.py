"""End-to-end API tests that bypass the network by monkey-patching the
data fetcher.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_module


def test_list_strategies():
    client = TestClient(app_module.app)
    resp = client.get("/api/strategies")
    assert resp.status_code == 200
    ids = {s["id"] for s in resp.json()}
    assert ids == {"buy_hold", "ma_crossover", "rsi"}


def test_backtest_endpoint(monkeypatch, trending_ohlc):
    monkeypatch.setattr(app_module, "get_ohlc", lambda *a, **kw: trending_ohlc)

    client = TestClient(app_module.app)
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "TEST",
            "start_date": "2023-01-02",
            "end_date": "2023-12-15",
            "strategies": ["buy_hold", "ma_crossover"],
            "initial_capital": 10_000,
            "params": {"short_window": 10, "long_window": 30},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ticker"] == "TEST"
    assert len(data["results"]) == 2
    assert data["best_strategy"] in {"buy_hold", "ma_crossover"}
    for r in data["results"]:
        assert "metrics" in r and "equity_curve" in r and "trades" in r
