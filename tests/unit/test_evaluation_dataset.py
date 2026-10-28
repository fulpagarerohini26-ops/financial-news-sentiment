from __future__ import annotations

import csv
from pathlib import Path

import pytest

from financial_news_sentiment.evaluation import (
    evaluate_labeled_examples,
    load_labeled_examples,
)
from financial_news_sentiment.evaluation_dataset import (
    DatasetValidationError,
    create_deterministic_split,
    validate_evaluation_dataset,
)

ARTICLE_FIELDS = [
    "internal_article_id",
    "ticker",
    "provider_name",
    "provider_article_id",
    "source_url",
    "headline",
    "summary",
    "published_at",
    "publication_timezone_handling",
    "collected_at_utc",
    "dataset_version",
    "provenance_ref",
    "permission_review_id",
    "usage_notes",
    "partition",
]
ANNOTATION_FIELDS = [
    "internal_article_id",
    "annotator_code",
    "annotator_role",
    "annotated_at_utc",
    "human_label",
    "uncertain",
    "rationale",
    "annotation_guide_version",
]
PERMISSION_FIELDS = [
    "permission_review_id",
    "provider_name",
    "terms_url",
    "checked_at_utc",
    "account_plan_verified",
    "research_use",
    "local_storage",
    "display",
    "redistribution",
    "evaluation_reporting",
    "attribution_requirement",
    "retention_requirement",
    "written_approval_reference",
    "reviewer_notes",
]
ADJUDICATION_FIELDS = [
    "internal_article_id",
    "resolution_status",
    "adjudicated_label",
    "adjudicated_at_utc",
    "adjudicator_code",
    "rationale",
]


def _article(article_id: str, headline: str, **overrides: str) -> dict[str, str]:
    row = {
        "internal_article_id": article_id,
        "ticker": "ACME",
        "provider_name": "Synthetic Source",
        "provider_article_id": "",
        "source_url": "",
        "headline": headline,
        "summary": "",
        "published_at": "2026-10-27T09:00:00-04:00",
        "publication_timezone_handling": "Source offset retained, normalized to UTC",
        "collected_at_utc": "2026-10-28T10:00:00Z",
        "dataset_version": "test-v1",
        "provenance_ref": "synthetic-fixture:test",
        "permission_review_id": "review-1",
        "usage_notes": "Synthetic unit test data; not real news.",
        "partition": "",
    }
    row.update(overrides)
    return row


def _annotation(
    article_id: str,
    role: str,
    label: str,
    *,
    uncertain: str = "no",
    rationale: str = "Independent synthetic test annotation.",
    annotator: str | None = None,
) -> dict[str, str]:
    return {
        "internal_article_id": article_id,
        "annotator_code": annotator or f"annotator-{role}",
        "annotator_role": role,
        "annotated_at_utc": "2026-10-28T11:00:00Z",
        "human_label": label,
        "uncertain": uncertain,
        "rationale": rationale,
        "annotation_guide_version": "guide-1",
    }


def _permission(**overrides: str) -> dict[str, str]:
    row = {
        "permission_review_id": "review-1",
        "provider_name": "Synthetic Source",
        "terms_url": "https://example.invalid/terms",
        "checked_at_utc": "2026-10-28T09:00:00Z",
        "account_plan_verified": "yes",
        "research_use": "allowed",
        "local_storage": "allowed",
        "display": "unclear",
        "redistribution": "unclear",
        "evaluation_reporting": "allowed",
        "attribution_requirement": "Synthetic test-only attribution.",
        "retention_requirement": "Delete temporary test dataset after run.",
        "written_approval_reference": "synthetic-test-only",
        "reviewer_notes": "Test fixture state; not a legal or real permission finding.",
    }
    row.update(overrides)
    return row


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _dataset_files(
    directory: Path,
    articles: list[dict[str, str]],
    annotations: list[dict[str, str]],
    permissions: list[dict[str, str]] | None = None,
    adjudications: list[dict[str, str]] | None = None,
) -> tuple[Path, Path, Path, Path]:
    article_path = _write(directory / "articles.csv", ARTICLE_FIELDS, articles)
    annotation_path = _write(
        directory / "annotations.csv", ANNOTATION_FIELDS, annotations
    )
    permission_path = _write(
        directory / "permissions.csv",
        PERMISSION_FIELDS,
        permissions or [_permission()],
    )
    adjudication_path = _write(
        directory / "adjudications.csv", ADJUDICATION_FIELDS, adjudications or []
    )
    return article_path, annotation_path, permission_path, adjudication_path


