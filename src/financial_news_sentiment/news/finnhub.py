"""Finnhub company-news HTTP adapter."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

import requests

from financial_news_sentiment.news.models import NewsArticle
from financial_news_sentiment.settings import get_finnhub_api_key

_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
_REQUEST_TIMEOUT_SECONDS = 10
_TICKER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,19}\Z")


class FinnhubNewsError(RuntimeError):
    """Base error for Finnhub company-news retrieval."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FinnhubAuthenticationError(FinnhubNewsError):
    """Finnhub rejected the configured credentials or account access."""


class FinnhubRateLimitError(FinnhubNewsError):
    """Finnhub rate-limited the request."""


class FinnhubRequestError(FinnhubNewsError):
    """The request failed or Finnhub returned an unsuccessful HTTP status."""


class FinnhubResponseError(FinnhubNewsError):
    """Finnhub returned invalid JSON or an invalid article payload."""


class FinnhubNewsClient:
    """Retrieve and normalize company news from Finnhub."""

    def get_company_news(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[NewsArticle]:
        """Return articles for the inclusive date range, or an empty list."""
        normalized_ticker = _validate_ticker(ticker)
        _validate_date_range(start_date, end_date)
        api_key = get_finnhub_api_key()

        try:
            response = requests.get(
                _COMPANY_NEWS_URL,
                params={
                    "symbol": normalized_ticker,
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                    "token": api_key,
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise FinnhubRequestError(
                "Finnhub news request failed due to a network or transport error."
            ) from None

        if response.status_code in (401, 403):
            raise FinnhubAuthenticationError(
                f"Finnhub rejected the request with HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise FinnhubRateLimitError(
                "Finnhub rate-limited the request (HTTP 429).",
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise FinnhubRequestError(
                f"Finnhub returned unsuccessful HTTP status {response.status_code}.",
                status_code=response.status_code,
            )

        try:
            payload: Any = response.json()
        except ValueError:
            raise FinnhubResponseError(
                "Finnhub returned invalid JSON.", status_code=response.status_code
            ) from None

        if not isinstance(payload, list):
            raise FinnhubResponseError(
                "Finnhub company-news response must be a JSON array.",
                status_code=response.status_code,
            )

        try:
            return [
                _normalize_article(item, normalized_ticker, index)
                for index, item in enumerate(payload)
            ]
        except FinnhubResponseError as error:
            raise FinnhubResponseError(
                str(error), status_code=response.status_code
            ) from None


def _validate_ticker(ticker: str) -> str:
    if not isinstance(ticker, str) or not _TICKER_PATTERN.fullmatch(ticker.strip()):
        raise ValueError(
            "ticker must be 1-20 letters, digits, periods, or hyphens and start "
            "with a letter or digit"
        )
    return ticker.strip().upper()


def _validate_date_range(start_date: date, end_date: date) -> None:
    if (
        not isinstance(start_date, date)
        or isinstance(start_date, datetime)
        or not isinstance(end_date, date)
        or isinstance(end_date, datetime)
    ):
        raise TypeError("start_date and end_date must be datetime.date values")
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")


def _normalize_article(item: object, ticker: str, index: int) -> NewsArticle:
    context = f"Finnhub article at index {index}"
    if not isinstance(item, dict):
        raise FinnhubResponseError(f"{context} must be a JSON object.")

    headline = item.get("headline")
    if not isinstance(headline, str) or not headline.strip():
        raise FinnhubResponseError(f"{context} is missing a usable headline.")

    timestamp = item.get("datetime")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise FinnhubResponseError(
            f"{context} is missing an integer Unix publication timestamp."
        )
    try:
        published_at = datetime.fromtimestamp(timestamp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        raise FinnhubResponseError(
            f"{context} has an out-of-range Unix publication timestamp."
        ) from None

    article_id = item.get("id")
    if article_id is not None and (
        not isinstance(article_id, int) or isinstance(article_id, bool)
    ):
        raise FinnhubResponseError(f"{context} has a non-integer article identifier.")

    return NewsArticle(
        ticker=ticker,
        headline=headline,
        published_at=published_at,
        published_timestamp=timestamp,
        provider_article_id=article_id,
        summary=_optional_text(item, "summary", context),
        source=_optional_text(item, "source", context),
        article_url=_optional_text(item, "url", context),
        category=_optional_text(item, "category", context),
        related=_optional_text(item, "related", context),
    )


def _optional_text(item: dict[str, Any], field: str, context: str) -> str | None:
    value = item.get(field)
    if value is not None and not isinstance(value, str):
        raise FinnhubResponseError(f"{context} has a non-text {field} field.")
    return value
