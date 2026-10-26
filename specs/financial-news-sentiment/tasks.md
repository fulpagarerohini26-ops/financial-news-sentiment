# Tasks: GenAI-Powered Financial News Sentiment Analyzer

**Input**: Design documents from `/specs/financial-news-sentiment/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/data-sources.md`, and `.specify/memory/constitution.md`

**Format**: `[ID] [P?] [Story] Description`

**Story key**: US1 Analyze a Company and Date Range; US2 Validate and Prepare News Records; US3 Analyze Headline and Summary Sentiment; US4 View Sentiment Statistics and Trends; US5 Compare Sentiment With Stock-Price Movements; US6 Understand Results and Limitations; US7 Optionally Compare Contextual LLM Sentiment; US8 Reproduce and Evaluate the Project.

## Phase 1: Setup and Verification Gates

**Purpose**: Establish the reproducible project foundation and resolve external-source/calendar gates before any corresponding integration.

- [ ] T001 [US8] Audit direct dependencies against the approved plan; retain only dependencies used by the MVP, add any missing planned test/runtime dependency, and regenerate `uv.lock` with `pyproject.toml` as the source of truth.
- [ ] T002 [P] [US8] Create the planned module and test directory structure under `src/financial_news_sentiment/`, `src/financial_news_sentiment/news/`, `src/financial_news_sentiment/market/`, `tests/unit/`, and `tests/integration/` without adding unplanned services or storage.
- [ ] T003 [US8] Add typed runtime settings in `src/financial_news_sentiment/config.py` for CSV paths, optional Finnhub credentials, and explicit timezone/configuration values; loading settings without credentials must succeed for offline mode.
- [ ] T004 [US8] Add a placeholder-only `.env.example`, ensure `.env` and credential files remain ignored by `.gitignore`, and verify no real key/token is present in tracked files.
- [ ] T005 [US1] Verify Finnhub's official endpoint, request/date semantics, response fields and timestamp meaning, authentication/access, quotas/rate limits, failure behavior, terms/licensing, attribution, retention, and classroom-use restrictions; record dated evidence and an integrate/do-not-integrate decision in `specs/financial-news-sentiment/research.md` before any Finnhub adapter work.
- [ ] T006 [US5] Evaluate market-data candidates for Nasdaq ticker coverage, historical daily OHLC availability and required daily close, access/free-tier limits, close adjustment/corporate-action convention, errors, and usage/display terms; record official evidence, selected provider or unresolved status, and why it is suitable or unsuitable in `specs/financial-news-sentiment/research.md` before any live market adapter work.
- [ ] T007 [US5] Before session-alignment implementation, human-review a version-controlled annual Nasdaq schedule ledger against the official Nasdaq holiday/trading-calendar sources; verify closures, early closes, `America/New_York`/DST conversion, ledger coverage and fail-closed behavior, storage terms, and the preceding-session boundary required for the selected price provider; record dated source evidence and reviewed supported year(s) in `specs/financial-news-sentiment/research.md`. Do not treat the `exchange-calendars` XNAS alias as Nasdaq or use a generic weekday calendar. The 2026 ledger and its storage approval are reviewed; T007 remains open until the 2025 preceding-session boundary is verified for a selected price provider.
- [ ] T008 [US5] Before session-alignment implementation, confirm the plan's recorded decision to retain Nasdaq-session alignment; only if concrete schedule evidence now shows another mandatory MVP deliverable is threatened, record that deliverable and rationale in `research.md` and select the documented calendar-day fallback before implementation. Do not add runtime mode switching.

## Phase 2: Foundational Models and Configuration

**Purpose**: Provide shared, provider-neutral records and errors needed by all story work. All user-story implementation depends on this phase.

- [ ] T009 [P] [US8] Define the request, normalized news, validation report, sentiment, aggregate, market, session-assignment, comparison, and result records with the invariants in `data-model.md` in `src/financial_news_sentiment/models.py`.
- [ ] T010 [P] [US1] Define distinct input, validation, empty-result, missing-credential, authentication, rate-limit, timeout/network, malformed-response, and partial-result error/status types in `src/financial_news_sentiment/errors.py`.
- [ ] T011 [US1] Implement ticker/date/source/path/timezone settings validation in `src/financial_news_sentiment/config.py`; invalid or reversed date ranges must be rejected without changing the requested scope.
- [ ] T012 [P] [US1] Add unit tests in `tests/unit/test_config.py` for valid and invalid ticker/date/source settings, missing CSV paths, and credential-free CSV configuration.

