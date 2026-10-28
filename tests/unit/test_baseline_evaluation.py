from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from financial_news_sentiment.evaluation import (
    EvaluationCSVError,
    calculate_evaluation_metrics,
    evaluate_labeled_examples,
    load_labeled_examples,
)

_FIELDS = [
    "article_id",
    "ticker",
    "headline",
    "human_label",
    "summary",
    "source",
    "published_at",
    "annotation_notes",
]


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "article_id": "sample-1",
        "ticker": "aapl",
        "headline": "Excellent revenue growth!",
        "human_label": "Positive",
        "summary": "Summary sentiment is deliberately not evaluated.",
        "source": "Synthetic Test Source",
        "published_at": "2026-10-27T09:00:00-04:00",
        "annotation_notes": "Fixture-authored label.",
    }
    row.update(overrides)
    return row


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    fields: list[str] | None = None,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or _FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_labeled_csv_loads_optional_fields_and_timestamp(
    tmp_path: Path,
) -> None:
    path = tmp_path / "labels.csv"
    _write_csv(path, [_row()])

    examples, excluded = load_labeled_examples(path)

    assert excluded == ()
    assert len(examples) == 1
    example = examples[0]
    assert example.article_id == "sample-1"
    assert example.article.ticker == "AAPL"
    assert example.article.headline == "Excellent revenue growth!"
    assert example.human_label == "Positive"
    assert example.summary == "Summary sentiment is deliberately not evaluated."
    assert example.article.source == "Synthetic Test Source"
    assert example.article.published_at == datetime(2026, 10, 27, 13, tzinfo=UTC)
    assert example.annotation_notes == "Fixture-authored label."
    assert example.article.summary is None


@pytest.mark.parametrize("label", ["positive", "Bullish", "", "Unknown"])
def test_invalid_human_labels_are_excluded_with_reason(
    tmp_path: Path, label: str
) -> None:
    path = tmp_path / "invalid-label.csv"
    _write_csv(path, [_row(human_label=label)])

    examples, excluded = load_labeled_examples(path)

    assert examples == ()
    assert len(excluded) == 1
    assert "human_label must be Positive, Negative, or Neutral" in excluded[0].reason


def test_missing_required_row_fields_are_excluded_and_counted(tmp_path: Path) -> None:
    path = tmp_path / "missing-fields.csv"
    _write_csv(path, [_row(article_id="", ticker="", headline="")])

    examples, excluded = load_labeled_examples(path)

    assert examples == ()
    assert len(excluded) == 1
    assert excluded[0].reason == (
        "article_id is required; ticker is required; headline is required"
    )


def test_missing_required_columns_fail_schema_validation(tmp_path: Path) -> None:
    path = tmp_path / "missing-columns.csv"
    _write_csv(path, [], fields=["article_id", "headline"])

    with pytest.raises(EvaluationCSVError, match="human_label, ticker"):
        load_labeled_examples(path)


