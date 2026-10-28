# Quickstart: Financial News Sentiment Analyzer

**Status**: The CSV news adapter and independent headline/summary VADER baseline are implemented. The Streamlit app and market-data workflow remain planned.

## Prerequisites

- Python 3.12, per `.python-version`.
- uv and Git.
- No credentials or network access for the CSV-only workflow.
- Permitted news and market CSVs with documented provenance and conventions.

## Environment Setup

From the repository root in PowerShell:

```powershell
uv sync --locked
```

Use `uv run --locked` so the selected Python and lockfile are honored.

## Offline Baseline Demonstration

```powershell
uv run --locked python scripts/demo_baseline_sentiment.py
```

The script reads the clearly synthetic `data/samples/synthetic_news_articles.csv` through the offline CSV adapter, independently analyzes each normalized article headline and non-empty summary with VADER, and prints article IDs, tickers, headlines, scores/labels, summary availability, and separate aggregate metrics. Missing summaries display as `N/A` and are excluded from summary denominators. It makes no network requests and requires no API key. The Streamlit interface and stock-price comparison are not implemented in this milestone.

## Optional Live News

The `finnhub-python` SDK is already declared and locked at 2.4.29. Its basic client methods are documented in the [Finnhub SDK interface check](research.md#python-sdk-interface-check-2026-10-26). This does not complete the live-news verification gate: endpoint/date behavior, response-field semantics, access, limits, terms, attribution, and permitted use still need documented evidence. If verified and permitted, configure credentials using an environment variable or ignored local configuration documented by the implementation. Never commit a credential or place it in a tracked example. CSV must remain usable when credentials are absent or live access fails.

## Tests and Quality Checks

```powershell
uv run --locked pytest tests/unit/test_baseline_sentiment.py
uv run --locked pytest
uv run --locked ruff check .
```

Tests use controlled input and mocked provider requests; they do not make live requests. See [docs/METHODOLOGY.md](../../docs/METHODOLOGY.md) for the current baseline policy and limitations.

## Headline Baseline Evaluation

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py
```

By default, this evaluates the explicitly synthetic labeled fixture, not real
financial news. Supply `--input path\to\labeled.csv` for a compatible
manually-labeled dataset. See [docs/EVALUATION.md](../../docs/EVALUATION.md)
for the schema, labeling guide, metrics, and limitations.

For provenance/annotation validation and a deterministic development/held-out
split, use `scripts/prepare_evaluation_dataset.py` as documented in the
evaluation guide. It makes no network requests and only splits records whose
local-evaluation rights are explicitly reviewed. Real-news data collection
remains pending.

## Expected Behavior

The future application is expected to show valid headline and available-summary analysis, validation and coverage counts, session alignment, and visualizations. The current baseline scores headlines and summaries independently, but does not implement the UI, stock-price comparison, or any prediction. Sentiment results are estimates, not investment advice or a validated price-prediction model.
