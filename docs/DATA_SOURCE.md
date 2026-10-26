# Financial News Sentiment Analyzer — Data Source and Data Requirements

## 1. Purpose

This document records the planned data sources, required fields, data-quality expectations, and constraints for the Financial News Sentiment Analyzer.

## 2. Financial News Source

Selected primary news provider: Finnhub.

Official website: https://finnhub.io/

Documentation: https://finnhub.io/docs/api/company-news

Official OpenAPI specification: https://finnhub.io/static/swagger.json

The official specification was checked on 2026-10-26. It documents the
`GET /api/v1/company-news` endpoint, required query parameters `symbol`,
`from`, and `to`, and API-key authentication through the `token` query
parameter. The documented response is an array with `category`, `datetime`
(Unix seconds), `headline`, `id`, `related`, `source`, `summary`, and `url`
fields. The implementation sends the requested dates as `YYYY-MM-DD` and does
not retry requests.

`financial_news_sentiment.news.finnhub.FinnhubNewsClient` uses the existing
`FINNHUB_API_KEY` configuration. Its timeout is 10 seconds. HTTP authentication
failures (401/403), rate limiting (429), other HTTP/network failures, and
invalid or malformed responses raise distinct provider exceptions; the token
and token-bearing request URL are not included in those error messages.

The normalized `NewsArticle` requires a non-empty headline and integer Unix
publication timestamp. A missing or malformed required field rejects the
response rather than inventing data or silently dropping an article. The
provider article ID, summary, source, URL, category, and related-symbol text
are optional and remain `None` when omitted. Publication timestamps are
preserved as integer seconds and converted to timezone-aware UTC datetimes.
Ticker is the normalized requested symbol.

The client passes both caller-supplied dates directly as `from` and `to`;
inclusive date-range semantics are the caller contract, but Finnhub's
documentation does not specify boundary inclusivity. A one-time live request
confirmed access for the configured account, ticker, and date range shown
below; it did not verify exact date-boundary behavior, ongoing entitlement,
quotas, retention rights, or terms of use.

### Company-News Manual Smoke Test

One controlled live request was made with the key in the ignored project
`.env`:

| Test detail | Result |
|---|---|
| Run date | 2026-10-26 |
| Script | [`scripts/smoke_test_finnhub_news.py`](../scripts/smoke_test_finnhub_news.py) |
| Ticker and dates | `AAPL`, `2026-10-20` through `2026-10-26` |
| Outcome | Passed; HTTP `200`, 239 articles returned |

To repeat the check manually with one chosen ticker/date range, run from the
repository root:

```powershell
uv run python scripts/smoke_test_finnhub_news.py AAPL 2026-10-20 2026-10-26
```

The script prints the HTTP status, record count, and up to three sanitized
publication-time/source/category/headline samples. An empty response is
reported separately as a successful request with zero articles. It never
prints the API key or request URL. Automated tests mock HTTP and do not make
live requests.

### Finnhub Exchange-Symbol Smoke Test

| Test detail | Result |
|---|---|
| Run date | 2026-10-26 |
| Script | [`scripts/test_finnhub_exchange.py`](../scripts/test_finnhub_exchange.py) |
| Endpoint | `GET /api/v1/stock/symbol` |
| Exchange parameter | `US` |
| Outcome | Passed; HTTP `200`, `31,122` records returned, and the script completed successfully |

The script printed these first three records:

| Symbol | Description | Type | Currency |
|---|---|---|---|
| `NGIF` | NUVEEN GLOBAL INFRA FUND/ETF | ETP | USD |
| `CABGY` | CARLSBERG A-B-SPON ADR | ADR | USD |
| `HNWAF` | HANWA CO LTD | Common Stock | USD |

This is a live, point-in-time smoke-test result, not a fixed expected count or a verified Nasdaq ticker universe. It confirms that, during this run, the configured credential could make this symbol-list request for exchange code `US` and receive a JSON list. The sample includes different security types, and the script does not inspect or verify each record's listing venue. The `US` parameter must not be interpreted as proof that every returned symbol is Nasdaq-listed.

