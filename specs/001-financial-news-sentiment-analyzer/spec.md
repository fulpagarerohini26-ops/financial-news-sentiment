# Feature Specification: GenAI-Powered Financial News Sentiment Analyzer

**Feature Branch**: `001-financial-news-sentiment-analyzer`

**Created**: 2026-10-18

**Status**: Draft for review

**Input**: User description: Create an implementation-ready specification from the existing project documentation for financial news retrieval, headline and summary sentiment analysis, three-class classification, sentiment visualization, comparison with stock-price movements, and optional LLM-based contextual sentiment. Do not implement application code or assume unverified provider behavior.

## Clarifications

### Session 2026-10-18

- Q: When may the project select daily aggregation instead of market-session alignment? → A: At the planning checkpoint, only if the estimate indicates session alignment would jeopardize another mandatory MVP deliverable by the capstone deadline; document the rationale and selected mode.
- Q: Which single exchange calendar governs session assignment? → A: Nasdaq only.
- Q: How are news timestamps assigned to Nasdaq sessions? → A: Use the close-to-close window (previous session close, current session close]; after-close, weekend, and holiday articles go to the next eligible session.
- Q: At what checkpoint is the schedule-based fallback selected? → A: During planning, before implementation, with the threatened MVP deliverable and rationale recorded.

## User Scenarios & Testing

### User Story 1 - Analyze a Company and Date Range (Priority: P1)

As a financial analyst or project demonstrator, I want to select a company ticker and analysis period and retrieve available company-specific news so that I can explore the news published for that scope.

**Why this priority**: News retrieval and scope selection are the entry point for all required analysis.

**Independent Test**: Submit a supported ticker and valid date range using a controlled provider response; verify that the selected scope is applied and records are returned in the application's logical news-record shape.

**Acceptance Scenarios**:

1. **Given** a supported ticker and valid date range, **When** the user requests analysis, **Then** the system retrieves available news for that company and period and identifies the data source.
2. **Given** an invalid ticker or invalid date range, **When** the user requests analysis, **Then** the system explains the input problem and does not present results for a different scope.
3. **Given** a successful retrieval with no matching articles, **When** the results are presented, **Then** the system shows an informative empty state rather than treating the result as an error or as neutral sentiment.

### User Story 2 - Validate and Prepare News Records (Priority: P1)

As a user, I want incomplete, malformed, and duplicate news records handled consistently so that the analysis reflects usable articles without hiding data-quality problems.

**Why this priority**: Invalid or repeated records can distort sentiment counts and trends.

**Independent Test**: Supply controlled records containing missing optional fields, missing required fields, malformed timestamps, duplicate identifiers, and duplicate URLs; verify record disposition and any data-coverage notice.

**Acceptance Scenarios**:

1. **Given** a record with a usable headline and publication time but no summary, **When** it is processed, **Then** it remains available for headline analysis and its summary is marked unavailable.
2. **Given** a record without usable headline text or a valid publication time, **When** it is processed, **Then** it is excluded from the affected analysis and the data-quality issue is counted or reported.
3. **Given** two records with the same reliable article identifier, **When** they are processed, **Then** only one contributes to analysis and the deduplication rule is documented.
4. **Given** records that cannot be reliably identified as duplicates, **When** they are processed, **Then** the system does not silently merge them.

### User Story 3 - Analyze Headline and Summary Sentiment (Priority: P1)

As a user, I want non-empty headlines and summaries scored and classified independently so that I can inspect each text type without missing summaries being mistaken for neutral sentiment.

**Why this priority**: Independent baseline sentiment is the central analytical capability and is required before any optional LLM extension.

**Independent Test**: Use controlled positive, negative, neutral, boundary-score, empty, and missing text examples; verify numeric scores and labels against the documented method and thresholds.

**Acceptance Scenarios**:

