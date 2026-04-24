"""Tiingo daily prices endpoint. Requires TIINGO_API_KEY."""
from __future__ import annotations

import os
from datetime import date

import pandas as pd

NAME = "tiingo"
REQUIRES_KEY = True

_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def _api_key() -> str | None:
    return os.environ.get("TIINGO_API_KEY")


def is_available() -> bool:
    return bool(_api_key())


def fetch(ticker: str, start: date, end: date) -> pd.DataFrame:
    from . import ProviderError, RateLimitError

    import requests

    key = _api_key()
    if not key:
        raise ProviderError("tiingo: TIINGO_API_KEY not set")

    params = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "format": "json",
        "token": key,
    }
    r = requests.get(
        _URL.format(ticker=ticker),
        params=params,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code == 429:
        raise RateLimitError("tiingo rate limited")
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise ProviderError(f"tiingo returned no rows for {ticker}")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    ).set_index("Date").sort_index()

    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            raise ProviderError(f"tiingo response missing column: {col}")

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index.name = "Date"
    return df