**What this test does not verify:** Company News account access or actual response behavior; historical price/candle access; Nasdaq-only instrument coverage; date-boundary behavior; free-tier quotas or terms, attribution, retention, or classroom-use permissions. Do not use this result alone to approve Finnhub market-data integration. Those checks remain part of the verification gates in [research.md](../specs/financial-news-sentiment/research.md#finnhub-news-verification-gate).

To repeat the check from the repository root, configure `FINNHUB_API_KEY` and `FINNHUB_EXCHANGE_CODE` in the ignored local `.env` file, then run:

```powershell
uv run python scripts/test_finnhub_exchange.py
```

The script does not print the API key or request URL. Keep credentials out of command history, logs, and tracked files.

The project retains the `finnhub-python` dependency and its prior interface check, but this news adapter uses the already-declared `requests` library to keep provider HTTP handling explicit and isolated. The SDK's candle support does not establish that historical daily prices are available under the project's account or permitted terms. Keep CSV as the offline path.

The API documentation confirms the request and response schema, but not the project's account entitlement, date inclusivity, quotas, or licensing. Do not treat live news or market retrieval as confirmed until the manual access check and applicable verification gates are completed.

## 3. Required News Fields

| Logical field | Purpose | Handling |
|---|---|---|
| ticker | Company being analyzed | Required; set from the requested symbol |
| headline | Text for headline sentiment | Required; unusable articles are rejected |
| summary | Additional article text | Optional; score only when non-empty |
| published_at | Publication date and time | Required; converted from Unix seconds to UTC |
| source | News publisher | Optional |
| article_url | Link to the article | Optional, subject to provider response |
| provider_article_id | Article identifier | Optional; useful for deduplication |

These are logical application fields. The implementation shall map the provider's actual response fields to this internal schema.

## 4. Stock-Price Data

A suitable stock-price source must be selected and verified before implementing the price comparison feature. Nasdaq is the only supported exchange in MVP.

Required logical fields:

- ticker
- timestamp or trading date
- close (required for MVP)
- open, high, low, if available
- volume, if available
- adjusted close, if available and appropriate

The selected provider, endpoint, data coverage, and applicable usage restrictions shall be documented once verified. Only ticker, Nasdaq trading date, and closing price are required for MVP comparison.

### Comparison Interval and Alignment

The target design is market-session-based alignment using the Nasdaq calendar and America/New_York timezone. Assign timestamps in (previous session close, current session close] to that session; after-close, weekend, and holiday news goes to the next eligible session. At planning, calendar-day aggregation may be selected only if the estimate shows session alignment threatens another mandatory MVP deliverable by the capstone deadline; record the reason and selected mode. Missing observations shall not be silently imputed. Daily return is `((current close - previous Nasdaq session close) / previous Nasdaq session close) * 100`.

## 5. Data Processing Rules

1. Validate that records contain usable headline text and publication timestamps.
2. Handle missing summaries without treating them as neutral sentiment.
3. Normalize publication timestamps and document the time zone used.
4. Remove duplicate articles where a reliable identifier or deduplication rule is available.
5. Preserve original article text for auditability, subject to provider terms.
6. Record retrieval failures and malformed records.
7. Use consistent aggregation intervals when comparing sentiment and market data.
8. Do not silently substitute missing values with zero sentiment.

## 6. Demo Data

Local CSV datasets are required for automated tests, classroom demonstrations, and fallback when live news access is unavailable. The core CSV workflow shall run without network access.

Sample data shall not be represented as live financial news or market observations.

The source or creation method, permitted use, and limitations of each sample dataset shall be recorded. Synthetic samples shall be explicitly labeled synthetic.

## 7. Data Validation

Before using a dataset for analysis, verify:

- Record count and date range.
- Missing-value counts for key fields.
- Duplicate records.
- Timestamp validity.
- Distribution of sentiment labels.
- Coverage of stock-price data over the chosen period.

## 8. Data Limitations

News coverage and publication times may vary between providers. Market data may have missing trading days or different adjustment conventions.

These limitations shall be considered when interpreting sentiment trends and price comparisons.

Status: The Company News request/response schema and one live AAPL request are verified. Date-boundary behavior, ongoing account entitlement, usage terms, and the market-data provider remain unverified.