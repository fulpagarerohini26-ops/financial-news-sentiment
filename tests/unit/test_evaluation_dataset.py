from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

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
from financial_news_sentiment.evaluation_workflow import (
    _refuse_frozen_source_change,
    collect_finnhub_once,
    disagreement_report,
    export_annotator_sheet,
    freeze_split,
    import_annotator_sheet,
    import_permitted_csv,
    sha256_file,
    verify_frozen_heldout,
)

ARTICLE_FIELDS = [
    "internal_article_id",
    "ticker",
    "provider_name",
    "source_name",
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
    "source_identifier_storage",
    "source_url_storage",
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
        "source_name": "Synthetic Publisher",
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
        "source_identifier_storage": "allowed",
        "source_url_storage": "allowed",
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


def test_split_refuses_existing_outputs(tmp_path: Path) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional Acme reports strong revenue growth"),
            _article("a2", "Fictional Acme announces new manufacturing facility"),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a2", "primary", "Neutral"),
        ],
    )
    development, heldout = tmp_path / "development.csv", tmp_path / "heldout.csv"
    development.write_text("protected\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="refusing to overwrite"):
        create_deterministic_split(*files[:3], development, heldout, seed=3)
    assert development.read_text(encoding="utf-8") == "protected\n"


def test_collection_permission_gate_precedes_client_call(tmp_path: Path) -> None:
    permission_path = _write(
        tmp_path / "permissions.csv",
        PERMISSION_FIELDS,
        [_permission(provider_name="Finnhub", account_plan_verified="no")],
    )
    client = Mock()
    with pytest.raises(DatasetValidationError, match="no collection or import"):
        collect_finnhub_once(
            articles_path=tmp_path / "articles.csv",
            permissions_path=permission_path,
            permission_review_id="review-1",
            ticker="ACME",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
            dataset_version="real-v1",
            exclusions_path=tmp_path / "excluded.csv",
            client=client,
        )
    client.get_company_news.assert_not_called()
    assert not (tmp_path / "articles.csv").exists()


def test_collection_retention_flags_and_duplicate_exclusions(tmp_path: Path) -> None:
    from datetime import UTC, date, datetime

    from financial_news_sentiment.news.models import NewsArticle

    permission = _permission(
        provider_name="Finnhub",
        source_identifier_storage="allowed",
        source_url_storage="unclear",
    )
    permission_path = _write(
        tmp_path / "permissions.csv", PERMISSION_FIELDS, [permission]
    )
    client = Mock()
    one_article = NewsArticle(
        ticker="ACME",
        headline="Fictional issuer announces quarterly results",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
        published_timestamp=1790812800,
        provider_article_id=52,
        summary="Synthetic test summary",
        source="Example Publisher",
        article_url="https://example.invalid/story",
    )
    client.get_company_news.return_value = [one_article, one_article]
    articles_path = tmp_path / "articles.csv"
    exclusions = tmp_path / "excluded.csv"
    kwargs = {
        "articles_path": articles_path,
        "permissions_path": permission_path,
        "permission_review_id": "review-1",
        "ticker": "ACME",
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 2),
        "dataset_version": "real-v1",
        "client": client,
    }
    assert collect_finnhub_once(**kwargs, exclusions_path=exclusions) == (1, 1)
    client.get_company_news.assert_called_once()
    with articles_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["provider_article_id"] == "52"
    assert rows[0]["source_url"] == ""
    with exclusions.open(encoding="utf-8", newline="") as stream:
        excluded_rows = list(csv.DictReader(stream))
    assert "headline" not in excluded_rows[0]
    assert "duplicate" in excluded_rows[0]["reason"]


def test_offline_csv_import_is_permission_gated_and_preserves_summary(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "permitted.csv",
        [
            "ticker",
            "provider_article_id",
            "source",
            "article_url",
            "headline",
            "summary",
            "published_at",
        ],
        [
            {
                "ticker": "ACME",
                "provider_article_id": "31",
                "source": "Example Publisher",
                "article_url": "https://example.invalid/story",
                "headline": "Fictional Acme announces results",
                "summary": "Synthetic test summary",
                "published_at": "2026-10-01T10:00:00-04:00",
            }
        ],
    )
    permission_path = _write(
        tmp_path / "permissions.csv",
        PERMISSION_FIELDS,
        [
            _permission(
                provider_name="Permitted CSV Provider",
                source_identifier_storage="unclear",
                source_url_storage="unclear",
            )
        ],
    )
    articles_path, exclusions_path = (
        tmp_path / "articles.csv",
        tmp_path / "excluded.csv",
    )
    assert import_permitted_csv(
        source_path=source,
        articles_path=articles_path,
        permissions_path=permission_path,
        permission_review_id="review-1",
        provider_name="Permitted CSV Provider",
        dataset_version="real-v1",
        provenance_ref="permitted-csv:sample-1",
        exclusions_path=exclusions_path,
    ) == (1, 0)
    with articles_path.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["source_name"] == "Example Publisher"
    assert row["provider_article_id"] == ""
    assert row["source_url"] == ""
    assert row["summary"] == "Synthetic test summary"
    assert row["published_at"] == "2026-10-01T14:00:00+00:00"


