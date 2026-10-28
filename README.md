Pending: 
(1) Update the repository URL, author details, and execution commands later when your application structure is finalized.
(2) Add src/financial_news_sentiment/app.py to run app

# GenAI-Powered Financial News Sentiment Analyzer

## 1. Project Overview

The GenAI-Powered Financial News Sentiment Analyzer is a Python-based application designed to analyze financial news and visualize its sentiment in relation to stock-market movements.

Financial analysts and investors face challenges in tracking large volumes of financial news and understanding the potential implications of news sentiment. This project aims to simplify that process by applying Natural Language Processing (NLP), sentiment analysis, data visualization, and optional Large Language Model (LLM)-based contextual analysis.

The application will retrieve company-specific financial news, analyze available headlines and summaries, classify sentiment as Positive, Negative, or Neutral, and display sentiment trends alongside stock-price movements.

**Project status:** Project definition and planning.

Features described in this README represent the intended scope. They should not be considered implemented until verified through testing.

**Implemented milestone:** Offline CSV ingestion and a standalone VADER baseline that independently scores headlines and available summaries are available. The end-to-end example uses only the clearly synthetic fixture; the dashboard, stock-price comparison, and contextual LLM analysis remain out of scope for this milestone.

## 2. Objectives

The primary objectives are to:

- Retrieve company-specific financial news from Finnhub, subject to verification of its endpoint, fields, access requirements, terms, and usage limits.
- Process and validate financial news records.
- Calculate sentiment scores for headlines and available summaries.
- Classify sentiment as Positive, Negative, or Neutral.
- Calculate aggregate sentiment statistics.
- Visualize sentiment distributions and trends.
- Explore the relationship between news sentiment and stock-price movements.
- Optionally extend the baseline approach with contextual LLM-based sentiment analysis.
- Provide a reproducible, testable, and documented application using predominantly free development tools.

## 3. Key Features

### Core Features — Minimum Viable Product

1. **Company selection:** Enter or select a supported company ticker.
2. **Date filtering:** Select the period for news analysis.
3. **Financial news retrieval:** Retrieve company-specific news from the configured data source.
4. **Data preprocessing:** Validate records and handle missing fields and duplicate articles.
5. **Headline sentiment:** Analyze the sentiment of each available headline.
6. **Summary sentiment:** Analyze available summaries independently of headlines.
7. **Sentiment classification:** Assign Positive, Negative, or Neutral labels using documented thresholds.
8. **Aggregate analysis:** Calculate headline and summary sentiment statistics separately.
9. **Visualization:** Display sentiment distribution and trends.
10. **Stock-price comparison:** Compare sentiment trends with stock-price movements over a compatible period.
11. **Error handling:** Display understandable messages for missing data, invalid inputs, and external service failures.
12. **Local CSV support:** Load datasets for automated tests, demonstrations, and fallback when live news access is unavailable; run the core CSV workflow without network access.

### Optional Enhancements

- LLM-based contextual sentiment analysis.
- Comparison of baseline NLP and LLM-based sentiment results.
- Export of analysis results to CSV.
- Additional company comparison and filtering features.
- A bounded agentic workflow for analysis routing and result validation.

Optional features will be implemented only after the core application is functional and tested.

## 4. Technology Stack

The planned technology stack is:

| Component | Planned technology |
|---|---|
| Programming language | Python 3.12 baseline |
| Environment and dependencies | uv |
| Development IDE | Visual Studio Code |
| Version control | Git and GitHub |
| Specification-driven development | GitHub Spec Kit |
| News data | Finnhub |
| Data processing | Pandas and NumPy |
| Baseline sentiment analysis | VADER |
| Visualization | Plotly and/or Matplotlib |
| User interface | Streamlit |
| Testing | pytest |
| Code quality | Ruff |
| Optional LLM inference | Compatible local model or separately configured inference service |

The VADER baseline uses compound thresholds of Negative <= -0.05, Positive >= 0.05, and Neutral strictly between those values. The `vadersentiment>=3.3.2` dependency is declared in `pyproject.toml`; the lockfile resolves it to version 3.3.2.