1. **Given** a valid non-empty headline, **When** baseline analysis runs, **Then** that headline receives a numeric score and one Positive, Negative, or Neutral label.
2. **Given** a valid non-empty summary, **When** baseline analysis runs, **Then** its score and label are calculated separately from the headline.
3. **Given** an empty or missing summary, **When** results are presented, **Then** summary sentiment is unavailable and is not counted as Neutral.
4. **Given** a score on a classification boundary, **When** the label is assigned, **Then** the documented threshold rule determines the result consistently.

### User Story 4 - View Sentiment Statistics and Trends (Priority: P1)

As a user, I want to view sentiment distributions and trends for the selected company and period so that I can understand how available headline and summary sentiment varies over time.

**Why this priority**: Aggregation and visualization turn article-level outputs into the project's required reviewable analysis.

**Independent Test**: Provide a fixed set of scored records across multiple dates; verify separate headline and summary counts/statistics and verify that plotted values match those aggregates.

**Acceptance Scenarios**:

1. **Given** valid scored records, **When** aggregate results are displayed, **Then** headline and summary results remain separate and use only available valid scores.
2. **Given** no valid scores for an interval, **When** a trend is displayed, **Then** the interval is shown as unavailable or absent, not as zero or Neutral.
3. **Given** available records across the selected period, **When** the user views results, **Then** sentiment distribution and time trend are shown with the selected period and aggregation basis identified.

### User Story 5 - Compare Sentiment With Stock-Price Movements (Priority: P1)

As a user, I want sentiment aggregates compared with suitable stock-price observations over a compatible period so that I can explore whether the series vary together.

**Why this priority**: The original project objectives and approved scope explicitly retain price comparison as part of the MVP, while keeping its interpretation exploratory.

**Independent Test**: Supply controlled sentiment and market observations with known dates and gaps; verify documented alignment, visible coverage, and that the displayed comparison uses only compatible observations.

**Acceptance Scenarios**:

1. **Given** suitable news sentiment and market data for a compatible period, **When** the comparison is displayed, **Then** the aligned intervals and data sources are identified.
2. **Given** missing market observations or incompatible date coverage, **When** the comparison is requested, **Then** missing coverage is disclosed and no values are silently invented or forward-filled.
3. **Given** a statistical relationship is displayed, **When** users interpret it, **Then** it is described as exploratory and not as proof of causation or a guaranteed prediction.

### User Story 6 - Understand Results and Limitations (Priority: P1)

As a user, I want the data source, analysis method, date range, coverage, and limitations disclosed so that I can interpret outputs responsibly.

**Why this priority**: Sentiment and market data are incomplete estimates; transparent context is necessary to prevent unsupported financial conclusions.

**Independent Test**: Review a result with source and method metadata plus a missing-data case; verify that required context and limitations are available and no investment advice or causal claim is presented.

**Acceptance Scenarios**:

1. **Given** an analysis result, **When** it is presented, **Then** the selected source, analysis method, thresholds, period, and relevant coverage limitations are available to the user.
2. **Given** a sentiment-price comparison, **When** it is presented, **Then** it is distinguished from stock-price prediction and does not claim sentiment caused a movement.
3. **Given** a retrieval or processing failure, **When** the user views the result, **Then** the failure is described without presenting incomplete data as complete.

### User Story 7 - Optionally Compare Contextual LLM Sentiment (Priority: P2)

As a user, I want an optional contextual LLM analysis that is clearly separated from baseline NLP results so that I can compare interpretations without making the baseline depend on an LLM.

**Why this priority**: Contextual GenAI supports the capstone theme but is explicitly optional and must not block the reliable baseline.

**Independent Test**: When the extension is implemented, run the same controlled input with the baseline available and verify that LLM output, model/configuration, and failures are separately identified; when it is not configured, verify that baseline analysis remains usable.

**Acceptance Scenarios**:

