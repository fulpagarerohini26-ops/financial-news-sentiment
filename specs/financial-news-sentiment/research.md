# Research and Verification Plan: Financial News Sentiment Analyzer

**Status**: Provider behavior and terms have not been verified as of 2026-10-19. Items below are explicit pre-integration tasks, not claims about provider capabilities.

This document records decisions necessary to implement the authoritative [specification](spec.md).

## Decision Summary

| Topic | Planning decision | Status |
|---|---|---|
| Baseline sentiment | VADER compound: Positive `>= 0.05`, Negative `<= -0.05`, Neutral strictly between | Required by spec; dependency declared |
| News input | CSV is the first complete path; Finnhub is the selected live-news candidate | Endpoint, fields, access, limits, and terms pending verification |
| Market input | Provider-independent interface with CSV fallback | Live provider unselected; do not assume Finnhub free access includes historical prices |
| Alignment | Nasdaq sessions, `America/New_York`, `(previous close, current close]` | Selected; verify calendar package and edge behavior before implementation |
| Calendar-day fallback | Not selected because current evidence identifies no mandatory deliverable threatened by the bounded single-calendar work | Reconsider only before implementation with concrete schedule evidence |
| UI/charts | Streamlit and Plotly, consistent with the charter and existing dependencies | Planned, not implemented |
| LLM | Outside mandatory MVP | Deferred |

## Finnhub News Verification Gate

Use current official documentation and terms. The repository's starting links are [Finnhub API documentation](https://finnhub.io/docs/api) and [Finnhub](https://finnhub.io/); these links are not evidence that requirements have been met.

Before implementing a live adapter, record verification date and exact endpoint/request parameters; ticker and date filtering; date inclusivity and historical availability; response field names/types; timestamp semantics/timezone; headline, summary, URL, source, and ID availability; authentication; free-tier availability and limits; rate limits/error responses; terms/licensing; attribution; retention/redistribution rules; and permitted classroom use. Capture official references or permitted excerpts. Map only verified fields. If terms do not permit the planned use, do not integrate; keep CSV operational.

## Market-Data Provider Verification Gate

Compare viable candidates (for example, Alpha Vantage, Stooq, or Yahoo Finance access libraries) as candidates only; this list makes no claim about access, reliability, or permitted use. Prefer official documentation and terms. For each candidate, verify:

- Nasdaq ticker coverage; historical daily coverage; trading date and close fields.
- Authentication, account requirements, free-tier status, quotas, throttling, and availability.
- Terms, licensing, attribution, storage, display, and redistribution restrictions.
- Whether close is raw, split-adjusted, dividend-adjusted, or otherwise adjusted; corporate-action treatment.
- Session/timezone semantics, corrections, missing observations, and error behavior.

Select a provider only after documenting evidence. Keep `MarketDataSource` provider-independent and CSV-backed. Do not mix price conventions. A close-to-close return is unavailable if either the current close or immediately previous Nasdaq-session close is missing; never substitute the last available observation. If an acceptable live source is not verified, retain the CSV path and report live retrieval as unresolved.

## Nasdaq Calendar Verification Gate

Evaluate a maintained calendar library (candidate: `exchange-calendars`) for Nasdaq/XNAS schedule coverage, holidays, early closes, DST, timezone-aware open/close instants, Python 3.12 compatibility, license, maintenance, and API behavior. Verify controlled dates against authoritative calendar examples. Keep calendar lookup behind a narrow interface. If no compatible library meets these checks, document the issue and reassess schedule risk before implementation; do not silently switch alignment modes.

## Data and Rule Decisions

- **Date range**: Treat selected start/end as inclusive New York calendar dates. Convert to `[start-date midnight, midnight after end-date)` in `America/New_York`; normalize timestamps before filtering.
- **Timestamps**: Accept timezone-aware timestamps. Naive CSV timestamps require an explicit documented source timezone; never infer machine-local time or silently assume UTC. Reject/count unusable timestamps.
- **News CSV**: Required `ticker`, `published_at`, `headline`; optional `summary`, `source`, `article_url`, `provider_article_id`.
- **Market CSV**: Required `ticker`, `trading_date`, `close`; document currency and raw/adjusted price basis.
- **Deduplication**: Primary key is non-empty provider ID scoped to source. If absent, use only an unambiguous exact normalized URL (lowercase host, remove default port and fragment; preserve query parameters). Do not merge records without reliable identity; report dispositions.
- **Aggregates**: Keep headline and summary populations separate. Use only valid VADER scores; empty intervals are unavailable, not zero or Neutral.
- **Comparison**: Per ticker/session, compare mean headline score and mean summary score separately with close-to-close return. Scatter plot only matched observations; disclose excluded coverage. Correlation is not required; do not add it without explicit method and interpretation.
- **Errors**: Distinguish invalid input, empty result, rejected records, missing credentials, authentication, rate limit, timeout/network/service failure, malformed response, and partial retrieval. Partial data must be labeled partial, never complete.

Detailed column rules are in [contracts/data-sources.md](contracts/data-sources.md).

## Planning Checkpoint and Schedule Risk

The charter/spec do not state a capstone deadline or team-capacity estimate. Based on the documented scope, session alignment covers one exchange and one deterministic assignment rule with a finite test matrix; no other mandatory deliverable is currently identified as threatened. Retain session alignment and do not activate the fallback. If concrete deadline/capacity evidence changes this assessment, record the affected deliverable, estimate, and fallback decision before implementation. No ad-hoc switch is allowed during implementation.

## Dependency Audit

Current `pyproject.toml` declares Finnhub, Matplotlib, NumPy, pandas, Plotly, scikit-learn, Streamlit, TextBlob, and VADER. The baseline plan clearly needs pandas, VADER, Streamlit, and Plotly. Audit direct/transitive needs and remove unused direct dependencies as a deliberate configuration task; retain uv lockfile reproducibility. Add a Finnhub client and calendar library only after their gates. No LLM client or paid service is required.