def test_annotation_export_is_blinded_and_requires_display_permission(
    tmp_path: Path,
) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article(
                "a1", "Fictional issuer reports results", summary="Synthetic summary"
            ),
            _article("a2", "Fictional issuer files report"),
        ],
        [],
        [_permission(display="allowed")],
    )
    output = tmp_path / "annotator.csv"
    selection = _write(
        tmp_path / "second-subset.csv",
        ["internal_article_id"],
        [{"internal_article_id": "a1"}],
    )
    assert (
        export_annotator_sheet(
            articles_path=files[0],
            annotations_path=files[1],
            permissions_path=files[2],
            permission_review_id="review-1",
            output_path=output,
            guide_version="guide-1",
            role="primary",
            selection_path=selection,
        )
        == 1
    )
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
        headers = rows[0].keys()
    assert rows[0]["human_label"] == ""
    assert rows[0]["headline"] == "Fictional issuer reports results"
    assert "summary" not in headers
    assert not any("prediction" in header.casefold() for header in headers)
    with pytest.raises(DatasetValidationError, match="refusing to overwrite"):
        export_annotator_sheet(
            articles_path=files[0],
            annotations_path=files[1],
            permissions_path=files[2],
            permission_review_id="review-1",
            output_path=output,
            guide_version="guide-1",
            role="primary",
            selection_path=selection,
        )


def test_annotation_import_counts_missing_and_rejects_bad_labels(
    tmp_path: Path,
) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Fictional issuer reports results"),
            _article("a2", "Fictional issuer files report"),
        ],
        [],
    )
    sheet_fields = [
        "internal_article_id",
        "ticker",
        "provider_name",
        "headline",
        "published_at",
        "human_label",
        "uncertain",
        "rationale",
        "annotation_guide_version",
    ]
    sheet = _write(
        tmp_path / "completed.csv",
        sheet_fields,
        [
            {
                "internal_article_id": "a1",
                "ticker": "ACME",
                "provider_name": "Synthetic Source",
                "headline": "Fictional issuer reports results",
                "published_at": "2026-10-27T09:00:00-04:00",
                "human_label": "Neutral",
                "uncertain": "no",
                "rationale": "Factual wording.",
                "annotation_guide_version": "guide-1",
            },
            {
                "internal_article_id": "a2",
                "ticker": "ACME",
                "provider_name": "Synthetic Source",
                "headline": "Fictional issuer files report",
                "published_at": "2026-10-27T09:00:00-04:00",
                "human_label": "",
                "uncertain": "no",
                "rationale": "",
                "annotation_guide_version": "guide-1",
            },
        ],
    )
    assert import_annotator_sheet(
        sheet_path=sheet,
        articles_path=files[0],
        annotations_path=files[1],
        annotator_code="human-01",
        role="primary",
        guide_version="guide-1",
        annotated_at_utc="2026-10-28T12:00:00Z",
    ) == (1, 1)
    bad_sheet = _write(
        tmp_path / "bad.csv",
        sheet_fields,
        [
            {
                "internal_article_id": "a2",
                "ticker": "ACME",
                "provider_name": "Synthetic Source",
                "headline": "Fictional issuer files report",
                "published_at": "2026-10-27T09:00:00-04:00",
                "human_label": "Bullish",
                "uncertain": "no",
                "rationale": "",
                "annotation_guide_version": "guide-1",
            }
        ],
    )
    with pytest.raises(DatasetValidationError, match="invalid human label"):
        import_annotator_sheet(
            sheet_path=bad_sheet,
            articles_path=files[0],
            annotations_path=files[1],
            annotator_code="human-02",
            role="second",
            guide_version="guide-1",
        )
    duplicate_sheet = _write(
        tmp_path / "duplicate.csv",
        sheet_fields,
        [
            {
                "internal_article_id": "a2",
                "ticker": "ACME",
                "provider_name": "Synthetic Source",
                "headline": "Fictional issuer files report",
                "published_at": "2026-10-27T09:00:00-04:00",
                "human_label": "Neutral",
                "uncertain": "no",
                "rationale": "Factual wording.",
                "annotation_guide_version": "guide-1",
            }
        ]
        * 2,
    )
    with pytest.raises(DatasetValidationError, match="duplicate article ID"):
        import_annotator_sheet(
            sheet_path=duplicate_sheet,
            articles_path=files[0],
            annotations_path=tmp_path / "separate-annotations.csv",
            annotator_code="human-03",
            role="primary",
            guide_version="guide-1",
        )


