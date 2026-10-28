# VADER Headline Baseline Evaluation

## Dataset and provenance

`data/evaluation/synthetic_financial_news_labels.csv` is a small, manually
authored **synthetic pipeline fixture**, not real financial news. It was
authored on 2026-10-28 and contains fictional Acme headlines; its labels were
assigned while writing the fixture according to the guide below, not generated
from VADER. It is version-controlled for repeatable tests and demonstrations.
It is not a training set, an independently annotated real-news sample, or
evidence of financial-news performance. No manually labeled real-news dataset
was present in the repository when this evaluation was added.

The fixture has 12 valid rows: four Positive, four Negative, and four Neutral
human labels. There are no excluded rows in the checked-in fixture. The
fixture's sample size is intentionally small. No second annotator labeled a
subset, and inter-annotator agreement was not measured.

## CSV schema

CSV files must be UTF-8 with a header. Required columns are:

| Column | Required | Meaning |
|---|---:|---|
| `article_id` | Yes | Unique non-empty dataset record identifier; kept as text |
| `ticker` | Yes | Non-empty ticker accepted by the shared ticker validator |
| `headline` | Yes | Non-empty headline to classify |
| `human_label` | Yes | Exactly `Positive`, `Negative`, or `Neutral` |
| `summary` | No | Optional retained context; not scored in this evaluation |
| `source` | No | Optional provenance/source label |
| `published_at` | No | Optional ISO 8601 timestamp with timezone offset |
| `annotation_notes` | No | Optional rationale or uncertainty note |

Unknown or duplicate headers and missing required headers invalidate the file.
Invalid data rows (including missing required values, unsupported labels,
invalid ticker/timestamp, malformed field counts, and duplicate article IDs)
are excluded and reported with row numbers and reasons. Blank lines are
ignored. An unresolved annotation must not be forced into one of the classes:
leave `human_label` blank and explain the uncertainty in `annotation_notes`;
the row is then excluded and counted.

If `published_at` is absent, the loader supplies the shared article model with
an internal UTC epoch placeholder because that model requires a timestamp.
This placeholder is not treated as source metadata and is not included in the
evaluation report. A provided timestamp must be timezone-aware.

## Labeling guide

The human label describes sentiment **expressed by the news text**, not
whether an event is good or bad for a stock, the expected direction of its
price, or any subsequent market movement.

- **Positive:** The wording expresses favorable tone (for example, praise,
  success, improvement, or optimism).
- **Negative:** The wording expresses unfavorable tone (for example,
  criticism, failure, deterioration, or concern).
- **Neutral:** Factual wording without a clear positive or negative expressed
  tone. A factual announcement is not automatically positive or negative
  because it may matter to investors.
- **Mixed/conflicting:** Consider the headline as a whole. Use the dominant
  expressed tone only when one is clear; use Neutral when the wording presents
  conflicting facts without a clear expressed polarity. Record the reasoning.
- **Ambiguous/numeric events:** Do not infer tone or price implications from a
  number alone (including beats, misses, gains, losses, or percentage
  changes). Follow the text's expressed wording and note ambiguity.
- **Uncertain:** Do not silently force a class. Leave the label blank and
  record the uncertainty in notes so the evaluator excludes and counts it.

For future real-news evaluation, preserve source/date and collection
provenance, use a separately maintained evaluation set (not training or
development data), and have a second person independently label a feasible
subset before adjudication. Report disagreements and calculate agreement only
if it is actually measured. The synthetic fixture has no second annotator.

## Real-news dataset preparation (workflow only; collection pending)

No real-news records have been collected or labeled for this project. The
offline templates in `data/evaluation/real_news/` define separate files for
article provenance, independent annotations, source permission reviews, and
adjudication records. They contain no headlines or invented human annotations.
The workflow is ready for lawful records, but real collection is currently
blocked: account-specific research/storage/report rights and publisher rights
have not been confirmed, and a second independent annotator has not yet been
engaged.

The articles CSV requires:

| Column | Meaning |
|---|---|
| `internal_article_id` | Stable dataset-local identifier |
| `ticker` | Validated ticker/company identifier |
| `provider_name` | Provider or publisher |
| `provider_article_id` | Optional source identifier, only when retention is permitted |
| `source_url` | Optional URL, only when retaining it is permitted |
| `headline`, `summary` | Text; summary is optional and is never used in this headline evaluation |
| `published_at` | ISO 8601 timestamp with explicit offset |
| `publication_timezone_handling` | How the original zone/offset and UTC normalization were handled |
| `collected_at_utc` | Collection timestamp in UTC |
| `dataset_version` | Dataset revision |
| `provenance_ref` | Reference to the permitted source/collection record |
| `permission_review_id` | Link to a reviewed permission record |
| `usage_notes` | Applicable use, attribution, and retention notes |
| `partition` | Blank before splitting; otherwise `development` or `heldout` |

