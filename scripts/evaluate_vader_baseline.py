"""Evaluate the existing VADER baseline on a labeled CSV dataset."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from financial_news_sentiment.evaluation import (
    EvaluationReport,
    evaluate_labeled_examples,
    load_labeled_examples,
)


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository_root
        / "data"
        / "evaluation"
        / "synthetic_financial_news_labels.csv",
        help="labeled evaluation CSV (defaults to the synthetic pipeline fixture)",
    )
    parser.add_argument(
        "--misclassifications-csv",
        type=Path,
        help="optionally write misclassified rows to this local CSV path",
    )
    parser.add_argument(
        "--dataset-category",
        choices=("synthetic_pipeline_verification", "manually_labeled_real_news"),
        default="synthetic_pipeline_verification",
        help="label the provenance category in the report; defaults to synthetic",
    )
    args = parser.parse_args()

    examples, excluded = load_labeled_examples(args.input)
    report = evaluate_labeled_examples(examples, excluded)
    print(
        json.dumps(
            _report_payload(report, args.input, args.dataset_category),
            indent=2,
            ensure_ascii=False,
        )
    )
    if args.misclassifications_csv is not None:
        _write_misclassifications(args.misclassifications_csv, report)


def _report_payload(
    report: EvaluationReport, dataset_path: Path, dataset_category: str
) -> dict[str, object]:
    metrics = report.metrics
    return {
        "dataset": str(dataset_path),
        "dataset_category": dataset_category,
        "dataset_note": (
            "The category is caller-declared and does not verify provenance, "
            "human annotation, or usage permissions."
        ),
        "evaluated_count": metrics.evaluated_count,
        "excluded_count": len(report.excluded_records),
        "excluded_records": [asdict(record) for record in report.excluded_records],
        "accuracy": metrics.accuracy,
        "per_class": {
            label: asdict(values) for label, values in metrics.per_class.items()
        },
        "macro_f1": metrics.macro_f1,
        "human_class_distribution": metrics.human_class_distribution,
        "confusion_matrix": {
            "labels": ["Positive", "Negative", "Neutral"],
            "rows": "human labels",
            "columns": "VADER predictions",
            "counts": metrics.confusion_matrix,
        },
        "misclassified_examples": [
            {
                "article_id": example.article_id,
                "human_label": example.human_label,
                "prediction": example.prediction,
                "compound_score": example.compound_score,
                "headline": example.headline,
                "annotation_notes": example.annotation_notes,
            }
            for example in report.misclassified_examples
        ],
    }


def _write_misclassifications(path: Path, report: EvaluationReport) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "article_id",
                "human_label",
                "prediction",
                "compound_score",
                "headline",
                "annotation_notes",
            ),
        )
        writer.writeheader()
        for example in report.misclassified_examples:
            writer.writerow(
                {
                    "article_id": example.article_id,
                    "human_label": example.human_label,
                    "prediction": example.prediction,
                    "compound_score": f"{example.compound_score:.6f}",
                    "headline": example.headline,
                    "annotation_notes": example.annotation_notes or "",
                }
            )


if __name__ == "__main__":
    main()
