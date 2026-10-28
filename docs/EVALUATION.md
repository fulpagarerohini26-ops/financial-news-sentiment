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

The reported figures are **synthetic fixture results only**. They are not
results from manually labeled real financial news, not an out-of-sample or
temporal evaluation, and not a measure of stock-price prediction. A small,
hand-authored, balanced fixture is highly unrepresentative and has selection
and author-labeling bias. VADER may misread financial terminology, numeric
events, sarcasm, mixed language, and context. Sentiment is text classification,
not investment advice or a validated price-prediction model.