1. **Given** no LLM is configured, **When** baseline analysis is requested, **Then** all mandatory baseline functions remain available.
2. **Given** an LLM extension is configured and invoked, **When** contextual output is returned, **Then** it is labeled as LLM-generated, kept distinct from baseline scores, and accompanied by its model/configuration.
3. **Given** an LLM service fails or returns invalid output, **When** the result is presented, **Then** baseline results remain distinguishable and the LLM failure is reported without being treated as a baseline result.

### User Story 8 - Reproduce and Evaluate the Project (Priority: P1)

As a project reviewer, I want documented setup, configuration, tests, and evaluation evidence so that I can reproduce the baseline analysis and assess its limitations.

**Why this priority**: Reproducibility and evidence are required capstone deliverables, not optional implementation details.

**Independent Test**: Follow the documented setup in a clean supported environment, run the automated tests, and review the recorded evaluation protocol and results.

**Acceptance Scenarios**:

1. **Given** the committed dependency and configuration documentation, **When** a reviewer follows the setup instructions, **Then** the supported environment and application commands are documented without requiring secrets to be committed.
2. **Given** MVP acceptance is being prepared, **When** evaluation readiness is reviewed, **Then** the project records whether a small manual sentiment review is feasible and the reason for its determination.
3. **Given** a manual review or formal evaluation is performed, **When** results are reported, **Then** the sample size, labeling approach, thresholds, actual observations, and limitations are documented; formal metrics are included only when supported by a suitable labeled dataset.

### Edge Cases

- Empty news response, empty headline, missing summary, missing source or URL, malformed record, and invalid publication timestamp.
- Duplicate article identifiers, duplicate URLs, and records without a reliable deduplication key.
- Invalid ticker, reversed or otherwise invalid date range, and no data for the selected period.
- Provider timeout, authentication failure, rate limiting, service outage, and malformed provider response; report the failure without asserting unverified retry behavior.
- Missing market sessions, differing news and market coverage, timezone differences, and non-trading dates.
- No valid sentiment scores for an aggregation interval; do not substitute zero or Neutral.
- Optional LLM unavailable, misconfigured, rate-limited, or returning invalid/unverifiable output; baseline remains independent.
- Sample data used in a demonstration; it must be labeled as sample data and not presented as live provider data.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST let the user provide a company ticker and MUST validate that it is acceptable for the selected data source before analysis.
- **FR-002**: The system MUST let the user select a date range and MUST reject invalid ranges without silently changing the requested period.
- **FR-003**: The system MUST retrieve available company-specific financial news for the selected ticker and date range from a configured, verified source.
- **FR-004**: The system MUST normalize provider records into logical news fields: ticker, headline, publication time, optional summary, optional source, optional article URL, and optional provider article identifier. Actual provider field names and availability MUST be verified and documented before integration.
- **FR-005**: The system MUST validate required record content, handle missing optional fields, and apply a documented duplicate-handling rule. Records with matching reliable provider identifiers MUST NOT contribute more than once. Records without a reliable identity MUST NOT be silently merged.
- **FR-006**: The system MUST handle empty results, malformed responses, invalid inputs, provider errors, network failures, and rate limits with understandable status or error feedback. It MUST NOT present failed or partial retrieval as complete without disclosure.
- **FR-007**: The system MUST calculate a baseline sentiment score and Positive, Negative, or Neutral label for each valid non-empty headline.
- **FR-008**: The system MUST calculate summary sentiment separately for each available non-empty summary. Missing or empty summaries MUST be marked unavailable, not Neutral.
- **FR-009**: The system MUST use documented baseline classification thresholds, including deterministic handling of threshold boundaries. The baseline method is VADER. Sentiment classification uses the VADER compound score with thresholds: Positive >= 0.05, Negative <= -0.05, Neutral between -0.05 and 0.05.
- **FR-010**: The system MUST calculate aggregate sentiment statistics for headlines and summaries separately, using only valid available scores and identifying the aggregation basis.
- **FR-011**: The system MUST provide sentiment distribution and trend visualizations for the selected period when valid data is available. Visualized counts and values MUST correspond to the displayed records and aggregation rules.
- **FR-012**: The system MUST compare aggregated sentiment with stock-price movements using Nasdaq market sessions by default. If, at the planning checkpoint, the estimate indicates that session alignment would jeopardize another mandatory MVP deliverable by the capstone deadline, the project MAY select calendar-day aggregation as the fallback and MUST record the decision and rationale before implementation. The system MUST identify the price-data source, time basis, alignment rule, coverage, and any statistical method used.
- **FR-013**: The system MUST describe sentiment-price relationships as exploratory, MUST distinguish sentiment analysis from stock-price prediction, and MUST NOT claim that correlation proves causation or implies guaranteed investment outcomes.
- **FR-014**: The system MAY provide an LLM-based contextual sentiment extension. If present, it MUST be optional, separately labeled from baseline NLP, and document the model and configuration. Baseline scoring and visualization MUST remain usable without LLM configuration or service access.
- **FR-015**: The system MUST identify whether results use live provider data or sample data and MUST disclose the data source, relevant date range, analysis method, and material limitations.
- **FR-016**: The system MUST support local CSV datasets for automated tests, demonstrations, and fallback operation when the live news provider is unavailable. The core analysis workflow MUST be runnable from local datasets without network access. Any included sample data MUST document its provenance and limitations and MUST be clearly identified as non-live data.

