"""Baseline sentiment analysis and summary metrics."""

from financial_news_sentiment.sentiment.baseline_analyzer import (
    BaselineSentimentAnalyzer,
    SentimentLabel,
    SentimentResult,
    classify_compound_score,
)
from financial_news_sentiment.sentiment.metrics import (
    SentimentMetrics,
    summarize_sentiment,
)

__all__ = [
    "BaselineSentimentAnalyzer",
    "SentimentLabel",
    "SentimentMetrics",
    "SentimentResult",
    "classify_compound_score",
    "summarize_sentiment",
]
