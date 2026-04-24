from __future__ import annotations

from datetime import date

import pandas as pd

NAME = "yahoo"
REQUIRES_KEY = False

_REQUIRED = ["Open", "High", "Low", "Close", "Volume"]


def is_available() -> bool:
    return True


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        from . import ProviderError

        raise ProviderError(f"yahoo response missing columns: {missing}")
    df = df[_REQUIRED].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"
    return df.dropna()


def _via_download(ticker: str, start: date, end: date) -> pd.DataFrame:
    import yfinance as yf

    end_plus = pd.Timestamp(end) + pd.Timedelta(days=1)
    df = yf.download(
        ticker,
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        end=end_plus.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    return df if df is not None else pd.DataFrame()


def _via_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    import yfinance as yf

    end_plus = pd.Timestamp(end) + pd.Timedelta(days=1)
    t = yf.Ticker(ticker)
    return t.history(
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        end=end_plus.strftime("%Y-%m-%d"),
        auto_adjust=True,
    )


def fetch(ticker: str, start: date, end: date) -> pd.DataFrame:
    from . import ProviderError

    for attempt in (_via_download, _via_ticker):
        try:
            df = attempt(ticker, start, end)
        except Exception:
            continue
        if df is not None and not df.empty:
            return _normalize(df)

    raise ProviderError(f"yahoo returned no rows for {ticker}")