The current baseline uses `vaderSentiment` 3.3.2 from the local Python environment. It independently analyzes the trimmed headline and each non-empty summary, preserves the original article, and records headline results alongside an explicit summary status and optional summary score/label. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for thresholds, missing-text behavior, batch rules, separate aggregate definitions, limitations, tests, and the offline example.

Run the offline demonstration from the repository root:

```powershell
uv run python scripts/demo_baseline_sentiment.py
```

The demo makes no network requests and labels its fixture as synthetic, not real financial news.

Evaluate the VADER headline baseline against the checked-in synthetic pipeline fixture:

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py
```

This fixture is not real financial news and its metrics are not evidence of
real-world accuracy. See [docs/EVALUATION.md](docs/EVALUATION.md) for the
dataset schema, labeling guide, measured synthetic results, and evaluation
limitations. A separate local-only real-news dataset validation and seeded
split workflow is documented there, including a one-request permission-gated
collector, offline CSV import, prediction-free annotation sheets, disagreement
reporting, and hash-verified split freeze. Real-news collection remains blocked
pending applicable terms and rights review.

The application will prioritize local execution and free tools. External API usage and optional LLM inference may be subject to provider limits and hardware requirements.

## 5. High-Level Processing Workflow

1. The user selects a company ticker and date range.
2. The application retrieves financial news from Finnhub or loads a documented local CSV dataset.
3. The application validates and normalizes the news records.
4. Headline and summary text are processed independently.
5. The baseline NLP method calculates sentiment scores.
6. Scores are mapped to Positive, Negative, or Neutral labels using documented thresholds.
7. Aggregate sentiment statistics are calculated.
8. Suitable stock-price data is aligned with sentiment using Nasdaq market sessions and the America/New_York timezone; news in (previous session close, current session close) maps to that session, and after-close/weekend/holiday news maps to the next eligible session. At the planning checkpoint, calendar-day aggregation may be chosen only if session alignment threatens another mandatory MVP deliverable by the capstone deadline; record the rationale.
9. The application generates sentiment and price-comparison visualizations.
10. If implemented, an optional LLM extension provides contextual sentiment analysis for comparison with the baseline.

## 6. Data Sources

### Financial News

Selected primary news provider: Finnhub, subject to verification before integration.

- Official website: https://finnhub.io/
- API documentation: https://finnhub.io/docs/api

The Finnhub Company News API endpoint, response fields, availability, usage limits, and applicable terms will be verified before implementation. No unverified provider capability or free quota is assumed. Configure the API key locally as described in API Configuration; never commit the key.

### Stock-Price Data

A suitable stock-price source will be selected and verified during technical planning. Nasdaq is the only MVP exchange; comparison requires ticker, trading date, and closing price.

The implementation will document the selected provider, fields, data coverage, and applicable usage restrictions.

Daily return is calculated as `((current close - previous Nasdaq session close) / previous Nasdaq session close) * 100`. Market-session alignment is preferred; calendar-day aggregation may be selected at planning only if the estimate threatens another mandatory MVP deliverable by the capstone deadline. The selected mode and rationale must be documented.

### Sample Data

Local CSV datasets are required for automated tests, classroom demonstrations, and fallback when live news access is unavailable. The core CSV workflow runs without network access.

Sample data will be clearly identified as non-live and will not be represented as real financial news or market observations.

## 7. Project Structure

The planned project structure is:

```text
financial-news-sentiment/
├── .specify/
├── .github/
├── docs/
│   ├── PROJECT_CHARTER.md
│   ├── REQUIREMENTS.md
│   ├── USER_STORIES.md
│   ├── ACCEPTANCE_CRITERIA.md
│   ├── SCOPE_AND_ASSUMPTIONS.md
│   ├── DATA_SOURCE.md
│   ├── RISKS_AND_CONSTRAINTS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── TEST_PLAN.md
│   ├── TEST_RESULTS.md
│   ├── METHODOLOGY.md
│   ├── LIMITATIONS.md
│   ├── FINAL_REPORT.md
│   └── screenshots/
├── src/
│   └── financial_news_sentiment/
├── tests/
├── data/
│   ├── sample/
│   └── evaluation/
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

This structure is a proposed design and will be finalized during technical planning.

## 8. Local Setup

### Prerequisites

- Windows 64-bit or another supported operating system.
- Python 3.12.
- uv.
- Git.
- Visual Studio Code.
- GitHub Desktop, if preferred for graphical Git operations.