The annotation file is keyed by `internal_article_id` and stores a pseudonymous
`annotator_code`, `annotator_role` (`primary` or `second`), UTC annotation
timestamp, label, uncertainty flag, rationale, and guide version. One primary
annotation is expected for an included article; a second annotation is
independent and required only for a subset. Preserve both labels. The separate
adjudication file records pending/resolved state, adjudicated label, UTC time,
adjudicator code, and rationale; never overwrite the originals. Uncertain
annotations are recorded with a blank label, `uncertain=yes`, and a reason.

The permission review file records the terms URL and check date, actual
account/plan verification, research, local storage, display, redistribution,
and evaluation-report status (`allowed`, `prohibited`, or `unclear`),
attribution and retention requirements, written-approval reference, and
reviewer notes. The validator reports
`review_cleared_for_local_evaluation` only when the review record is complete,
the account plan is marked verified, required research/local-storage/report
uses are marked allowed, and approval/evidence fields are present. This is a
structured owner-entered review status—not a legal determination, provider
grant, or proof that a record is permitted. Display and redistribution remain
separately recorded. Missing permission evidence is reported as not reviewed
or unclear, never inferred from populated article provenance.
The report includes separate status counts for permission-review records and
for article records linked to those reviews; an empty article template may
therefore show a pending review while the linked-record counts are zero.