def test_provenance_fields_and_permission_review_are_separately_reported(
    tmp_path: Path,
) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [_article("a1", "A fictional company reports results.")],
        [_annotation("a1", "primary", "Neutral")],
        [_permission(account_plan_verified="no")],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.total_records_received == 1
    assert report.valid_provenance_records == 1
    assert report.permission_state_counts["unclear"] == 1
    assert report.permission_state_counts["review_cleared_for_local_evaluation"] == 0
    assert report.human_label_counts == {
        "Positive": 0,
        "Negative": 0,
        "Neutral": 1,
    }


def test_unknown_permission_review_reference_invalidates_provenance(
    tmp_path: Path,
) -> None:
    article = _article("a1", "A fictional headline.")
    article["permission_review_id"] = "missing-review"
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path, [article], [_annotation("a1", "primary", "Neutral")]
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.valid_provenance_records == 0
    assert report.excluded_record_count == 1
    assert any(
        "permission review ID is unknown" in issue.reason
        for issue in report.excluded_records
    )


def test_missing_article_provenance_and_bad_annotation_are_reported(
    tmp_path: Path,
) -> None:
    article = _article("bad", "A fictional headline.")
    article["collected_at_utc"] = ""
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [article],
        [_annotation("bad", "primary", "Bullish")],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.total_records_received == 1
    assert report.valid_provenance_records == 0
    assert report.invalid_or_missing_required_count == 1
    assert report.excluded_record_count == 1
    assert report.invalid_annotation_count == 1
    assert report.missing_primary_annotation_count == 0
    assert any("collected_at_utc" in issue.reason for issue in report.excluded_records)
    assert any("human_label" in issue.reason for issue in report.excluded_records)


def test_uncertain_annotations_do_not_force_a_label(tmp_path: Path) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [_article("a1", "A fictional headline.")],
        [
            _annotation(
                "a1",
                "primary",
                "Neutral",
                uncertain="yes",
                rationale="Needs context before assigning a class.",
            )
        ],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.invalid_annotation_count == 1
    assert report.missing_primary_annotation_count == 1
    assert any(
        "uncertain annotations must leave human_label blank" in issue.reason
        for issue in report.excluded_records
    )


def test_exact_and_near_duplicate_detection_and_cross_partition_leakage(
    tmp_path: Path,
) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [
            _article(
                "a1",
                "Fictional Acme reports strong quarterly revenue growth",
                partition="development",
            ),
            _article(
                "a2",
                "Fictional Acme reports strong quarterly revenue growth!",
                partition="heldout",
            ),
            _article(
                "a3",
                "Fictional Acme reports strong quarterly revenue growth today",
                partition="",
            ),
        ],
        [_annotation("a1", "primary", "Positive")],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.duplicate_count >= 1
    assert report.potential_duplicate_count >= 1
    assert report.partition_leakage_count == 2


def test_second_annotation_disagreement_rate_and_kappa(tmp_path: Path) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional Acme grows."),
            _article("a2", "Fictional Acme files."),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a1", "second", "Neutral"),
            _annotation("a2", "primary", "Neutral"),
            _annotation("a2", "second", "Neutral"),
        ],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.second_annotator_coverage_count == 2
    assert report.second_annotator_coverage_rate == 1.0
    assert report.paired_annotation_count == 2
    assert report.disagreement_count == 1
    assert report.disagreement_rate == 0.5
    assert report.cohen_kappa == pytest.approx(0.0)


def test_second_annotation_requires_distinct_annotator_codes(tmp_path: Path) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(
        tmp_path,
        [_article("a1", "Fictional Acme grows.")],
        [
            _annotation("a1", "primary", "Positive", annotator="person-1"),
            _annotation("a1", "second", "Positive", annotator="person-1"),
        ],
    )

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.invalid_annotation_count == 1
    assert report.second_annotator_coverage_count == 0
    assert any(
        "different annotator codes" in issue.reason for issue in report.excluded_records
    )


