"""Trading calendar helpers — avoid API calls for non-trading days (weekends/holidays)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd


_DEFAULT_EXCHANGE = "NYSE"


def _valid_trading_days(start: date, end: date, exchange: str) -> list[date]:
    import pandas_market_calendars as mcal

    cal = mcal.get_calendar(exchange)
    sched = cal.valid_days(
        start_date=pd.Timestamp(start),
        end_date=pd.Timestamp(end),
    )
    return [d.date() for d in sched]


def missing_trading_days(
    ticker: str,  # kept for future per-exchange routing
    start: date,
    end: date,
    cached: set[date],
    exchange: str = _DEFAULT_EXCHANGE,
) -> list[date]:
    """Return trading days in [start, end] that are not already in `cached`.

    Clips `end` to today so we don't keep re-fetching future dates that
    don't exist yet.
    """
    today = datetime.now(timezone.utc).date()
    effective_end = min(end, today)
    if effective_end < start:
        return []

    valid = _valid_trading_days(start, effective_end, exchange)
    return [d for d in valid if d not in cached]
