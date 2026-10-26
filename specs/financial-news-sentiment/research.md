# Research and Verification Plan: Financial News Sentiment Analyzer

**Status**: Nasdaq session-calendar approach selected on 2026-10-24. The annual source data still requires human review before it is considered supported. News and market-provider behavior and terms remain pre-integration verification tasks.

This document records decisions necessary to implement the authoritative [specification](spec.md).

## Decision Summary

| Topic | Planning decision | Status |
|---|---|---|
| Baseline sentiment | VADER compound: Positive `>= 0.05`, Negative `<= -0.05`, Neutral strictly between | Required by spec; dependency declared |
| News input | CSV is the first complete path; Finnhub is the selected live-news candidate | SDK method interface checked; endpoint semantics, fields, access, limits, and terms pending verification |
| Market input | Provider-independent interface with CSV fallback | Live provider unselected; do not assume Finnhub free access includes historical prices |
| Alignment | Nasdaq sessions, `America/New_York`, `(previous close, current close]` | Requirement retained; selected approach is the official-source, version-controlled annual schedule ledger below; do not use the tested XNAS-to-XNYS alias. No year is yet verified by a committed reviewed ledger. |
| Calendar-day fallback | Not selected; current evidence identifies no mandatory deliverable threatened by the bounded annual-ledger verification and adapter work | Reconsider only before implementation with concrete schedule evidence |
| UI/charts | Streamlit and Plotly, consistent with the charter and existing dependencies | Planned, not implemented |
| LLM | Outside mandatory MVP | Deferred |

## Finnhub News Verification Gate

Use current official documentation and terms. The repository's starting links are [Finnhub API documentation](https://finnhub.io/docs/api) and [Finnhub](https://finnhub.io/); these links are not evidence that requirements have been met.

Before implementing a live adapter, record verification date and exact endpoint/request parameters; ticker and date filtering; date inclusivity and historical availability; response field names/types; timestamp semantics/timezone; headline, summary, URL, source, and ID availability; authentication; free-tier availability and limits; rate limits/error responses; terms/licensing; attribution; retention/redistribution rules; and permitted classroom use. Capture official references or permitted excerpts. Map only verified fields. If terms do not permit the planned use, do not integrate; keep CSV operational.

### Python SDK Interface Check: 2026-10-26

The project already declares `finnhub-python>=2.4.29` in `pyproject.toml`, and `uv.lock` resolves it to `2.4.29`. The project virtual environment has that version installed. Its public import is `import finnhub`; the checked client interface is `finnhub.Client(api_key=...)`.

The installed SDK source confirms these call shapes:

| Client method | Parameters | SDK route | Response handling |
|---|---|---|---|
| `company_news(symbol, _from, to)` | Symbol and date arguments; `_from` is translated to the request parameter `from` | `/company-news` | Returns endpoint JSON without SDK normalization; verify response shape and fields against current API documentation |
| `stock_candles(symbol, resolution, _from, to)` | Symbol, resolution such as `D`, and Unix-second bounds | `/stock/candle` | Returns endpoint JSON without SDK normalization; verify candle status/arrays and timestamp semantics before mapping |
| `news_sentiment(symbol)` | Symbol | `/news-sentiment` | Returns endpoint JSON without SDK normalization; it does not replace the required per-article headline/summary scoring |

The SDK defines `FinnhubAPIException` (with `status_code`) and `FinnhubRequestException`; the checked client also sets a 10-second default request timeout. These facts describe the installed SDK code only. They do not verify Finnhub's current endpoint access, date inclusivity, timestamp meaning, returned fields, account eligibility, quotas, rate limits, service behavior, or terms. The SDK check therefore does **not** close T005, authorize a live adapter, or establish that Finnhub is suitable as the MVP price source. No live request was made as part of this check.

Implementation implication: use the SDK behind the planned news-source boundary, instantiate it only when live retrieval is requested and credentials exist, map returned records to the provider-neutral schema, and translate API/request failures into the project's distinct source statuses. Keep CSV as the credential-free offline path. Validate candle status/array consistency and daily-bar timestamp semantics before considering any candle data for Nasdaq-session returns.

