# Project Charter — GenAI-Powered Financial News Sentiment Analyzer

## 1. Project Information

| Field | Details |
|---|---|
| Project name | GenAI-Powered Financial News Sentiment Analyzer |
| Project type | Advanced GenAI and Agentic AI Capstone |
| Project category | Financial news analytics and sentiment analysis |
| Project status | Project definition and planning |
| Development approach | Specification-driven, iterative development |
| Primary language | Python |
| Initial execution environment | Local machine |
| Planned interface | Streamlit |

## 2. Background and Problem Statement

Financial markets generate large volumes of company-specific news, making it difficult for analysts and investors to monitor financial developments and understand the sentiment expressed in news articles.

Traditional manual analysis can be time-consuming and may not provide a consistent view of sentiment trends across headlines and summaries.

This project aims to develop an AI-powered financial sentiment analyzer that retrieves financial news, applies NLP and sentiment-analysis techniques, and visualizes sentiment trends alongside stock-price movements.

The project will also explore an optional LLM-based extension for contextual financial sentiment understanding.

The application is intended to support data exploration and analysis. It will not guarantee market predictions or investment outcomes.

## 3. Project Objectives

The project shall aim to:

1. Retrieve company-specific financial news from Finnhub, subject to verification of its endpoint, fields, access requirements, terms, and usage limits.
2. Analyze headlines and available summaries using NLP sentiment techniques.
3. Classify sentiment into Positive, Negative, and Neutral categories.
4. Calculate aggregate sentiment scores and statistics.
5. Visualize sentiment distributions and trends.
6. Explore the relationship between news sentiment and stock-price movements.
7. Optionally extend the baseline with LLM-based contextual sentiment analysis.
8. Deliver a working, tested, reproducible, and documented application.

## 4. Project Scope

### 4.1 In Scope

The initial release includes:

- Company ticker and date-range selection.
- Company-specific financial news retrieval.
- News data validation and preprocessing.
- Independent headline and summary sentiment analysis.
- Numerical sentiment scores and documented classification thresholds.
- Aggregate sentiment statistics.
- Sentiment distribution and trend visualizations.
- Comparison of sentiment with suitable stock-price data.
- Local CSV datasets for automated testing, classroom demonstrations, and fallback when live news access is unavailable.
- Basic input validation and error handling.
- Automated tests for core processing and analysis.
- Documentation, screenshots, and evaluation results.

### 4.2 Optional Scope

The following enhancements may be implemented after the core release:

- LLM-based contextual sentiment analysis.
- Comparison between baseline NLP and LLM outputs.
- CSV export of analyzed results.
- Additional company-comparison features.
- A bounded agentic workflow for routing analysis and validating results.

### 4.3 Out of Scope

The initial release will not include:

- Automated stock trading or brokerage integration.
- Guaranteed stock-price predictions or investment returns.
- Personalized financial advice.
- Training a large language model from scratch.
- Mandatory paid cloud infrastructure.
- Claims of causal impact without supporting evidence.

## 5. Target Users

### Primary Users

- Financial analysts exploring financial news.
- Learners demonstrating NLP, GenAI, and data-visualization skills.
- Project evaluators reviewing the application's functionality and methodology.

### User Needs

Users should be able to select a company and analysis period, view available news, understand the assigned sentiment labels and scores, and inspect sentiment trends alongside stock-price movements.

## 6. Proposed Technology Stack

| Area | Planned choice |
|---|---|
| Programming | Python 3.12 baseline |
| Environment management | uv |
| IDE | Visual Studio Code |
| Version control | Git and GitHub |
| Specification-driven development | GitHub Spec Kit |
| News provider | Finnhub, subject to verification of endpoint fields, access requirements, terms, and usage limits |
| Data processing | Pandas and NumPy |
| Baseline sentiment | VADER |
| Visualization | Plotly and/or Matplotlib |
| User interface | Streamlit |
| Automated testing | pytest |
| Code quality | Ruff |
| Optional contextual analysis | Compatible local LLM or separately configured inference service |

Nasdaq is the only exchange in MVP comparison. Market-session alignment is preferred, with calendar-day aggregation permitted only when the planning estimate shows session work would threaten another mandatory MVP deliverable by the capstone deadline. The decision and rationale shall be recorded before implementation.

The final libraries and versions will be confirmed during technical planning. Free and open-source tools will be preferred where practical.

