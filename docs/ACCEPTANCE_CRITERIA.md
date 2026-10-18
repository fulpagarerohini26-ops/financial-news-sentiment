# Financial News Sentiment Analyzer — Acceptance Criteria

## 1. Purpose

This document defines measurable conditions for accepting the first working release of the Financial News Sentiment Analyzer.

## 2. Functional Acceptance Criteria

| ID | Requirement | Acceptance condition |
|---|---|---|
| AC-01 | Company selection | The user can enter a supported ticker and the application validates the input. |
| AC-02 | Date range | The user can select a valid date range for the news query. |
| AC-03 | News retrieval | A valid data response is converted into a structured collection of news records. |
| AC-04 | Empty response | If no news is available, the application displays an informative message rather than failing. |
| AC-05 | Headline sentiment | Every valid non-empty headline receives a numerical sentiment score and a label. |
| AC-06 | Summary sentiment | Every available non-empty summary receives a score and label; missing summaries are handled explicitly. |
| AC-07 | Label mapping | Positive, Negative, and Neutral labels follow the documented score thresholds. |
| AC-08 | Aggregate statistics | Headline and summary sentiment statistics are calculated separately, using only available valid scores. |
| AC-09 | Sentiment charts | The application displays sentiment distribution and trends for the selected period when data is available. |
| AC-10 | Price comparison | Available stock-price data can be aligned to a compatible time period and compared with aggregated sentiment. |
| AC-11 | LLM extension | If implemented, contextual LLM results are clearly separated from baseline results. |
| AC-12 | Error handling | API errors, invalid inputs, and missing data produce understandable feedback. |
| AC-13 | Offline demo | If implemented, the sample-data mode works without a live news API key. |

## 3. Quality Acceptance Criteria

| ID | Requirement | Acceptance condition |
|---|---|---|
| QA-01 | Testability | Core sentiment and aggregation logic has automated unit tests. |
| QA-02 | Reproducibility | A reviewer can install dependencies and run the documented application commands. |
| QA-03 | Secret management | No real API key or credential is present in tracked project files. |
| QA-04 | Transparency | The UI or documentation identifies the data source, baseline method, and limitations. |
| QA-05 | Evidence | Final submission includes genuine screenshots and recorded test results. |
| QA-06 | Evaluation | Sentiment performance is evaluated against a manually labeled test set, with the results reported honestly. |

## 4. Baseline Sentiment Evaluation

A manually labeled test set shall be created to evaluate the baseline sentiment classifier.

The test set should include positive, negative, and neutral financial text examples.

Where the dataset is sufficiently representative, report:

- Accuracy
- Per-class precision and recall
- Macro F1-score
- Confusion matrix

The dataset size, labeling approach, classification thresholds, and observed metrics shall be documented.

## 5. Stock-Price Analysis Evaluation

The application shall document:

- The source of the stock-price data.
- The price and sentiment aggregation intervals.
- How timestamps and market trading days are aligned.
- The statistical method used, if correlation is calculated.
- The limitations of interpreting correlation.

No minimum correlation or trading-prediction accuracy is assumed in this project definition.

## 6. Completion Decision

A requirement is accepted only after its acceptance condition has been tested and the result recorded.

Unimplemented optional features shall be reported as deferred rather than marked complete.

Final status: Pending implementation and verification.