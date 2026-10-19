# Planned Data Source Contracts

These logical contracts define the planned CSV and provider boundaries. They do not assert that a provider is available or that the application implements these formats today.

## News Records

| Logical field | Required | Meaning |
|---|---:|---|
| `ticker` | Yes | Company ticker, or one explicitly selected ticker for a single-ticker file |
| `headline` | Yes | Non-empty headline text |
| `published_at` | Yes | Timestamp with offset, or paired with explicit CSV timezone setting |
| `summary` | No | Optional summary |
| `source` | No | Publisher/source |
| `article_url` | No | Article URL |
| `provider_article_id` | No | Source-scoped provider ID |

News CSV is UTF-8 with a header. Required columns are `ticker`, `published_at`, `headline`; optional columns are `summary`, `source`, `article_url`, `provider_article_id`. Empty optional cells mean unavailable. Rows with missing required fields or invalid timestamps are rejected and counted; a malformed file may fail as a whole.

Use ISO 8601 timestamps with `Z` or an explicit offset. Naive timestamps require an explicit documented source timezone; never infer machine-local time or silently assume UTC. Filter inclusive New York calendar dates by converting to `[start-date midnight, midnight after end-date)` in `America/New_York` after normalization.

If a single-ticker CSV omits `ticker`, the user must explicitly select the ticker; do not infer it from a filename. Record provenance, live/local/sample status, timestamp convention, and permitted use.

## Deduplication

Primary identity is a non-empty provider ID scoped by source. If unavailable, an unambiguous exact normalized URL may be used: lowercase host, remove default port and fragment, preserve query parameters. Records with no reliable identity remain distinct. Report duplicate count and key type.

## Market Observations

Required logical fields: `ticker`, `trading_date` (`YYYY-MM-DD` Nasdaq session date), and `close` (finite positive value). CSV is UTF-8 with these header names. Rows are keyed by ticker/session date. Reject duplicate keys, invalid dates, and missing/non-positive/non-finite close values with disposition counts. Missing sessions are not synthesized.

Document currency and whether close is raw, split-adjusted, dividend-adjusted, or otherwise adjusted, including corporate-action treatment. Do not mix conventions. Sample rows must have provenance/limitations and must not be represented as live.

## Source Adapter Behavior

An adapter accepts a validated request and returns normalized records plus source identity, coverage, and status, or a typed source error. A live adapter maps actual verified provider fields and does not pass provider-specific objects into core logic. The market interface is provider-independent and has a CSV implementation. No assumption is made that a news provider's free tier includes historical prices.

Distinguish invalid configuration/input, empty result, malformed response, authentication failure, rate limit, timeout/network/service failure, and partial/incomplete retrieval. Partial results carry explicit status and are never labeled complete. Retries are unspecified unless provider policy is verified and behavior is deliberately designed.

## Alignment and Comparison

- Nasdaq only; use actual session closes, holidays, early closes, and `America/New_York` timezone rules.
- News in `(previous session close, current session close]` maps to the current session. After-close, weekend, and holiday news maps to the next eligible session.
- Compute `((current close - previous Nasdaq session close) / previous Nasdaq session close) * 100` only when both required closes are present and valid.
- Never forward-fill or substitute a previous available but non-consecutive observation.
- Compare per-session mean headline compound score and mean summary compound score independently with return. Preserve counts and disclose unmatched sessions.
- Selected mode is Nasdaq session alignment. Calendar-day aggregation is allowed only if the planning fallback condition is met and documented before implementation; no ad-hoc runtime switching.
