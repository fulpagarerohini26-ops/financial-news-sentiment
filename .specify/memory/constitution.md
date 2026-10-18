# Project Constitution: GenAI-Powered Financial News Sentiment Analyzer

## Article I: Modular and Maintainable Architecture

- The application MUST separate news ingestion, data validation, preprocessing, sentiment analysis, aggregation, visualization, and optional LLM integration into logically distinct modules.
- Components MUST have clear responsibilities and well-defined interfaces.
- Core sentiment and data-processing logic MUST be testable independently of the user interface and external services.
- Implementation MUST avoid unnecessary complexity and keep the solution appropriate for a student capstone.

## Article II: Testability and Quality Assurance

- Core business logic MUST be covered by automated tests.
- Tests MUST cover valid inputs, invalid inputs, missing data, empty results, duplicate records, and relevant failure scenarios.
- Sentiment classification and aggregation MUST be tested against documented expected outcomes.
- Defects identified during testing MUST be addressed or documented as known limitations.
- A feature MUST NOT be considered complete solely because it runs successfully; its expected behavior MUST also be verified.

## Article III: Reproducibility and Configuration

- Project dependencies MUST be explicitly declared and reproducibly managed.
- Setup instructions MUST describe the supported Python environment, dependency installation, configuration, and application execution.
- Sentiment methods, classification thresholds, data transformations, and evaluation procedures MUST be documented.
- Environment-specific values, including API credentials, MUST be supplied through configuration rather than hard-coded into application logic.
- Sample data MUST be clearly identified and MUST NOT be represented as live financial news.

## Article IV: Responsible AI and Financial Interpretation

- Sentiment results MUST be presented as analytical estimates, not as guaranteed stock-price predictions or investment recommendations.
- The application MUST communicate that financial news sentiment can be ambiguous, incomplete, or incorrectly classified.
- Comparisons between sentiment and stock-price movements MUST distinguish observed relationships from causal claims.
- The application MUST NOT claim that sentiment caused a price movement without appropriate supporting evidence.
- Any optional LLM-generated interpretation MUST be treated as potentially incorrect and evaluated accordingly.
- Limitations affecting the interpretation of results MUST be documented and visible to users where relevant.

## Article V: Data Integrity and Reliability

- Incoming news records MUST be validated and normalized before analysis.
- Missing, malformed, or duplicate records MUST be handled through documented rules.
- The application MUST handle unavailable data, empty results, network failures, API errors, and rate limits gracefully.
- Headline sentiment and article-summary sentiment MUST be kept distinguishable wherever both are analyzed.
- Stock-price and news data MUST be aligned using documented date and time-handling rules before comparisons are presented.
- The application MUST distinguish actual provider data from fallback or demonstration data.

## Article VI: Security, Privacy, and Data-Source Compliance

- API keys, access tokens, and other secrets MUST NOT be committed to source control.
- Sensitive configuration files MUST be excluded from version control, with a safe example configuration provided when needed.
- External data sources MUST be used according to their applicable terms, rate limits, licensing, and attribution requirements.
- The application MUST request and process only the data necessary for its defined functionality.
- Any data-source restrictions that affect reproducibility or demonstration MUST be documented.

## Article VII: Cost-Conscious and Controlled GenAI Adoption

- The initial implementation MUST prioritize a reliable baseline sentiment-analysis workflow.
- The baseline MUST function without requiring a paid LLM service.
- LLM-based contextual sentiment, baseline-versus-LLM comparisons, and agentic workflows SHOULD be added only after the baseline is tested.
- Optional GenAI capabilities MUST have clear boundaries, documented configuration requirements, and testable behavior.
- The project SHOULD prefer free or locally runnable tools where practical, without compromising security, data integrity, or evaluation quality.

## Article VIII: Evidence-Based Evaluation

- The project MUST record whether a small manually reviewed sentiment sample is feasible and the rationale for that assessment.
- Where feasible, baseline sentiment SHOULD be reviewed using manually labeled financial text with a documented labeling approach.
- Formal accuracy, precision, recall, macro F1-score, and confusion-matrix metrics MAY be reported when supported by a suitable labeled dataset.
- Evaluation results MUST reflect actual executed tests and measurements; results MUST NOT be fabricated or inferred from successful application execution.
- Limitations caused by dataset size, class imbalance, financial language, or source coverage MUST be disclosed.

## Article IX: Documentation and Traceability

- Requirements MUST be traceable to acceptance criteria and verification methods.
- Significant technical decisions and scope changes MUST be documented.
- The README and project documentation MUST reflect the implemented behavior rather than planned but unfinished features.
- Test results, evaluation evidence, setup instructions, methodology, and known limitations MUST be maintained as the project develops.
- Any deferred or incomplete mandatory feature MUST be clearly identified.

## Article X: Scope and Definition of Done

- The mandatory MVP MUST be completed and validated before optional enhancements are treated as deliverables.
- The MVP MUST support company selection, date-range filtering, news loading, validation, baseline sentiment classification, aggregation, and meaningful visualization.
- Stock-price comparison MUST be included if retained as a mandatory requirement in the approved project specification; otherwise, it MUST be clearly identified as a planned enhancement.
- The project MUST include automated tests, documented setup instructions, reproducible configuration, and a statement of known limitations.
- A feature MUST be considered complete only when its acceptance criteria have been verified and relevant evidence has been recorded.
- Changes to the approved scope MUST be reviewed and reflected in the relevant project documents.

## Governance

These principles govern the specification, planning, implementation, testing, and delivery of the GenAI-Powered Financial News Sentiment Analyzer.

When a proposed implementation conflicts with this constitution, the conflict MUST be resolved before the affected work is accepted. Any amendment to these principles MUST be documented and reflected in subsequent project decisions.

All MUST, SHOULD, and MAY statements are normative: MUST indicates a mandatory requirement, SHOULD indicates a recommended practice that may be departed from with justification, and MAY indicates an optional capability.
