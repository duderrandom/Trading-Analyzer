from __future__ import annotations

import pytest

from app.backtest.portfolio import Portfolio


def test_equity_marks_to_market():
    pf = Portfolio(cash=1_000.0, shares=10.0)
    assert pf.equity(price=50.0) == 1_500.0


def test_allocate_and_liquidate_round_trip():
    pf = Portfolio(cash=10_000.0)
    pf.allocate(price=100.0, shares=50.0, commission=10.0)
    assert pf.cash == pytest.approx(10_000 - 100 * 50 - 10)
    assert pf.shares == 50.0
    assert pf.is_long

    sold = pf.liquidate(price=110.0, commission=10.0)
    assert sold == 50.0
    assert not pf.is_long
    assert pf.cash == pytest.approx(10_000 - 100 * 50 - 10 + 50 * 110 - 10)


def test_allocate_rejects_overdraft():
    pf = Portfolio(cash=100.0)
    with pytest.raises(ValueError):
        pf.allocate(price=50.0, shares=10.0, commission=0.0)  # needs 500
