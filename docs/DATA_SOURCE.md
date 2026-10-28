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
documentation does not specify boundary inclusivity. Exact `from`/`to`
boundary inclusivity remains unverified, and request semantics are not changed
based on an assumption. A successful live request confirmed access for the
tested account, ticker, and date range shown below at the time of the check
only. It does not establish ongoing entitlement, quotas or rate limits,
retention rights, or permitted usage terms.

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

### Real-News Evaluation Permissions Review: 2026-10-28

The current [Finnhub Terms of Service](https://finnhub.io/terms-of-service)
were reviewed on 2026-10-28. The page says that site use does not grant
ownership or an intellectual-property license in data (including third-party
content), that data must be deleted if the subscription ends, and that data
or derived results must not be redistributed/shared without Finnhub's written
approval. It also says listed plans are for personal use unless explicitly
stated otherwise. These terms do **not** establish permission for this
project's particular private research, local retention, storage of publisher
headlines/summaries, use in evaluation outputs, or publication.

The terms link to UTP plan data policies
(https://www.utpplan.com/DOC/datapolicies.pdf) and a subscriber agreement
(https://www.utpplan.com/DOC/subagreement.pdf). Those PDF links could not be
retrieved for review in this check. Account-specific plan terms, written
approval, attribution requirements, permitted retention duration, and
publisher/source copyright and redistribution rights remain unresolved. The
prior account access smoke test is not a license grant.

**Decision:** real-news collection and storage are not cleared and have not
been started for this dataset milestone. Do not use Finnhub or another source
to populate evaluation files until the applicable account terms and source
rights have been checked, documented, and explicit written approval obtained
where required. No collection has occurred. The collector is invoked only by
an explicit command and is permission-gated. Keep display and redistribution
rights separately documented even when internal evaluation is authorized.
This project has not determined legal permission.

The evaluation-preparation CLI now includes an explicit one-request
`collect-finnhub` command and a permission-gated `import-csv` command. Neither
runs by default. Collection checks the linked review before constructing the
Finnhub client/request, makes one request for the caller-specified ticker and
date range, records UTC collection time and dataset provenance, and emits
duplicate exclusions without headline text. Provider article IDs and source
URLs are retained only when their separate permission-review fields are
`allowed`. This workflow has not been used to collect news; an API request
success would still not prove permission.

## 3. Required News Fields

| Logical field | Purpose | Handling |
|---|---|---|
| ticker | Company being analyzed | Required; set from the requested symbol |
| headline | Text for headline sentiment | Required; unusable articles are rejected |
| summary | Additional article text | Optional; retained unchanged and scored independently when non-empty; missing or blank summaries are unavailable |
| published_at | Publication date and time | Required; converted from Unix seconds to UTC |
| source | News publisher | Optional |
| article_url | Link to the article | Optional, subject to provider response |
| provider_article_id | Article identifier | Optional; useful for deduplication |
| source_name | Publisher returned by the provider | Optional; distinct from the provider used for retrieval |

These are logical application fields. The implementation shall map the
provider's actual response fields to this internal schema.

### Offline News CSV Format

`financial_news_sentiment.news.csv_adapter.load_news_csv(file_path)` reads a
local CSV without network access, Finnhub credentials, or extra dependencies.
It returns the same `list[NewsArticle]` model used by the Finnhub client.
`data/samples/synthetic_news_articles.csv` is a synthetic test/demo fixture,
not real financial news or a Finnhub response.

CSV files must be UTF-8 (an optional UTF-8 BOM is accepted) with one header row.
Column names are exact; unsupported or duplicate headers are rejected.

| CSV column | Model field | Required | Mapping and validation |
|---|---|---:|---|
| `ticker` | `ticker` | Yes | Validated with the same ticker rules as Finnhub and uppercased |
| `headline` | `headline` | Yes | Must contain non-whitespace text; original text is retained |
| `published_at` | `published_at`, `published_timestamp` | Yes | ISO 8601 timestamp with `Z` or explicit UTC offset; normalized to UTC and integer Unix seconds |
| `provider_article_id` | `provider_article_id` | No | Blank becomes `None`; otherwise a whole-number integer |
| `summary` | `summary` | No | Blank or whitespace-only becomes `None` |
| `source` | `source` | No | Blank or whitespace-only becomes `None` |
| `article_url` | `article_url` | No | Blank or whitespace-only becomes `None` |
| `category` | `category` | No | Blank or whitespace-only becomes `None` |
| `related` | `related` | No | Blank or whitespace-only becomes `None` |

The only required columns are `ticker`, `headline`, and `published_at`.
Optional columns may be omitted entirely. Optional empty cells are represented
as `None`; the adapter does not invent IDs, summaries, sources, URLs, or
categories. Naive timestamps are rejected because no source timezone is
configured; callers must supply an explicit offset rather than relying on the
machine timezone. An empty dataset is valid when the required header row is
present and there are no data rows.

Every valid row is retained in source order, including exact repeated rows or
rows with the same article ID. The CSV adapter does not deduplicate: identity
and provider scope cannot be safely inferred from this schema alone. Any
invalid row rejects the file with its record number; malformed CSV, unreadable
or non-UTF-8 files, missing/unsupported columns, and malformed timestamps
raise `NewsCSVError` with an actionable message. No partial result is returned.

Run the offline ingestion tests from the repository root:

```powershell
uv run pytest tests/unit/test_csv_news.py
```

Minimal offline example:

```python
from pathlib import Path

from financial_news_sentiment.news.csv_adapter import load_news_csv

articles = load_news_csv(Path("data/samples/synthetic_news_articles.csv"))
for article in articles:
    print(article.ticker, article.published_at.isoformat(), article.headline)
```

The provided records are explicitly synthetic, use illustrative headlines and
reserved `.invalid` URLs, and must not be presented as actual Finnhub output.

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
4. Apply only a source-specific documented deduplication rule; the offline news CSV adapter preserves all rows.
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