## Phase 3: User Story 1 - Analyze a Company and Date Range (Priority: P1)

**Goal**: Select and faithfully load a ticker/date-scoped news set, with CSV as the complete offline path and live news only when verified.

**Independent Test**: Given a controlled CSV or verified-provider response, confirm the requested ticker and inclusive dates are honored, returned records use the logical schema, and empty/error results are distinct.

- [ ] T013 [P] [US1] Add CSV-source tests in `tests/unit/test_csv_news_source.py` for required/optional columns, one-ticker selection when ticker is omitted, inclusive New York date filtering, empty data, and malformed file behavior.
- [ ] T014 [US1] Implement the UTF-8 news CSV reader in `src/financial_news_sentiment/news/csv_source.py` using the documented columns and requiring explicit ticker selection when a single-ticker file omits `ticker`.
- [ ] T015 [P] [US1] Add request-scope tests in `tests/unit/test_request_scope.py` for accepted/rejected tickers, reversed dates, inclusive date boundaries, and rejection rather than silent scope substitution.
- [ ] T016 [US1] Implement request and news-date filtering in `src/financial_news_sentiment/workflow.py`, converting selected inclusive New York dates to the documented half-open timestamp interval after explicit timezone normalization.
- [ ] T017 [US1] Implement `src/financial_news_sentiment/news/finnhub_source.py` only if T005 records that access, fields, and terms permit the planned use; map only verified fields. If the gate is unresolved or fails, leave live retrieval unavailable with an explicit status and preserve CSV operation.
- [ ] T018 [P] [US1] Add controlled adapter tests in `tests/unit/test_finnhub_source.py` for verified field mapping, empty responses, authentication/rate-limit/network/malformed/partial failures; if T005 blocks integration, test the explicit unavailable status instead of simulating provider capabilities.

## Phase 4: User Story 2 - Validate and Prepare News Records (Priority: P1)

**Goal**: Normalize usable news, reject/report invalid records, and deduplicate only on reliable identity.

**Independent Test**: Feed controlled records with missing fields, malformed timestamps, ID/URL duplicates, and no reliable identity; verify accepted/rejected/duplicate counts and retained records.

- [ ] T019 [P] [US2] Add validation tests in `tests/unit/test_validation.py` for blank headlines, absent required fields, aware and explicitly localized naive timestamps, invalid timestamps, missing summaries, and malformed records.
- [ ] T020 [US2] Implement timestamp normalization, required-field checks, optional-field handling, and record disposition counts in `src/financial_news_sentiment/validation.py`; do not infer machine-local time or silently assume UTC.
- [ ] T021 [P] [US2] Add deduplication tests in `tests/unit/test_deduplication.py` for source-scoped IDs, exact normalized URLs, duplicate count/key type, and preservation of records without a reliable key.
- [ ] T022 [US2] Implement the documented ID-then-unambiguous-normalized-URL deduplication rules in `src/financial_news_sentiment/validation.py`; preserve query parameters, remove URL fragments/default ports, and never merge unidentified records.
- [ ] T023 [P] [US2] Add validation-report tests in `tests/unit/test_validation_report.py` asserting input/accepted/rejected/duplicate/unidentifiable counts and actionable rejection reasons.
- [ ] T024 [US2] Expose validation coverage and actionable record/file errors through the normalized report in `src/financial_news_sentiment/validation.py` without logging secrets or unnecessary raw provider payloads.

## Phase 5: User Story 3 - Analyze Headline and Summary Sentiment (Priority: P1)

**Goal**: Score valid headlines and available summaries independently using the specified VADER baseline.

**Independent Test**: Verify scores and labels for controlled text at, immediately below, and immediately above both thresholds; confirm missing summaries have no score or label.

