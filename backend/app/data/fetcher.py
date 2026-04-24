"""OHLC orchestration.

Flow:
    1. CSV path (if given) — bypass cache and providers entirely.
    2. Look in SQLite cache for the requested (ticker, range).
    3. Ask the market calendar which trading days in the range are missing.
    4. For any gap, walk the provider priority list (Twelve Data → Tiingo →
       Stooq → Yahoo). 429s fall through to the next provider; other
       provider errors are collected and surfaced only if every provider fails.
    5. Persist the gap fill to SQLite and return the caller's requested slice.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from . import cache, providers
from .calendar import missing_trading_days


REQUIRED_COLS = ["Open", "High", "Low", "Close", "Volume"]


class DataFetchError(RuntimeError):
    """Raised when OHLC data cannot be fetched or is invalid."""


def load_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise DataFetchError("CSV must contain a 'Date' column.")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataFetchError(f"CSV missing columns: {missing}")
    return df[REQUIRED_COLS].dropna()


def _fetch_from_providers(ticker: str, start: date, end: date) -> pd.DataFrame:
    active = providers.active()
    if not active:
        raise DataFetchError("No data providers are available.")

    errors: list[str] = []
    for provider in active:
        try:
            df = provider.fetch(ticker, start, end)
            if df.empty:
                errors.append(f"{provider.NAME}: empty response")
                continue
            return df
        except providers.RateLimitError as e:
            errors.append(f"{provider.NAME}: rate limited ({e})")
        except providers.ProviderError as e:
            errors.append(f"{provider.NAME}: {e}")
        except Exception as e:  # network / parse errors — try next provider
            errors.append(f"{provider.NAME}: {type(e).__name__}: {e}")

    raise DataFetchError(
        f"All providers failed for '{ticker}' in {start}..{end}. "
        + "; ".join(errors)
    )


def get_ohlc(
    ticker: str,
    start: date,
    end: date,
    csv_path: str | Path | None = None,
) -> pd.DataFrame:
    if csv_path is not None:
        df = load_csv(csv_path)
        df = df.loc[str(start) : str(end)]
        if df.empty:
            raise DataFetchError("CSV contains no rows in the requested range.")
        return df

    cached_df = cache.get_cached(ticker, start, end)
    already = cache.cached_dates(ticker, start, end)
    missing = missing_trading_days(ticker, start, end, already)

    if missing:
        gap_start, gap_end = missing[0], missing[-1]
        fetched = _fetch_from_providers(ticker, gap_start, gap_end)
        cache.save(ticker, fetched)
        cached_df = cache.get_cached(ticker, start, end)

    if cached_df.empty:
        raise DataFetchError(
            f"No data available for '{ticker}' in {start}..{end}. "
            "Check the symbol and date range."
        )

    return cached_df.loc[str(start) : str(end)]