def test_disagreement_report_uses_original_independent_labels(tmp_path: Path) -> None:
    files = _dataset_files(
        tmp_path,
        [_article("a1", "Fictional Acme reports results")],
        [
            _annotation("a1", "primary", "Positive", annotator="person-a"),
            _annotation("a1", "second", "Negative", annotator="person-b"),
        ],
    )
    report = disagreement_report(files[0], files[1])
    assert report["paired_annotation_count"] == 1
    assert report["disagreement_count"] == 1
    assert report["disagreement_rate"] == 1.0
    assert report["disagreements"][0]["primary_label"] == "Positive"


def test_freeze_requires_reviewed_complete_real_news_and_hashes_artifacts(
    tmp_path: Path,
) -> None:
    from financial_news_sentiment.evaluation_workflow import _evaluator_ids

    articles = [
        _article(
            "a1",
            "Fictional Acme reports strong annual revenue growth",
            provider_name="Finnhub",
            provenance_ref="finnhub:2026-10-01:2026-10-02",
            dataset_version="real-v1",
            usage_notes="Permission review confirms local evaluation use.",
        ),
        _article(
            "a2",
            "Fictional Acme announces facility expansion in Ohio",
            provider_name="Finnhub",
            provenance_ref="finnhub:2026-10-01:2026-10-02",
            dataset_version="real-v1",
            usage_notes="Permission review confirms local evaluation use.",
        ),
    ]
    annotations = [
        _annotation("a1", "primary", "Positive"),
        _annotation("a1", "second", "Positive", annotator="annotator-second"),
        _annotation("a2", "primary", "Neutral"),
    ]
    permission = _permission(
        provider_name="Finnhub",
        display="allowed",
        written_approval_reference="recorded-review-evidence",
        reviewer_notes="Synthetic test permission fixture only.",
    )
    files = _dataset_files(
        tmp_path,
        articles,
        annotations,
        [permission],
    )
    dev, heldout = tmp_path / "dev.csv", tmp_path / "heldout.csv"
    counts = create_deterministic_split(
        *files[:3], dev, heldout, seed=12, heldout_fraction=0.5
    )
    assert counts[0] and counts[1]
    split_manifest = tmp_path / "split.json"
    split_manifest.write_text(
        json.dumps(
            {
                "dataset_category": "manually_labeled_real_news",
                "development_article_ids": sorted(_evaluator_ids(dev)),
                "heldout_article_ids": sorted(_evaluator_ids(heldout)),
                "source_sha256": {
                    "articles": sha256_file(files[0]),
                    "annotations": sha256_file(files[1]),
                    "permissions": sha256_file(files[2]),
                },
                "development_sha256": sha256_file(dev),
                "heldout_sha256": sha256_file(heldout),
            }
        ),
        encoding="utf-8",
    )
    freeze_path = tmp_path / "freeze.json"
    freeze_split(
        articles_path=files[0],
        annotations_path=files[1],
        permissions_path=files[2],
        development_path=dev,
        heldout_path=heldout,
        split_manifest_path=split_manifest,
        freeze_manifest_path=freeze_path,
    )
    manifest = verify_frozen_heldout(heldout, freeze_path)
    assert manifest["freeze_status"] == "FROZEN"
    with pytest.raises(DatasetValidationError, match="belongs to frozen dataset"):
        _refuse_frozen_source_change(files[0], "articles")
    heldout.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="hash differs"):
        verify_frozen_heldout(heldout, freeze_path)


def test_synthetic_fixture_cannot_be_frozen(tmp_path: Path) -> None:
    files = _dataset_files(
        tmp_path,
        [
            _article("a1", "Synthetic first example"),
            _article("a2", "Synthetic second example"),
        ],
        [
            _annotation("a1", "primary", "Positive"),
            _annotation("a2", "primary", "Neutral"),
        ],
    )
    with pytest.raises(DatasetValidationError, match="synthetic or test-only"):
        freeze_split(
            articles_path=files[0],
            annotations_path=files[1],
            permissions_path=files[2],
            development_path=tmp_path / "development.csv",
            heldout_path=tmp_path / "heldout.csv",
            split_manifest_path=tmp_path / "split.json",
            freeze_manifest_path=tmp_path / "freeze.json",
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
