# Financial News Sentiment Analyzer — Requirements

## 1. Purpose

This document defines the functional and non-functional requirements for the GenAI-Powered Financial News Sentiment Analyzer.

The application will retrieve financial news, analyze the sentiment expressed in news headlines and summaries, and visualize sentiment trends alongside stock-price movements.

## 2. Project Objectives

The application aims to:

1. Fetch company-specific financial news from Finnhub, subject to verification of the selected endpoint, access requirements, and applicable terms.
2. Analyze headlines and summaries using NLP sentiment analysis.
3. Classify sentiment as Positive, Negative, or Neutral.
4. Calculate and visualize sentiment scores and trends.
5. Explore the relationship between news sentiment and stock-price movements.
6. Provide an optional LLM-based contextual sentiment analysis extension.

## 3. Functional Requirements

### FR-01: Company Selection

The application shall allow the user to select or enter a supported company ticker symbol, such as AAPL.

### FR-02: Date Range Selection

The application shall allow the user to specify a date range for retrieving financial news.

### FR-03: Financial News Retrieval

The application shall retrieve available company-specific financial news from Finnhub, subject to verification of provider fields, access requirements, terms, and usage limits.

It shall handle empty responses and report data retrieval errors clearly.

### FR-04: News Data Processing

The application shall validate and process retrieved news records, including available headlines, summaries, publication timestamps, article URLs, and source information.

Missing optional fields shall not cause the entire application to fail.

### FR-05: Headline Sentiment Analysis

The application shall calculate a sentiment score for each available news headline using the selected baseline NLP method.

### FR-06: Summary Sentiment Analysis

The application shall calculate a sentiment score for each non-empty news summary.

If a summary is missing or empty, the application shall indicate that summary sentiment is unavailable.

### FR-07: Sentiment Classification

The application shall classify analyzed text using VADER compound scores: Negative at <= -0.05, Positive at >= 0.05, and Neutral strictly between those boundaries.

### FR-08: Aggregate Sentiment Analysis

The application shall calculate aggregate sentiment measures for the selected company and date range.

Headline and summary sentiment shall be reported separately.

### FR-09: Sentiment Visualization

The application shall display sentiment distributions and sentiment trends over the selected date range.

### FR-10: Stock-Price Comparison

The application shall load suitable stock-price data and compare price movements with news sentiment over a compatible period. NSE is the only supported exchange for MVP comparison. Market-session alignment using the NSE calendar and Asia/Kolkata timezone is preferred; calendar-day aggregation may be selected at planning only if the estimate threatens another mandatory MVP deliverable by the capstone deadline. The selected market-data source and its fields, terms, coverage, and access requirements shall be verified and documented.

Any statistical relationship shall be described as exploratory unless supported by a more rigorous predictive evaluation.

### FR-11: Contextual LLM Analysis

The application may provide an LLM-based contextual sentiment analysis extension.

This extension shall be distinguishable from the baseline NLP result, and its model and configuration shall be documented.

### FR-12: Results Presentation

The application shall present analyzed news records, sentiment labels, numerical scores, summary statistics, and visualizations through a user-friendly interface.

### FR-13: Local CSV Support

The application shall load documented local CSV datasets for testing, classroom demonstration, and fallback when live news access is unavailable. The core CSV analysis workflow shall run without network access. Any included sample data shall identify provenance and limitations and shall not be represented as live data.

## 4. Non-Functional Requirements

### NFR-01: Usability

A user shall be able to select a company and date range and view results without editing source code.

### NFR-02: Reliability

The application shall handle missing data, empty news responses, API failures, and invalid user inputs gracefully.

### NFR-03: Security

API credentials shall be supplied through environment configuration and shall not be committed to source control.

### NFR-04: Maintainability

News retrieval, preprocessing, sentiment analysis, market-data processing, and visualization shall be separated into logical modules.

### NFR-05: Reproducibility

The project shall include dependency configuration, a lockfile, execution instructions, and documented analysis settings.
Local CSV schemas and sample-data provenance shall also be documented.

### NFR-06: Testability

Core processing and sentiment functions shall be independently testable using controlled test data.
Tests shall cover exact VADER threshold boundaries, CSV loading, separate headline/summary calculations, and NSE session assignment for close, after-close, weekends, holidays, and time-zone handling.

### NFR-07: Transparency

The application shall identify its data source, analysis method, relevant date range, and known limitations.

## 5. Constraints

- The project shall prioritize free development tools and local execution.
- Live data access may depend on provider availability, account limits, and API terms.
- NSE is the sole MVP exchange; its calendar and Asia/Kolkata timezone govern the preferred session alignment.
- Local CSVs are required for tests, demonstrations, and provider fallback; live and sample data shall be distinguishable.
- LLM-based analysis may require local model resources or a separately configured inference service.
- Sentiment analysis results shall not be presented as guaranteed stock-price predictions.

## 6. Traceability

Each functional requirement shall be mapped to one or more user stories, implementation tasks, tests, and evidence items before final submission.

## 7. Status

Status: Draft — to be reviewed and approved before architecture planning.