### Quality Requirements

- **QR-001**: Core validation, sentiment classification, aggregation, and error-handling logic MUST be independently testable without a live news/market API or LLM service.
- **QR-002**: Automated unit tests MUST cover valid and invalid news records, missing fields, duplicate handling, sentiment labels and threshold boundaries, separate aggregates, empty data, and relevant provider/service failures.
- **QR-003**: Dependencies, supported runtime, configuration requirements, sentiment method and thresholds, data transformations, evaluation protocol, setup, and execution instructions MUST be documented sufficiently for reproduction.
- **QR-004**: API keys, access tokens, and other secrets MUST NOT appear in tracked files. External data MUST be used in accordance with verified provider terms, usage limits, licensing, and attribution requirements.
- **QR-005**: Before MVP acceptance, the project MUST record whether a small manually reviewed sentiment sample was feasible and the reason for that assessment. Where feasible, the baseline SHOULD be reviewed against manually labeled financial text, with the sample size, labeling approach, thresholds, observations, and limitations documented. Formal accuracy, per-class precision and recall, macro F1-score, and confusion-matrix metrics MAY be reported when a suitable labeled dataset supports them. All reported results MUST be based on actual observations.
- **QR-006**: Documentation and acceptance evidence MUST reflect verified implementation and executed results. Planned, optional, or unverified behavior MUST NOT be reported as implemented.
- **QR-007**: All mandatory acceptance criteria MUST be verified before the MVP is considered complete. Optional features may be deferred and MUST be reported as deferred rather than marked complete.

### Requirement Traceability

| Requirement | Acceptance criteria | User stories |
|---|---|---|
| FR-001 | AC-01 | US-01 |
| FR-002 | AC-02 | US-01 |
| FR-003, FR-004 | AC-03, AC-04 | US-01, US-02 |
| FR-005 | AC-14 | US-02 |
| FR-006 | AC-12 | US-01, US-02 |
| FR-007, FR-009 | AC-05, AC-07 | US-03 |
| FR-008, FR-009 | AC-06, AC-07 | US-03 |
| FR-010 | AC-08 | US-04 |
| FR-011 | AC-09 | US-04 |
| FR-012 | AC-10, AC-15, AC-18 | US-05 |
| FR-013 | AC-16 | US-05, US-06 |
| FR-014 | AC-11, AC-17 | US-07 |
| FR-015 | QA-04 | US-06, US-08 |
| FR-016 | AC-13 | US-08 |
| QR-001, QR-002 | QA-01 | US-02, US-03, US-04, US-05 |
| QR-003 | QA-02 | US-08 |
| QR-004 | QA-03 | US-08 |
| QR-005 | QA-06 | US-08 |
| QR-006 | QA-04, QA-05 | US-06, US-08 |
| QR-007 | QA-01 through QA-06 | US-01 through US-08 |

