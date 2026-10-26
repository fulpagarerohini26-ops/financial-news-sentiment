from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version

import pytest

from financial_news_sentiment.news.models import NewsArticle
from financial_news_sentiment.sentiment.baseline_analyzer import (
    BaselineSentimentAnalyzer,
    classify_compound_score,
)
from financial_news_sentiment.sentiment.metrics import summarize_sentiment


def _article(
    headline: str = "Company reports results",
    *,
    article_id: int | None = 42,
    summary: str | None = None,
) -> NewsArticle:
    return NewsArticle(
        ticker="AAPL",
        headline=headline,
        published_at=datetime(2026, 10, 20, tzinfo=UTC),
        published_timestamp=1792497600,
        provider_article_id=article_id,
        summary=summary,
        source="Synthetic Test Wire",
        article_url="https://example.invalid/story",
    )


def test_clearly_positive_headline_is_positive() -> None:
    result = BaselineSentimentAnalyzer().analyze(
        _article("Excellent results deliver strong growth!")
    )

    assert result.label == "Positive"
    assert result.compound_score > 0.05


def test_clearly_negative_headline_is_negative() -> None:
    result = BaselineSentimentAnalyzer().analyze(
        _article("Disappointing results show severe losses!")
    )

    assert result.label == "Negative"
    assert result.compound_score < -0.05


def test_neutral_factual_headline_is_neutral() -> None:
    result = BaselineSentimentAnalyzer().analyze(
        _article("The company released its annual report on Tuesday.")
    )

    assert result.label == "Neutral"
    assert -0.05 < result.compound_score < 0.05


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.050001, "Positive"),
        (0.05, "Positive"),
        (0.049999, "Neutral"),
        (-0.049999, "Neutral"),
        (-0.05, "Negative"),
        (-0.050001, "Negative"),
        (0.0, "Neutral"),
    ],
)
def test_classification_threshold_boundaries(score: float, label: str) -> None:
    assert classify_compound_score(score) == label


def test_thresholds_can_be_configured_and_are_validated() -> None:
    analyzer = BaselineSentimentAnalyzer(
        positive_threshold=0.2,
        negative_threshold=-0.3,
    )

    assert analyzer.positive_threshold == 0.2
    assert analyzer.negative_threshold == -0.3
    assert (
        classify_compound_score(0.1, positive_threshold=0.2, negative_threshold=-0.3)
        == "Neutral"
    )

    with pytest.raises(ValueError, match="thresholds"):
        BaselineSentimentAnalyzer(positive_threshold=-0.05)


@pytest.mark.parametrize("headline", ["", " ", " \t\n"])
def test_empty_or_whitespace_headline_is_rejected(headline: str) -> None:
    with pytest.raises(ValueError, match="headline must not be blank"):
        BaselineSentimentAnalyzer().analyze(_article(headline))


def test_non_text_headline_is_rejected() -> None:
    article = replace(_article(), headline=None)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="headline must be text"):
        BaselineSentimentAnalyzer().analyze(article)


def test_missing_summary_does_not_prevent_headline_analysis() -> None:
    article = _article("Positive outlook and excellent results", summary=None)

    result = BaselineSentimentAnalyzer().analyze(article)

    assert result.article is article
    assert result.article.summary is None
    assert result.label == "Positive"


def test_summary_and_other_metadata_do_not_contribute_to_score() -> None:
    analyzer = BaselineSentimentAnalyzer()
    article = _article(
        "The company released its annual report on Tuesday.",
        summary="Terrible losses and disastrous performance!",
    )

    result = analyzer.analyze(article)
    headline_only_result = analyzer.analyze(
        _article("The company released its annual report on Tuesday.")
    )

    assert result.compound_score == headline_only_result.compound_score
    assert result.label == "Neutral"
    assert result.article.summary == "Terrible losses and disastrous performance!"


def test_source_article_fields_are_preserved_and_result_is_associated() -> None:
    article = _article("  Excellent results!  ", summary="A sample summary.")
    original_fields = (
        article.ticker,
        article.headline,
        article.summary,
        article.source,
        article.article_url,
        article.provider_article_id,
        article.published_at,
        article.published_timestamp,
    )

    result = BaselineSentimentAnalyzer().analyze(article)

    assert result.article is article
    assert result.article_id == 42
    assert (
        article.ticker,
        article.headline,
        article.summary,
        article.source,
        article.article_url,
        article.provider_article_id,
        article.published_at,
        article.published_timestamp,
    ) == original_fields
    assert result.analyzer_name == "VADER"
    assert result.analyzer_version == version("vaderSentiment")