- [ ] T025 [P] [US3] Add threshold and text tests in `tests/unit/test_sentiment.py` covering exact `-0.05`/`0.05`, values on either side, representative labels, empty text, and missing text.
- [ ] T026 [US3] Implement VADER compound scoring and deterministic labels in `src/financial_news_sentiment/sentiment.py`: Negative `<= -0.05`, Positive `>= 0.05`, Neutral strictly between; retain method/version metadata.
- [ ] T027 [P] [US3] Add separate-text tests in `tests/unit/test_sentiment.py` proving headline and summary are scored independently and an absent/empty summary is unavailable rather than Neutral.
- [ ] T028 [US3] Return separate headline and optional-summary sentiment results from `src/financial_news_sentiment/sentiment.py`, including finite score validation and no LLM dependency.

## Phase 6: User Story 4 - View Sentiment Statistics and Trends (Priority: P1)

**Goal**: Aggregate headline and summary populations separately and plot the two required sentiment views accurately.

**Independent Test**: Use fixed scored records across intervals; compare aggregate counts/means and chart series to expected values, including intervals with no valid scores.

- [ ] T029 [P] [US4] Add aggregation tests in `tests/unit/test_aggregation.py` for separate text types, valid-score-only counts, empty intervals, and expected means/label distributions.
- [ ] T030 [US4] Implement ticker/interval/text-type aggregates in `src/financial_news_sentiment/aggregation.py`, retaining counts and coverage and representing empty groups as unavailable, not zero or Neutral.
- [ ] T031 [P] [US4] Add chart-series tests in `tests/unit/test_visualization.py` that compare sentiment distribution and trend series with controlled aggregates and verify empty intervals are absent/unavailable.
- [ ] T032 [US4] Implement Plotly sentiment-distribution and sentiment-trend charts in `src/financial_news_sentiment/visualization.py`, labeling period, text type, counts, and aggregation basis.

## Phase 7: User Story 5 - Compare Sentiment With Stock-Price Movements (Priority: P1)

**Goal**: Load documented daily closes, align news to Nasdaq sessions, calculate valid close-to-close returns, and compare only matched observations.

**Independent Test**: Supply controlled session schedules, timestamps, and price gaps; verify boundary/holiday assignments, returns, matches, and visible missing coverage without imputation.

- [ ] T033 [P] [US5] Add market CSV tests in `tests/unit/test_csv_market_source.py` for required columns, dates, finite positive close, duplicate ticker/session keys, missing data, and explicit price convention metadata.
- [ ] T034 [US5] Implement the UTF-8 daily-close CSV source in `src/financial_news_sentiment/market/csv_source.py`; reject invalid/duplicate keys and never synthesize missing sessions.
- [ ] T035 [P] [US5] Add Nasdaq alignment tests in `tests/unit/test_alignment.py` for `(previous close, current close]`, exact close boundaries, after-close, weekends, holidays, early closes, DST, and next-eligible-session assignment.
- [ ] T036 [US5] After T007 is reviewed, implement the narrow adapter and session assignment in `src/financial_news_sentiment/market/alignment.py` from the verified annual Nasdaq ledger using `America/New_York`; reject out-of-coverage dates explicitly and never infer sessions from weekdays. Preserve the selected Nasdaq-session mode; do not substitute calendar-day alignment.
- [ ] T037 [P] [US5] Add return tests in `tests/unit/test_market_returns.py` for the specified percentage formula, missing current/previous consecutive-session close, invalid close, and no forward-fill/substitution.
- [ ] T038 [US5] Implement close-to-close return calculation in `src/financial_news_sentiment/market/alignment.py`; require both current and immediately previous Nasdaq-session closes and preserve unavailable returns.
- [ ] T039 [US5] Implement a provider-independent market-source interface in `src/financial_news_sentiment/market/interface.py` exposing ticker, Nasdaq trading date, close, source, coverage, and price-convention metadata.
- [ ] T040 [US5] Implement `src/financial_news_sentiment/market/provider_source.py` only if T006 verifies historical coverage, required daily close, conventions, access, and terms; otherwise expose live market retrieval as unavailable and keep CSV functional. Do not assume free-tier historical OHLC or price access.
- [ ] T041 [P] [US5] Add controlled market-adapter failure tests in `tests/unit/test_market_provider.py` for missing credentials, authentication, rate limit, timeout/network, malformed response, and partial coverage; if T006 blocks integration, verify its explicit unavailable status.
- [ ] T042 [P] [US5] Add comparison tests in `tests/unit/test_comparison.py` for session joins, independent headline/summary means, matched-only observations, coverage gaps, and the absence of filling/imputation.
- [ ] T043 [US5] Implement comparison construction in `src/financial_news_sentiment/market/alignment.py`, preserving per-session counts and source/coverage metadata and excluding unmatched observations from comparison values.
- [ ] T044 [US5] Implement the stock-price trend chart in `src/financial_news_sentiment/visualization.py`, displaying observed closes and actual gaps without fabricated values.
- [ ] T045 [US5] Implement the sentiment-versus-price comparison chart in `src/financial_news_sentiment/visualization.py` using only matched values and identifying the compared sentiment series and return basis.