### Acceptance Criteria

The following preserves the project acceptance-criteria identifiers and adds only criteria needed to make data handling, alignment, and baseline independence explicit.

| ID | Requirement | Acceptance condition | Story |
|---|---|---|---|
| AC-01 | Company selection | The user can enter a ticker accepted by the configured source; invalid input receives actionable feedback. | US-01 |
| AC-02 | Date range | The user can select a valid date range; invalid/reversed ranges are rejected without silent substitution. | US-01 |
| AC-03 | News retrieval | Company news is retrieved from the verified Finnhub source or loaded from a valid local CSV dataset; each input is mapped to the documented logical news record. Provider fields are verified before integration. | US-01, US-08 |
| AC-04 | Empty response | No matching news produces an informative empty state, not a crash or fabricated neutral result. | US-01 |
| AC-05 | Headline sentiment | Each valid non-empty headline receives a score and label from the selected baseline method. | US-03 |
| AC-06 | Summary sentiment | Each available non-empty summary receives an independent score and label; missing/empty summaries are unavailable. | US-03 |
| AC-07 | Label mapping | VADER compound scores at or below -0.05 are Negative, scores at or above 0.05 are Positive, and scores strictly between -0.05 and 0.05 are Neutral; tests verify both exact boundaries. | US-03 |
| AC-08 | Aggregate statistics | Headline and summary statistics are separate and use only valid available scores. | US-04 |
| AC-09 | Sentiment charts | The application displays a sentiment-distribution chart and a sentiment-trend chart; both reflect available data for the selected period and identify their aggregation basis. | US-04 |
| AC-10 | Price comparison | The application displays a stock-price trend and a sentiment-versus-price comparison. Daily return is calculated as ((current close - previous Nasdaq session close) / previous Nasdaq session close) * 100; source, interval, coverage, and alignment are disclosed. | US-05 |
| AC-11 | LLM extension | If implemented, contextual LLM results are optional and clearly separated from baseline results; baseline works without them. | US-07 |
| AC-12 | Error handling | Invalid inputs, missing required data, empty responses, API/service failures, and rate limits produce understandable feedback. | US-01, US-02 |
| AC-13 | CSV and offline support | Local CSV datasets can be loaded for tests, demonstration, and provider fallback; the core analysis workflow completes without network access, and sample data is identified as non-live with provenance and limitations documented. | US-08 |
| AC-14 | Record validation and duplicates | Required fields and timestamps are validated; optional fields may be absent; duplicate rules are documented and verified with controlled records. | US-02 |
| AC-15 | Data alignment | In the preferred mode, timezone-aware news timestamps are assigned to the Nasdaq session window (previous session close, current session close] in America/New_York; after-close, weekend, and holiday news is assigned to the next eligible session. Missing observations are disclosed and never imputed. | US-05 |
| AC-16 | Responsible interpretation | Results identify method/data limitations, do not present sentiment as a price prediction or advice, and do not claim correlation proves causation. | US-05, US-06 |
| AC-17 | Baseline independence | Baseline analysis and results remain usable when no LLM is configured or the LLM service fails. | US-07 |
| QA-01 | Testability | Automated unit tests cover core validation, sentiment classification, aggregation, and error handling independently of live services. | US-02 through US-05 |
| QA-02 | Reproducibility | A reviewer can follow documented dependency, configuration, and execution instructions in the supported environment. | US-08 |
| QA-03 | Secret management | No real API key, credential, or token is present in tracked project files. | US-08 |
| QA-04 | Transparency | The interface or documentation identifies data source, baseline method, date scope, relevant coverage, and limitations. | US-06, US-08 |
| QA-05 | Evidence | Genuine screenshots and executed test results are included in the final submission. | US-08 |
| QA-06 | Evaluation | The feasibility and rationale for a small manual review are recorded; where feasible, observations are documented. Formal metrics are reported only when supported by a suitable labeled dataset, and all reported results are actual. | US-08 |
| AC-18 | Alignment fallback decision | At the planning checkpoint, if the session-alignment estimate threatens another mandatory MVP deliverable by the capstone deadline, the project records the affected deliverable, rationale, and selected calendar-day fallback before implementation. Acceptance tests verify the selected mode; no ad-hoc mode switch is made during implementation. | US-05 |