### Environment Setup

Clone the repository or open the existing project folder in VS Code.

From the project root, run:

```powershell
uv python pin 3.12
uv venv --python 3.12
```

Activate the environment in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies from the committed project configuration:

```powershell
uv sync
```

The dependency configuration will be maintained as the project evolves.

### API Configuration

For live Finnhub retrieval, copy `.env.example` to `.env` and replace the placeholder with your Finnhub API key. The `.env` file is excluded from Git. The application can read the key with `get_finnhub_api_key()` from `financial_news_sentiment.settings`; the value is loaded from the process environment first, then the project `.env` file. Local CSV workflows do not require credentials.

Alternatively, set the environment variable directly in PowerShell for the current terminal:

```powershell
$env:FINNHUB_API_KEY = "your_finnhub_api_key_here"
```

An example configuration may be provided in `.env.example`, without any real credentials.

Never commit API keys or other secrets.

To make one controlled Company News request and print only the status, count,
and a few sanitized fields, see the [Finnhub smoke-test procedure](docs/DATA_SOURCE.md#company-news-manual-smoke-test).

## 9. Running the Application

The final application entry point and launch command will be confirmed during implementation.

The planned interface framework is Streamlit. Once the entry point has been created, the application will be launched using a command similar to:

```powershell
uv run streamlit run src/financial_news_sentiment/app.py
```

The command above is a planned example, not a claim that the application entry point already exists.

## 10. Testing and Evaluation

Testing will cover:

- News data retrieval and response validation.
- Missing headlines and summaries.
- Sentiment scoring and classification.
- Aggregate sentiment calculations.
- Empty data and API failure handling.
- Stock-price and sentiment time alignment.
- Dashboard functionality.
- Optional LLM response handling.
- Reproducibility of setup and execution.

The project will record whether a small manually reviewed sample is feasible and why. Where feasible, use a manually labeled financial-text sample to discuss strengths and limitations.

Formal accuracy, per-class precision and recall, macro F1-score, and a confusion matrix may be reported when supported by a suitable labeled dataset. Report only observed results, with dataset size, labeling approach, thresholds, and limitations.

The relationship between sentiment and price movements will be analyzed separately from classifier quality. Correlation will not be treated as proof of causation or predictive performance.

Actual test results and evaluation metrics will be added after execution.

## 11. Documentation and Deliverables

The final submission will include:

- Working source code.
- Clear methodology and architecture documentation.
- Requirements and acceptance criteria.
- Test cases and actual test results.
- Output screenshots and evaluation evidence.
- Setup and user instructions.
- Known limitations and future enhancements.
- A final project report.

## 12. Responsible Use and Limitations

Sentiment scores are model-generated estimates and may not correctly interpret all financial language or market context.

Stock prices can be affected by many factors beyond the news included in this application.

The application is intended for educational, analytical, and exploratory purposes. It does not guarantee stock-price predictions, investment returns, or trading outcomes, and it does not execute trades.

Results should be interpreted in light of data coverage, model limitations, and the documented methodology.

## 13. Development Methodology

The project will follow a specification-driven and iterative development approach using GitHub Spec Kit.

The planned lifecycle is:

1. Project definition.
2. Requirements and acceptance criteria.
3. Architecture and technical planning.
4. Task breakdown.
5. Incremental implementation.
6. Automated and manual testing.
7. Evaluation and refinement.
8. Documentation and evidence collection.
9. Final release and submission.

Implementation will begin only after the core requirements and acceptance criteria have been reviewed.

## 14. Project Status

Current stage: Project definition and planning.

Next milestone: Complete and validate requirements, user stories, acceptance criteria, data-source assumptions, and risk documentation.

## 15. References

- Supplied capstone problem statement: GenAI-Powered Financial News Sentiment Analyzer.
- Finnhub official website: https://finnhub.io/
- Finnhub API documentation: https://finnhub.io/docs/api
- GitHub Spec Kit: https://github.com/github/spec-kit
- Python documentation: https://docs.python.org/3/
- Streamlit documentation: https://docs.streamlit.io/
- pytest documentation: https://docs.pytest.org/

Additional model, library, and data-provider references will be recorded as those components are selected.