# Baseline Sentiment Analysis

## Method and reproducibility

The first sentiment milestone uses VADER from the `vaderSentiment` Python
package, version **3.3.2** (declared in `pyproject.toml` and pinned by
`uv.lock`). VADER is a lightweight, locally executed lexicon-and-rule baseline
that requires no hosted model, API key, network request, or model download
during inference. Its implementation has been verified with the project’s
Python 3.12 environment.

The analyzer reports the package’s **compound** score, normalized to `[-1.0,
1.0]`. Classification uses configurable inclusive thresholds, defaulting to:

| Compound score | Label |
|---|---|
| `>= 0.05` | Positive |
| `<= -0.05` | Negative |
| Otherwise | Neutral |

Thresholds must be finite, within `[-1.0, 1.0]`, and satisfy
`negative_threshold < 0 < positive_threshold`. Scores must be finite and
within `[-1.0, 1.0]`.

## Text policy and input behavior

The article’s **headline** and available **summary** are analyzed independently.
They are never concatenated, and neither score is substituted for the other.
Surrounding whitespace is trimmed for scoring, while the original
`NewsArticle` and every source field remain unchanged. Ticker, source, URL,
category, related symbols, timestamps, and article IDs do not contribute to
either score.

The existing normalized model requires a headline, but direct analyzer calls
also validate it: a missing/non-text headline is invalid, and an empty or
whitespace-only headline raises an error instead of receiving a Neutral label.
A null, empty, or whitespace-only summary is valid unavailable input; its
`SummarySentimentResult` has `status="unavailable"` and both
`compound_score` and `label` set to `None`. A non-empty summary has
`status="available"` and its own score and label, including when its score
classifies as Neutral. Thus a valid near-zero score cannot be confused with
missing text.

Single-article analysis returns a typed result containing the original article,
its optional `provider_article_id`, the unchanged headline score and label,
analyzer name and package version, and a `summary_result`. The nested summary
result references the same article and carries its own status, optional score
and label, analyzer name, and package version. Existing headline result fields
remain available under their original names. Batch analysis preserves input
order and article-object association; an empty batch returns an empty list. A
batch containing a non-article or repeated non-null provider article ID is
rejected. Articles without provider IDs remain linked through their source
article object.

## Separate aggregate metrics

`summarize_sentiment` reports headline metrics. `summarize_summary_sentiment`
reports summary metrics using only available summary results. For each
function, the denominator is its available result count: counts are
Positive/Negative/Neutral classification counts, percentages are
`count / available_count * 100`, rounded independently to two decimal places,
and average compound is the arithmetic mean of the included compound scores.
Missing or blank summaries are excluded from both the summary denominator and
summary average. The metrics object retains `total_articles` for compatibility;
`available_count` is an alias for that count.

An empty input or a collection with no available summaries returns zero counts
and percentages and an unavailable (`None`) average. No division by zero
occurs. Independently rounded percentages can differ from 100% by a small
rounding amount. Headline and summary aggregates remain separate; this
milestone does not calculate an overall score or headline-summary disagreement
metric.

These descriptive counts and scores are not returns, forecasts, causal
evidence, or investment recommendations.

## Offline demonstration and tests

The demonstration reads the explicitly synthetic
`data/samples/synthetic_news_articles.csv` fixture through the existing CSV
adapter, analyzes those normalized articles, and prints IDs, tickers,
headlines, headline scores/labels, summary availability and available summary
scores/labels, and separate headline and summary aggregates. Unavailable
summaries display as `N/A`. It makes no HTTP requests:

```powershell
uv run python scripts/demo_baseline_sentiment.py
```

Run the focused sentiment tests and the complete test suite with:

```powershell
uv run pytest tests/unit/test_baseline_sentiment.py
uv run pytest
```

The demo and tests do not require Finnhub credentials or network access.

## Limitations

This is a baseline sentiment classifier, **not a validated financial
prediction model**, investment advice, or a forecast of stock-price movement.
VADER is general-domain and may misread financial terminology, numeric events,
negation scope, sarcasm, or context. Scores are descriptive text
classifications; neither average is evidence of price impact. No manually
labeled financial-news evaluation or prediction claim is made by this
implementation.