## Key Entities

- **Analysis Request**: User-selected ticker and date range, plus the request's source and analysis configuration.
- **News Article**: A company-related news record with headline and publication time; summary, publisher/source, URL, and provider identifier may be absent.
- **Sentiment Result**: A score, Positive/Negative/Neutral label, text type (headline or summary), method, and threshold configuration associated with an article.
- **Sentiment Aggregate**: A period-based summary of valid article-level sentiment results, with separate headline and summary populations and their counts/coverage.
- **Market Observation**: A ticker-associated price observation with date/time and available price fields, source, and coverage.
- **Comparison Result**: Sentiment aggregates and market observations aligned under a documented interval/time rule, with coverage and interpretation limitations.
- **Evaluation Example**: Financial text, human-assigned sentiment label, labeling guidance, and optional baseline output used to assess classifier performance.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For every valid ticker/date-range test request, the system returns a documented set of retrieved records, a clearly identified empty state, or an actionable error; it does not silently substitute another scope.
- **SC-002**: Every retained non-empty headline in a controlled test set receives exactly one baseline score and one of the three documented labels; every non-empty summary is analyzed separately.
- **SC-003**: Missing summaries and empty aggregation intervals are never counted as Neutral or zero sentiment; aggregate totals match the valid input records in controlled tests.
- **SC-004**: Controlled Nasdaq session tests assign timestamps in (previous close, current close] to that session and after-close, weekend, and holiday timestamps to the next eligible session; any approved fallback uses calendar dates and discloses missing matched observations.
- **SC-005**: All mandatory acceptance scenarios have corresponding verification evidence, and the automated tests for core logic pass before MVP acceptance.
- **SC-006**: A reviewer can follow the documented setup to install dependencies and run the project without any secret committed to the repository.
- **SC-007**: Evaluation documentation records the feasibility decision and rationale for manual review; where performed, it records sample size, labeling approach, thresholds, observations, and limitations. Formal metrics are included only when supported by suitable labeled data, and no unmeasured performance claim is made.
- **SC-008**: Results and documentation distinguish baseline NLP from optional LLM output and distinguish exploratory price comparison from prediction or causation.

## Assumptions

- The primary user is a financial analyst, learner, or project reviewer using the application for educational and exploratory analysis, not for automated trading or personalized investment advice.
- Finnhub is the selected news provider. Its endpoint, fields, access requirements, usage limits, terms, and suitability must still be verified before integration. The API key is to be configured locally and must not be committed.
- A stock-price source has not yet been selected. Market-data availability, adjustment conventions, and terms must be verified before implementation.
- Logical news fields in this specification are application-level concepts; provider response names and availability may differ.
- The baseline is VADER with compound thresholds: Negative <= -0.05, Neutral between -0.05 and 0.05, and Positive >= 0.05.
- Nasdaq is the only exchange in MVP. Use the Nasdaq trading calendar and America/New_York timezone. Assign news in (previous session close, current session close] to the current session; after-close, weekend, and holiday news goes to the next eligible session. At the planning checkpoint, use calendar-day aggregation only if the session-alignment estimate threatens another mandatory MVP deliverable by the capstone deadline; record the decision and rationale.
- A small manual sentiment review SHOULD be performed where feasible and its feasibility assessment recorded. Formal classification metrics MAY be reported when suitable labeled data exists; no minimum classifier score is assumed.
- Data coverage may be incomplete, and sentiment methods may misinterpret financial terminology, negation, sarcasm, or context.
- Live API and optional LLM access may require credentials and may be constrained by terms, usage limits, availability, or local hardware.
- Sample data, if used, is only a clearly identified fallback or demonstration and is not live financial news.
- The requested MVP includes stock-price comparison; the existing constitution's conditional wording is satisfied because this specification retains that objective.

