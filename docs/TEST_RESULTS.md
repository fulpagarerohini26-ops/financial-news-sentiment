# Provider Diagnostic Results

## Finnhub Probe: 2026-10-19

This is an observed, single-run diagnostic of Finnhub access for this account. It is not an application integration test, does not establish account-wide plan entitlement, and does not complete the provider-verification gate. No token or response body was stored.

Command, run from the repository root in the Python 3.12 project environment:

```powershell
uv run --no-sync --env-file .env python scripts/validate_finnhub.py
```

### Company News

- Endpoint: Finnhub `GET /api/v1/company-news`
- Request: `AAPL`, 2026-10-01 through 2026-10-07 inclusive
- HTTP status: `200`
- JSON: valid; top-level list
- Records: `238`
- Returned fields: `category`, `datetime`, `headline`, `id`, `image`, `related`, `source`, `summary`, `url`
- Missing or unusable: timestamps `0`, headlines `0`, sources `0`, URLs `0`, summaries `1`
- Date observation: interpreting the Unix timestamps as UTC and converting to `America/New_York`, one timestamp falls on 2026-09-30, outside the requested calendar-date range. Observed timestamp coverage was 2026-09-30 through 2026-10-07 in New York.

### Historical Daily Candles

- Endpoint: Finnhub `GET /api/v1/stock/candle`
- Request: `AAPL`, resolution `D`, same date range
- HTTP status: `403`; valid JSON object with field `error`
- Result: denied; message: `You don't have access to this resource.`
- OHLCV arrays and daily values: unavailable, so lengths and values could not be validated.

### Interpretation and Follow-Up

These results establish only what the API returned for this particular request and account at the time of the probe. The candle denial does not by itself identify whether the cause is plan entitlement, endpoint permissions, or another account restriction. Finnhub's [stock-candles documentation](https://finnhub.io/docs/api/stock-candles) labels the endpoint Premium; confirm the account-specific reason in the Finnhub dashboard or with Finnhub support. Do not infer broader historical-price access from a short-range result.

The [company-news documentation](https://finnhub.io/docs/api/company-news) and [stock-candles documentation](https://finnhub.io/docs/api/stock-candles) should be checked again for current field definitions, timestamp semantics, date boundaries, limits, and applicable usage terms before any adapter is implemented. This diagnostic did not verify licensing, attribution, retention, redistribution, classroom-use terms, or overall plan entitlement. No stock-price provider has been selected.

## Baseline Sentiment Verification: 2026-10-26

Commands were run from the repository root with Python 3.12.15 and the locked
environment:

| Command | Observed result |
|---|---|
| `uv run --locked pytest` | Passed: 81 passed, 7 xfailed |
| `uv run --locked ruff check .` | Passed: all checks passed |
| Pylance diagnostics for the new analyzer, metrics, package initializer, demo, and sentiment tests | Passed: no diagnostics returned |
| `uv run --locked ruff format --check .` | Failed because existing unrelated repository files are not formatted; changed Python files were checked separately |
| `uv run --locked python scripts/demo_baseline_sentiment.py` | Passed; loaded three synthetic CSV articles and printed article IDs, tickers, headlines, scores, labels, and aggregate metrics without network access |

The suite's seven expected failures are the existing `xfail` cases in the
Nasdaq calendar verification tests; they are not reported as passing tests.
This verification covers the baseline implementation and does not establish
financial-news classification accuracy or predictive validity.

## VADER Evaluation Pipeline: 2026-10-28

The checked-in evaluation dataset is a small synthetic fixture, not real
financial news. Running
`uv run --locked python scripts/evaluate_vader_baseline.py` observed 12
evaluated examples, zero excluded rows, and human class counts of 4 Positive,
4 Negative, and 4 Neutral. Accuracy and macro F1 were both 0.8333. Two
synthetic mismatches were observed: the fictional “steep decline” headline
was predicted Neutral, and the factual “loss of 2%” headline was predicted
Negative. These numbers validate pipeline execution only; they are not
real-news performance results. Full evaluation semantics and the confusion
matrix are documented in [EVALUATION.md](EVALUATION.md).

The full repository suite on 2026-10-28 completed with **108 passed and 7
expected failures** (`uv run --locked pytest`). Repository Ruff lint passed;
format checking passed for the changed Python files. Pylance returned no
diagnostics for the evaluation module, CLI script, or evaluation tests.

## Real-News Dataset Workflow Verification: 2026-10-28

The local validation command was run against the tracked real-news templates:

```powershell
uv run --locked python scripts/prepare_evaluation_dataset.py validate --articles data/evaluation/real_news/articles_template.csv --annotations data/evaluation/real_news/annotations_template.csv --permissions data/evaluation/real_news/permission_reviews_template.csv
```

Observed report: **0 article records received**, **0 valid provenance
records**, one permission-review template classified `not_reviewed`, zero
permission-cleared articles, zero annotations, and no disagreement or
partition measurements. This verifies empty-template handling only; it is not
a real-news dataset validation.

At that checkpoint, the full suite completed with **122 passed and 7 xfailed**
(`uv run --locked pytest`). `uv run --locked ruff check .`, changed-file Ruff
format checks, `git diff --check`, and Pylance diagnostics for the new
dataset module, preparation command, evaluator CLI, and dataset tests passed.
The synthetic evaluator still reports its separate 12-example fixture results;
no real-news model evaluation has been run.

## Collection and Annotation Workflow: 2026-10-28

The final workflow suite completed with **131 passed and 7 xfailed**
(`uv run --locked pytest`), including Finnhub, CSV, sentiment, evaluation, and
Nasdaq calendar tests. The 7 expected failures are existing Nasdaq calendar
verification xfails.

`uv run --locked ruff check .`, Ruff format checks for all changed Python
files, `git diff --check`, and Pylance diagnostics for the changed workflow,
dataset, CLI, evaluator, and test files passed. The focused workflow/evaluator
run completed with **37 passed**.

The CLI validation command reported zero real-news articles, zero valid
provenance records, and one permission review `not_reviewed`. An explicit
`collect-finnhub` command using that unresolved review was rejected before the
Finnhub adapter was called; no network request or output files were created.
The manually labeled synthetic fixture still evaluates separately as
`synthetic_pipeline_verification`; no real-news collection, annotation,
split, freeze, or evaluation was performed.

## Readiness Review and Split Validation: 2026-10-28

Added a `validate-split` command to check that development and held-out files
match the current source hashes, permission-cleared article set, resolved
human labels, partition IDs, class counts, and duplicate/near-duplicate
grouping. A test deliberately changes a held-out label and updates its file
hash; validation rejects the modified label against its independent
annotation. The unresolved-permission test also confirms that both Finnhub
collection and offline CSV import stop before creating article outputs.

Observed checks:

| Command | Result |
|---|---|
| `uv run --locked pytest tests/unit/test_evaluation_dataset.py` | Passed: 24 tests |
| `uv run --locked pytest` | Passed: 132 passed, 7 xfailed |
| `uv run --locked ruff check .` | Passed |
| `uv run --locked ruff format --check src/financial_news_sentiment/evaluation_dataset.py src/financial_news_sentiment/evaluation_workflow.py scripts/prepare_evaluation_dataset.py tests/unit/test_evaluation_dataset.py` | Passed |
| `git diff --check` | Passed |
| `uv run --locked python scripts/prepare_evaluation_dataset.py --help` | Passed; lists `validate-split` |

No real-news collection or import, human annotation, split, freeze, or
real-news evaluation was performed. Provider rights remain unresolved, and
the tracked data files remain templates.