## Phase 8: User Story 6 - Understand Results and Limitations (Priority: P1)

**Goal**: Make provenance, methods, coverage, limitations, and exploratory interpretation visible wherever results are presented.

**Independent Test**: Inspect successful, empty, partial, and failed results and confirm source/method/scope/coverage are disclosed without causal, predictive, or investment-advice claims.

- [ ] T046 [P] [US6] Add result-metadata tests in `tests/unit/test_result_metadata.py` for source kind (live/local/sample), source identity, date range, VADER thresholds/version, validation counts, alignment/price convention, coverage, and limitations.
- [ ] T047 [US6] Populate result metadata in `src/financial_news_sentiment/workflow.py` from actual request and adapter outcomes; distinguish live, local, and sample data and never label partial retrieval complete.
- [ ] T048 [P] [US6] Add presentation-contract tests in `tests/unit/test_result_presentation.py` for source/method/scope/coverage disclosure, separate empty/partial/failure states, and exploratory-not-causal interpretation.

## Phase 9: User Story 8 - Reproduce and Evaluate the Project (Priority: P1)

**Goal**: Deliver a network-independent representative workflow, reproducible setup/tests, honest evaluation evidence, and traceability.

**Independent Test**: In a supported Python 3.12 environment without credentials/network, follow documented setup, run tests and CSV workflow, and inspect genuine evidence and requirement traceability.

- [ ] T049 [P] [US8] Add small deterministic news and market CSV fixtures under `tests/fixtures/` covering positive/negative/neutral text, missing summary, duplicate, malformed row, session boundaries, and price gaps; label fixture provenance and non-live status.
- [ ] T050 [P] [US8] Add an offline integration test in `tests/integration/test_csv_workflow.py` that runs with network access blocked and no provider/LLM credentials and asserts outputs, coverage, and non-live provenance.
- [ ] T051 [US8] Compose CSV loading, validation, sentiment, aggregation, and optional market comparison in `src/financial_news_sentiment/workflow.py`; keep each core operation independently callable and preserve explicit partial/error status.
- [ ] T052 [US1] Implement the Streamlit request controls and source selection in `src/financial_news_sentiment/app.py` for ticker, inclusive date range, CSV paths, and verified live-source availability; CSV selection must work without credentials.
- [ ] T053 [US6] Connect app controls to the workflow and render informative no-results, invalid-input, missing-credential, provider-failure, and partial-result states with source/method/scope/coverage disclosures; describe comparisons as exploratory, not causal, predictive, or investment advice, and never present a different scope as successful.
- [ ] T054 [US8] Update `README.md` and `specs/financial-news-sentiment/quickstart.md` with Python/uv setup, app/test commands, CSV schemas and timezone configuration, offline execution, optional credentials, secret handling, and verified/unresolved provider limitations.
- [ ] T055 [US8] Update `docs/DATA_SOURCE.md`, `docs/METHODOLOGY.md`, `docs/TEST_RESULTS.md`, and `docs/FINAL_REPORT.md` only with verified source rules, actual executed test/evaluation results, known limitations, and explicit deferred/unavailable capabilities.
- [ ] T056 [US8] Record whether a small manual financial-text review is feasible and why; if performed, document actual sample size, labeling approach, thresholds, observations, and limitations in `docs/FINAL_REPORT.md`; report formal metrics only with suitable labeled data.
- [ ] T057 [US8] Run `uv run pytest` and `uv run ruff check .`, resolve failures attributable to this feature, record actual outputs, verify acceptance-criteria/user-story traceability in `docs/TEST_RESULTS.md`, and capture genuine application screenshots under `docs/screenshots/`.

