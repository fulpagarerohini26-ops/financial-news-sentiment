"""Make one manually controlled Finnhub company-news request."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date

from financial_news_sentiment.news.finnhub import (
    FinnhubNewsClient,
    FinnhubNewsError,
)


def _date_argument(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format")
    return parsed


def _safe_text(value: str, max_length: int = 160) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", value)[:max_length]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch one company's Finnhub news for a date range."
    )
    parser.add_argument("ticker", help="company ticker, for example AAPL")
    parser.add_argument("start_date", type=_date_argument, help="inclusive YYYY-MM-DD")
    parser.add_argument("end_date", type=_date_argument, help="inclusive YYYY-MM-DD")
    args = parser.parse_args()

    try:
        articles = FinnhubNewsClient().get_company_news(
            args.ticker, args.start_date, args.end_date
        )
    except FinnhubNewsError as error:
        status_code = getattr(error, "status_code", None)
        print(f"HTTP status: {status_code if status_code is not None else 'unavailable'}")
        print(f"Finnhub request failed: {error}", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as error:
        print("HTTP status: unavailable")
        print(f"Finnhub request failed: {error}", file=sys.stderr)
        return 1

    print("HTTP status: 200")
    print(f"Records returned: {len(articles)}")
    if not articles:
        print("The request succeeded, but Finnhub returned no articles.")
        return 0

    print("Sample articles (sanitized fields):")
    for article in articles[:3]:
        print(
            f"- {article.published_at.isoformat()} | "
            f"{_safe_text(article.source or 'Unknown source', 80)} | "
            f"{_safe_text(article.category or 'Uncategorized', 40)} | "
            f"{_safe_text(article.headline)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
