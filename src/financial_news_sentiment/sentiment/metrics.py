"""Aggregation of article-level baseline sentiment results."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real

from financial_news_sentiment.sentiment.baseline_analyzer import (
    SentimentLabel,
    SentimentResult,
    SummarySentimentResult,
)


@dataclass(frozen=True, slots=True)
class SentimentMetrics:
    """Counts, percentages, and mean compound score for analyzed articles."""

    total_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_percentage: float
    negative_percentage: float
    neutral_percentage: float
    average_compound_score: float | None

    @property
    def available_count(self) -> int:
        """Return the number of valid sentiment results represented."""
        return self.total_articles


def summarize_sentiment(
    results: Iterable[SentimentResult],
) -> SentimentMetrics:
    """Summarize results; percentages are rounded to two decimal places.

    Empty input yields zero counts and percentages, with no average score.
    Duplicate non-null article IDs and malformed results are rejected.
    """
    if isinstance(results, (str, bytes)) or not isinstance(results, Iterable):
        raise TypeError("results must be an iterable of SentimentResult objects")

    result_list = tuple(results)
    seen_ids: set[int] = set()
    for result in result_list:
        if not isinstance(result, SentimentResult):
            raise TypeError("results must contain only SentimentResult objects")
        score = result.compound_score
        if (
            not isinstance(score, Real)
            or isinstance(score, bool)
            or not math.isfinite(float(score))
            or not -1.0 <= score <= 1.0
        ):
            raise ValueError("each compound score must be finite and in [-1, 1]")
        if result.label not in ("Positive", "Negative", "Neutral"):
            raise ValueError("each result must have a valid sentiment label")

        article_id = result.article_id
        if article_id is not None:
            if article_id in seen_ids:
                raise ValueError(f"duplicate provider article ID: {article_id}")
            seen_ids.add(article_id)

    return _metrics_from_scores(
        [(float(result.compound_score), result.label) for result in result_list]
    )


def summarize_summary_sentiment(
    results: Iterable[SentimentResult],
) -> SentimentMetrics:
    """Summarize available summary results, excluding unavailable summaries.

    Percentages use available summaries as their denominator and are rounded
    independently to two decimal places. An empty set yields zero counts and
    percentages, with no average score.
    """
    if isinstance(results, (str, bytes)) or not isinstance(results, Iterable):
        raise TypeError("results must be an iterable of SentimentResult objects")

    result_list = tuple(results)
    summaries: list[SummarySentimentResult] = []
    seen_ids: set[int] = set()
    for result in result_list:
        if not isinstance(result, SentimentResult):
            raise TypeError("results must contain only SentimentResult objects")
        article_id = result.article_id
        if article_id is not None:
            if article_id in seen_ids:
                raise ValueError(f"duplicate provider article ID: {article_id}")
            seen_ids.add(article_id)
        summary = result.summary_result
        if summary is None:
            continue
        if not isinstance(summary, SummarySentimentResult):
            raise TypeError("summary_result must be a SummarySentimentResult or None")
        if summary.article is not result.article:
            raise ValueError("summary result must reference its source article")
        if summary.status == "unavailable":
            if summary.compound_score is not None or summary.label is not None:
                raise ValueError("unavailable summaries must not have a score or label")
            continue
        if summary.status != "available":
            raise ValueError("summary result must have a valid availability status")
        if summary.compound_score is None or summary.label is None:
            raise ValueError("available summaries must have a score and label")
        score = summary.compound_score
        if (
            not isinstance(score, Real)
            or isinstance(score, bool)
            or not math.isfinite(float(score))
            or not -1.0 <= score <= 1.0
        ):
            raise ValueError("each summary score must be finite and in [-1, 1]")
        if summary.label not in ("Positive", "Negative", "Neutral"):
            raise ValueError("each summary result must have a valid sentiment label")
        summaries.append(summary)

    return _metrics_from_scores(
        [
            (float(result.compound_score), result.label)
            for result in summaries
            if result.compound_score is not None and result.label is not None
        ]
    )


def _metrics_from_scores(
    scores: list[tuple[float, SentimentLabel]],
) -> SentimentMetrics:
    total = len(scores)
    if not total:
        return SentimentMetrics(0, 0, 0, 0, 0.0, 0.0, 0.0, None)

    positive_count = sum(label == "Positive" for _, label in scores)
    negative_count = sum(label == "Negative" for _, label in scores)
    neutral_count = sum(label == "Neutral" for _, label in scores)
    percentages = tuple(
        round(count / total * 100, 2)
        for count in (positive_count, negative_count, neutral_count)
    )
    return SentimentMetrics(
        total_articles=total,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        positive_percentage=percentages[0],
        negative_percentage=percentages[1],
        neutral_percentage=percentages[2],
        average_compound_score=math.fsum(score for score, _ in scores) / total,
    )
