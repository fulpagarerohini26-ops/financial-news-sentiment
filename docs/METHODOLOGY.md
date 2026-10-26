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

Only the article’s **headline** is analyzed in this baseline. Surrounding
whitespace is trimmed for scoring, while the original `NewsArticle` and its
headline remain unchanged. Summary, ticker, source, URL, category, related
symbols, timestamps, and article IDs do not contribute to the score. The
summary is deliberately excluded rather than concatenated or separately
weighted; this avoids making longer summaries disproportionately influential
and keeps this first baseline focused on the headline.

The existing normalized model requires a headline, but direct analyzer calls
also validate it: a missing/non-text headline is invalid, and an empty or
whitespace-only headline raises an error instead of receiving a Neutral label.
Missing summaries are valid because summaries are not required for this
analysis.

Single-article analysis returns a typed result containing the original article,
its optional `provider_article_id`, compound score, label, analyzer name, and
package version. Batch analysis preserves input order and article-object
association; an empty batch returns an empty list. A batch containing a
non-article or repeated non-null provider article ID is rejected. Articles
without provider IDs remain supported and linked through their source article
object.

## Summary metrics

`summarize_sentiment` reports total analyzed articles; Positive, Negative, and
Neutral counts; corresponding percentages rounded independently to two decimal
places; and the arithmetic mean compound score. Percentages can differ from
100% by a small rounding amount. Empty input yields zero counts and
percentages and an unavailable (`None`) average; it never divides by zero or
represents missing data as Neutral.

These descriptive counts and scores are not returns, forecasts, causal
evidence, or investment recommendations.

## Offline demonstration and tests

The demonstration reads the explicitly synthetic
`data/samples/synthetic_news_articles.csv` fixture through the existing CSV
adapter, analyzes those normalized articles, and prints IDs, tickers,
headlines, scores, labels, and basic metrics. It makes no HTTP requests:

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
prediction model**. VADER is general-domain and may misread financial
terminology, numeric events, negation scope, sarcasm, or context. Headline-only
analysis omits potentially useful article details; it does not yet score
summaries independently. No manually labeled financial-news evaluation or
prediction claim is made by this implementation.