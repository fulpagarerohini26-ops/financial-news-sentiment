"""Headline-only VADER sentiment analysis for normalized news articles."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import version
from typing import Literal

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from financial_news_sentiment.news.models import NewsArticle

SentimentLabel = Literal["Positive", "Negative", "Neutral"]
DEFAULT_POSITIVE_THRESHOLD = 0.05
DEFAULT_NEGATIVE_THRESHOLD = -0.05
_ANALYZER_NAME = "VADER"
_ANALYZER_VERSION = version("vaderSentiment")


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """A sentiment estimate linked to its unchanged source article."""

    article: NewsArticle
    compound_score: float
    label: SentimentLabel
    analyzer_name: str
    analyzer_version: str

    @property
    def article_id(self) -> int | None:
        """Return the provider ID when the source article has one."""
        return self.article.provider_article_id


def classify_compound_score(
    compound_score: float,
    *,
    positive_threshold: float = DEFAULT_POSITIVE_THRESHOLD,
    negative_threshold: float = DEFAULT_NEGATIVE_THRESHOLD,
) -> SentimentLabel:
    """Classify a VADER compound score using configurable inclusive cutoffs."""
    if not isinstance(compound_score, (int, float)) or isinstance(compound_score, bool):
        raise TypeError("compound_score must be a real number")
    score = float(compound_score)
    if not math.isfinite(score) or not -1.0 <= score <= 1.0:
        raise ValueError("compound_score must be finite and in the range [-1, 1]")

    positive, negative = _validate_thresholds(positive_threshold, negative_threshold)
    if score >= positive:
        return "Positive"
    if score <= negative:
        return "Negative"
    return "Neutral"


class BaselineSentimentAnalyzer:
    """Analyze article headlines with the locally installed VADER lexicon.

    Summaries and metadata are deliberately excluded from the sentiment text.
    Surrounding headline whitespace is ignored, but the source article is never
    modified. Headlines that are absent or whitespace-only are rejected.
    """

    __slots__ = (
        "_analyzer",
        "negative_threshold",
        "positive_threshold",
    )

    analyzer_name = _ANALYZER_NAME
    analyzer_version = _ANALYZER_VERSION

    def __init__(
        self,
        *,
        positive_threshold: float = DEFAULT_POSITIVE_THRESHOLD,
        negative_threshold: float = DEFAULT_NEGATIVE_THRESHOLD,
    ) -> None:
        (
            self.positive_threshold,
            self.negative_threshold,
        ) = _validate_thresholds(positive_threshold, negative_threshold)
        self._analyzer = SentimentIntensityAnalyzer()

    def analyze(self, article: NewsArticle) -> SentimentResult:
        """Analyze one article's headline and retain its source article."""
        _validate_article(article)
        return self._analyze_validated(article)

    def analyze_many(self, articles: Iterable[NewsArticle]) -> list[SentimentResult]:
        """Analyze articles in order; reject repeated known provider IDs."""
        if isinstance(articles, (str, bytes)) or not isinstance(articles, Iterable):
            raise TypeError("articles must be an iterable of NewsArticle objects")

        article_list = tuple(articles)
        seen_ids: set[int] = set()
        for article in article_list:
            _validate_article(article)
            article_id = article.provider_article_id
            if article_id is not None:
                if article_id in seen_ids:
                    raise ValueError(f"duplicate provider article ID: {article_id}")
                seen_ids.add(article_id)

        return [self._analyze_validated(article) for article in article_list]

    def _analyze_validated(self, article: NewsArticle) -> SentimentResult:
        text = article.headline.strip()
        compound_score = self._analyzer.polarity_scores(text)["compound"]
        label = classify_compound_score(
            compound_score,
            positive_threshold=self.positive_threshold,
            negative_threshold=self.negative_threshold,
        )
        return SentimentResult(
            article=article,
            compound_score=compound_score,
            label=label,
            analyzer_name=self.analyzer_name,
            analyzer_version=self.analyzer_version,
        )


def _validate_article(article: NewsArticle) -> None:
    if not isinstance(article, NewsArticle):
        raise TypeError("article must be a NewsArticle")
    if not isinstance(article.headline, str):
        raise TypeError("article headline must be text")
    if not article.headline.strip():
        raise ValueError("article headline must not be blank")
    article_id = article.provider_article_id
    if article_id is not None and (
        not isinstance(article_id, int) or isinstance(article_id, bool)
    ):
        raise TypeError("article provider_article_id must be an integer or None")


def _validate_thresholds(
    positive_threshold: float, negative_threshold: float
) -> tuple[float, float]:
    thresholds = (positive_threshold, negative_threshold)
    if any(
        not isinstance(threshold, (int, float)) or isinstance(threshold, bool)
        for threshold in thresholds
    ):
        raise TypeError("sentiment thresholds must be real numbers")

    positive, negative = (float(value) for value in thresholds)
    if (
        not math.isfinite(positive)
        or not math.isfinite(negative)
        or not -1.0 <= negative < 0.0 < positive <= 1.0
    ):
        raise ValueError(
            "thresholds must be finite, with negative_threshold < 0 < "
            "positive_threshold, and both in [-1, 1]"
        )
    return positive, negative