## Phase 10: Optional User Story 7 - Contextual LLM Comparison (Priority: P2, Non-MVP)

**Purpose**: Optional follow-on only after all mandatory MVP tasks and acceptance checks are complete. No task in this phase blocks CSV, baseline analysis, or MVP acceptance.

- [ ] T058 [US7] Only if separately approved after MVP completion, add an isolated optional LLM adapter and configuration with separately labeled model/configuration/output and failure status; verify baseline analysis and charts remain usable with no LLM credentials and when the LLM fails.

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 (Setup and verification)** has no code prerequisites. Finnhub, market-provider, and Nasdaq-ledger integration tasks remain gated on T005, T006, and T007 respectively; T008 preserves the planning-time-only fallback rule.
- **Phase 2 (Foundation)** follows dependency/configuration setup and blocks story implementation.
- **Phases 3-9 (Mandatory MVP)** depend on Phase 2. Core CSV and baseline work proceeds regardless of provider-gate outcomes. Implement news/market network adapters only after their respective gate passes. Market-session code requires calendar verification and the recorded alignment decision.
- **Phase 10 (Optional LLM)** is non-blocking and may begin only after mandatory MVP acceptance; it is not a prerequisite for any earlier phase.

### Key Within-Phase Dependencies

- T014 and T016 depend on T009-T012; T017 depends on T005 and the normalized models/errors.
- T020-T024 depend on the normalized records from Phase 2; T026-T028 depend on validated records and the VADER dependency audit.
- T030-T032 depend on sentiment results; T034-T045 depend on the market contract, T006/T007 decisions, validated data, and tested return/alignment behavior.
- T047-T048 and T051-T053 compose completed core operations; T054-T057 document and verify actual behavior after implementation.

### Parallel Opportunities

- Within Phase 1, provider/calendar research can be conducted independently, but findings must be consolidated into `research.md` without conflicting edits.
- Foundation models and error types (T009-T010) can be developed in parallel. Test tasks marked `[P]` may be prepared independently of implementation when their inputs/contracts are stable.
- CSV news work and source-gate research are independent; CSV work does not wait for Finnhub. Market CSV parsing can proceed independently of the optional live market adapter, while session assignment must wait for the calendar gate.
- Sentiment aggregation and visualization work follows its explicit data dependencies; the LLM follow-on is independent only after MVP acceptance.

## Requirement Traceability

US1: T003-T018, T052-T053. US2: T019-T024. US3: T025-T028. US4: T029-T032. US5: T006-T008, T033-T045. US6: T046-T048. US8: T001-T004, T009, T012, T049-T057. US7 is optional and non-blocking: T058.

| Specification requirements | Tasks |
|---|---|
| FR-001, FR-002 | T011-T016, T052-T053 |
| FR-003, FR-004 | T005, T013-T018 |
| FR-005 | T019-T024 |
| FR-006 | T010, T018, T023-T024, T041, T053 |
| FR-007, FR-008, FR-009 | T025-T028 |
| FR-010 | T029-T030 |
| FR-011 | T031-T032 |
| FR-012 | T006-T008, T033-T045 |
| FR-013 | T045, T048, T053 |
| FR-014 | T058 |
| FR-015 | T046-T048, T053 |
| FR-016 | T003-T004, T013-T014, T049-T054 |
| QR-001, QR-002 | T013, T015, T018-T032, T033-T043, T046, T050 |
| QR-003 | T001, T054-T055 |
| QR-004 | T004, T054, T057 |
| QR-005 | T056 |
| QR-006 | T055-T057 |
| QR-007 | T057-T058 |