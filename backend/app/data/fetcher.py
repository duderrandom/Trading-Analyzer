"""Historical OHLC data fetching.

Primary source: Yahoo Finance via `yfinance`.
Fallback: CSV file with columns Date,Open,High,Low,Close,Volume.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


REQUIRED_COLS = ["Open", "High", "Low", "Close", "Volume"]


class DataFetchError(RuntimeError):
    """Raised when OHLC data cannot be fetched or is invalid."""


def fetch_yahoo(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Download daily OHLC from Yahoo Finance.

    `end` is exclusive on Yahoo's side, so we extend by one day so the
    caller's inclusive range is respected.
    """
    import yfinance as yf  # imported lazily so tests can run without network

    end_plus = pd.Timestamp(end) + pd.Timedelta(days=1)
    df = yf.download(
        ticker,
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        end=end_plus.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )
    if df is None or df.empty:
        raise DataFetchError(
            f"No data returned for ticker '{ticker}' in {start}..{end}. "
            "Check the symbol and date range."
        )

    # yfinance may return a MultiIndex when multiple tickers are requested;
    # flatten to the single-ticker case.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataFetchError(f"Provider response missing columns: {missing}")

    df = df[REQUIRED_COLS].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"
    return df.dropna()


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLC from a CSV with a Date column and OHLCV columns."""
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise DataFetchError("CSV must contain a 'Date' column.")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataFetchError(f"CSV missing columns: {missing}")
    return df[REQUIRED_COLS].dropna()


def get_ohlc(
    ticker: str,
    start: date,
    end: date,
    csv_path: str | Path | None = None,
) -> pd.DataFrame:
    """Single entry point used by the API layer.

    If `csv_path` is provided, load from CSV and slice to the range.
    Otherwise fetch from Yahoo Finance.
    """
    if csv_path is not None:
        df = load_csv(csv_path)
        df = df.loc[str(start) : str(end)]
        if df.empty:
            raise DataFetchError("CSV contains no rows in the requested range.")
        return df
    return fetch_yahoo(ticker, start, end)
