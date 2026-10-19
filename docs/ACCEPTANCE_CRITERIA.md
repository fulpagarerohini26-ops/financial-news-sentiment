# Financial News Sentiment Analyzer — Acceptance Criteria

## 1. Purpose

This document defines measurable conditions for accepting the first working release of the Financial News Sentiment Analyzer.

## 2. Functional Acceptance Criteria

| ID | Requirement | Acceptance condition |
|---|---|---|
| AC-01 | Company selection | The user can enter a supported ticker and the application validates the input. |
| AC-02 | Date range | The user can select a valid date range for the news query. |
| AC-03 | News retrieval | A verified Finnhub response or local CSV dataset is converted into the documented logical news-record structure. |
| AC-04 | Empty response | If no news is available, the application displays an informative message rather than failing. |
| AC-05 | Headline sentiment | Every valid non-empty headline receives a numerical sentiment score and a label. |
| AC-06 | Summary sentiment | Every available non-empty summary receives a score and label; missing summaries are handled explicitly. |
| AC-07 | Label mapping | VADER compound scores <= -0.05 are Negative, >= 0.05 are Positive, and strictly between -0.05 and 0.05 are Neutral; exact boundaries are tested. |
| AC-08 | Aggregate statistics | Headline and summary sentiment statistics are calculated separately, using only available valid scores. |
| AC-09 | Sentiment charts | The application displays sentiment distribution and sentiment trends for the selected period; plotted values match the underlying records and aggregation. |
| AC-10 | Price comparison | The application displays stock-price trends and a sentiment-versus-price comparison using the selected alignment mode and documented close-to-close return calculation. |
| AC-11 | LLM extension | If implemented, contextual LLM results are clearly separated from baseline results. |
| AC-12 | Error handling | API errors, invalid inputs, and missing data produce understandable feedback. |
| AC-13 | CSV and offline support | Local CSV datasets support automated tests, demonstrations, and provider fallback; the core workflow runs from local data without network access. Included samples are identified as non-live and include provenance and limitations. |
| AC-14 | NSE session assignment | With the preferred mode, timezone-aware news in (previous NSE session close, current session close) maps to that session; after-close, weekend, and holiday news maps to the next eligible session using Asia/Kolkata boundaries. |
| AC-15 | Daily fallback decision | At planning, if the session-alignment estimate threatens another mandatory MVP deliverable by the capstone deadline, the affected deliverable, rationale, and calendar-day fallback selection are recorded before implementation. |
| AC-16 | Session fallback alignment | If calendar-day fallback is selected, only matching ticker/calendar-date observations are compared; unmatched weekend/holiday data is disclosed and excluded. |
| AC-17 | Required charts | The application displays a sentiment distribution chart, sentiment trend chart, stock-price trend chart, and sentiment-versus-price chart; each is checked against controlled data. |
| AC-18 | Manual review feasibility | The project records whether a small manual sentiment review was feasible and why; if performed, observations and limitations are documented. Formal metrics are optional and only reported when supported by suitable labeled data. |

## 3. Quality Acceptance Criteria

| ID | Requirement | Acceptance condition |
|---|---|---|
| QA-01 | Testability | Automated unit tests cover validation, VADER threshold boundaries, separate headline/summary aggregation, CSV loading, error handling, and the selected price-alignment mode without live services. |
| QA-02 | Reproducibility | A reviewer can install dependencies and run the documented application commands. |
| QA-03 | Secret management | No real API key or credential is present in tracked project files. |
| QA-04 | Transparency | The UI or documentation identifies the data source, baseline method, and limitations. |
| QA-05 | Evidence | Final submission includes genuine screenshots and recorded test results. |
| QA-06 | Evaluation | The manual-review feasibility decision is recorded; where review is feasible, actual observations and limitations are reported. Formal classification metrics may be reported when a suitable labeled dataset is available. |

## 4. Baseline Sentiment Evaluation

A small manually reviewed sample should be used where feasible to discuss the baseline classifier's strengths and limitations. The project shall record the feasibility decision and rationale.

The test set should include positive, negative, and neutral financial text examples.

Formal metrics may be reported when a suitable labeled dataset is available. Where reported, include:

- Accuracy
- Per-class precision and recall
- Macro F1-score
- Confusion matrix

The dataset size, labeling approach, classification thresholds, and observed metrics shall be documented.
No metric may be estimated or claimed without actual observations.

## 5. Stock-Price Analysis Evaluation

The application shall document:

- The source of the stock-price data.
- The price and sentiment aggregation intervals.
- The NSE exchange calendar and Asia/Kolkata timezone used by the preferred session-based mode.
- The planning rationale and selected mode if calendar-day fallback is used.
- The close-to-close return calculation: `((current close - previous NSE session close) / previous NSE session close) * 100`.
- How timestamps and market trading days are aligned.
- The statistical method used, if correlation is calculated.
- The limitations of interpreting correlation.

No minimum correlation or trading-prediction accuracy is assumed in this project definition.

## 6. Completion Decision

A requirement is accepted only after its acceptance condition has been tested and the result recorded.

Unimplemented optional features shall be reported as deferred rather than marked complete.

Final status: Pending implementation and verification.