# Implementation Plan: Financial News Sentiment Analyzer

**Branch**: `financial-news-sentiment` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Authoritative feature requirements in `/specs/financial-news-sentiment/spec.md`.

## Summary

Deliver the specified local-first MVP for ticker/date-scoped financial-news analysis. CSV is the first complete execution path and automated-test fixture source. Normalize and validate news, deduplicate only on reliable identity, score headlines and non-empty summaries independently with VADER, aggregate them separately, align sentiment to Nasdaq sessions, and compare with verified closing-price observations. Finnhub and market-provider integration are gated on documented verification of fields, access, limits, terms, and price conventions. The four required charts are sentiment distribution, sentiment trend, stock-price trend, and sentiment versus price. Optional LLM work is excluded from MVP.

The planning checkpoint retains Nasdaq session alignment: this is a single-exchange calendar integration with bounded boundary tests, and current project documentation identifies no mandatory deliverable it would threaten. Therefore the specification's conditional calendar-day fallback is not selected. Record and revisit this decision only before implementation if a concrete schedule estimate changes the risk.

## Technical Context

**Language/Version**: Python 3.12 (`.python-version`).

**Primary Dependencies**: uv; pandas for CSV/table handling; `vadersentiment` for baseline scoring; Streamlit for the UI based on the project charter; Plotly for the four charts. Finnhub client is conditional on research. Nasdaq sessions use the selected official-source annual schedule ledger and a small adapter; add no calendar package unless separate verification demonstrates an exact Nasdaq calendar is preferable. Audit current dependencies before implementation; avoid unrelated NLP/ML or framework dependencies.

**Storage**: Local CSV inputs and in-memory analysis results; no database.

**Testing**: pytest unit and offline integration tests; Ruff. No live provider or LLM is required by the default test suite.

**Target Platform**: Local Python environment on Windows or another Python 3.12-supported platform.

**Project Type**: Single Python package with a local Streamlit interface.

**Performance Goals**: Responsive analysis of a capstone-sized local dataset; no throughput target is specified.

**Constraints**: CSV analysis must run without network, API credentials, or an LLM. No partial/failed retrieval may be presented as complete. No missing sentiment or price observations may be imputed. Provider use must comply with verified terms and limits; no secrets in tracked files.

**Scale/Scope**: One selected ticker and date range per analysis; Nasdaq is the only MVP exchange. No trading, investment advice, multi-company comparison, or required LLM.

## Constitution Check

**Gate before research**: Pass. The proposed scope keeps ingestion, validation, scoring, aggregation, market alignment, visualization, configuration, and error handling separable and independently testable; local CSV is a first-class path; baseline does not depend on paid services; external providers remain gated on compliance research.

**Gate after design**: Pass with implementation conditions. Do not add a provider until endpoint/data rights/limits are verified. Keep headline and summary results separate. Record exact schema and alignment rules. Add no claims about actual implementation, tests, provider availability, or classifier quality until evidenced. A small manual-review feasibility decision and genuine screenshots/test results remain delivery evidence tasks.

## Architecture and Data Flow

Use a single package and small module boundaries, not services. Keep UI, network I/O, and configuration at the edges; core transformations receive normalized records and return results. A provider protocol/adapter is justified only to isolate news and market data sources.

1. The UI collects ticker, inclusive date range, and source/input selection; configuration reads local environment values without exposing secrets.
2. A CSV source or verified Finnhub adapter loads records; source-specific fields are mapped to the logical schema.
3. Validation rejects unusable headlines/timestamps, counts issues, normalizes timestamps, and deduplicates on a reliable provider ID or unambiguous normalized URL. Unidentified records are retained separately rather than merged.
4. VADER scores each usable headline and each available non-empty summary independently; missing summaries remain unavailable. Thresholds are Negative `<= -0.05`, Neutral `(-0.05, 0.05)`, Positive `>= 0.05`.
5. Aggregation computes separate text-type counts and compound-score summaries by selected interval; intervals with no valid observations remain unavailable.
6. A CSV or verified market adapter supplies ticker, Nasdaq trading date, and a documented close series. A calendar adapter assigns news to the Nasdaq session window `(previous session close, current session close]` in `America/New_York`; after-close, weekend, and holiday items go to the next eligible session.
7. Daily close-to-close return uses the spec formula only when both the current and previous Nasdaq-session closes exist. Join sentiment and market values by ticker/session without filling gaps.
8. The UI renders the four required visualizations and discloses data source, live/sample status, method, thresholds, period, alignment, coverage, missing observations, and exploratory limitations.

## Project Structure

### Documentation (this feature)

```text
specs/financial-news-sentiment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── data-sources.md
├── spec.md
└── tasks.md                 # Later /speckit.tasks output
```

### Source Code (planned)

