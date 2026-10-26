"""Run the baseline analyzer on the clearly synthetic offline CSV fixture."""

from __future__ import annotations

from pathlib import Path

from financial_news_sentiment.news.csv_adapter import load_news_csv
from financial_news_sentiment.sentiment import (
    BaselineSentimentAnalyzer,
    summarize_sentiment,
)


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    fixture = repository_root / "data" / "samples" / "synthetic_news_articles.csv"
    articles = load_news_csv(fixture)
    results = BaselineSentimentAnalyzer().analyze_many(articles)
    metrics = summarize_sentiment(results)

    print("Baseline sentiment demo - SYNTHETIC sample data, not real financial news")
    print("Article ID | Ticker | Headline | Compound | Sentiment")
    for result in results:
        print(
            f"{result.article_id} | {result.article.ticker} | "
            f"{result.article.headline} | {result.compound_score:.4f} | "
            f"{result.label}"
        )
    print(
        f"Total: {metrics.total_articles}; positive: {metrics.positive_count}; "
        f"negative: {metrics.negative_count}; neutral: {metrics.neutral_count}; "
        f"average compound: {metrics.average_compound_score}"
    )


if __name__ == "__main__":
    main()
