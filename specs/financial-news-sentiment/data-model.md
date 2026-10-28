# Data Model: Financial News Sentiment Analyzer

These are logical records and invariants. Provider-specific fields must be verified and mapped at source boundaries. `NewsArticle` and the baseline sentiment result types are implemented; future request, market, session, and comparison records remain planned.

## AnalysisRequest

- `ticker`: non-empty symbol accepted by the selected source.
- `start_date`, `end_date`: inclusive selected dates; start must not exceed end.
- `news_source`: local CSV or verified live source.
- `news_path`, `market_path`: required for the corresponding CSV sources.
- `alignment_mode`: `nasdaq_session` for the selected MVP; calendar-day fallback is not active.
- `timestamp_timezone`: explicit source timezone for naive CSV timestamps.

Invalid requests are rejected; ticker, date range, and mode are never silently substituted.

## NewsArticle

| Field | Constraint | Required |
|---|---|---:|
| `ticker` | Matches requested analysis scope | Yes |
| `headline` | Non-empty after trimming | Yes |
| `published_at` | Timezone-aware after explicit normalization | Yes |
| `summary` | Text or unavailable | No |
| `source` | Publisher/source or unavailable | No |
| `article_url` | URL or unavailable | No |
| `provider_article_id` | Provider-scoped ID or unavailable | No |
| `source_kind` | Live, local, or sample provenance | Yes in result metadata |

Missing summary does not prevent headline analysis. Invalid required fields exclude the record and increment a quality count. Retention of original text is subject to verified source terms.

## ValidationReport

Input, accepted, rejected, duplicate, and unidentifiable-record counts; rejection reasons; duplicate key type; and source/date coverage. Avoid logging secrets or unnecessary raw payloads.

## Baseline Sentiment Results

`SentimentResult` preserves its existing headline fields: the unchanged article,
compound score, label, analyzer name/version, and optional `article_id`
property. It now also has an optional `summary_result` field, populated by the
baseline analyzer. `SummarySentimentResult` references the same article and
has a status, optional compound score, optional label, analyzer name/version,
and optional `article_id` property.

- Headline score is finite and in `[-1, 1]`; its label is Negative for scores
  `<= -0.05`, Positive for scores `>= 0.05`, and Neutral otherwise.
- A non-empty summary is scored independently with the same method and
  thresholds and has `status="available"`.
- A null, empty, or whitespace-only summary has `status="unavailable"`, with
  no score and no label; it is not Neutral.
- Headline and summary text are never concatenated and scores are never
  substituted across fields.

## SentimentAggregate

Headline and summary aggregates are calculated separately using
`summarize_sentiment` and `summarize_summary_sentiment`. Each reports the
available-result count, mean compound score, positive/negative/neutral counts,
and their percentages. Percentages use the available-result count as the
denominator, are rounded independently to two decimal places, and may have a
small rounding difference from 100%. Unavailable summaries are excluded from
summary counts, percentages, and average. Empty groups have zero counts and
percentages and no average score; missing data is not assigned zero or Neutral.

## MarketObservation

- `ticker` and `trading_date` (Nasdaq session date).
- `close`: finite positive value with documented currency and raw/adjusted convention.
- `source_kind`: live provider or local/sample CSV.

Price convention must be consistent within a comparison. Invalid/missing keys or close values are rejected. Missing sessions remain missing.

## SessionAssignment

Contains normalized `published_at`, `session_date`, actual timezone-aware `session_close`, and an assignment status. For consecutive Nasdaq sessions, an instant strictly after the previous close and at or before the current close belongs to the current session. After-close, weekend, and holiday events map to the next eligible session. Use actual early closes and `America/New_York` DST rules.

## ComparisonObservation

One ticker/session record with session date, headline and summary mean scores/counts separately, current and immediately previous Nasdaq-session closes, close-to-close return when computable, and match/coverage status.

Return is `((current_close - previous_session_close) / previous_session_close) * 100`. If either close is missing, return is unavailable. Never substitute a non-consecutive prior observation. Comparison charts use matched available values and disclose exclusions.

## AnalysisResult

Contains request scope; source and live/sample status; method and thresholds; validation report; article-level scores; separate aggregates; market coverage; comparison values; alignment and price convention; and limitations/errors. Distinguish empty data, partial retrieval, and failure.

## Relationships and Invariants

Flow: request -> CSV/verified source -> normalized records -> validation/deduplication -> independent headline/summary scores -> separate aggregates -> Nasdaq session assignment -> market returns -> matched comparisons -> chart/result metadata.

1. Missing summaries are unavailable, not Neutral, and do not contribute to summary aggregate denominators.
2. Reliable duplicate identities contribute once; unidentifiable records are not silently merged.
3. Invalid requests are never changed silently.
4. Headline and summary statistics stay separate.
5. Empty intervals are not assigned zero sentiment.
6. Missing closes/returns/matches are never imputed or forward-filled.
7. Failed or partial retrieval is never labeled complete.
8. Live, local, and sample data are distinguished.
9. Optional LLM output is outside baseline records and aggregates.
