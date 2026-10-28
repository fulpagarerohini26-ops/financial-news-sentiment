"""Permission-gated collection and human annotation workflow helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from financial_news_sentiment.evaluation import HUMAN_LABELS
from financial_news_sentiment.evaluation_dataset import (
    _ADJUDICATION_FIELDS,
    _ANNOTATION_FIELDS,
    _ARTICLE_FIELDS,
    _PERMISSION_FIELDS,
    DatasetValidationError,
    _Article,
    _eligible_evaluation_rows,
    _find_duplicate_pairs,
    _is_utc_timestamp,
    _permission_state,
    _PermissionReview,
    _read_csv,
    _write_csv,
    validate_evaluation_dataset,
)
from financial_news_sentiment.news.csv_adapter import load_news_csv
from financial_news_sentiment.news.finnhub import FinnhubNewsClient
from financial_news_sentiment.news.models import NewsArticle

ANNOTATOR_SHEET_FIELDS = (
    "internal_article_id",
    "ticker",
    "provider_name",
    "headline",
    "published_at",
    "human_label",
    "uncertain",
    "rationale",
    "annotation_guide_version",
)
_EXCLUSION_FIELDS = ("internal_article_id", "reason")
_DISAGREEMENT_FIELDS = (
    "internal_article_id",
    "primary_annotator_code",
    "primary_label",
    "second_annotator_code",
    "second_label",
)


def collect_finnhub_once(
    *,
    articles_path: str | Path,
    permissions_path: str | Path,
    permission_review_id: str,
    ticker: str,
    start_date: date,
    end_date: date,
    dataset_version: str,
    exclusions_path: str | Path,
    client: FinnhubNewsClient | None = None,
) -> tuple[int, int]:
    """Make one Finnhub request after the linked review clears storage and use."""
    permission = _require_permission(permissions_path, permission_review_id, "Finnhub")
    return _save_source_articles(
        articles_path=articles_path,
        exclusions_path=exclusions_path,
        permission=permission,
        provider_name="Finnhub",
        dataset_version=dataset_version,
        provenance_ref=f"finnhub-company-news:{start_date}:{end_date}",
        articles=(client or FinnhubNewsClient()).get_company_news(
            ticker, start_date, end_date
        ),
    )


def import_permitted_csv(
    *,
    source_path: str | Path,
    articles_path: str | Path,
    permissions_path: str | Path,
    permission_review_id: str,
    provider_name: str,
    dataset_version: str,
    provenance_ref: str,
    exclusions_path: str | Path,
) -> tuple[int, int]:
    """Import an independently obtained CSV after permission is verified."""
    permission = _require_permission(
        permissions_path, permission_review_id, provider_name
    )
    return _save_source_articles(
        articles_path=articles_path,
        exclusions_path=exclusions_path,
        permission=permission,
        provider_name=provider_name,
        dataset_version=dataset_version,
        provenance_ref=provenance_ref,
        articles=load_news_csv(source_path),
    )


def export_annotator_sheet(
    *,
    articles_path: str | Path,
    permissions_path: str | Path,
    annotations_path: str | Path,
    permission_review_id: str,
    output_path: str | Path,
    guide_version: str,
    role: str,
    selection_path: str | Path | None = None,
) -> int:
    """Create a blinded annotation sheet with no model predictions or labels."""
    if role not in ("primary", "second"):
        raise ValueError("role must be primary or second")
    permission = _require_permission(
        permissions_path, permission_review_id, provider_name=None
    )
    if permission.values["display"].strip().lower() != "allowed":
        raise DatasetValidationError(
            "annotation export requires permission review display=allowed"
        )
    output = Path(output_path)
    if output.exists():
        raise DatasetValidationError(
            f"{output}: refusing to overwrite an existing file"
        )
    validation = validate_evaluation_dataset(
        articles_path, annotations_path, permissions_path
    )
    if (
        validation.invalid_or_missing_required_count
        or validation.invalid_annotation_count
        or validation.invalid_permission_review_count
    ):
        raise DatasetValidationError(
            "annotation export requires valid article provenance and permission rows"
        )

    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    annotation_rows = _read_csv(annotations_path, _ANNOTATION_FIELDS)
    existing_ids = {
        row["internal_article_id"].strip()
        for _, row in annotation_rows
        if row.get("_row_error") is None and row["annotator_role"].strip() == role
    }
    selected_ids: set[str] | None = None
    if selection_path is not None:
        selection_rows = _read_csv(selection_path, ("internal_article_id",))
        selected_list = [
            row["internal_article_id"].strip()
            for _, row in selection_rows
            if "_row_error" not in row
        ]
        if any(not article_id for article_id in selected_list):
            raise DatasetValidationError("selection file contains a blank article ID")
        if len(selected_list) != len(set(selected_list)):
            raise DatasetValidationError(
                "selection file contains duplicate article IDs"
            )
        selected_ids = set(selected_list)
        known_ids = {row["internal_article_id"].strip() for _, row in article_rows}
        unknown_ids = selected_ids - known_ids
        if unknown_ids:
            raise DatasetValidationError(
                "selection file references unknown article IDs: "
                + ", ".join(sorted(unknown_ids))
            )
    export_rows: list[dict[str, str]] = []
    for row_number, values in article_rows:
        article_id = values["internal_article_id"].strip()
        if "_row_error" in values:
            raise DatasetValidationError(
                f"{articles_path}: invalid article row {row_number}"
            )
        if (
            values["permission_review_id"].strip()
            != permission.values["permission_review_id"]
        ):
            raise DatasetValidationError(
                f"{article_id}: article is not linked to the requested permission review"
            )
        if article_id in existing_ids:
            continue
        if selected_ids is not None and article_id not in selected_ids:
            continue
        export_rows.append(
            {
                "internal_article_id": article_id,
                "ticker": values["ticker"],
                "provider_name": values["provider_name"],
                "headline": values["headline"],
                "published_at": values["published_at"],
                "human_label": "",
                "uncertain": "",
                "rationale": "",
                "annotation_guide_version": guide_version,
            }
        )
    _write_csv(output, ANNOTATOR_SHEET_FIELDS, export_rows)
    return len(export_rows)


def import_annotator_sheet(
    *,
    sheet_path: str | Path,
    articles_path: str | Path,
    annotations_path: str | Path,
    annotator_code: str,
    role: str,
    guide_version: str,
    annotated_at_utc: str | None = None,
) -> tuple[int, int]:
    """Validate and append one annotator's independent labels."""
    if role not in ("primary", "second"):
        raise ValueError("role must be primary or second")
    if not annotator_code.strip():
        raise ValueError("annotator_code must not be blank")
    annotated_at = annotated_at_utc or datetime.now(UTC).isoformat()
    if not _is_utc_timestamp(annotated_at):
        raise ValueError("annotated_at_utc must be an ISO 8601 UTC timestamp")

    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    articles_by_id = {
        row["internal_article_id"].strip(): row
        for _, row in article_rows
        if "_row_error" not in row
    }
    known_ids = set(articles_by_id)
    sheet_rows = _read_csv(sheet_path, ANNOTATOR_SHEET_FIELDS)
    existing_rows = (
        list(_read_csv(annotations_path, _ANNOTATION_FIELDS))
        if Path(annotations_path).exists()
        else []
    )
    existing_keys: set[tuple[str, str]] = set()
    existing_codes: dict[str, str] = {}
    for _, row in existing_rows:
        if "_row_error" in row:
            raise DatasetValidationError(
                f"{annotations_path}: fix malformed existing annotation rows first"
            )
        key = (row["internal_article_id"].strip(), row["annotator_role"].strip())
        if key in existing_keys:
            raise DatasetValidationError(
                f"{annotations_path}: duplicate existing article/role annotation"
            )
        existing_keys.add(key)
        existing_codes[key[0]] = row["annotator_code"].strip()

    imported: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    missing_count = 0
    errors: list[str] = []
    for row_number, row in sheet_rows:
        if "_row_error" in row:
            errors.append(f"row {row_number}: {row['_row_error']}")
            continue
        article_id = row["internal_article_id"].strip()
        label = row["human_label"].strip()
        uncertain = row["uncertain"].strip().lower()
        if row["annotation_guide_version"].strip() != guide_version:
            errors.append(f"row {row_number}: annotation guide version mismatch")
        if not article_id or article_id not in known_ids:
            errors.append(f"row {row_number}: unknown or blank article ID")
        elif any(
            row[field].strip() != articles_by_id[article_id][article_field].strip()
            for field, article_field in (
                ("ticker", "ticker"),
                ("provider_name", "provider_name"),
                ("headline", "headline"),
                ("published_at", "published_at"),
            )
        ):
            errors.append(
                f"row {row_number}: annotator sheet content does not match article"
            )
        if article_id in seen_ids:
            errors.append(f"row {row_number}: duplicate article ID")
        seen_ids.add(article_id)
        if (article_id, role) in existing_keys:
            errors.append(f"row {row_number}: annotation for this role already exists")
        if existing_codes.get(article_id) == annotator_code:
            errors.append(
                f"row {row_number}: primary and second annotators must differ"
            )
        if uncertain not in ("", "yes", "no"):
            errors.append(f"row {row_number}: uncertain must be yes or no")
        if uncertain == "yes":
            if label:
                errors.append(f"row {row_number}: uncertain labels must be blank")
            if not row["rationale"].strip():
                errors.append(f"row {row_number}: uncertainty requires a rationale")
        elif not label:
            missing_count += 1
            continue
        elif label not in HUMAN_LABELS:
            errors.append(f"row {row_number}: invalid human label")
        if errors and errors[-1].startswith(f"row {row_number}:"):
            continue
        imported.append(
            {
                "internal_article_id": article_id,
                "annotator_code": annotator_code,
                "annotator_role": role,
                "annotated_at_utc": annotated_at,
                "human_label": label,
                "uncertain": "yes" if uncertain == "yes" else "no",
                "rationale": row["rationale"].strip(),
                "annotation_guide_version": guide_version,
            }
        )
    if errors:
        raise DatasetValidationError("annotation import failed: " + "; ".join(errors))

    target = Path(annotations_path)
    _refuse_frozen_source_change(target, "annotations")
    target.parent.mkdir(parents=True, exist_ok=True)
    all_rows = [row for _, row in existing_rows] + imported
    _atomic_write_csv(target, _ANNOTATION_FIELDS, all_rows)
    return len(imported), missing_count


