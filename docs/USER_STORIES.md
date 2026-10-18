# Financial News Sentiment Analyzer — User Stories

## 1. Primary User

**Financial analyst / project demonstrator**

The user wants to explore company-specific financial news and understand the sentiment expressed in the available headlines and summaries.

## 2. User Stories

### US-01: Select a Company

As a user, I want to enter a company ticker so that I can analyze news for a specific company.

Priority: Must have

Related requirements: FR-01

### US-02: Select an Analysis Period

As a user, I want to select a date range so that I can analyze financial news for a relevant period.

Priority: Must have

Related requirements: FR-02

### US-03: Retrieve Financial News

As a user, I want to retrieve company-specific news so that I can analyze available financial information.

Priority: Must have

Related requirements: FR-03

### US-04: Analyze Headline Sentiment

As a user, I want each headline to have a sentiment score and label so that I can quickly understand its expressed tone.

Priority: Must have

Related requirements: FR-05, FR-07

### US-05: Analyze Summary Sentiment

As a user, I want available news summaries to be analyzed separately so that I can compare headline tone with summary tone.

Priority: Must have

Related requirements: FR-06, FR-07

### US-06: View Aggregate Sentiment

As a user, I want to view overall sentiment statistics so that I can understand the distribution of positive, negative, and neutral news.

Priority: Must have

Related requirements: FR-08, FR-09

### US-07: Compare Sentiment and Stock Prices

As a user, I want to compare sentiment trends with stock-price movements so that I can explore whether the two vary together.

Priority: Must have

Related requirements: FR-10

### US-08: Understand Contextual Sentiment

As a user, I want an optional LLM-based analysis so that I can compare contextual financial interpretation with the baseline NLP result.

Priority: Should have

Related requirements: FR-11

### US-09: Understand the Analysis

As a user, I want to see the data source, analysis method, and limitations so that I can interpret the results responsibly.

Priority: Must have

Related requirements: FR-12, NFR-07

### US-10: Recover from Data Errors

As a user, I want clear error messages when data is unavailable so that I understand why results cannot be displayed.

Priority: Must have

Related requirements: FR-03, NFR-02

### US-11: Load Local CSV Data

As a reviewer or developer, I want to load documented local CSV datasets so that I can test, demonstrate, or use the core analysis workflow when live news access is unavailable.

Priority: Must have

Related requirements: FR-13, NFR-01, NFR-05

Acceptance: The core CSV workflow runs without network access, and included sample data is identified as non-live with its provenance and limitations documented.

## 3. User Story Completion Rule

A user story is complete only when:

1. Its implementation satisfies the related acceptance criteria.
2. Relevant automated or documented manual tests have passed.
3. The result is observable in the application or test output.
4. Relevant documentation and evidence have been updated.