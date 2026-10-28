"""Reproducible evaluation of the existing VADER headline baseline."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from financial_news_sentiment.news.models import NewsArticle
from financial_news_sentiment.news.normalization import (
    normalize_published_at,
    validate_ticker,
)
from financial_news_sentiment.sentiment.baseline_analyzer import (
    BaselineSentimentAnalyzer,
    SentimentLabel,
)

HUMAN_LABELS: tuple[SentimentLabel, ...] = ("Positive", "Negative", "Neutral")
_REQUIRED_COLUMNS = frozenset({"article_id", "ticker", "headline", "human_label"})
_OPTIONAL_COLUMNS = frozenset({"summary", "source", "published_at", "annotation_notes"})
_SUPPORTED_COLUMNS = _REQUIRED_COLUMNS | _OPTIONAL_COLUMNS
_MISSING_DATE = datetime(1970, 1, 1, tzinfo=UTC)


class EvaluationCSVError(ValueError):
    """Raised when an evaluation CSV cannot be parsed or has an invalid schema."""


@dataclass(frozen=True, slots=True)
class LabeledNewsExample:
    """A manually labeled headline and its source metadata."""

    article_id: str
    article: NewsArticle
    human_label: SentimentLabel
    annotation_notes: str | None
    summary: str | None


@dataclass(frozen=True, slots=True)
class ExcludedRecord:
    """A CSV data row excluded from evaluation with an explicit reason."""

    row_number: int
    article_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class EvaluatedExample:
    """Human annotation and VADER prediction kept as distinct fields."""

    article_id: str
    ticker: str
    headline: str
    human_label: SentimentLabel
    prediction: SentimentLabel
    compound_score: float
    annotation_notes: str | None


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    """Per-class precision, recall, F1, and denominators."""

    precision: float
    recall: float
    f1: float
    support: int
    predicted_count: int


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Metrics over one consistent set of valid labeled examples."""

    evaluated_count: int
    accuracy: float | None
    per_class: dict[SentimentLabel, ClassMetrics]
    macro_f1: float
    human_class_distribution: dict[SentimentLabel, int]
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Evaluation output, including examples excluded during CSV validation."""

    metrics: EvaluationMetrics
    examples: tuple[EvaluatedExample, ...]
    excluded_records: tuple[ExcludedRecord, ...]

    @property
    def misclassified_examples(self) -> tuple[EvaluatedExample, ...]:
        """Return evaluated examples whose predicted label differs from human."""
        return tuple(
            example
            for example in self.examples
            if example.human_label != example.prediction
        )


def load_labeled_examples(
    file_path: str | Path,
) -> tuple[tuple[LabeledNewsExample, ...], tuple[ExcludedRecord, ...]]:
    """Load valid labeled headlines and retain row-level exclusions.

    Required columns are article_id, ticker, headline, and human_label.
    Publication timestamps are parsed only when supplied; absent timestamps
    use an internal epoch placeholder because the shared NewsArticle model
    requires one. The placeholder is not exposed as source metadata.
    """
    path = Path(file_path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            try:
                headers = next(reader)
            except StopIteration:
                raise EvaluationCSVError(
                    f"{path}: CSV is empty and has no header row."
                ) from None

            _validate_headers(headers, path)
            examples: list[LabeledNewsExample] = []
            excluded: list[ExcludedRecord] = []
            seen_ids: set[str] = set()
            for row_number, values in enumerate(reader, start=2):
                if not values:
                    continue
                if len(values) != len(headers):
                    excluded.append(
                        ExcludedRecord(
                            row_number=row_number,
                            article_id=None,
                            reason=(
                                f"expected {len(headers)} fields, found {len(values)}"
                            ),
                        )
                    )
                    continue
                row = dict(zip(headers, values, strict=True))
                example, reason = _normalize_row(row)
                if reason is not None:
                    excluded.append(
                        ExcludedRecord(
                            row_number=row_number,
                            article_id=_optional_value(row.get("article_id")),
                            reason=reason,
                        )
                    )
                elif example is not None:
                    if example.article_id in seen_ids:
                        excluded.append(
                            ExcludedRecord(
                                row_number=row_number,
                                article_id=example.article_id,
                                reason="duplicate article_id",
                            )
                        )
                        continue
                    seen_ids.add(example.article_id)
                    examples.append(example)
            return tuple(examples), tuple(excluded)
    except FileNotFoundError as error:
        raise EvaluationCSVError(f"{path}: CSV file was not found.") from error
    except PermissionError as error:
        raise EvaluationCSVError(
            f"{path}: permission denied while reading CSV file."
        ) from error
    except UnicodeDecodeError as error:
        raise EvaluationCSVError(f"{path}: file is not valid UTF-8 text.") from error
    except csv.Error as error:
        raise EvaluationCSVError(f"{path}: malformed CSV input: {error}") from error
    except OSError as error:
        raise EvaluationCSVError(f"{path}: unable to read CSV file: {error}") from error


def evaluate_labeled_examples(
    examples: Iterable[LabeledNewsExample],
    excluded_records: Iterable[ExcludedRecord] = (),
) -> EvaluationReport:
    """Score only the headline using the existing baseline and compute metrics."""
    example_list = tuple(examples)
    excluded_list = tuple(excluded_records)
    if any(not isinstance(example, LabeledNewsExample) for example in example_list):
        raise TypeError("examples must contain only LabeledNewsExample objects")
    if any(not isinstance(record, ExcludedRecord) for record in excluded_list):
        raise TypeError("excluded_records must contain only ExcludedRecord objects")

    analyzed = BaselineSentimentAnalyzer().analyze_many(
        example.article for example in example_list
    )
    evaluated = tuple(
        EvaluatedExample(
            article_id=example.article_id,
            ticker=example.article.ticker,
            headline=example.article.headline,
            human_label=example.human_label,
            prediction=result.label,
            compound_score=result.compound_score,
            annotation_notes=example.annotation_notes,
        )
        for example, result in zip(example_list, analyzed, strict=True)
    )
    metrics = calculate_evaluation_metrics(
        (example.human_label for example in evaluated),
        (example.prediction for example in evaluated),
    )
    return EvaluationReport(metrics, evaluated, excluded_list)


def calculate_evaluation_metrics(
    human_labels: Iterable[str],
    predictions: Iterable[str],
) -> EvaluationMetrics:
    """Calculate fixed-order metrics; undefined per-class values are zero.

    Confusion-matrix rows are human labels and columns are VADER predictions,
    both ordered Positive, Negative, Neutral. Empty input has undefined
    accuracy (None), zero class metrics, and macro F1 of zero.
    """
    human = tuple(_validated_label(label, "human label") for label in human_labels)
    predicted = tuple(_validated_label(label, "prediction") for label in predictions)
    if len(human) != len(predicted):
        raise ValueError("human_labels and predictions must have equal lengths")

    human_distribution: dict[SentimentLabel, int] = {}
    for label in HUMAN_LABELS:
        human_distribution[label] = sum(value == label for value in human)
    matrix = [[0 for _ in HUMAN_LABELS] for _ in HUMAN_LABELS]
    for actual, guess in zip(human, predicted, strict=True):
        matrix[HUMAN_LABELS.index(actual)][HUMAN_LABELS.index(guess)] += 1

    per_class: dict[SentimentLabel, ClassMetrics] = {}
    f1_values: list[float] = []
    for class_index, label in enumerate(HUMAN_LABELS):
        true_positive = matrix[class_index][class_index]
        support = sum(matrix[class_index])
        predicted_count = sum(row[class_index] for row in matrix)
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        per_class[label] = ClassMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            support=support,
            predicted_count=predicted_count,
        )
        f1_values.append(f1)

    count = len(human)
    accuracy = (
        sum(actual == guess for actual, guess in zip(human, predicted, strict=True))
        / count
        if count
        else None
    )
    return EvaluationMetrics(
        evaluated_count=count,
        accuracy=accuracy,
        per_class=per_class,
        macro_f1=math.fsum(f1_values) / len(HUMAN_LABELS),
        human_class_distribution=human_distribution,
        confusion_matrix=tuple(tuple(row) for row in matrix),
    )


def _validate_headers(headers: list[str], path: Path) -> None:
    if any(not header.strip() for header in headers):
        raise EvaluationCSVError(f"{path}: CSV headers must not be blank.")
    if len(headers) != len(set(headers)):
        raise EvaluationCSVError(f"{path}: CSV contains duplicate column names.")
    missing = sorted(_REQUIRED_COLUMNS - set(headers))
    if missing:
        raise EvaluationCSVError(
            f"{path}: missing required CSV column(s): {', '.join(missing)}."
        )
    unsupported = sorted(set(headers) - _SUPPORTED_COLUMNS)
    if unsupported:
        raise EvaluationCSVError(
            f"{path}: unsupported CSV column(s): {', '.join(unsupported)}."
        )


def _normalize_row(row: dict[str, str]) -> tuple[LabeledNewsExample | None, str | None]:
    article_id = row["article_id"].strip()
    ticker_value = row["ticker"]
    headline = row["headline"]
    label_value = row["human_label"].strip()
    reasons: list[str] = []
    if not article_id:
        reasons.append("article_id is required")
    if not isinstance(ticker_value, str) or not ticker_value.strip():
        reasons.append("ticker is required")
    if not isinstance(headline, str) or not headline.strip():
        reasons.append("headline is required")
    if label_value not in HUMAN_LABELS:
        reasons.append("human_label must be Positive, Negative, or Neutral")

    ticker: str | None = None
    if ticker_value.strip():
        try:
            ticker = validate_ticker(ticker_value)
        except ValueError:
            reasons.append("ticker is invalid")

    published_at = _MISSING_DATE
    published_timestamp = 0
    timestamp_text = row.get("published_at", "").strip()
    if timestamp_text:
        try:
            parsed = datetime.fromisoformat(timestamp_text)
            if parsed.utcoffset() is None:
                raise ValueError("timestamp needs timezone")
            published_at, published_timestamp = normalize_published_at(parsed)
        except ValueError:
            reasons.append("published_at must be ISO 8601 with a timezone offset")

    if reasons:
        return None, "; ".join(reasons)

    assert ticker is not None
    label = _validated_label(label_value, "human label")
    summary = _optional_value(row.get("summary"))
    article = NewsArticle(
        ticker=ticker,
        headline=headline,
        published_at=published_at,
        published_timestamp=published_timestamp,
        summary=None,
        source=_optional_value(row.get("source")),
    )
    return (
        LabeledNewsExample(
            article_id=article_id,
            article=article,
            human_label=label,
            annotation_notes=_optional_value(row.get("annotation_notes")),
            summary=summary,
        ),
        None,
    )


def _validated_label(value: str, field: str) -> SentimentLabel:
    if value == "Positive":
        return "Positive"
    if value == "Negative":
        return "Negative"
    if value == "Neutral":
        return "Neutral"
    raise ValueError(f"{field} must be one of {', '.join(HUMAN_LABELS)}; got {value!r}")


def _optional_value(value: str | None) -> str | None:
    return value if value is not None and value.strip() else None