def test_empty_dataset_evaluates_without_division_by_zero(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    _write_csv(path, [])
    examples, excluded = load_labeled_examples(path)

    report = evaluate_labeled_examples(examples, excluded)

    assert report.metrics.evaluated_count == 0
    assert report.metrics.accuracy is None
    assert report.metrics.macro_f1 == 0.0
    assert report.metrics.confusion_matrix == ((0, 0, 0), (0, 0, 0), (0, 0, 0))
    assert report.metrics.human_class_distribution == {
        "Positive": 0,
        "Negative": 0,
        "Neutral": 0,
    }


def test_metrics_on_known_examples_and_confusion_matrix_orientation() -> None:
    metrics = calculate_evaluation_metrics(
        ["Positive", "Positive", "Negative", "Negative", "Neutral"],
        ["Positive", "Negative", "Negative", "Neutral", "Neutral"],
    )

    assert metrics.evaluated_count == 5
    assert metrics.accuracy == pytest.approx(0.6)
    assert metrics.confusion_matrix == (
        (1, 1, 0),
        (0, 1, 1),
        (0, 0, 1),
    )
    assert metrics.human_class_distribution == {
        "Positive": 2,
        "Negative": 2,
        "Neutral": 1,
    }
    assert metrics.per_class["Positive"].precision == pytest.approx(1.0)
    assert metrics.per_class["Positive"].recall == pytest.approx(0.5)
    assert metrics.per_class["Positive"].f1 == pytest.approx(2 / 3)
    assert metrics.per_class["Negative"].precision == pytest.approx(0.5)
    assert metrics.per_class["Negative"].recall == pytest.approx(0.5)
    assert metrics.per_class["Negative"].f1 == pytest.approx(0.5)
    assert metrics.per_class["Neutral"].precision == pytest.approx(0.5)
    assert metrics.per_class["Neutral"].recall == pytest.approx(1.0)
    assert metrics.per_class["Neutral"].f1 == pytest.approx(2 / 3)
    assert metrics.macro_f1 == pytest.approx((2 / 3 + 0.5 + 2 / 3) / 3)


def test_zero_division_is_zero_for_absent_human_and_predicted_classes() -> None:
    metrics = calculate_evaluation_metrics(["Positive"], ["Negative"])

    assert metrics.accuracy == 0.0
    assert metrics.per_class["Positive"].precision == 0.0
    assert metrics.per_class["Positive"].recall == 0.0
    assert metrics.per_class["Negative"].precision == 0.0
    assert metrics.per_class["Negative"].recall == 0.0
    assert metrics.per_class["Neutral"].precision == 0.0
    assert metrics.per_class["Neutral"].recall == 0.0
    assert metrics.macro_f1 == 0.0


def test_metrics_reject_mismatched_or_invalid_labels() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        calculate_evaluation_metrics(["Positive"], [])
    with pytest.raises(ValueError, match="human label"):
        calculate_evaluation_metrics(["Bullish"], ["Positive"])


def test_excluded_records_and_misclassification_details_are_reported(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mixed.csv"
    _write_csv(
        path,
        [
            _row(
                article_id="wrong",
                headline="The company reports a loss of 2% in the quarter",
                human_label="Neutral",
                annotation_notes="Factual phrasing; sentiment is not the event impact.",
            ),
            _row(article_id="invalid", human_label="Bullish"),
            _row(article_id="missing", headline=" "),
            _row(article_id="correct", headline="Excellent revenue growth!"),
            _row(article_id="wrong"),
        ],
    )
    examples, excluded = load_labeled_examples(path)

    report = evaluate_labeled_examples(examples, excluded)

    assert report.metrics.evaluated_count == 2
    assert len(report.excluded_records) == 3
    assert report.excluded_records[0].article_id == "invalid"
    assert "headline is required" in report.excluded_records[1].reason
    assert report.excluded_records[2].reason == "duplicate article_id"
    errors = report.misclassified_examples
    assert len(errors) == 1
    assert errors[0].article_id == "wrong"
    assert errors[0].human_label == "Neutral"
    assert errors[0].prediction == "Negative"
    assert errors[0].compound_score < -0.05
    assert errors[0].headline == "The company reports a loss of 2% in the quarter"
    assert errors[0].annotation_notes == (
        "Factual phrasing; sentiment is not the event impact."
    )


def test_evaluation_is_deterministic_and_uses_existing_headline_analyzer(
    tmp_path: Path,
) -> None:
    path = tmp_path / "single.csv"
    _write_csv(path, [_row()])
    examples, excluded = load_labeled_examples(path)

    first = evaluate_labeled_examples(examples, excluded)
    second = evaluate_labeled_examples(examples, excluded)

    assert first == second
    assert first.examples[0].prediction == "Positive"
    assert first.examples[0].compound_score > 0.05


def test_optional_timestamp_may_be_absent_and_invalid_timestamp_is_excluded(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timestamps.csv"
    _write_csv(
        path,
        [
            _row(article_id="no-date", published_at=""),
            _row(article_id="bad-date", published_at="2026-10-27T09:00:00"),
        ],
    )

    examples, excluded = load_labeled_examples(path)

    assert len(examples) == 1
    assert examples[0].article.published_timestamp == 0
    assert len(excluded) == 1
    assert "timezone offset" in excluded[0].reason