def test_result_keeps_article_association_when_provider_id_is_missing() -> None:
    article = _article("Ordinary factual news", article_id=None)

    result = BaselineSentimentAnalyzer().analyze(article)

    assert result.article is article
    assert result.article_id is None


def test_batch_empty_multiple_articles_and_input_order() -> None:
    analyzer = BaselineSentimentAnalyzer()
    articles = [
        _article("Excellent growth!", article_id=1),
        _article("Severe losses!", article_id=2),
        _article("The company filed its report.", article_id=None),
    ]

    assert analyzer.analyze_many([]) == []
    results = analyzer.analyze_many(articles)

    assert len(results) == 3
    assert [result.article for result in results] == articles
    assert [result.article_id for result in results] == [1, 2, None]


def test_analysis_is_repeatable_for_identical_input() -> None:
    analyzer = BaselineSentimentAnalyzer()
    article = _article("Excellent growth with strong results!")

    first = analyzer.analyze(article)
    second = analyzer.analyze(article)

    assert first.compound_score == second.compound_score
    assert first.label == second.label
    assert first.analyzer_version == second.analyzer_version


def test_invalid_article_input_is_rejected() -> None:
    analyzer = BaselineSentimentAnalyzer()

    with pytest.raises(TypeError, match="NewsArticle"):
        analyzer.analyze("not an article")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="iterable"):
        analyzer.analyze_many(None)  # type: ignore[arg-type]


def test_batch_rejects_invalid_articles_and_duplicate_ids() -> None:
    analyzer = BaselineSentimentAnalyzer()

    with pytest.raises(TypeError, match="NewsArticle"):
        analyzer.analyze_many([_article(), "not an article"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="duplicate provider article ID: 7"):
        analyzer.analyze_many(
            [_article(article_id=7), _article("Different article", article_id=7)]
        )


def test_classifier_rejects_invalid_scores() -> None:
    with pytest.raises(ValueError, match="range"):
        classify_compound_score(1.1)
    with pytest.raises(ValueError, match="finite"):
        classify_compound_score(float("nan"))
    with pytest.raises(TypeError, match="real number"):
        classify_compound_score(True)  # type: ignore[arg-type]


def test_summary_metrics_calculate_counts_percentages_and_average() -> None:
    results = BaselineSentimentAnalyzer().analyze_many(
        [
            _article("Excellent growth!", article_id=1),
            _article("Severe losses!", article_id=2),
            _article("The company filed its report.", article_id=3),
        ]
    )

    metrics = summarize_sentiment(results)

    assert metrics.total_articles == 3
    assert (metrics.positive_count, metrics.negative_count, metrics.neutral_count) == (
        1,
        1,
        1,
    )
    assert (
        metrics.positive_percentage,
        metrics.negative_percentage,
        metrics.neutral_percentage,
    ) == (33.33, 33.33, 33.33)
    assert sum(
        (
            metrics.positive_percentage,
            metrics.negative_percentage,
            metrics.neutral_percentage,
        )
    ) == pytest.approx(100.0, abs=0.02)
    assert metrics.average_compound_score == pytest.approx(
        sum(result.compound_score for result in results) / 3
    )


def test_empty_metrics_are_zeroed_without_an_average() -> None:
    metrics = summarize_sentiment([])

    assert metrics.total_articles == 0
    assert (
        metrics.positive_count == metrics.negative_count == metrics.neutral_count == 0
    )
    assert (
        metrics.positive_percentage,
        metrics.negative_percentage,
        metrics.neutral_percentage,
    ) == (0.0, 0.0, 0.0)
    assert metrics.average_compound_score is None


def test_metrics_reject_invalid_and_duplicate_results() -> None:
    with pytest.raises(TypeError, match="SentimentResult"):
        summarize_sentiment([object()])  # type: ignore[list-item]

    result = BaselineSentimentAnalyzer().analyze(_article(article_id=9))
    with pytest.raises(ValueError, match="duplicate provider article ID: 9"):
        summarize_sentiment([result, result])
