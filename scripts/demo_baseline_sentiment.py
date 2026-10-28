"""Run the baseline analyzer on the clearly synthetic offline CSV fixture."""

from __future__ import annotations

from pathlib import Path

from financial_news_sentiment.news.csv_adapter import load_news_csv
from financial_news_sentiment.sentiment import (
    BaselineSentimentAnalyzer,
    SentimentMetrics,
    summarize_sentiment,
    summarize_summary_sentiment,
)


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    fixture = repository_root / "data" / "samples" / "synthetic_news_articles.csv"
    articles = load_news_csv(fixture)
    results = BaselineSentimentAnalyzer().analyze_many(articles)
    headline_metrics = summarize_sentiment(results)
    summary_metrics = summarize_summary_sentiment(results)

    print("Sentiment demo - SYNTHETIC sample data, not real financial news")
    print(
        "Article ID | Ticker | Headline | Headline compound | Headline sentiment | "
        "Summary status | Summary compound | Summary sentiment"
    )
    for result in results:
        summary = result.summary_result
        summary_score = (
            f"{summary.compound_score:.4f}"
            if summary is not None and summary.status == "available"
            else "N/A"
        )
        summary_label = (
            summary.label
            if summary is not None and summary.status == "available"
            else "N/A"
        )
        summary_status = summary.status if summary is not None else "unavailable"
        print(
            f"{result.article_id} | {result.article.ticker} | "
            f"{result.article.headline} | {result.compound_score:.4f} | "
            f"{result.label} | {summary_status} | {summary_score} | {summary_label}"
        )
    _print_metrics("Headline", headline_metrics)
    _print_metrics("Summary", summary_metrics)


def _print_metrics(text_type: str, metrics: SentimentMetrics) -> None:
    print(f"{text_type} aggregates:")
    print(
        f"  Available: {metrics.total_articles}; "
        f"positive: {metrics.positive_count} ({metrics.positive_percentage:.2f}%); "
        f"negative: {metrics.negative_count} ({metrics.negative_percentage:.2f}%); "
        f"neutral: {metrics.neutral_count} ({metrics.neutral_percentage:.2f}%); "
        f"average compound: {metrics.average_compound_score}"
    )


if __name__ == "__main__":
    main()
