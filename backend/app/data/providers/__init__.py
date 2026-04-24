"""OHLC data providers.

Each provider exposes:
    NAME: str                       — short identifier used in errors/logs
    REQUIRES_KEY: bool              — True if the provider needs an API key
    is_available() -> bool          — True if the provider is usable now
    fetch(ticker, start, end) -> pd.DataFrame  — OHLCV indexed by Date

Providers raise RateLimitError on HTTP 429 and ProviderError on other failures.
The orchestrator in `fetcher.py` tries providers in the order listed in PRIORITY.
"""
from __future__ import annotations

from . import stooq, tiingo, twelvedata, yahoo


class ProviderError(RuntimeError):
    """A provider failed in a way that should trigger fallback."""


class RateLimitError(ProviderError):
    """HTTP 429 or an equivalent soft limit — fall back immediately."""


# Fastest / most accurate first. Key-gated providers skip themselves when
# their API key isn't set, so the chain gracefully degrades.
PRIORITY = [twelvedata, tiingo, stooq, yahoo]


def active() -> list:
    return [p for p in PRIORITY if p.is_available()]