As checked on 2026-10-28, Finnhub's public
[Terms of Service](https://finnhub.io/terms-of-service) state that access
does not grant ownership or IP rights, data must be deleted if a subscription
ends, and data or derived results may not be redistributed/shared without
written approval. Account-plan terms, private research/storage rights,
evaluation-output use, retention duration, required attribution, written
approval, and underlying publisher rights remain unresolved. The linked UTP
policy and subscriber-agreement PDFs could not be retrieved for this review.
Therefore **no collection or storage of real news has been authorized or
started**. See [DATA_SOURCE.md](DATA_SOURCE.md) for the dated source review and
unresolved terms. Do not fetch records to populate these templates until the
specific use is verified and documented.

### Independent annotation and agreement

Annotators must use the labeling guide above, work independently, and not see
VADER predictions before both have submitted their original labels. Record
the second annotator on the subset chosen before comparison. The report
calculates the disagreement rate as differing, valid two-annotator pairs /
all valid two-annotator pairs. Cohen's kappa is calculated on those same
pairs; it is unavailable when there are no pairs or expected agreement is
exactly 1.0. Small or class-imbalanced subsets make agreement statistics
unstable; report counts and limitations alongside kappa. Unresolved
disagreements and uncertain cases are excluded from split/evaluation exports
until adjudicated.

### Deterministic development/held-out split

The split command groups exact normalized headline duplicates and likely
near-duplicates (normalized text similarity >= 0.90) before seeded random
assignment. Headlines are normalized by case-folding, replacing punctuation
with spaces, and collapsing whitespace. Same source/provider article IDs and
source URLs are also flagged as duplicates by validation. A group is assigned
as a unit, preventing detected related headlines from crossing partitions.
The held-out fraction is a target and can differ due to group sizes. No
stratification is forced; class counts are recorded per output, and a small
sample may have unbalanced or missing classes. Inspect duplicate warnings
because automatic near-duplicate detection can miss paraphrases or flag
similar but distinct headlines.

The split manifest records the seed, fraction target, output IDs, sizes, and
class counts. Keep the held-out file untouched by threshold selection, model
selection, prompt work, and error-driven tuning. Use development data for any
future tuning. A held-out result is not representative of all financial news
without a sampling design and evidence.

The validator's `total_records_received` is the article-file row count.
`human_label_counts` use valid primary annotations as recorded; adjudication
does not overwrite that original-label distribution.
`invalid_or_missing_required_count` counts invalid article rows.
`excluded_record_count` counts invalid article rows plus valid-provenance
articles lacking a permission-cleared review, primary annotation, or resolved
uncertainty/disagreement. Separate invalid-annotation,
invalid-permission-review, and invalid-adjudication counts are reported;
`excluded_records` lists issues across the input files and eligibility
exclusions. Duplicate and potential-duplicate counts are unique article
records participating in flagged pairs; the pair list shows each relationship.
Second-annotator coverage uses valid provenance records as its denominator;
disagreement and kappa use only complete, valid, non-uncertain pairs.

Validate the templates (which currently have no articles):

```powershell
uv run --locked python scripts/prepare_evaluation_dataset.py validate --articles data/evaluation/real_news/articles_template.csv --annotations data/evaluation/real_news/annotations_template.csv --permissions data/evaluation/real_news/permission_reviews_template.csv
```

After lawful acquisition, terms review, and human annotation, validate copied
working files (do not enter records into the tracked templates):

```powershell
uv run --locked python scripts/prepare_evaluation_dataset.py validate --articles path\to\articles.csv --annotations path\to\annotations.csv --permissions path\to\permission-reviews.csv --adjudications path\to\adjudications.csv
```

Create a deterministic split only when at least two eligible examples have
complete, permission-cleared annotations:

```powershell
uv run --locked python scripts/prepare_evaluation_dataset.py split --articles path\to\articles.csv --annotations path\to\annotations.csv --permissions path\to\permission-reviews.csv --adjudications path\to\adjudications.csv --development-output path\to\development.csv --heldout-output path\to\heldout.csv --manifest-output path\to\split-manifest.json --seed 20261028 --heldout-fraction 0.2
```

The split refuses malformed records, skips unresolved disagreements and
records without the structured local-evaluation permission status, and
requires at least two eligible examples. It writes evaluator-compatible
headline CSVs; pass only `heldout.csv` to
`scripts/evaluate_vader_baseline.py` for final evaluation. The output contains
headline excerpts and is subject to the applicable rights and retention
restrictions.

## Evaluation method

Run the existing `BaselineSentimentAnalyzer` once per valid example, using the
headline only. The loader deliberately keeps `summary=None` in the
`NewsArticle` passed to that analyzer, even when the CSV has a summary. It does
not modify or combine headline and summary text. The existing VADER package
version and thresholds are used unchanged: Positive at compound `>= 0.05`,
Negative at `<= -0.05`, and Neutral otherwise.

All reported metrics use the exact same set of valid labeled rows. Excluded
rows are not scored. Confusion-matrix labels and order are **Positive,
Negative, Neutral** for both axes; rows are human labels and columns are VADER
predictions. Accuracy is correct predictions divided by evaluated examples.
Each class's precision is `TP / predicted_count`, recall is `TP / human
support`, and F1 is the harmonic mean of precision and recall. Macro F1 is the
unweighted mean of the three class F1 scores. A zero denominator for a class
metric is reported as zero. For an empty evaluation, accuracy is undefined
(`null` in JSON); per-class metrics and macro F1 are zero. Human class
distribution reports counts in the evaluated set.

Misclassifications are listed with record ID, human label, VADER prediction,
compound score, headline, and annotation notes. No automatic root-cause label
is assigned. A reviewer may categorize errors (for example financial
terminology, numeric event, mixed sentiment, ambiguity, or context) only
after inspecting the individual case. Optional CSV export is local and
explicit; respect source terms and do not distribute copyrighted text.

## Observed synthetic fixture results

Command run with the locked project environment:

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py
```

Observed result on the checked-in fixture: **12 evaluated**, **0 excluded**;
human class distribution Positive **4**, Negative **4**, Neutral **4**.

| Metric | Observed value |
|---|---:|
| Accuracy | 0.8333 |
| Positive precision / recall / F1 | 1.0000 / 1.0000 / 1.0000 |
| Negative precision / recall / F1 | 0.7500 / 0.7500 / 0.7500 |
| Neutral precision / recall / F1 | 0.7500 / 0.7500 / 0.7500 |
| Macro F1 | 0.8333 |

Confusion matrix (rows are human labels; columns are VADER predictions, each
in Positive, Negative, Neutral order):

| Human \ VADER | Positive | Negative | Neutral |
|---|---:|---:|---:|
| Positive | 4 | 0 | 0 |
| Negative | 0 | 3 | 1 |
| Neutral | 0 | 1 | 3 |

The two fixture mismatches are (1) a fictional headline describing a “steep
decline in quarterly revenue,” labeled Negative but predicted Neutral, and
(2) a fictional headline factually reporting a 2% loss, labeled Neutral but
predicted Negative. These are observed mismatches on synthetic examples; no
root cause is assigned, and they do not characterize real financial text or
support a performance claim. The metric values are included to verify the
pipeline only.

## Running and limitations

Run on the synthetic fixture:

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py
```

Run another compatible labeled CSV and optionally write a local
misclassification CSV:

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py --input path\to\labeled.csv --misclassifications-csv path\to\errors.csv
```

For a held-out real-news CSV produced by the permission-gated workflow, declare
its reporting category explicitly:

```powershell
uv run --locked python scripts/evaluate_vader_baseline.py --input path\to\heldout.csv --dataset-category manually_labeled_real_news
```

The reported figures are **synthetic fixture results only**. They are not
results from manually labeled real financial news, not an out-of-sample or
temporal evaluation, and not a measure of stock-price prediction. A small,
hand-authored, balanced fixture is highly unrepresentative and has selection
and author-labeling bias. VADER may misread financial terminology, numeric
events, sarcasm, mixed language, and context. Sentiment is text classification,
not investment advice or a validated price-prediction model.
