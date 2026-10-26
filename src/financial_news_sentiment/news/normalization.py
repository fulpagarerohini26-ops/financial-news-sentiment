"""Shared validation and timestamp normalization for news providers."""

from __future__ import annotations

import re
from datetime import UTC, datetime

_TICKER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,19}\Z")


def validate_ticker(ticker: str) -> str:
    """Validate a ticker and return its canonical uppercase representation."""
    if not isinstance(ticker, str) or not _TICKER_PATTERN.fullmatch(ticker.strip()):
        raise ValueError(
            "ticker must be 1-20 letters, digits, periods, or hyphens and start "
            "with a letter or digit"
        )
    return ticker.strip().upper()


def normalize_published_at(value: int | datetime) -> tuple[datetime, int]:
    """Return a UTC datetime and integer Unix seconds for a news timestamp."""
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("published_at must include a timezone offset")
        try:
            published_at = value.astimezone(UTC)
            timestamp = int(published_at.timestamp())
        except (OverflowError, OSError, ValueError):
            raise ValueError("published_at is outside the supported range") from None
        return published_at, timestamp

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("published_at must be a datetime or integer Unix timestamp")
    try:
        published_at = datetime.fromtimestamp(value, tz=UTC)
    except (OverflowError, OSError, ValueError):
        raise ValueError("published_at is outside the supported range") from None
    return published_at, value
