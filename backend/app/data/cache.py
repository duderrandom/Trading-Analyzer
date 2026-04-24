"""SQLite OHLC cache.

Stores daily bars keyed by (ticker, date). `save` is an upsert so repeated
fetches over overlapping ranges never produce duplicates.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import date
from pathlib import Path

import pandas as pd


# Path overridable for tests via env var. Default lives alongside the app.
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "cache.db"
_DB_PATH = Path(os.environ.get("TRADING_ANALYZER_CACHE_DB", _DEFAULT_DB))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlc (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL NOT NULL,
    high   REAL NOT NULL,
    low    REAL NOT NULL,
    close  REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);
"""

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def _norm(ticker: str) -> str:
    return ticker.upper().strip()


def get_cached(ticker: str, start: date, end: date) -> pd.DataFrame:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlc "
            "WHERE ticker = ? AND date BETWEEN ? AND ? ORDER BY date",
            (_norm(ticker), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
        ).fetchall()

    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")


def cached_dates(ticker: str, start: date, end: date) -> set[date]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT date FROM ohlc WHERE ticker = ? AND date BETWEEN ? AND ?",
            (_norm(ticker), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
        ).fetchall()
    return {date.fromisoformat(r[0]) for r in rows}


def save(ticker: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    t = _norm(ticker)
    records = [
        (
            t,
            idx.strftime("%Y-%m-%d"),
            float(row.Open),
            float(row.High),
            float(row.Low),
            float(row.Close),
            float(row.Volume),
        )
        for idx, row in df.iterrows()
    ]
    with _lock, _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO ohlc "
            "(ticker, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            records,
        )
        conn.commit()
    return len(records)
