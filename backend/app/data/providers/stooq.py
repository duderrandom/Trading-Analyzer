"""Stooq CSV endpoint. As of 2026 stooq requires an API key (STOOQ_API_KEY)."""
from __future__ import annotations

import io
import os
from datetime import date

import pandas as pd

NAME = "stooq"
REQUIRES_KEY = True

_URL = "https://stooq.com/q/d/l/"
_REQUIRED = ["Open", "High", "Low", "Close", "Volume"]


def _api_key() -> str | None:
    return os.environ.get("STOOQ_API_KEY")


def is_available() -> bool:
    return bool(_api_key())


def _download(symbol: str, start: date, end: date, key: str) -> pd.DataFrame:
    import requests

    params = {
        "s": symbol,
        "d1": start.strftime("%Y%m%d"),
        "d2": end.strftime("%Y%m%d"),
        "i": "d",
        "apikey": key,
    }
    r = requests.get(_URL, params=params, timeout=15)
    if r.status_code == 429:
        from . import RateLimitError

        raise RateLimitError("stooq rate limited")
    r.raise_for_status()
    text = r.text.strip()
    if not text or "Date,Open,High,Low,Close,Volume" not in text.splitlines()[0]:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(text))


def fetch(ticker: str, start: date, end: date) -> pd.DataFrame:
    from . import ProviderError

    key = _api_key()
    if not key:
        raise ProviderError("stooq: STOOQ_API_KEY not set")

    t = ticker.lower()
    df = pd.DataFrame()
    for symbol in (f"{t}.us", t):
        df = _download(symbol, start, end, key)
        if not df.empty:
            break

    if df.empty:
        raise ProviderError(f"stooq returned no rows for {ticker}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise ProviderError(f"stooq response missing columns: {missing}")

    df = df[_REQUIRED].dropna()
    df.index.name = "Date"
    return df
