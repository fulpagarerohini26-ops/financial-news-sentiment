# Quickstart Plan: Financial News Sentiment Analyzer

**Status**: Planned instructions. The app entry point and CSV loader do not yet exist; these commands do not assert a runnable implementation.

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

Use `uv run` so the selected Python and lockfile are honored. Confirm final commands after the application entry point is implemented.

## Planned CSV-Only Run

```powershell
uv run streamlit run src/financial_news_sentiment/app.py
```

Select CSV sources and provide news/market paths, ticker, and inclusive date range. The core workflow must run with networking blocked and without API keys or LLM setup. It must label local/sample data and disclose provenance and coverage. See [contracts/data-sources.md](contracts/data-sources.md) for planned CSV fields and timestamp/close conventions.

## Optional Live News

Finnhub remains gated on recorded verification of endpoint/field mapping, authentication, free-tier availability and limits, terms, attribution, and permitted use. If verified and permitted, configure credentials using an environment variable or ignored local configuration documented by the implementation. Never commit a credential or place it in a tracked example. CSV must remain usable when credentials are absent or live access fails.

## Planned Tests and Quality Checks

```powershell
uv run pytest
uv run ruff check .
```

The default test suite must not call live providers. The CSV integration test must pass without network access or provider credentials. Record actual outputs in project evidence; this plan reports no executed test results.

## Expected Behavior

For valid data, show separate headline and available-summary scores/aggregates, validation and coverage counts, session alignment, and all four required visualizations. For empty data, invalid input, or source failure, show an informative status without fabricated neutral sentiment or presenting incomplete data as complete. Explain that sentiment/price comparison is exploratory, not prediction or investment advice.
