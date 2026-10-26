# Financial News Sentiment Analyzer — Data Source and Data Requirements

## 1. Purpose

This document records the planned data sources, required fields, data-quality expectations, and constraints for the Financial News Sentiment Analyzer.

## 2. Financial News Source

Selected primary news provider: Finnhub, subject to verification before integration.

Official website: https://finnhub.io/

Documentation: https://finnhub.io/docs/api

The application will use the Finnhub Company News API after verifying provider availability, authentication requirements, response fields, usage limits, and terms of service. No unverified capability or free quota is assumed. The API key must be configured locally and must not be committed to the repository.

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

**What this test does not verify:** Company News access or response fields; historical price/candle access; Nasdaq-only instrument coverage; date or timestamp semantics; free-tier quotas or rate limits; terms, attribution, retention, or classroom-use permissions. Do not use this result alone to approve Finnhub news or market-data integration. Those checks remain part of the verification gates in [research.md](../specs/financial-news-sentiment/research.md#finnhub-news-verification-gate).

To repeat the check from the repository root, configure `FINNHUB_API_KEY` and `FINNHUB_EXCHANGE_CODE` in the ignored local `.env` file, then run:

```powershell
uv run python scripts/test_finnhub_exchange.py
```

The script does not print the API key or request URL. Keep credentials out of command history, logs, and tracked files.

The project dependency is `finnhub-python` (locked at 2.4.29). Its client is imported as `finnhub`; `Client(api_key=...)` provides `company_news(symbol, _from, to)`, where `_from` is the Python parameter name for the API's `from` date parameter. The SDK also exposes `stock_candles(...)`, but its presence does not establish that historical daily prices are available under the project's account or permitted terms. See the dated interface check and unresolved verification gate in [research.md](../specs/financial-news-sentiment/research.md#python-sdk-interface-check-2026-10-26).

The SDK interface check verifies how to invoke the client, not Finnhub's current entitlement, response-field semantics, date inclusivity, timestamp timezone, quotas, or licensing. Do not mark live news or market retrieval available until the applicable verification gate is completed. Keep provider objects at the adapter boundary and normalize verified fields to the logical schema below; CSV remains the offline path.

## 3. Required News Fields

| Logical field | Purpose | Handling |
|---|---|---|
| ticker | Company being analyzed | Required for company-level analysis |
| headline | Text for headline sentiment | Required for headline scoring |
| summary | Additional article text | Optional; score only when non-empty |
| published_at | Publication date and time | Required for time-based aggregation |
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

Status: Draft — confirm actual API fields and market-data source during technical planning.