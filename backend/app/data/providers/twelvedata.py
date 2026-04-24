"""Twelve Data time_series endpoint. Requires TWELVEDATA_API_KEY."""
from __future__ import annotations

import os
from datetime import date

import pandas as pd

NAME = "twelvedata"
REQUIRES_KEY = True

_URL = "https://api.twelvedata.com/time_series"


def _api_key() -> str | None:
    return os.environ.get("TWELVEDATA_API_KEY")


def is_available() -> bool:
    return bool(_api_key())


def fetch(ticker: str, start: date, end: date) -> pd.DataFrame:
    from . import ProviderError, RateLimitError

    import requests

    key = _api_key()
    if not key:
        raise ProviderError("twelvedata: TWELVEDATA_API_KEY not set")

    params = {
        "symbol": ticker,
        "interval": "1day",
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "format": "JSON",
        "apikey": key,
    }
    r = requests.get(_URL, params=params, timeout=15)
    if r.status_code == 429:
        raise RateLimitError("twelvedata rate limited")
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and data.get("code") == 429:
        raise RateLimitError("twelvedata rate limited")
    if isinstance(data, dict) and data.get("status") == "error":
        raise ProviderError(f"twelvedata: {data.get('message', 'unknown error')}")

    values = data.get("values") if isinstance(data, dict) else None
    if not values:
        raise ProviderError(f"twelvedata returned no rows for {ticker}")

    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.rename(
        columns={
            "datetime": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    ).set_index("Date").sort_index()

    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            raise ProviderError(f"twelvedata response missing column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index.name = "Date"
    return df
