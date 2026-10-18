# Financial News Sentiment Analyzer — Data Source and Data Requirements

## 1. Purpose

This document records the planned data sources, required fields, data-quality expectations, and constraints for the Financial News Sentiment Analyzer.

## 2. Financial News Source

Planned and Selected provider: Finnhub

Official website: https://finnhub.io/

Documentation: https://finnhub.io/docs/api

The application will use an appropriate company-specific news endpoint, subject to verification of provider availability, authentication requirements, usage limits, and terms of service. The generated API key must be configured locally and must not be committed to the repository.

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

A suitable stock-price source must be selected and verified before implementing the price comparison feature.

Required logical fields:

- ticker
- timestamp or trading date
- open, high, low, close, if available
- volume, if available
- adjusted close, if available and appropriate

The selected provider, endpoint, data coverage, and applicable usage restrictions shall be documented once verified.

### Comparison Interval and Alignment

The target design is market-session-based alignment of news sentiment with stock-price observations. Daily aggregation is the fallback if reliable session-level alignment cannot be supported by the verified data. The market calendar, timezone, handling of news outside trading hours, and price-movement measure remain to be specified before implementation. Missing observations shall not be silently imputed.

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

If a live API is unavailable, the application may use a clearly identified sample dataset for demonstrations and tests.

Sample data shall not be represented as live financial news.

The source, creation method, and any limitations of the sample data shall be recorded.

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