def disagreement_report(
    articles_path: str | Path, annotations_path: str | Path
) -> dict[str, Any]:
    """Report independent primary/second labels before adjudication."""
    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    annotations = _read_csv(annotations_path, _ANNOTATION_FIELDS)
    article_ids = {
        row["internal_article_id"].strip()
        for _, row in article_rows
        if "_row_error" not in row
    }
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row_number, row in annotations:
        if "_row_error" in row:
            raise DatasetValidationError(
                f"{annotations_path}: invalid annotation row {row_number}"
            )
        article_id = row["internal_article_id"].strip()
        if article_id not in article_ids:
            raise DatasetValidationError(
                f"{annotations_path}: annotation references unknown article {article_id}"
            )
        role = row["annotator_role"].strip()
        if role not in ("primary", "second") or role in grouped[article_id]:
            raise DatasetValidationError(
                f"{annotations_path}: invalid or duplicate annotation role for {article_id}"
            )
        grouped[article_id][role] = row
        label = row["human_label"].strip()
        uncertain = row["uncertain"].strip().lower()
        if label and label not in HUMAN_LABELS:
            raise DatasetValidationError(
                f"{annotations_path}: invalid label in row {row_number}"
            )
        if uncertain not in ("", "yes", "no"):
            raise DatasetValidationError(
                f"{annotations_path}: invalid uncertainty flag in row {row_number}"
            )

    primary_complete = 0
    second_coverage = 0
    paired = 0
    disagreements: list[dict[str, str]] = []
    for article_id in sorted(article_ids):
        roles = grouped.get(article_id, {})
        primary = roles.get("primary")
        second = roles.get("second")
        if primary and primary["human_label"].strip() in HUMAN_LABELS:
            primary_complete += 1
        if second is not None:
            second_coverage += 1
        if (
            primary is None
            or second is None
            or primary["uncertain"].strip().lower() == "yes"
            or second["uncertain"].strip().lower() == "yes"
            or primary["human_label"].strip() not in HUMAN_LABELS
            or second["human_label"].strip() not in HUMAN_LABELS
        ):
            continue
        if primary["annotator_code"].strip() == second["annotator_code"].strip():
            raise DatasetValidationError(
                f"article {article_id}: annotators must have distinct codes"
            )
        paired += 1
        if primary["human_label"].strip() != second["human_label"].strip():
            disagreements.append(
                {
                    "internal_article_id": article_id,
                    "primary_annotator_code": primary["annotator_code"].strip(),
                    "primary_label": primary["human_label"].strip(),
                    "second_annotator_code": second["annotator_code"].strip(),
                    "second_label": second["human_label"].strip(),
                }
            )
    return {
        "article_count": len(article_ids),
        "primary_annotation_count": primary_complete,
        "missing_primary_count": len(article_ids) - primary_complete,
        "second_annotator_coverage_count": second_coverage,
        "second_annotator_coverage_rate": (
            second_coverage / len(article_ids) if article_ids else None
        ),
        "paired_annotation_count": paired,
        "disagreement_count": len(disagreements),
        "disagreement_rate": len(disagreements) / paired if paired else None,
        "disagreements": disagreements,
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_split(
    *,
    articles_path: str | Path,
    annotations_path: str | Path,
    permissions_path: str | Path,
    development_path: str | Path,
    heldout_path: str | Path,
    split_manifest_path: str | Path,
    freeze_manifest_path: str | Path,
    adjudications_path: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze a fully validated, independently annotated real-news split."""
    freeze_path = Path(freeze_manifest_path)
    dataset_directory = freeze_path.parent.resolve()
    required_same_directory = (
        articles_path,
        annotations_path,
        permissions_path,
        development_path,
        heldout_path,
        split_manifest_path,
    )
    if any(
        Path(path).parent.resolve() != dataset_directory
        for path in required_same_directory
    ):
        raise DatasetValidationError(
            "source files, split outputs, and freeze manifest must share a versioned directory"
        )
    if (
        adjudications_path is not None
        and Path(adjudications_path).parent.resolve() != dataset_directory
    ):
        raise DatasetValidationError(
            "adjudications and freeze manifest must share a versioned directory"
        )
    frozen_inputs = {
        Path(path).resolve()
        for path in (
            articles_path,
            annotations_path,
            permissions_path,
            development_path,
            heldout_path,
            split_manifest_path,
            adjudications_path,
        )
        if path is not None
    }
    if freeze_path.resolve() in frozen_inputs:
        raise DatasetValidationError("freeze manifest must be a separate output file")
    if freeze_path.exists():
        raise DatasetValidationError(f"{freeze_path}: refusing to overwrite a freeze")
    source_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    if any(
        any(
            marker
            in f"{row['provider_name']} {row['provenance_ref']} {row['dataset_version']}".casefold()
            for marker in ("synthetic", "fixture", "test-only")
        )
        for _, row in source_rows
    ):
        raise DatasetValidationError(
            "synthetic or test-only source records cannot be frozen as real news"
        )
    split_report = validate_split_artifacts(
        articles_path=articles_path,
        annotations_path=annotations_path,
        permissions_path=permissions_path,
        development_path=development_path,
        heldout_path=heldout_path,
        split_manifest_path=split_manifest_path,
        adjudications_path=adjudications_path,
    )
    report = validate_evaluation_dataset(
        articles_path, annotations_path, permissions_path, adjudications_path
    )
    if report.valid_provenance_records < 2:
        raise DatasetValidationError("at least two real-news articles are required")
    if (
        report.excluded_record_count
        or report.invalid_or_missing_required_count
        or report.invalid_annotation_count
        or report.invalid_permission_review_count
        or report.invalid_adjudication_count
    ):
        raise DatasetValidationError(
            "cannot freeze while any article is excluded or annotation is incomplete"
        )
    if report.second_annotator_coverage_count < 1:
        raise DatasetValidationError(
            "cannot freeze until an independent second annotator has labeled a subset"
        )
    dev_ids = _evaluator_ids(development_path)
    heldout_ids = _evaluator_ids(heldout_path)
    source_files = split_report["source_files"]

    articles = [
        _Article(
            row_number,
            row
            | {
                "partition": (
                    "development"
                    if row["internal_article_id"].strip() in dev_ids
                    else "heldout"
                )
            },
            row["internal_article_id"].strip(),
        )
        for row_number, row in source_rows
    ]
    if any(pair.cross_partition for pair in _find_duplicate_pairs(articles)):
        raise DatasetValidationError(
            "duplicate or near-duplicate articles cross partitions"
        )
    dataset_versions = sorted(
        {
            row["dataset_version"].strip()
            for _, row in source_rows
            if row["dataset_version"].strip()
        }
    )
    manifest = {
        "dataset_category": "manually_labeled_real_news",
        "freeze_status": "FROZEN",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "dataset_versions": dataset_versions,
        "source_files": {key: Path(path).name for key, path in source_files.items()},
        "source_sha256": {key: sha256_file(path) for key, path in source_files.items()},
        "split_manifest_sha256": sha256_file(split_manifest_path),
        "development_sha256": sha256_file(development_path),
        "heldout_sha256": sha256_file(heldout_path),
        "development_count": len(dev_ids),
        "heldout_count": len(heldout_ids),
        "second_annotator_coverage_count": report.second_annotator_coverage_count,
        "disagreement_count": report.disagreement_count,
        "heldout_policy": "final evaluation only; not for tuning or model selection",
    }
    _atomic_write_text(
        freeze_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def validate_split_artifacts(
    *,
    articles_path: str | Path,
    annotations_path: str | Path,
    permissions_path: str | Path,
    development_path: str | Path,
    heldout_path: str | Path,
    split_manifest_path: str | Path,
    adjudications_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate split hashes, eligible labels, partition membership, and leakage."""
    report = validate_evaluation_dataset(
        articles_path, annotations_path, permissions_path, adjudications_path
    )
    if (
        report.invalid_or_missing_required_count
        or report.invalid_annotation_count
        or report.invalid_permission_review_count
        or report.invalid_adjudication_count
    ):
        raise DatasetValidationError(
            "cannot validate split while dataset contains malformed records"
        )
    try:
        with Path(split_manifest_path).open(encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetValidationError(
            f"unable to read split manifest: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise DatasetValidationError("split manifest must contain a JSON object")
    if manifest.get("dataset_category") != "manually_labeled_real_news":
        raise DatasetValidationError("split manifest is not marked as real-news")

    source_files: dict[str, str | Path] = {
        "articles": articles_path,
        "annotations": annotations_path,
        "permissions": permissions_path,
    }
    if adjudications_path is not None:
        source_files["adjudications"] = adjudications_path
    source_hashes = manifest.get("source_sha256")
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(source_files):
        raise DatasetValidationError(
            "split manifest source list differs from the supplied source files"
        )
    for key, path in source_files.items():
        if source_hashes.get(key) != sha256_file(path):
            raise DatasetValidationError(
                f"{key} source changed after split generation; create a new split"
            )
    output_paths = {
        "development": development_path,
        "heldout": heldout_path,
    }
    actual_rows = {
        partition: _read_evaluator_rows(path)
        for partition, path in output_paths.items()
    }
    for partition, path in output_paths.items():
        if manifest.get(f"{partition}_sha256") != sha256_file(path):
            raise DatasetValidationError(
                f"{partition} file hash differs from split manifest"
            )
    dev_ids = {row["article_id"] for row in actual_rows["development"]}
    heldout_ids = {row["article_id"] for row in actual_rows["heldout"]}
    if not dev_ids or not heldout_ids or dev_ids & heldout_ids:
        raise DatasetValidationError(
            "development and held-out files must both be non-empty and disjoint"
        )
    manifest_dev_ids = manifest.get("development_article_ids")
    manifest_heldout_ids = manifest.get("heldout_article_ids")
    if not isinstance(manifest_dev_ids, list) or not all(
        isinstance(article_id, str) for article_id in manifest_dev_ids
    ):
        raise DatasetValidationError("development article IDs are invalid in manifest")
    if not isinstance(manifest_heldout_ids, list) or not all(
        isinstance(article_id, str) for article_id in manifest_heldout_ids
    ):
        raise DatasetValidationError("held-out article IDs are invalid in manifest")
    if dev_ids != set(manifest_dev_ids):
        raise DatasetValidationError("development IDs differ from split manifest")
    if heldout_ids != set(manifest_heldout_ids):
        raise DatasetValidationError("held-out IDs differ from split manifest")

    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    annotation_rows = _read_csv(annotations_path, _ANNOTATION_FIELDS)
    permission_rows = _read_csv(permissions_path, _PERMISSION_FIELDS)
    adjudication_rows = (
        _read_csv(adjudications_path, _ADJUDICATION_FIELDS)
        if adjudications_path is not None
        else ()
    )
    eligible = _eligible_evaluation_rows(
        article_rows, annotation_rows, permission_rows, adjudication_rows
    )
    expected = {row["article_id"]: row for row in eligible}
    actual = {row["article_id"]: row for rows in actual_rows.values() for row in rows}
    if actual.keys() != expected.keys():
        raise DatasetValidationError(
            "split article IDs do not match permission-cleared, resolved annotations"
        )
    for article_id, expected_row in expected.items():
        actual_row = actual[article_id]
        for field in ("ticker", "headline", "human_label", "source", "published_at"):
            if actual_row[field] != expected_row[field]:
                raise DatasetValidationError(
                    f"{article_id}: split {field} differs from source or annotation"
                )
    articles = [
        _Article(
            row_number,
            row
            | {
                "partition": (
                    "development"
                    if row["internal_article_id"].strip() in dev_ids
                    else "heldout"
                )
            },
            row["internal_article_id"].strip(),
        )
        for row_number, row in article_rows
        if row["internal_article_id"].strip() in expected
    ]
    if any(pair.cross_partition for pair in _find_duplicate_pairs(articles)):
        raise DatasetValidationError(
            "duplicate or near-duplicate articles cross partitions"
        )

    distributions = {
        partition: _label_distribution(rows) for partition, rows in actual_rows.items()
    }
    for partition, rows in actual_rows.items():
        if len(rows) != manifest.get(f"{partition}_size"):
            raise DatasetValidationError(
                f"{partition} count differs from split manifest"
            )
        manifest_counts = manifest.get(f"{partition}_class_counts")
        if (
            not isinstance(manifest_counts, dict)
            or {label: manifest_counts.get(label, 0) for label in HUMAN_LABELS}
            != distributions[partition]
        ):
            raise DatasetValidationError(
                f"{partition} class counts differ from split manifest"
            )
    return {
        "dataset_category": manifest["dataset_category"],
        "development_count": len(dev_ids),
        "heldout_count": len(heldout_ids),
        "development_class_counts": distributions["development"],
        "heldout_class_counts": distributions["heldout"],
        "partition_leakage_count": 0,
        "source_sha256": manifest["source_sha256"],
        "development_sha256": manifest["development_sha256"],
        "heldout_sha256": manifest["heldout_sha256"],
        "manifest": manifest,
        "source_files": source_files,
    }


def verify_frozen_heldout(
    heldout_path: str | Path, freeze_manifest_path: str | Path
) -> dict[str, Any]:
    """Verify that the evaluated held-out file is the frozen artifact."""
    try:
        with Path(freeze_manifest_path).open(encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetValidationError(
            f"unable to read freeze manifest: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise DatasetValidationError("freeze manifest must contain a JSON object")
    if manifest.get("freeze_status") != "FROZEN":
        raise DatasetValidationError("freeze manifest is not marked FROZEN")
    if manifest.get("dataset_category") != "manually_labeled_real_news":
        raise DatasetValidationError("freeze manifest is not marked as real-news")
    if manifest.get("heldout_count", 0) < 1:
        raise DatasetValidationError("frozen held-out set is empty")
    if manifest.get("heldout_sha256") != sha256_file(heldout_path):
        raise DatasetValidationError(
            "held-out file hash differs from frozen manifest; do not evaluate it"
        )
    return manifest


def _require_permission(
    permissions_path: str | Path,
    review_id: str,
    provider_name: str | None,
) -> _PermissionReview:
    rows = _read_csv(permissions_path, _PERMISSION_FIELDS)
    matches = [
        row
        for _, row in rows
        if "_row_error" not in row
        and row["permission_review_id"].strip() == review_id.strip()
    ]
    if len(matches) != 1:
        raise DatasetValidationError("permission review ID is missing or not unique")
    row = matches[0]
    if (
        provider_name is not None
        and row["provider_name"].strip().casefold() != provider_name.strip().casefold()
    ):
        raise DatasetValidationError("permission review provider does not match source")
    review = _PermissionReview(row, _permission_state(row))
    if review.state != "review_cleared_for_local_evaluation":
        raise DatasetValidationError(
            f"permission review is {review.state}; no collection or import performed"
        )
    return review


def _save_source_articles(
    *,
    articles_path: str | Path,
    exclusions_path: str | Path,
    permission: _PermissionReview,
    provider_name: str,
    dataset_version: str,
    provenance_ref: str,
    articles: list[NewsArticle],
) -> tuple[int, int]:
    if not dataset_version.strip() or not provenance_ref.strip():
        raise ValueError("dataset_version and provenance_ref must not be blank")
    target = Path(articles_path)
    exclusions = Path(exclusions_path)
    if target.name.endswith("_template.csv"):
        raise DatasetValidationError(
            "refusing to write collection data into a template"
        )
    if target.resolve() == exclusions.resolve():
        raise ValueError("article and exclusion output paths must be different")
    if exclusions.exists():
        raise DatasetValidationError(
            f"{exclusions}: refusing to overwrite an existing exclusions report"
        )
    _refuse_frozen_source_change(target, "articles")
    existing_rows = list(_read_csv(target, _ARTICLE_FIELDS)) if target.exists() else []
    if any("_row_error" in row for _, row in existing_rows):
        raise DatasetValidationError("fix malformed article rows before importing")
    review_id = permission.values["permission_review_id"].strip()
    existing_provider_ids = {
        row["provider_article_id"].strip()
        for _, row in existing_rows
        if row["provider_name"].strip().casefold() == provider_name.casefold()
        and row["provider_article_id"].strip()
    }
    existing_urls = {
        row["source_url"].strip().rstrip("/")
        for _, row in existing_rows
        if row["source_url"].strip()
    }
    existing_headlines = {
        (
            row["provider_name"].strip().casefold(),
            row["ticker"].strip().upper(),
            _normalize_headline(row["headline"]),
        )
        for _, row in existing_rows
    }
    now = datetime.now(UTC).isoformat()
    inserted: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    retain_provider_id = (
        permission.values["source_identifier_storage"].strip().lower() == "allowed"
    )
    retain_url = permission.values["source_url_storage"].strip().lower() == "allowed"
    for article in articles:
        provider_id = (
            str(article.provider_article_id)
            if retain_provider_id and article.provider_article_id is not None
            else ""
        )
        source_url = article.article_url or ""
        stored_url = source_url if retain_url else ""
        identity = "|".join(
            (
                provider_name.casefold(),
                article.ticker,
                provider_id or source_url or article.published_at.isoformat(),
                _normalize_headline(article.headline),
            )
        )
        internal_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        headline_key = (
            provider_name.casefold(),
            article.ticker.upper(),
            _normalize_headline(article.headline),
        )
        is_duplicate = (
            (provider_id and provider_id in existing_provider_ids)
            or (source_url and source_url.rstrip("/") in existing_urls)
            or headline_key in existing_headlines
            or internal_id in seen_ids
        )
        if is_duplicate:
            excluded.append(
                {
                    "internal_article_id": internal_id,
                    "reason": "duplicate provider ID, URL, or normalized headline",
                }
            )
            continue
        seen_ids.add(internal_id)
        existing_headlines.add(headline_key)
        if provider_id:
            existing_provider_ids.add(provider_id)
        if source_url:
            existing_urls.add(source_url.rstrip("/"))
        inserted.append(
            {
                "internal_article_id": internal_id,
                "ticker": article.ticker,
                "provider_name": provider_name,
                "source_name": article.source or "",
                "provider_article_id": provider_id,
                "source_url": stored_url,
                "headline": article.headline,
                "summary": article.summary or "",
                "published_at": article.published_at.isoformat(),
                "publication_timezone_handling": (
                    "Timestamp normalized to UTC by the existing source adapter; original offset is not preserved"
                ),
                "collected_at_utc": now,
                "dataset_version": dataset_version,
                "provenance_ref": provenance_ref,
                "permission_review_id": review_id,
                "usage_notes": permission.values["reviewer_notes"].strip(),
                "partition": "",
            }
        )

    all_rows = [row for _, row in existing_rows] + inserted
    _atomic_write_csv(target, _ARTICLE_FIELDS, all_rows)
    _write_csv(exclusions, _EXCLUSION_FIELDS, excluded)
    return len(inserted), len(excluded)


def _evaluator_ids(path: str | Path) -> set[str]:
    return {row["article_id"] for row in _read_evaluator_rows(path)}


def _read_evaluator_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required_fields = {
            "article_id",
            "ticker",
            "headline",
            "human_label",
            "source",
            "published_at",
        }
        if not reader.fieldnames or not required_fields <= set(reader.fieldnames):
            raise DatasetValidationError(
                f"{path}: missing required split fields: "
                + ", ".join(sorted(required_fields - set(reader.fieldnames or ())))
            )
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(field) is None for field in required_fields):
                raise DatasetValidationError(
                    f"{path}:{row_number}: malformed split CSV row"
                )
            rows.append(
                {
                    key: value
                    for key, value in row.items()
                    if key is not None and value is not None
                }
            )
    ids = [row.get("article_id", "").strip() for row in rows]
    if any(
        not row["article_id"].strip()
        or not row["ticker"].strip()
        or not row["headline"].strip()
        or not row["human_label"].strip()
        for row in rows
    ):
        raise DatasetValidationError(f"{path}: split contains a blank required value")
    if any(not article_id for article_id in ids) or len(ids) != len(set(ids)):
        raise DatasetValidationError(f"{path}: blank or duplicate article IDs")
    for row in rows:
        row["article_id"] = row["article_id"].strip()
    return rows


def _label_distribution(rows: list[dict[str, str]]) -> dict[str, int]:
    distribution = {label: 0 for label in HUMAN_LABELS}
    for row in rows:
        label = row["human_label"]
        if label not in distribution:
            raise DatasetValidationError(f"invalid split label: {label}")
        distribution[label] += 1
    return distribution


def _refuse_frozen_source_change(path: Path, source_key: str) -> None:
    if not path.exists():
        return
    for freeze_path in path.parent.glob("freeze*.json"):
        try:
            with freeze_path.open(encoding="utf-8") as stream:
                manifest = json.load(stream)
        except json.JSONDecodeError as error:
            raise DatasetValidationError(
                f"{freeze_path}: cannot safely modify source while freeze manifest is invalid"
            ) from error
        if not isinstance(manifest, dict):
            raise DatasetValidationError(
                f"{freeze_path}: cannot safely modify source while freeze manifest is invalid"
            )
        if manifest.get("source_files", {}).get(source_key) == path.name:
            raise DatasetValidationError(
                f"{path} belongs to frozen dataset {freeze_path.name}; "
                "write a new dataset/split version instead"
            )


def _normalize_headline(value: str) -> str:
    return " ".join(
        "".join(
            character.lower() if character.isalnum() else " " for character in value
        ).split()
    )


def _atomic_write_csv(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(
                {field: row.get(field, "") for field in fields} for row in rows
            )
        os.replace(temporary_name, path)
    except OSError:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary_name, path)
    except OSError:
        Path(temporary_name).unlink(missing_ok=True)
        raise
