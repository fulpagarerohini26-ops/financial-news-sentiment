"""Provider-independent news article model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NewsArticle:
    """A normalized article with its publication time represented in UTC."""

    ticker: str
    headline: str
    published_at: datetime
    published_timestamp: int
    provider_article_id: int | None = None
    summary: str | None = None
    source: str | None = None
    article_url: str | None = None
    category: str | None = None
    related: str | None = None