## 7. High-Level Methodology

The project will follow a specification-driven development lifecycle:

1. Define the problem, users, scope, assumptions, and objectives.
2. Document functional and non-functional requirements.
3. Define user stories and measurable acceptance criteria.
4. Design the architecture, data flow, and test strategy.
5. Break implementation into small, testable tasks.
6. Implement news retrieval and data preprocessing.
7. Implement baseline sentiment scoring and classification.
8. Develop aggregate analysis and visualizations.
9. Integrate stock-price comparison.
10. Optionally add LLM-based contextual analysis.
11. Evaluate outputs, address defects, and document results.
12. Prepare final code, screenshots, methodology, and submission report.

## 8. Key Deliverables

| ID | Deliverable | Description |
|---|---|---|
| D-01 | Project documentation | Charter, README, requirements, user stories, scope, and assumptions |
| D-02 | Technical design | Architecture, data flow, and implementation plan |
| D-03 | Working application | Financial news analysis interface and core functionality |
| D-04 | Sentiment analysis | Headline and summary scores and classifications |
| D-05 | Visualizations | Sentiment trends and stock-price comparison |
| D-06 | Optional GenAI extension | Contextual sentiment analysis, if implemented |
| D-07 | Testing and evaluation | Automated tests and recorded evaluation results |
| D-08 | Evidence package | Genuine application screenshots and output results |
| D-09 | Final report | Methodology, architecture, findings, limitations, and future scope |
| D-10 | Reproducible release | Source code, dependency configuration, and run instructions |

## 9. Success Criteria

The project will be considered successful when:

1. The application retrieves or loads valid financial news data.
2. Available headlines and summaries are analyzed independently.
3. Sentiment scores and labels follow documented rules.
4. Aggregate sentiment statistics and visualizations are generated.
5. Suitable stock-price data can be compared with sentiment over a compatible period.
6. Errors and missing data are handled transparently.
7. Core functionality has relevant automated tests.
8. Evaluation results are documented without unsupported performance claims.
9. A reviewer can reproduce the setup and run the documented application.
10. The final submission contains working code, methodology, screenshots or results, and appropriate documentation.

Optional features will be reported separately and will not be treated as mandatory success criteria for the MVP.

## 10. Assumptions and Constraints

### Assumptions

- A suitable financial news data source can be accessed or replaced with permitted sample data.
- News headlines, summaries, and timestamps may be incomplete.
- Baseline sentiment methods may misinterpret financial context.
- Stock-price movement depends on factors beyond news sentiment.
- An optional local LLM requires compatible hardware and model resources.

### Constraints

- Prefer free development tools and local execution.
- External API availability, quotas, and terms may restrict data retrieval.
- API credentials must not be committed to Git.
- Dependencies must be reproducible.
- News and market data must be used according to applicable terms.
- Sentiment-price correlation must not automatically be presented as causation.

## 11. Key Risks and Mitigation

| Risk | Mitigation |
|---|---|
| API unavailable or rate-limited | Graceful error handling and optional demo data |
| Incomplete news records | Validation and missing-data reporting |
| Incorrect sentiment classification | Evaluation against manually labeled examples |
| Misleading price comparison | Consistent timestamp alignment and documented limitations |
| LLM inconsistency | Keep the baseline independent and evaluate the extension separately |
| Dependency incompatibility | Use a supported Python version and lock dependencies |
| Credential exposure | Environment-based configuration and Git exclusions |

## 12. Governance and Change Management

Project requirements and scope shall be documented before implementation.

Changes to mandatory features, technology choices, or acceptance criteria shall be recorded in the relevant project documentation and reviewed for their impact on time, complexity, testing, and deliverables.

Git will be used to maintain version history and track implementation changes.

## 13. Definition of Done

The capstone is complete when:

- Mandatory acceptance criteria have been implemented and verified.
- Relevant tests have been executed and actual results recorded.
- The application can be run using the documented instructions.
- The methodology, architecture, limitations, and evaluation are documented.
- Genuine screenshots or other output evidence are available.
- Source code and dependency configuration are ready for submission.
- Known defects and deferred optional features are disclosed.

## 14. Approval Status

Charter status: Draft — for review.

Approval milestone: Confirm project scope, requirements, acceptance criteria, and assumptions before proceeding to detailed technical planning.