## Open Questions for Review

1. Which market-data provider should be selected after verifying available fields, coverage, access requirements, terms, and usage limits? No provider capability or free quota is assumed.

### Resolved Design Decisions

#### 1. Data Sources and Access Strategy

**Decision:** The application will use **Finnhub** as the primary financial news source for the MVP implementation. Local CSV datasets are also required for automated testing, classroom demonstrations, and fallback operation when provider access is unavailable.

##### News Data

- Finnhub Company News API is the primary source of financial news.
- The system MUST retrieve company-specific news using a valid ticker and date range.
- Retrieved records MUST be normalized into the application's logical news-record structure.
- Provider fields, authentication requirements, availability, usage limits, and terms MUST be verified before integration; no endpoint capability or free quota is assumed.

Required news fields:

- ticker or explicit single-ticker dataset selection
- publication timestamp
- headline

Optional news fields:

- summary
- source
- URL
- provider article identifier

##### Market Data

- Historical stock-price data will be obtained from a documented market-data source selected during implementation.
- MVP comparison requires only:
  - ticker
  - trading date
  - closing price

Additional OHLCV fields MAY be included if available but are not required for MVP completion.

##### Offline Support

- Local CSV datasets MUST be supported for:
  - automated testing
  - classroom demonstrations
  - fallback operation when API access is unavailable
- The core analysis workflow MUST run from local CSV data without network access.
- CSV schemas MUST identify required columns and sample-data provenance; sample records MUST NOT be represented as live data.

##### Credential Management

- API keys MUST be stored using environment variables or local configuration files excluded from version control.
- Secrets MUST NOT be committed to the repository.

##### Failure Handling

- API failures, missing credentials, rate limits, and invalid responses MUST generate clear user-facing messages.
- The system MUST NOT display incomplete data as successful analysis.

##### Rationale

Finnhub is already identified in the project requirements and provides a realistic financial-news source. CSV support ensures reliable demonstrations, reproducible testing, and simplified development.

---

#### 2. Baseline Sentiment Method and Classification Thresholds

**Decision:** The project will use **VADER (Valence Aware Dictionary and sEntiment Reasoner)** as the baseline sentiment-analysis method.

##### Text Analysis Scope

Sentiment analysis MUST be performed independently for:

- article headlines
- article summaries (when available)

Headline sentiment and summary sentiment MUST be calculated separately and reported separately.

##### Classification Method

The VADER compound score will be used for classification.

Default thresholds:

- Positive: compound score >= 0.05
- Negative: compound score <= -0.05
- Neutral: -0.05 < compound score < 0.05

##### Output

For every successfully processed text:

- compound score MUST be stored
- sentiment label MUST be assigned
- text type (headline or summary) MUST be recorded

##### Missing Data Handling

- Missing headlines cannot be analyzed.
- Missing summaries MUST be marked as unavailable.
- Missing summaries MUST NOT be classified as Neutral.

##### Evaluation

- The project MUST record whether a small manually reviewed sample was feasible and why.
- Where feasible, sentiment quality SHOULD be reviewed using a small manually inspected sample of articles.
- Any reported evaluation results MUST be based on actual observations and MUST NOT be estimated or assumed.
- Formal accuracy, precision, recall, macro F1-score, and confusion-matrix reporting MAY be included when a suitable labeled evaluation dataset is available.

##### Rationale

VADER is free, lightweight, deterministic, easy to implement, and suitable for a first NLP capstone project while still demonstrating practical sentiment-analysis concepts.

---

#### 3. Comparison Interval, Timestamp Alignment, and Price Movement

**Decision:** The preferred comparison approach is **Nasdaq Market Session Based Comparison**, using the Nasdaq trading calendar and America/New_York timezone.

