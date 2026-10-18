# Financial News Sentiment Analyzer — Scope and Assumptions

## 1. In Scope — Minimum Viable Product (MVP)

The first release shall include:

1. Company ticker and date-range selection.
2. Financial news retrieval through a supported data source.
3. News data validation and preprocessing.
4. Baseline sentiment scoring for headlines and summaries.
5. Positive, Negative, and Neutral classification.
6. Aggregate sentiment statistics.
7. Sentiment distribution and trend visualizations.
8. Exploratory comparison between news sentiment and stock-price movements.
9. Clear reporting of data and processing errors.
10. Automated tests for core processing and sentiment functionality.
11. Local CSV support for automated tests, classroom demonstrations, and fallback when live news access is unavailable; the core CSV workflow runs without network access.
12. Setup instructions, methodology, test results, and screenshots.

## 2. Optional Enhancements

The following features may be added after the MVP is working:

- LLM-based contextual sentiment analysis.
- Comparison between baseline NLP and LLM results.
- Additional company filters or comparison between companies.
- Export of analysis results to CSV.
- A more advanced agentic workflow for routing, analyzing, and validating results.

Optional features shall not delay completion of the core requirements.

## 3. Out of Scope

The initial release will not:

- Execute stock trades or connect to a brokerage account.
- Guarantee stock-price predictions or investment returns.
- Provide personalized investment recommendations.
- Train a financial LLM from scratch.
- Require paid cloud infrastructure.
- Claim causal relationships between news sentiment and price changes without supporting analysis.

## 4. Assumptions

1. Finnhub is the selected primary news source, subject to verification of its endpoint, fields, credentials, terms, and usage limits; local CSV data supports tests, demonstrations, and fallback.
2. Nasdaq is the only exchange supported for the MVP comparison.
3. Market-session alignment is preferred; calendar-day aggregation may be selected at planning only if the estimate threatens another mandatory MVP deliverable by the capstone deadline.
4. Preferred-mode news timestamps use (previous Nasdaq session close, current session close] in America/New_York; after-close, weekend, and holiday records map to the next eligible session.
5. API availability, rate limits, and data coverage may vary.
6. News headlines and summaries may be incomplete or biased.
7. General-purpose sentiment models may not correctly interpret financial terminology, sarcasm, negation, or context.
8. Stock-price movement may be affected by events other than the analyzed news.
9. The development environment supports the selected Python dependencies.
10. An optional local LLM depends on available hardware and model compatibility.

## 5. Constraints

- Prefer free, open-source development tools.
- Keep API credentials outside source control.
- Avoid redistribution of news or market data unless permitted by the applicable terms.
- Use a reproducible dependency configuration.
- Identify sample CSV provenance and limitations and do not present samples as live data.
- Keep baseline NLP functionality independent of optional LLM functionality.

## 6. Definition of MVP Completion

The MVP is complete when all mandatory acceptance criteria are implemented, tested, documented, and supported by genuine evidence.

Optional enhancements may be deferred and shall be identified in the final report.