def test_empty_dataset_reports_safe_counts_and_undefined_agreement(
    tmp_path: Path,
) -> None:
    articles, annotations, permissions, adjudications = _dataset_files(tmp_path, [], [])

    report = validate_evaluation_dataset(
        articles, annotations, permissions, adjudications
    )

    assert report.total_records_received == 0
    assert report.valid_provenance_records == 0
    assert report.second_annotator_coverage_rate is None
    assert report.disagreement_rate is None
    assert report.cohen_kappa is None
    assert (
        report.permission_review_state_counts["review_cleared_for_local_evaluation"]
        == 1
    )


def test_deterministic_split_keeps_near_duplicates_together_and_evaluates(
    tmp_path: Path,
) -> None:
    rows = [
        _article("a1", "Fictional company reports excellent annual results"),
        _article("a2", "Fictional company reports excellent annual results!"),
        _article("a3", "Fictional company announces severe losses in quarter"),
        _article("a4", "Fictional company files report on Thursday"),
        _article("a5", "Fictional company wins customer award after growth"),
    ]
    annotations = [
        _annotation("a1", "primary", "Positive"),
        _annotation("a2", "primary", "Positive"),
        _annotation("a3", "primary", "Negative"),
        _annotation("a4", "primary", "Neutral"),
        _annotation("a5", "primary", "Positive"),
    ]
    files = _dataset_files(tmp_path, rows, annotations)
    development_a = tmp_path / "development-a.csv"
    heldout_a = tmp_path / "heldout-a.csv"
    development_b = tmp_path / "development-b.csv"
    heldout_b = tmp_path / "heldout-b.csv"

    first_counts = create_deterministic_split(
        *files[:3], development_a, heldout_a, seed=35
    )
    second_counts = create_deterministic_split(
        *files[:3], development_b, heldout_b, seed=35
    )

    assert first_counts == second_counts
    assert development_a.read_bytes() == development_b.read_bytes()
    assert heldout_a.read_bytes() == heldout_b.read_bytes()
    dev_examples, dev_excluded = load_labeled_examples(development_a)
    heldout_examples, heldout_excluded = load_labeled_examples(heldout_a)
    assert not dev_excluded and not heldout_excluded
    dev_ids = {example.article_id for example in dev_examples}
    heldout_ids = {example.article_id for example in heldout_examples}
    assert dev_ids.isdisjoint(heldout_ids)
    assert bool({"a1", "a2"} & dev_ids) == ("a1" in dev_ids and "a2" in dev_ids)
    assert bool({"a1", "a2"} & heldout_ids) == (
        "a1" in heldout_ids and "a2" in heldout_ids
    )
    heldout_report = evaluate_labeled_examples(heldout_examples)
    assert heldout_report.metrics.evaluated_count == len(heldout_examples)


def test_same_provider_article_id_is_grouped_across_split(tmp_path: Path) -> None:
    rows = [
        _article(
            "a1", "Fictional Acme reports strong growth", provider_article_id="88"
        ),
        _article(
            "a2",
            "A completely different fictional wording about markets",
            provider_article_id="88",
        ),
        _article("a3", "Fictional Acme files a report"),
    ]
    annotations = [
        _annotation("a1", "primary", "Positive"),
        _annotation("a2", "primary", "Positive"),
        _annotation("a3", "primary", "Neutral"),
    ]
    files = _dataset_files(tmp_path, rows, annotations)
    dev, heldout = tmp_path / "dev.csv", tmp_path / "heldout.csv"
    create_deterministic_split(*files[:3], dev, heldout, seed=3, heldout_fraction=0.5)

    with dev.open(encoding="utf-8", newline="") as stream:
        dev_ids = {row["article_id"] for row in csv.DictReader(stream)}
    with heldout.open(encoding="utf-8", newline="") as stream:
        heldout_ids = {row["article_id"] for row in csv.DictReader(stream)}

    assert ("a1" in dev_ids) == ("a2" in dev_ids)
    assert ("a1" in heldout_ids) == ("a2" in heldout_ids)