At the planning checkpoint, the project MAY select **Daily Aggregation** only if the estimate indicates that session alignment would jeopardize another mandatory MVP deliverable by the capstone deadline. The affected deliverable, estimate, rationale, and selected mode MUST be recorded before implementation; no ad-hoc mode switch is allowed during implementation.

##### Preferred Design: Market Session Based Comparison

- News articles are assigned to trading sessions.
- Sentiment is aggregated at the market-session level.
- Session sentiment is compared with stock-price movement for the same trading session.
- Use the session window (previous Nasdaq session close, current Nasdaq session close], expressed as UTC instants for America/New_York session boundaries.
- News after the current session close, on weekends, or on Nasdaq market holidays MUST be assigned to the next eligible session.
- This rule includes pre-market and regular-session news in the current session when their timestamps fall inside the window.

##### Approved Fallback: Daily Aggregation

If approved at the planning checkpoint under the schedule rule above:

- News sentiment is aggregated by calendar date.
- Sentiment and stock-price observations are compared using daily intervals.
- Only matching ticker/calendar-date observations are compared; weekend or holiday news without a matching market date is disclosed and excluded.
- The selected alignment method MUST be documented in the plan and final project report.

##### Sentiment Aggregation

For each comparison interval, calculate:

- article count
- average sentiment score
- positive article count
- negative article count
- neutral article count

Intervals without valid sentiment data MUST be reported as unavailable rather than assigned an artificial Neutral value.

##### Price Movement Calculation

Daily percentage return is calculated as:
((Current Close - Previous Nasdaq Session Close) / Previous Nasdaq Session Close) * 100

If the previous session close is missing, invalid, or zero, the return is unavailable and MUST NOT be estimated or imputed.


##### Data Alignment

- Sentiment and market data MUST be matched using:
  - ticker
  - comparison interval

- Missing observations MUST be disclosed.
- Missing values MUST NOT be automatically created, estimated, or forward-filled.

##### Visualization Requirements

The MVP MUST provide:

- sentiment distribution chart
- sentiment trend chart
- stock-price trend chart
- sentiment versus stock-price comparison chart

Each chart MUST be verified against controlled input data and the selected aggregation/alignment mode.

##### Interpretation Rules

Results MUST be presented as exploratory analysis only.

The application MUST NOT:

- claim predictive capability
- provide investment advice
- claim that sentiment directly causes stock-price movement
- present correlation as proof of causation

##### Rationale

Market-session alignment best reflects the intended analytical design. Daily aggregation remains an acceptable and lower-complexity fallback suitable for capstone completion.

---

#### 4. Optional LLM-Based Contextual Sentiment

**Decision:** LLM-based sentiment analysis is optional and outside MVP requirements.

##### Scope

If implemented:

- LLM output MUST be clearly separated from VADER output.
- The selected model MUST be documented.
- Baseline functionality MUST continue to operate without LLM access.

##### MVP Requirement

The project is considered complete without any LLM integration.

##### Rationale

The educational objectives of the capstone can be fully achieved using the VADER baseline while keeping implementation effort manageable.

---

#### 5. MVP Completion Criteria

The MVP is considered complete when all of the following are demonstrated:

- Company news can be retrieved from Finnhub or approved local CSV datasets.
- Headlines can be analyzed using VADER.
- Available summaries are analyzed independently from headlines.
- Sentiment labels are generated correctly.
- Sentiment statistics are calculated successfully.
- Required visualizations are displayed.
- Stock-price comparison is available.
- Automated unit tests for validation, VADER classification (including exact threshold boundaries), separate headline/summary aggregation, CSV loading, error handling, and the selected price-alignment mode pass.
- Reproducible setup instructions are documented.
- Screenshots and demonstration evidence are captured.
- Source code is committed to GitHub.
- Project documentation is complete and reviewable.
- A feasibility decision and rationale for a small manual sentiment review are documented; any reported results are actual observations.