## Market-Data Provider Verification Gate

Compare viable candidates (for example, Alpha Vantage, Stooq, or Yahoo Finance access libraries) as candidates only; this list makes no claim about access, reliability, or permitted use. Prefer official documentation and terms. For each candidate, verify:

- Nasdaq ticker coverage; historical daily coverage; trading date and close fields.
- Authentication, account requirements, free-tier status, quotas, throttling, and availability.
- Terms, licensing, attribution, storage, display, and redistribution restrictions.
- Whether close is raw, split-adjusted, dividend-adjusted, or otherwise adjusted; corporate-action treatment.
- Session/timezone semantics, corrections, missing observations, and error behavior.

Select a provider only after documenting evidence. Keep `MarketDataSource` provider-independent and CSV-backed. Do not mix price conventions. A close-to-close return is unavailable if either the current close or immediately previous Nasdaq-session close is missing; never substitute the last available observation. If an acceptable live source is not verified, retain the CSV path and report live retrieval as unresolved.

## Nasdaq Calendar Verification Gate

The earlier library-evaluation gate is resolved as a design choice in [Calendar Approach Decision](#calendar-approach-decision-2026-10-24); the tested `exchange-calendars` XNAS alias is rejected. Before implementation, a human must verify and review the initial annual schedule ledger, its official source references, the preceding-session boundary needed for return calculations, date coverage and fail-closed behavior, and storage terms. No alias or generic weekday calendar may stand in for Nasdaq.

### Candidate Validation: 2026-10-19

The project targets Python 3.12. The plan names `exchange-calendars` as a candidate, but it is not declared in `pyproject.toml` or `uv.lock`. Version `4.13.2` was installed in the local project venv for this validation only; this did not add a project dependency.

**Result: candidate blocked for direct Nasdaq use.** `get_calendar_names(include_aliases=False)` does not include `XNAS`. Although `XNAS` and `NASDAQ` appear when aliases are included, both `get_calendar("XNAS")` and `get_calendar("NASDAQ")` return an object whose name is `XNYS`. This is an NYSE calendar, not an exact Nasdaq calendar. Do not count matching hours on the selected sample dates as verification of Nasdaq calendar identity or use this alias in an adapter.

For evidence only, the returned XNYS schedule was compared with the official Nasdaq schedule:

| Date / case | Expected Nasdaq session (Eastern) | Expected Nasdaq session (UTC) | Actual returned XNYS-alias schedule | Result as Nasdaq validation |
|---|---|---|---|---|
| 2026-11-24, full session | 09:30-16:00 EST | 14:30-21:00 UTC | 14:30-21:00 UTC | Not accepted; XNYS alias |
| 2026-11-28, Saturday | No session | No session | No session | Not accepted; XNYS alias |
| 2026-11-26, Thanksgiving | No session | No session | No session | Not accepted; XNYS alias |
| 2026-11-27, early close | 09:30-13:00 EST | 14:30-18:00 UTC | 14:30-18:00 UTC | Not accepted; XNYS alias |
| 2026-10-30, before DST ends | 09:30-16:00 EDT | 13:30-20:00 UTC | 13:30-20:00 UTC | Not accepted; XNYS alias |
| 2026-11-02, after DST ends | 09:30-16:00 EST | 14:30-21:00 UTC | 14:30-21:00 UTC | Not accepted; XNYS alias |

The observed XNYS schedule converts to `America/New_York` at offset `-04:00` on October 30 and `-05:00` on November 2, with both full sessions opening at 09:30 local time. The hours happen to match the published Nasdaq examples, including Saturday and Thanksgiving closures and the 1:00 p.m. ET early close, but they are XNYS output and are not accepted as Nasdaq validation. The automated verification module refuses to treat the alias as XNAS; its canonical-identifier and six schedule checks remain expected-failure until an exact Nasdaq calendar is available.

The installed calendar's locally available schedule spans 2006-10-19 through 2027-10-19. `is_session`/`sessions_in_range` reject dates outside the known range with `DateOutOfBounds`; slicing `.schedule.loc[...]` outside the range instead returns an empty frame, so callers must validate bounds and must not interpret that empty frame as a holiday. Calendar definitions/schedules are supplied by the installed package and queried locally; the library does not fetch a live Nasdaq schedule at request time. Accuracy still depends on package data being current and covering the requested date.

Official comparison references: [Nasdaq 2026 U.S. market holidays and trading hours](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule) and [Nasdaq Trader calendar](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar). Library references: [exchange-calendars repository and documentation](https://github.com/gerrymanoim/exchange_calendars) and [PyPI release history](https://pypi.org/project/exchange-calendars/).

The 2026-10-19 mitigation paragraph above is historical; the decision below supersedes it.

### Calendar Approach Decision: 2026-10-24

**Decision: use option 2, a version-controlled, manually verified Nasdaq schedule ledger and a small session-calendar adapter.** This is the simplest approach supported by current evidence and the student-capstone constraints. Do not use `exchange-calendars==4.13.2` for Nasdaq: `XNAS` and `NASDAQ` resolve to `XNYS`, so matching hours do not establish Nasdaq identity. `pandas-market-calendars` and other packages have not been verified and are not selected. Do not add a calendar dependency or implement the adapter as part of this decision. At decision time, the ledger is not yet committed and reviewed, so this is a selected approach, not a claim that an operational calendar exists.

**Authority and coverage policy**

- Source of truth: [Nasdaq U.S. Stock Market Holiday Schedule and trading hours](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule); [Nasdaq Trader calendar](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar). The Nasdaq Trading Calendar page also links year-specific calendar downloads, including [2025](https://www.nasdaqtrader.com/content/technicalsupport/2025tradingcalendar.pdf) and [2026](https://www.nasdaq.com/trading-calendar).
- First target year: **2026 only**, after a human has reviewed the complete year's official schedule and committed the verified ledger. The 2026 Nasdaq page currently lists full closures on Jan 1, Jan 19, Feb 16, Apr 3, May 25, Jun 19, Jul 3, Sep 7, Nov 26, and Dec 25, and early closes on Nov 27 and Dec 24 at 1:00 p.m. Eastern. These observed page entries are a transcription aid, not a claim that a verified project ledger already exists.
- 2025 is not initially supported as a full year. Before calculating the first 2026 close-to-close return, separately verify the immediately preceding Nasdaq session and close-date boundary (expected to require the 2025 calendar) against the official 2025 calendar. Until verified, that initial return must be unavailable rather than inferred.
- 2027 and later are out of coverage unless and until the official annual schedule is published, reviewed, and committed in the ledger. Publication alone does not mark a year supported; do not infer any year from recurring holiday rules.
- A year is supported only if its ledger records the year, `America/New_York`, official source URL(s), source checked date, reviewer, full closure list, early-close list, and review status. Confirm any applicable terms for storing/redistributing this derived schedule before committing it.

**Session rules**

- The calendar covers Nasdaq regular trading sessions only; extended hours are excluded.
- On a verified regular weekday, regular open is 09:30 and regular close is 16:00 in `America/New_York`, unless the official annual schedule gives a special session time.
- Exclude each official full-closure date. On each official early-close date, retain the session with the listed close (the current 2026 source says 13:00 Eastern on Nov 27 and Dec 24); the regular open remains 09:30 unless Nasdaq publishes a different open.
- Store dates and local clock times as schedule data and use Python's IANA `ZoneInfo("America/New_York")` at runtime. Never hard-code a fixed UTC offset: DST determines whether 09:30 is 13:30 UTC (EDT) or 14:30 UTC (EST), and similarly shifts closes. Convert schedule instants to UTC only at the boundary where a UTC instant is required.
- If Nasdaq publishes a correction or an unscheduled closure/changed session, update the version-controlled ledger from the official notice, record the notice URL and checked date, and add/update the date-specific test in the same reviewed change. Until that update is reviewed, affected dates are not treated as verified sessions.

**Coverage and failure behavior**

Expose the exact verified date range/year set through the adapter. Requests outside it must raise/return an explicit out-of-coverage result; they must not be treated as holidays, ordinary weekdays, or silently extrapolated. In-range weekends and listed holidays return no session. Missing or malformed annual data is a configuration/coverage error, not an empty schedule. If the yearly source has not yet been manually verified, that year is unsupported.

**Daily-bar alignment contract**

The live stock-price provider remains unselected. Its adapter must first document and test the provider's daily timestamp meaning, timezone, session-date convention, and adjustment basis. It must map each daily bar to the provider's documented Nasdaq trading-date label, then join by that canonical `trading_date`; it must not take the UTC calendar date or assume a timestamp convention without evidence. Reject or report bars that cannot be mapped to a verified session. For return calculation, request/retain the immediately preceding Nasdaq session close and never substitute the last available non-consecutive close. If the provider's timestamp semantics cannot be established, market alignment is unavailable pending verification; this does not authorize a calendar-day fallback.

**Automated verification plan**

The isolated calendar tests must use the committed, reviewed annual ledger and assert both the exact session label and UTC open/close instants, plus the `America/New_York` equivalents:

- Normal full session: 2026-11-24, 09:30-16:00 EST / 14:30-21:00 UTC.
- Weekend: 2026-11-28 returns no session.
- Full holiday: 2026-11-26 Thanksgiving returns no session.
- Early close: 2026-11-27, 09:30-13:00 EST / 14:30-18:00 UTC.
- DST: 2026-10-30 returns 09:30-16:00 EDT / 13:30-20:00 UTC; 2026-11-02 returns 09:30-16:00 EST / 14:30-21:00 UTC.
- Coverage: dates before/after verified years produce the explicit out-of-coverage outcome, not an empty holiday result; missing and unreviewed ledgers fail closed.
- Price-bar mapping: controlled provider timestamp fixtures around DST map to the documented session-date label, with non-session dates and ambiguous timestamp conventions rejected.

The existing `tests/verification/test_nasdaq_calendar.py` characterizes the rejected `exchange-calendars` candidate and its XNYS alias; its expected failures are evidence of that blocker, not tests of the selected annual-ledger adapter. A future adapter requires its own passing tests before implementation is accepted.

**Remaining verification**: the 2026 ledger review and permission to store its derived dates are recorded in [Initial Ledger Review](#initial-ledger-review-2026-10-26). Verify the 2025-12-31 preceding-session boundary before making the first 2026 return, verify the selected market provider's daily-bar timestamp semantics and price basis, and add 2027 only after its official schedule is published and checked. No stock-price provider is selected. Nasdaq-session alignment remains the requirement; no calendar-day fallback is selected. No concrete mandatory MVP deliverable is currently shown to be threatened by this approach.

### Initial Ledger Review: 2026-10-26

The 2026 ledger is recorded in `data/reference/nasdaq_schedule_2026.json`. On 2026-10-26, the complete 2026 schedule was checked against the official Nasdaq Trader holiday schedule and its linked 2026 calendar PDF. The source lists full closures on January 1, January 19, February 16, April 3, May 25, June 19, July 3, September 7, November 26, and December 25, and early closes at 1:00 p.m. Eastern on November 27 and December 24. Reviewer: Rohini Fulpagare; approval to store the derived schedule in version control was confirmed for this ledger.

This review supports only dates from 2026-01-01 through 2026-12-31. The 2025-12-31 preceding-session boundary remains unverified, so a close-to-close return requiring that prior session is not authorized by this ledger. 2027 and later remain out of coverage until an official annual schedule is published and reviewed. Market-provider timestamp semantics, price basis, and source selection remain unresolved.

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

Current `pyproject.toml` declares Finnhub, Matplotlib, NumPy, pandas, Plotly, scikit-learn, Streamlit, TextBlob, and VADER. The baseline plan clearly needs pandas, VADER, Streamlit, and Plotly; `finnhub-python` is already declared and locked at 2.4.29, although live integration remains gated by T005. Audit direct/transitive needs and remove unused direct dependencies as a deliberate configuration task; retain uv lockfile reproducibility. Add no calendar library unless its separate verification demonstrates an exact Nasdaq calendar is preferable to the selected reviewed-ledger approach. No LLM client or paid service is required.
