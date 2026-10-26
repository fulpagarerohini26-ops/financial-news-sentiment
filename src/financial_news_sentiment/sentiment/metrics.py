"""Aggregation of article-level baseline sentiment results."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real

from financial_news_sentiment.sentiment.baseline_analyzer import SentimentResult


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

    total = len(result_list)
    if not total:
        return SentimentMetrics(0, 0, 0, 0, 0.0, 0.0, 0.0, None)

    positive_count = sum(result.label == "Positive" for result in result_list)
    negative_count = sum(result.label == "Negative" for result in result_list)
    neutral_count = sum(result.label == "Neutral" for result in result_list)
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
        average_compound_score=math.fsum(
            float(result.compound_score) for result in result_list
        )
        / total,
    )
