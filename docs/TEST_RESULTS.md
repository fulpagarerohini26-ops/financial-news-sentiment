# Provider Diagnostic Results

## Finnhub Probe: 2026-10-19

This is an observed, single-run diagnostic of Finnhub access for this account. It is not an application integration test, does not establish account-wide plan entitlement, and does not complete the provider-verification gate. No token or response body was stored.

Command, run from the repository root in the Python 3.12 project environment:

```powershell
uv run --no-sync --env-file .env python scripts/validate_finnhub.py
```

### Company News

- Endpoint: Finnhub `GET /api/v1/company-news`
- Request: `AAPL`, 2026-10-01 through 2026-10-07 inclusive
- HTTP status: `200`
- JSON: valid; top-level list
- Records: `238`
- Returned fields: `category`, `datetime`, `headline`, `id`, `image`, `related`, `source`, `summary`, `url`
- Missing or unusable: timestamps `0`, headlines `0`, sources `0`, URLs `0`, summaries `1`
- Date observation: interpreting the Unix timestamps as UTC and converting to `America/New_York`, one timestamp falls on 2026-09-30, outside the requested calendar-date range. Observed timestamp coverage was 2026-09-30 through 2026-10-07 in New York.

### Historical Daily Candles

- Endpoint: Finnhub `GET /api/v1/stock/candle`
- Request: `AAPL`, resolution `D`, same date range
- HTTP status: `403`; valid JSON object with field `error`
- Result: denied; message: `You don't have access to this resource.`
- OHLCV arrays and daily values: unavailable, so lengths and values could not be validated.

### Interpretation and Follow-Up

These results establish only what the API returned for this particular request and account at the time of the probe. The candle denial does not by itself identify whether the cause is plan entitlement, endpoint permissions, or another account restriction. Finnhub's [stock-candles documentation](https://finnhub.io/docs/api/stock-candles) labels the endpoint Premium; confirm the account-specific reason in the Finnhub dashboard or with Finnhub support. Do not infer broader historical-price access from a short-range result.

The [company-news documentation](https://finnhub.io/docs/api/company-news) and [stock-candles documentation](https://finnhub.io/docs/api/stock-candles) should be checked again for current field definitions, timestamp semantics, date boundaries, limits, and applicable usage terms before any adapter is implemented. This diagnostic did not verify licensing, attribution, retention, redistribution, classroom-use terms, or overall plan entitlement. No stock-price provider has been selected.
