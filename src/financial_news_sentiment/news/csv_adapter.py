"""Offline CSV adapter for normalized financial news articles."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from financial_news_sentiment.news.models import NewsArticle
from financial_news_sentiment.news.normalization import (
    normalize_published_at,
    validate_ticker,
)

_REQUIRED_COLUMNS = frozenset({"ticker", "headline", "published_at"})
_OPTIONAL_COLUMNS = frozenset(
    {
        "provider_article_id",
        "summary",
        "source",
        "article_url",
        "category",
        "related",
    }
)
_SUPPORTED_COLUMNS = _REQUIRED_COLUMNS | _OPTIONAL_COLUMNS
_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+\Z")


class NewsCSVError(ValueError):
    """Raised when a news CSV cannot be read or contains invalid records."""


def load_news_csv(file_path: str | Path) -> list[NewsArticle]:
    """Read a UTF-8 news CSV and return normalized articles in row order.

    Duplicate rows are preserved; the adapter does not infer article identity
    or silently discard records.
    """
    path = Path(file_path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            try:
                headers = next(reader)
            except StopIteration:
                raise NewsCSVError(f"{path}: CSV is empty and has no header row.") from None

            _validate_headers(headers, path)
            articles: list[NewsArticle] = []
            for record_number, values in enumerate(reader, start=2):
                if len(values) != len(headers):
                    raise NewsCSVError(
                        f"{path}: CSV record {record_number} has {len(values)} "
                        f"fields; expected {len(headers)}."
                    )
                row = dict(zip(headers, values, strict=True))
                articles.append(_normalize_row(row, path, record_number))
            return articles
    except FileNotFoundError as error:
        raise NewsCSVError(f"{path}: CSV file was not found.") from error
    except PermissionError as error:
        raise NewsCSVError(f"{path}: permission denied while reading CSV file.") from error
    except UnicodeDecodeError as error:
        raise NewsCSVError(f"{path}: file is not valid UTF-8 text.") from error
    except csv.Error as error:
        raise NewsCSVError(f"{path}: malformed CSV input: {error}") from error
    except OSError as error:
        raise NewsCSVError(f"{path}: unable to read CSV file: {error}") from error


def _validate_headers(headers: list[str], path: Path) -> None:
    if any(not header.strip() for header in headers):
        raise NewsCSVError(f"{path}: CSV headers must not be blank.")
    if len(headers) != len(set(headers)):
        raise NewsCSVError(f"{path}: CSV contains duplicate column names.")

    missing = sorted(_REQUIRED_COLUMNS - set(headers))
    if missing:
        raise NewsCSVError(
            f"{path}: missing required CSV column(s): {', '.join(missing)}."
        )

    unsupported = sorted(set(headers) - _SUPPORTED_COLUMNS)
    if unsupported:
        raise NewsCSVError(
            f"{path}: unsupported CSV column(s): {', '.join(unsupported)}."
        )


def _normalize_row(row: dict[str, str], path: Path, record_number: int) -> NewsArticle:
    context = f"{path}: CSV record {record_number}"
    ticker = row["ticker"]
    headline = row["headline"]
    timestamp_text = row["published_at"].strip()

    try:
        normalized_ticker = validate_ticker(ticker)
        if not headline.strip():
            raise ValueError("headline is required and must not be blank")
        if not timestamp_text:
            raise ValueError("published_at is required and must not be blank")

        try:
            parsed_timestamp = datetime.fromisoformat(timestamp_text)
        except ValueError:
            raise ValueError(
                "published_at must be a valid ISO 8601 timestamp with an explicit "
                "timezone offset"
            ) from None
        if parsed_timestamp.utcoffset() is None:
            raise ValueError(
                "published_at must include a timezone offset; naive timestamps "
                "are not accepted"
            )
        published_at, published_timestamp = normalize_published_at(parsed_timestamp)

        article_id = _optional_integer(row, "provider_article_id")
    except ValueError as error:
        raise NewsCSVError(f"{context}: {error}.") from error

    return NewsArticle(
        ticker=normalized_ticker,
        headline=headline,
        published_at=published_at,
        published_timestamp=published_timestamp,
        provider_article_id=article_id,
        summary=_optional_text(row, "summary"),
        source=_optional_text(row, "source"),
        article_url=_optional_text(row, "article_url"),
        category=_optional_text(row, "category"),
        related=_optional_text(row, "related"),
    )


def _optional_integer(row: dict[str, str], field: str) -> int | None:
    value = row.get(field, "").strip()
    if not value:
        return None
    if not _INTEGER_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a whole-number integer or blank")
    return int(value)


def _optional_text(row: dict[str, str], field: str) -> str | None:
    value = row.get(field, "")
    return value if value.strip() else None
