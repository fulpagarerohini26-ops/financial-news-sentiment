# Financial News Sentiment Analyzer — Risks and Constraints

## 1. Risk Register

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| R-01 | API rate limit or outage | News cannot be retrieved | Handle failures gracefully and provide an optional demo dataset |
| R-02 | Missing or incomplete news | Biased or incomplete sentiment statistics | Validate fields and display data-coverage warnings |
| R-03 | Financial language misclassified by baseline NLP | Incorrect sentiment labels | Evaluate against manually labeled financial text |
| R-04 | LLM generates inconsistent interpretations | Unreliable contextual results | Constrain output, validate the response, and compare with source text |
| R-05 | News timestamps do not align with market data | Misleading comparisons | Normalize timestamps and document trading-calendar alignment |
| R-06 | Correlation is interpreted as causation | Unsupported conclusions | Describe results as exploratory and document confounding factors |
| R-07 | Python dependency incompatibility | Installation or runtime failures | Use a compatible Python version and lock dependencies |
| R-08 | API key exposed in Git | Credential misuse | Use environment variables and exclude secret files |
| R-09 | Optional local LLM is too resource-intensive | Slow or failed inference | Keep LLM functionality optional and use a compatible model |
| R-10 | Data redistribution violates provider terms | Compliance or licensing concerns | Review terms and use permitted sample data |

## 2. Responsible AI Considerations

- Sentiment labels are model outputs and may be incorrect.
- Generated explanations must not be presented as verified facts without supporting evidence.
- The application shall not guarantee investment performance.
- Users shall be informed of data coverage and model limitations.
- Results should support exploration and learning rather than automated investment decisions.

## 3. Operational Constraints

The initial application is intended for local execution.

External API calls and optional LLM inference may fail independently. Core data-processing and sentiment functions should remain testable without relying on live external services.

## 4. Review Policy

Risks shall be reviewed when selecting libraries, integrating external APIs, adding LLM functionality, and preparing the final submission.

Newly discovered risks and mitigations shall be added to this register.

Status: Draft — review during technical planning.