def test_split_refuses_single_duplicate_group_and_input_overwrite(
    tmp_path: Path,
) -> None:
    rows = [
        _article("a1", "Fictional Acme reports strong growth"),
        _article("a2", "Fictional Acme reports strong growth!"),
    ]
    annotations = [
        _annotation("a1", "primary", "Positive"),
        _annotation("a2", "primary", "Positive"),
    ]
    files = _dataset_files(tmp_path, rows, annotations)
    with pytest.raises(DatasetValidationError, match="one duplicate group"):
        create_deterministic_split(
            *files[:3],
            tmp_path / "dev.csv",
            tmp_path / "heldout.csv",
            seed=4,
        )
    with pytest.raises(ValueError, match="output paths"):
        create_deterministic_split(
            *files[:3],
            files[0],
            tmp_path / "heldout.csv",
            seed=4,
        )


def test_permission_unclear_blocks_split_and_never_claims_permission(
    tmp_path: Path,
) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional company grows."),
            _article("a2", "Fictional company files."),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a2", "primary", "Neutral"),
        ],
        [_permission(account_plan_verified="no")],
    )

    report = validate_evaluation_dataset(*files)

    assert report.permission_state_counts["unclear"] == 2
    assert report.excluded_record_count == 2
    assert sum(issue.file == "eligibility" for issue in report.excluded_records) == 2
    with pytest.raises(DatasetValidationError, match="at least two"):
        create_deterministic_split(
            *files[:3],
            tmp_path / "dev.csv",
            tmp_path / "heldout.csv",
            seed=1,
            adjudications_path=files[3],
        )


def test_disagreement_requires_adjudication_before_split(tmp_path: Path) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional company gains."),
            _article("a2", "Fictional company files."),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a1", "second", "Negative"),
            _annotation("a2", "primary", "Neutral"),
        ],
    )
    pending = validate_evaluation_dataset(*files)
    assert pending.disagreement_count == 1
    assert pending.excluded_record_count == 1
    assert any("unresolved" in issue.reason for issue in pending.excluded_records)
    dev, heldout = tmp_path / "dev.csv", tmp_path / "heldout.csv"
    with pytest.raises(DatasetValidationError, match="at least two"):
        create_deterministic_split(*files[:3], dev, heldout, seed=2)


def test_adjudication_is_separate_and_used_as_resolved_split_label(
    tmp_path: Path,
) -> None:
    adjudication = {
        "internal_article_id": "a1",
        "resolution_status": "resolved",
        "adjudicated_label": "Neutral",
        "adjudicated_at_utc": "2026-10-28T13:00:00Z",
        "adjudicator_code": "adjudicator-1",
        "rationale": "After discussion, the headline wording was judged factual.",
    }
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional Acme reports results"),
            _article("a2", "Fictional Acme announces an annual filing"),
            _article("a3", "Fictional Acme reports customer growth"),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a1", "second", "Negative"),
            _annotation("a2", "primary", "Neutral"),
            _annotation("a3", "primary", "Positive"),
        ],
        adjudications=[adjudication],
    )
    report = validate_evaluation_dataset(*files)
    assert report.invalid_adjudication_count == 0
    assert report.disagreement_count == 1
    assert report.human_label_counts["Positive"] == 2
    assert report.human_label_counts["Negative"] == 0
    assert report.human_label_counts["Neutral"] == 1

    development, heldout = tmp_path / "dev.csv", tmp_path / "heldout.csv"
    create_deterministic_split(
        *files[:3],
        development,
        heldout,
        seed=17,
        adjudications_path=files[3],
    )
    exported = []
    for path in (development, heldout):
        examples, excluded = load_labeled_examples(path)
        assert not excluded
        exported.extend(examples)
    assert (
        next(item for item in exported if item.article_id == "a1").human_label
        == "Neutral"
    )
    with files[1].open(encoding="utf-8", newline="") as stream:
        original_rows = list(csv.DictReader(stream))
    original_a1_labels = {
        row["human_label"]
        for row in original_rows
        if row["internal_article_id"] == "a1"
    }
    assert original_a1_labels == {"Positive", "Negative"}
