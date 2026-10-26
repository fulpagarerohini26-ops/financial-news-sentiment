from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from financial_news_sentiment.news.csv_adapter import NewsCSVError, load_news_csv
from financial_news_sentiment.news.finnhub import FinnhubNewsClient
from financial_news_sentiment.news.models import NewsArticle

_FIELDS = [
    "provider_article_id",
    "ticker",
    "headline",
    "published_at",
    "summary",
    "source",
    "article_url",
    "category",
    "related",
]


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fields: list[str] | None = None,
    encoding: str = "utf-8",
) -> None:
    with path.open("w", encoding=encoding, newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or _FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "provider_article_id": "123",
        "ticker": "aapl",
        "headline": "Company reports quarterly results",
        "published_at": "2024-01-01T05:30:00+05:30",
        "summary": "Revenue increased.",
        "source": "Example News",
        "article_url": "https://example.test/article",
        "category": "company",
        "related": "AAPL,MSFT",
    }
    row.update(overrides)
    return row


def test_valid_csv_maps_all_fields_and_normalizes_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "news.csv"
    _write_csv(path, [_row()])

    articles = load_news_csv(path)

    assert len(articles) == 1
    article = articles[0]
    assert isinstance(article, NewsArticle)
    assert article.ticker == "AAPL"
    assert article.provider_article_id == 123
    assert article.headline == "Company reports quarterly results"
    assert article.summary == "Revenue increased."
    assert article.published_at == datetime(2024, 1, 1, tzinfo=UTC)
    assert article.published_at.tzinfo is UTC
    assert article.published_timestamp == 1704067200
    assert article.source == "Example News"
    assert article.article_url == "https://example.test/article"
    assert article.category == "company"
    assert article.related == "AAPL,MSFT"


def test_csv_output_matches_finnhub_article_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "news.csv"
    _write_csv(path, [_row(published_at="2024-01-01T00:00:00Z")])
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.get_finnhub_api_key",
        lambda: "test-api-key",
    )
    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {
            "id": 123,
            "datetime": 1704067200,
            "headline": "Company reports quarterly results",
            "summary": "Revenue increased.",
            "source": "Example News",
            "url": "https://example.test/article",
            "category": "company",
            "related": "AAPL,MSFT",
        }
    ]
    request = Mock(return_value=response)
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", request)

    csv_article = load_news_csv(path)[0]
    finnhub_article = FinnhubNewsClient().get_company_news(
        "AAPL", date(2024, 1, 1), date(2024, 1, 2)
    )[0]

    assert type(csv_article) is type(finnhub_article) is NewsArticle
    assert csv_article == finnhub_article
    request.assert_called_once()


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "with-bom.csv"
    _write_csv(path, [_row()], encoding="utf-8-sig")

    assert load_news_csv(path)[0].ticker == "AAPL"


def test_missing_optional_columns_and_blank_values_remain_none(tmp_path: Path) -> None:
    path = tmp_path / "optional.csv"
    fields = ["ticker", "headline", "published_at"]
    _write_csv(
        path,
        [
            {
                "ticker": "MSFT",
                "headline": "A sample headline",
                "published_at": "2024-01-01T00:00:00Z",
            }
        ],
        fields=fields,
    )

    article = load_news_csv(path)[0]

    assert article.provider_article_id is None
    assert article.summary is None
    assert article.source is None
    assert article.article_url is None
    assert article.category is None
    assert article.related is None


def test_blank_optional_cells_remain_none(tmp_path: Path) -> None:
    path = tmp_path / "blank-optional.csv"
    row = _row(
        provider_article_id="",
        summary=" ",
        source="",
        article_url="",
        category="",
        related="",
    )
    _write_csv(path, [row])

    article = load_news_csv(path)[0]

    assert article.provider_article_id is None
    assert article.summary is None
    assert article.source is None
    assert article.article_url is None
    assert article.category is None
    assert article.related is None


def test_empty_csv_with_required_headers_returns_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    _write_csv(path, [], fields=["ticker", "headline", "published_at"])

    assert load_news_csv(path) == []


def test_missing_file_has_actionable_error(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"

    with pytest.raises(NewsCSVError, match="was not found"):
        load_news_csv(path)


def test_missing_required_columns_are_reported(tmp_path: Path) -> None:
    path = tmp_path / "missing-column.csv"
    _write_csv(path, [], fields=["ticker", "headline"])

    with pytest.raises(NewsCSVError, match="published_at"):
        load_news_csv(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("ticker", "", "ticker"),
        ("ticker", "AAPL/$", "ticker"),
        ("headline", "   ", "headline"),
        ("published_at", "", "published_at"),
        ("provider_article_id", "12.5", "whole-number integer"),
        ("provider_article_id", "12_3", "whole-number integer"),
    ],
)
def test_invalid_required_or_provided_fields_are_rejected(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    path = tmp_path / "invalid.csv"
    _write_csv(path, [_row(**{field: value})])

    with pytest.raises(NewsCSVError, match=message):
        load_news_csv(path)


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("not-a-timestamp", "valid ISO 8601"),
        ("2024-01-01T00:00:00", "naive timestamps are not accepted"),
    ],
)
def test_malformed_or_naive_timestamps_are_rejected(
    tmp_path: Path, timestamp: str, message: str
) -> None:
    path = tmp_path / "bad-timestamp.csv"
    _write_csv(path, [_row(published_at=timestamp)])

    with pytest.raises(NewsCSVError, match=message):
        load_news_csv(path)


def test_malformed_csv_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "malformed.csv"
    path.write_text(
        'ticker,headline,published_at\nAAPL,"unterminated,2024-01-01T00:00:00Z\n',
        encoding="utf-8",
    )

    with pytest.raises(NewsCSVError, match="malformed CSV"):
        load_news_csv(path)


def test_non_utf8_file_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "not-utf8.csv"
    path.write_bytes(b"ticker,headline,published_at\nAAPL,\xff,2024-01-01T00:00:00Z\n")

    with pytest.raises(NewsCSVError, match="not valid UTF-8"):
        load_news_csv(path)


def test_duplicate_records_are_preserved_in_input_order(tmp_path: Path) -> None:
    path = tmp_path / "duplicates.csv"
    duplicate = _row()
    _write_csv(path, [duplicate, duplicate])

    articles = load_news_csv(path)

    assert len(articles) == 2
    assert articles[0] == articles[1]
