from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import Mock

import pytest
import requests

from financial_news_sentiment.news.finnhub import (
    FinnhubAuthenticationError,
    FinnhubNewsClient,
    FinnhubRateLimitError,
    FinnhubRequestError,
    FinnhubResponseError,
)

_API_KEY = "test-api-key"
_START_DATE = date(2024, 1, 1)
_END_DATE = date(2024, 1, 2)
_ARTICLE = {
    "id": 123,
    "datetime": 1704067200,
    "headline": "Company reports quarterly results",
    "summary": "Revenue increased.",
    "source": "Example News",
    "url": "https://example.test/article",
    "category": "company",
    "related": "AAPL,MSFT",
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> FinnhubNewsClient:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.get_finnhub_api_key",
        lambda: _API_KEY,
    )
    return FinnhubNewsClient()


def _response(payload: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_valid_response_is_normalized_and_request_is_bounded(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    get = Mock(return_value=_response([_ARTICLE]))
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", get)

    articles = client.get_company_news("aapl", _START_DATE, _END_DATE)

    assert len(articles) == 1
    article = articles[0]
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
    get.assert_called_once_with(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": "AAPL",
            "from": "2024-01-01",
            "to": "2024-01-02",
            "token": _API_KEY,
        },
        timeout=10,
        allow_redirects=False,
    )


def test_empty_response_is_a_valid_empty_result(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    get = Mock(return_value=_response([]))
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", get)

    assert client.get_company_news("AAPL", _START_DATE, _END_DATE) == []
    get.assert_called_once()


def test_missing_api_key_fails_before_network_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get = Mock()
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.get_finnhub_api_key",
        Mock(side_effect=RuntimeError("Set FINNHUB_API_KEY")),
    )
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", get)

    with pytest.raises(RuntimeError, match="FINNHUB_API_KEY"):
        FinnhubNewsClient().get_company_news("AAPL", _START_DATE, _END_DATE)

    get.assert_not_called()


@pytest.mark.parametrize(
    "ticker",
    ["", "AAPL/BRK", "AAPL$", ".AAPL", "VERY-LONG-TICKER-NAME-123"],
)
def test_invalid_ticker_is_rejected_before_request(
    client: FinnhubNewsClient,
    monkeypatch: pytest.MonkeyPatch,
    ticker: str,
) -> None:
    get = Mock()
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", get)

    with pytest.raises(ValueError, match="ticker"):
        client.get_company_news(ticker, _START_DATE, _END_DATE)

    get.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date", "exception_type"),
    [
        (date(2024, 1, 2), date(2024, 1, 1), ValueError),
        ("2024-01-01", date(2024, 1, 2), TypeError),
        (datetime(2024, 1, 1), date(2024, 1, 2), TypeError),
    ],
)
def test_invalid_date_range_is_rejected_before_request(
    client: FinnhubNewsClient,
    monkeypatch: pytest.MonkeyPatch,
    start_date: date | str | datetime,
    end_date: date,
    exception_type: type[ValueError | TypeError],
) -> None:
    get = Mock()
    monkeypatch.setattr("financial_news_sentiment.news.finnhub.requests.get", get)

    with pytest.raises(exception_type):
        client.get_company_news("AAPL", start_date, end_date)  # type: ignore[arg-type]

    get.assert_not_called()


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_errors_do_not_expose_token_or_url(
    client: FinnhubNewsClient,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response(None, status_code)),
    )

    with pytest.raises(FinnhubAuthenticationError) as error:
        client.get_company_news("AAPL", _START_DATE, _END_DATE)

    assert str(status_code) in str(error.value)
    assert _API_KEY not in str(error.value)
    assert "https://" not in str(error.value)
    assert error.value.status_code == status_code


def test_rate_limit_response_is_distinct(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response(None, 429)),
    )

    with pytest.raises(FinnhubRateLimitError, match="429"):
        client.get_company_news("AAPL", _START_DATE, _END_DATE)


def test_server_error_is_reported_without_response_body(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response({"error": _API_KEY}, 500)),
    )

    with pytest.raises(FinnhubRequestError, match="500") as error:
        client.get_company_news("AAPL", _START_DATE, _END_DATE)

    assert _API_KEY not in str(error.value)
    assert error.value.status_code == 500


def test_network_error_is_reported_without_request_details(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(side_effect=requests.ConnectionError(f"failed with {_API_KEY}")),
    )

    with pytest.raises(FinnhubRequestError, match="network or transport") as error:
        client.get_company_news("AAPL", _START_DATE, _END_DATE)

    assert _API_KEY not in str(error.value)


def test_invalid_json_is_reported(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = _response(None)
    response.json.side_effect = ValueError("invalid JSON")
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=response),
    )

    with pytest.raises(FinnhubResponseError, match="invalid JSON") as error:
        client.get_company_news("AAPL", _START_DATE, _END_DATE)

    assert error.value.status_code == 200

@pytest.mark.parametrize("payload", [{"error": "invalid"}, [None]])
def test_unexpected_response_shapes_are_rejected(
    client: FinnhubNewsClient,
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response(payload)),
    )

    with pytest.raises(FinnhubResponseError):
        client.get_company_news("AAPL", _START_DATE, _END_DATE)


def test_missing_optional_fields_are_not_invented(
    client: FinnhubNewsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response([{"headline": "A headline", "datetime": 0}])),
    )

    article = client.get_company_news("AAPL", _START_DATE, _END_DATE)[0]

    assert article.provider_article_id is None
    assert article.summary is None
    assert article.source is None
    assert article.article_url is None
    assert article.category is None
    assert article.related is None


@pytest.mark.parametrize(
    ("article", "message"),
    [
        ({"datetime": 0}, "headline"),
        ({"headline": "A headline"}, "timestamp"),
    ],
)
def test_missing_required_article_fields_are_rejected(
    client: FinnhubNewsClient,
    monkeypatch: pytest.MonkeyPatch,
    article: dict[str, object],
    message: str,
) -> None:
    monkeypatch.setattr(
        "financial_news_sentiment.news.finnhub.requests.get",
        Mock(return_value=_response([article])),
    )

    with pytest.raises(FinnhubResponseError, match=message):
        client.get_company_news("AAPL", _START_DATE, _END_DATE)