```text
src/financial_news_sentiment/
├── app.py                    # Streamlit boundary
├── config.py                 # Runtime settings and secret lookup
├── models.py                 # Normalized request and result records
├── errors.py                 # Domain/provider errors and statuses
├── workflow.py               # Compose independent core operations
├── validation.py             # Validation, normalization, deduplication
├── sentiment.py              # VADER scoring and label thresholds
├── aggregation.py            # Separate headline/summary aggregates
├── visualization.py          # Chart-ready series and chart rendering
├── news/
│   ├── csv_source.py
│   └── finnhub_source.py      # Only after verification
└── market/
    ├── interface.py
    ├── csv_source.py
    ├── provider_source.py    # Name/provider selected after research
    └── alignment.py          # Nasdaq sessions and close-to-close return

tests/
├── unit/
└── integration/              # Offline CSV workflow; no live API by default

data/
├── sample/                   # Only permitted, provenance-documented data
└── evaluation/               # Optional manually reviewed examples
```

**Structure Decision**: Extend the existing `src/financial_news_sentiment` package. Add only the planned modules needed for independently testable boundaries. No frontend/backend split, database, microservices, or mandatory sample-data download.

## Delivery Phases and Risk Order

1. **Planning and verification gates**: Resolve Spec Kit feature path; document CSV schemas and date/time policy; verify Finnhub and candidate market providers and terms; human-review the initial version-controlled Nasdaq annual schedule ledger against official sources and verify price-bar date semantics before implementing alignment. Provider uncertainty is the largest delivery risk, so CSV and core logic must not wait on it.
2. **Foundation**: Audit dependencies; establish settings, normalized data models, error/status types, and pytest/Ruff conventions. Keep Python 3.12 and uv/lockfile workflow.
3. **Offline core**: Implement CSV news/market ingestion, validation/deduplication, separate VADER scoring, separate aggregates, and no-network workflow. Prove it with tests before live integration.
4. **Market comparison**: Implement Nasdaq assignment and return calculation with missing-data semantics; test boundaries, holidays, early closes, DST, and missing observations. The selected mode is market-session alignment; no runtime mode switching.
5. **Verified source adapters**: Add Finnhub and a market-data provider only if research confirms required fields, access, terms, limits, and historical coverage. Otherwise preserve CSV fallback and report live capability as unavailable, not complete.
6. **Presentation and evidence**: Add Streamlit inputs, informative empty/error states, metadata, and four charts. Complete quickstart, source/method/limitations documentation, traceability, actual test output, manual-review feasibility, and genuine screenshots.

## Test Strategy and Requirement Traceability

Tests are offline-first and deterministic. Inject controlled records, provider responses, calendar schedules, and market observations; avoid live API calls in default tests.

| Spec requirements | Planned verification |
|---|---|
| FR-001, FR-002 / AC-01, AC-02 | Valid/invalid ticker and date-range unit tests; no silent scope substitution |
| FR-003, FR-004 / AC-03 | CSV schema tests and verified-adapter mapping/contract tests; provider mapping is not accepted before research |
| FR-005 / AC-14 | Missing fields, malformed timestamps, ID/URL duplicates, unidentified records, and disposition-count tests |
| FR-006 / AC-04, AC-12 | Empty, malformed, timeout, authentication, rate-limit, outage, and incomplete-response handling tests; user-facing status inspection |
| FR-007 to FR-009 / AC-05 to AC-07 | VADER score/label tests including exact `-0.05` and `0.05` boundaries and values immediately inside/outside |
| FR-008, FR-010 / AC-06, AC-08 | Separate headline and summary result/aggregate tests; missing summary is unavailable, never neutral |
| FR-011 / AC-09 | Controlled chart-series tests for sentiment distribution and trend |
| FR-012 / AC-10, AC-15, AC-18 | Session window, after-close, weekend, holiday, early-close, DST, missing price, return calculation, selected-mode tests; no imputation |
| FR-013 / AC-16 | UI/documentation review for exploratory interpretation and no causal/predictive claims |
| FR-014 / AC-11, AC-17 | Optional LLM deferred; acceptance checks baseline operates without LLM configuration |
| FR-015 / QA-04, QA-05 | Result metadata tests plus manual UI review and genuine screenshots |
| FR-016 / AC-13 | CSV end-to-end integration with networking blocked and no credentials |
| QR-001 to QR-004 / QA-01 to QA-04 | Isolated core tests, reproducible setup check, secret review, and source/method disclosure check |
| QR-005, QR-006 / QA-05, QA-06 | Record manual-review feasibility and actual observations if conducted; no unsupported metrics or completion claims |
| QR-007 | Acceptance matrix marks mandatory criteria verified only with executed evidence; optional LLM marked deferred |

Focused tests must include invalid and missing fields, duplicates, empty datasets, provider errors, CSV offline execution, exact VADER boundaries, independent headline/summary aggregation, calendar edge cases, missing prices, and the single selected alignment mode. Chart tests compare plotted series to controlled expected aggregates; do not rely only on screenshot appearance.

## Complexity Tracking

No constitution violations or additional projects are proposed. The provider adapter and calendar boundary isolate external variability without introducing service layers or a general plugin framework.
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
