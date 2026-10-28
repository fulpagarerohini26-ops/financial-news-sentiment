"""Local validation, annotation agreement, and split preparation for evaluation."""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from financial_news_sentiment.evaluation import HUMAN_LABELS
from financial_news_sentiment.news.normalization import validate_ticker

PermissionState = Literal[
    "not_reviewed", "unclear", "prohibited", "review_cleared_for_local_evaluation"
]
_RIGHTS = ("allowed", "prohibited", "unclear")
_ARTICLE_FIELDS = (
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
)
_ANNOTATION_FIELDS = (
    "internal_article_id",
    "annotator_code",
    "annotator_role",
    "annotated_at_utc",
    "human_label",
    "uncertain",
    "rationale",
    "annotation_guide_version",
)
_PERMISSION_FIELDS = (
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
)
_ADJUDICATION_FIELDS = (
    "internal_article_id",
    "resolution_status",
    "adjudicated_label",
    "adjudicated_at_utc",
    "adjudicator_code",
    "rationale",
)
_ANNOTATOR_ROLES = ("primary", "second")
_ID_PATTERN = re.compile(r"\s+")
_HEADLINE_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_SIMILARITY_THRESHOLD = 0.9


class DatasetValidationError(ValueError):
    """Raised when an evaluation dataset file cannot be read or parsed."""


@dataclass(frozen=True, slots=True)
class DatasetIssue:
    file: str
    row_number: int | None
    article_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class DuplicatePair:
    first_article_id: str
    second_article_id: str
    kind: Literal["duplicate", "potential_duplicate"]
    similarity: float
    cross_partition: bool


@dataclass(frozen=True, slots=True)
class DatasetValidationReport:
    total_records_received: int
    valid_provenance_records: int
    permission_state_counts: dict[str, int]
    permission_review_state_counts: dict[str, int]
    duplicate_count: int
    potential_duplicate_count: int
    invalid_or_missing_required_count: int
    excluded_record_count: int
    invalid_annotation_count: int
    invalid_permission_review_count: int
    invalid_adjudication_count: int
    excluded_records: tuple[DatasetIssue, ...]
    human_label_counts: dict[str, int]
    missing_primary_annotation_count: int
    second_annotator_coverage_count: int
    second_annotator_coverage_rate: float | None
    disagreement_count: int
    paired_annotation_count: int
    disagreement_rate: float | None
    cohen_kappa: float | None
    development_partition_count: int
    heldout_partition_count: int
    unassigned_partition_count: int
    partition_leakage_count: int
    duplicate_pairs: tuple[DuplicatePair, ...]


@dataclass(frozen=True, slots=True)
class _Article:
    row_number: int
    values: dict[str, str]
    internal_article_id: str


@dataclass(frozen=True, slots=True)
class _Annotation:
    row_number: int
    article_id: str
    annotator_code: str
    role: str
    annotated_at: datetime
    label: str | None
    uncertain: bool


@dataclass(frozen=True, slots=True)
class _PermissionReview:
    values: dict[str, str]
    state: PermissionState


def validate_evaluation_dataset(
    articles_path: str | Path,
    annotations_path: str | Path,
    permissions_path: str | Path,
    adjudications_path: str | Path | None = None,
) -> DatasetValidationReport:
    """Validate metadata and annotations without fetching any source material.

    A review-cleared permission state is a structured dataset-owner
    attestation grounded in the cited terms review, not a legal determination.
    """
    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    annotation_rows = _read_csv(annotations_path, _ANNOTATION_FIELDS)
    permission_rows = _read_csv(permissions_path, _PERMISSION_FIELDS)
    adjudication_rows = (
        _read_csv(adjudications_path, _ADJUDICATION_FIELDS)
        if adjudications_path is not None
        else ()
    )
    issues: list[DatasetIssue] = []
    permission_reviews: dict[str, _PermissionReview] = {}
    for row_number, values in permission_rows:
        if "_row_error" in values:
            issues.append(
                DatasetIssue(
                    str(permissions_path),
                    row_number,
                    None,
                    values["_row_error"],
                )
            )
            continue
        review_id = values["permission_review_id"].strip()
        if not review_id or review_id in permission_reviews:
            issues.append(
                DatasetIssue(
                    str(permissions_path),
                    row_number,
                    None,
                    "missing or duplicate permission_review_id",
                )
            )
            continue
        permission_reviews[review_id] = _PermissionReview(
            values, _permission_state(values)
        )

    valid_articles: list[_Article] = []
    seen_article_ids: set[str] = set()
    invalid_article_count = 0
    for row_number, values in article_rows:
        article_id = values["internal_article_id"].strip()
        reasons = _validate_article_row(values, permission_reviews)
        if article_id and article_id in seen_article_ids:
            reasons.append("duplicate internal_article_id")
        if article_id:
            seen_article_ids.add(article_id)
        if reasons:
            invalid_article_count += 1
            issues.append(
                DatasetIssue(
                    str(articles_path),
                    row_number,
                    article_id or None,
                    "; ".join(reasons),
                )
            )
        else:
            valid_articles.append(_Article(row_number, values, article_id))

    article_by_id = {article.internal_article_id: article for article in valid_articles}
    annotations: dict[str, list[_Annotation]] = defaultdict(list)
    annotation_keys: set[tuple[str, str]] = set()
    invalid_annotation_count = 0
    for row_number, values in annotation_rows:
        if "_row_error" in values:
            invalid_annotation_count += 1
            issues.append(
                DatasetIssue(
                    str(annotations_path),
                    row_number,
                    None,
                    values["_row_error"],
                )
            )
            continue
        article_id = values["internal_article_id"].strip()
        annotator_code = values["annotator_code"].strip()
        role = values["annotator_role"].strip()
        label_text = values["human_label"].strip()
        uncertain = values["uncertain"].strip().lower()
        reasons: list[str] = []
        if article_id not in article_by_id:
            reasons.append("annotation references an unknown or invalid article")
        if not annotator_code:
            reasons.append("annotator_code is required")
        if role not in _ANNOTATOR_ROLES:
            reasons.append("annotator_role must be primary or second")
        if label_text and label_text not in HUMAN_LABELS:
            reasons.append("human_label must be Positive, Negative, Neutral, or blank")
        if uncertain not in ("", "yes", "no"):
            reasons.append("uncertain must be blank, yes, or no")
        if not _is_utc_timestamp(values["annotated_at_utc"]):
            reasons.append("annotated_at_utc must be an ISO 8601 UTC timestamp")
        if not values["annotation_guide_version"].strip():
            reasons.append("annotation_guide_version is required")
        if uncertain == "yes" and not values["rationale"].strip():
            reasons.append("uncertain annotations require a rationale")
        if uncertain == "yes" and label_text:
            reasons.append("uncertain annotations must leave human_label blank")
        if uncertain != "yes" and not label_text:
            reasons.append("non-uncertain annotations require a human_label")
        key = (article_id, role)
        if key in annotation_keys:
            reasons.append("duplicate annotation for article and annotator role")
        if reasons:
            invalid_annotation_count += 1
            issues.append(
                DatasetIssue(
                    str(annotations_path),
                    row_number,
                    article_id or None,
                    "; ".join(reasons),
                )
            )
            continue
        annotation_keys.add(key)
        annotations[article_id].append(
            _Annotation(
                row_number,
                article_id,
                annotator_code,
                role,
                datetime.fromisoformat(values["annotated_at_utc"].strip()),
                label_text or None,
                uncertain == "yes",
            )
        )

    for article_id, article_annotations in annotations.items():
        primary = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "primary"
            ),
            None,
        )
        second = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "second"
            ),
            None,
        )
        if (
            primary is not None
            and second is not None
            and primary.annotator_code == second.annotator_code
        ):
            article_annotations.remove(second)
            invalid_annotation_count += 1
            issues.append(
                DatasetIssue(
                    str(annotations_path),
                    second.row_number,
                    article_id,
                    "primary and second annotations must have different annotator codes",
                )
            )

    adjudications: dict[str, dict[str, str]] = {}
    invalid_adjudication_count = 0
    for row_number, values in adjudication_rows:
        if "_row_error" in values:
            invalid_adjudication_count += 1
            issues.append(
                DatasetIssue(
                    str(adjudications_path),
                    row_number,
                    None,
                    values["_row_error"],
                )
            )
            continue
        article_id = values["internal_article_id"].strip()
        status = values["resolution_status"].strip()
        label = values["adjudicated_label"].strip()
        reasons = []
        if article_id not in article_by_id:
            reasons.append("adjudication references an unknown or invalid article")
        if status not in ("pending", "resolved"):
            reasons.append("resolution_status must be pending or resolved")
        if status == "resolved" and label not in HUMAN_LABELS:
            reasons.append("resolved adjudication requires a valid label")
        if status == "pending" and label:
            reasons.append("pending adjudication must not have a final label")
        adjudicated_time_valid = _is_utc_timestamp(values["adjudicated_at_utc"])
        if not adjudicated_time_valid:
            reasons.append("adjudicated_at_utc must be an ISO 8601 UTC timestamp")
        article_annotations = annotations.get(article_id, [])
        primary = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "primary"
            ),
            None,
        )
        second = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "second"
            ),
            None,
        )
        if (
            primary is None
            or second is None
            or primary.uncertain
            or second.uncertain
            or primary.label is None
            or second.label is None
            or primary.label == second.label
        ):
            reasons.append(
                "adjudication requires a valid disagreement between two annotators"
            )
        elif adjudicated_time_valid and datetime.fromisoformat(
            values["adjudicated_at_utc"].strip()
        ) <= max(primary.annotated_at, second.annotated_at):
            reasons.append("adjudication must occur after both independent annotations")
        if not values["adjudicator_code"].strip():
            reasons.append("adjudicator_code is required")
        if not values["rationale"].strip():
            reasons.append("adjudication rationale is required")
        if article_id in adjudications:
            reasons.append("duplicate adjudication record")
        if reasons:
            invalid_adjudication_count += 1
            issues.append(
                DatasetIssue(
                    str(adjudications_path),
                    row_number,
                    article_id or None,
                    "; ".join(reasons),
                )
            )
        else:
            adjudications[article_id] = values

    invalid_permission_review_count = sum(
        1 for issue in issues if issue.file == str(permissions_path)
    )
    for article in valid_articles:
        article_id = article.internal_article_id
        exclusion_reasons: list[str] = []
        permission_state = _article_permission_state(article, permission_reviews)
        if permission_state != "review_cleared_for_local_evaluation":
            exclusion_reasons.append(f"permission status is {permission_state}")
        article_annotations = annotations.get(article_id, [])
        primary = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "primary"
            ),
            None,
        )
        second = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "second"
            ),
            None,
        )
        if primary is None:
            exclusion_reasons.append("missing primary annotation")
        elif primary.uncertain or primary.label is None:
            exclusion_reasons.append("primary annotation is uncertain or unlabeled")
        if second is not None and (second.uncertain or second.label is None):
            exclusion_reasons.append("second annotation is uncertain or unlabeled")
        if (
            primary is not None
            and second is not None
            and not primary.uncertain
            and not second.uncertain
            and primary.label is not None
            and second.label is not None
            and primary.label != second.label
            and (
                article_id not in adjudications
                or adjudications[article_id]["resolution_status"].strip() != "resolved"
            )
        ):
            exclusion_reasons.append("annotator disagreement is unresolved")
        if exclusion_reasons:
            issues.append(
                DatasetIssue(
                    "eligibility",
                    article.row_number,
                    article_id,
                    "; ".join(exclusion_reasons),
                )
            )
    pairs = _find_duplicate_pairs(valid_articles)
    permission_counts = Counter(
        _article_permission_state(article, permission_reviews)
        for article in valid_articles
    )
    primary_labels: dict[str, str] = {}
    paired: list[tuple[str, str]] = []
    missing_primary = 0
    second_coverage = 0
    disagreement_count = 0
    for article in valid_articles:
        article_annotations = annotations.get(article.internal_article_id, [])
        primary = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "primary"
            ),
            None,
        )
        second = next(
            (
                annotation
                for annotation in article_annotations
                if annotation.role == "second"
            ),
            None,
        )
        if primary is None or primary.uncertain or primary.label is None:
            missing_primary += 1
        else:
            primary_labels[article.internal_article_id] = primary.label
        if second is not None:
            second_coverage += 1
            if (
                primary is not None
                and not primary.uncertain
                and primary.label is not None
                and not second.uncertain
                and second.label is not None
            ):
                paired.append((primary.label, second.label))
                disagreement_count += primary.label != second.label

    distribution = {label: 0 for label in HUMAN_LABELS}
    for label in primary_labels.values():
        distribution[label] += 1
    dev_count = sum(
        article.values["partition"].strip().lower() == "development"
        for article in valid_articles
    )
    heldout_count = sum(
        article.values["partition"].strip().lower() == "heldout"
        for article in valid_articles
    )
    unassigned = len(valid_articles) - dev_count - heldout_count
    leakage_ids = {
        article_id
        for pair in pairs
        if pair.cross_partition
        for article_id in (pair.first_article_id, pair.second_article_id)
    }

    return DatasetValidationReport(
        total_records_received=len(article_rows),
        valid_provenance_records=len(valid_articles),
        permission_state_counts={
            state: permission_counts[state]
            for state in (
                "not_reviewed",
                "unclear",
                "prohibited",
                "review_cleared_for_local_evaluation",
            )
        },
        permission_review_state_counts={
            state: sum(review.state == state for review in permission_reviews.values())
            for state in (
                "not_reviewed",
                "unclear",
                "prohibited",
                "review_cleared_for_local_evaluation",
            )
        },
        duplicate_count=len(
            {
                article_id
                for pair in pairs
                if pair.kind == "duplicate"
                for article_id in (pair.first_article_id, pair.second_article_id)
            }
        ),
        potential_duplicate_count=len(
            {
                article_id
                for pair in pairs
                if pair.kind == "potential_duplicate"
                for article_id in (pair.first_article_id, pair.second_article_id)
            }
        ),
        invalid_or_missing_required_count=invalid_article_count,
        excluded_record_count=invalid_article_count
        + len(
            {
                issue.article_id
                for issue in issues
                if issue.file == "eligibility" and issue.article_id is not None
            }
        ),
        invalid_annotation_count=invalid_annotation_count,
        invalid_permission_review_count=invalid_permission_review_count,
        invalid_adjudication_count=invalid_adjudication_count,
        excluded_records=tuple(issues),
        human_label_counts=distribution,
        missing_primary_annotation_count=missing_primary,
        second_annotator_coverage_count=second_coverage,
        second_annotator_coverage_rate=(
            second_coverage / len(valid_articles) if valid_articles else None
        ),
        disagreement_count=disagreement_count,
        paired_annotation_count=len(paired),
        disagreement_rate=(disagreement_count / len(paired) if paired else None),
        cohen_kappa=_cohen_kappa(paired),
        development_partition_count=dev_count,
        heldout_partition_count=heldout_count,
        unassigned_partition_count=unassigned,
        partition_leakage_count=len(leakage_ids),
        duplicate_pairs=tuple(pairs),
    )


def create_deterministic_split(
    articles_path: str | Path,
    annotations_path: str | Path,
    permissions_path: str | Path,
    development_output: str | Path,
    heldout_output: str | Path,
    *,
    seed: int,
    heldout_fraction: float = 0.2,
    adjudications_path: str | Path | None = None,
) -> tuple[int, int]:
    """Write evaluator-compatible development/held-out CSVs by headline group.

    Exact and near-duplicate headlines are kept in the same partition.
    Unresolved independent-label disagreements and rows without approved
    local-evaluation permission are not included.
    """
    if not 0.0 < heldout_fraction < 1.0:
        raise ValueError("heldout_fraction must be between 0 and 1")
    input_paths = {
        Path(path).resolve()
        for path in (
            articles_path,
            annotations_path,
            permissions_path,
            adjudications_path,
        )
        if path is not None
    }
    output_paths = {
        Path(development_output).resolve(),
        Path(heldout_output).resolve(),
    }
    if len(output_paths) != 2 or input_paths & output_paths:
        raise ValueError(
            "split output paths must be distinct from each other and all inputs"
        )
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
            "cannot split while dataset has invalid article, annotation, permission, "
            "or adjudication rows; run validate and fix them"
        )
    if report.partition_leakage_count:
        raise DatasetValidationError(
            "cannot split while duplicate or near-duplicate headlines leak across partitions"
        )

    article_rows = _read_csv(articles_path, _ARTICLE_FIELDS)
    annotation_rows = _read_csv(annotations_path, _ANNOTATION_FIELDS)
    permission_rows = _read_csv(permissions_path, _PERMISSION_FIELDS)
    permission_reviews = {
        row["permission_review_id"].strip(): _PermissionReview(
            row, _permission_state(row)
        )
        for _, row in permission_rows
    }
    annotations_by_id: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for _, row in annotation_rows:
        annotations_by_id[row["internal_article_id"].strip()][
            row["annotator_role"].strip()
        ] = row
    adjudications = (
        {
            row["internal_article_id"].strip(): row
            for _, row in _read_csv(adjudications_path, _ADJUDICATION_FIELDS)
        }
        if adjudications_path is not None
        else {}
    )

    eligible: list[dict[str, str]] = []
    for _, row in article_rows:
        article_id = row["internal_article_id"].strip()
        if (
            _article_permission_state(_Article(0, row, article_id), permission_reviews)
            != "review_cleared_for_local_evaluation"
        ):
            continue
        labels = annotations_by_id.get(article_id, {})
        primary = labels.get("primary")
        second = labels.get("second")
        if primary is None:
            continue
        label = primary["human_label"].strip()
        if primary["uncertain"].strip().lower() == "yes" or label not in HUMAN_LABELS:
            continue
        if second is not None:
            second_label = second["human_label"].strip()
            if (
                second["uncertain"].strip().lower() == "yes"
                or second_label not in HUMAN_LABELS
            ):
                continue
            if label != second_label:
                adjudication = adjudications.get(article_id)
                if (
                    adjudication is None
                    or adjudication["resolution_status"].strip() != "resolved"
                    or adjudication["adjudicated_label"].strip() not in HUMAN_LABELS
                ):
                    continue
                label = adjudication["adjudicated_label"].strip()
        eligible.append(
            {
                "article_id": article_id,
                "ticker": row["ticker"].strip(),
                "headline": row["headline"],
                "human_label": label,
                "summary": "",
                "source": row["provider_name"].strip(),
                "published_at": row["published_at"].strip(),
                "annotation_notes": primary["rationale"].strip(),
                "_provider_key": (
                    f"{row['provider_name'].strip().casefold()}:"
                    f"{row['provider_article_id'].strip()}"
                    if row["provider_article_id"].strip()
                    else ""
                ),
                "_source_url_key": row["source_url"].strip().rstrip("/"),
            }
        )

    if len(eligible) < 2:
        raise DatasetValidationError(
            "at least two permission-cleared, annotated, resolved articles are required to split"
        )
    group_ids = _headline_groups(eligible)
    shuffled_groups = list(group_ids)
    random.Random(seed).shuffle(shuffled_groups)
    target_heldout = max(1, round(len(eligible) * heldout_fraction))
    heldout_ids: set[str] = set()
    heldout_count = 0
    for group in shuffled_groups:
        if heldout_count < target_heldout and heldout_count + len(group) < len(
            eligible
        ):
            heldout_ids.update(group)
            heldout_count += len(group)
    if not heldout_ids:
        raise DatasetValidationError(
            "cannot split because all eligible examples belong to one duplicate group"
        )

    development_rows = [row for row in eligible if row["article_id"] not in heldout_ids]
    heldout_rows = [row for row in eligible if row["article_id"] in heldout_ids]
    output_fields = (
        "article_id",
        "ticker",
        "headline",
        "human_label",
        "summary",
        "source",
        "published_at",
        "annotation_notes",
    )
    _write_csv(development_output, output_fields, development_rows)
    _write_csv(heldout_output, output_fields, heldout_rows)
    return len(development_rows), len(heldout_rows)


def report_to_json(report: DatasetValidationReport) -> str:
    """Serialize a dataset-validation report deterministically."""
    return json.dumps(asdict(report), indent=2, sort_keys=True)


def _read_csv(
    file_path: str | Path, required_headers: tuple[str, ...]
) -> tuple[tuple[int, dict[str, str]], ...]:
    path = Path(file_path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            try:
                headers = next(reader)
            except StopIteration:
                raise DatasetValidationError(
                    f"{path}: CSV is empty and has no header row"
                ) from None
            if len(headers) != len(set(headers)):
                raise DatasetValidationError(f"{path}: duplicate CSV column names")
            unsupported = sorted(set(headers) - set(required_headers))
            if unsupported:
                raise DatasetValidationError(
                    f"{path}: unsupported CSV columns: {', '.join(unsupported)}"
                )
            missing = sorted(set(required_headers) - set(headers))
            if missing:
                raise DatasetValidationError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            rows: list[tuple[int, dict[str, str]]] = []
            for row_number, values in enumerate(reader, start=2):
                if not values:
                    continue
                if len(values) != len(headers):
                    rows.append(
                        (
                            row_number,
                            {header: "" for header in headers}
                            | {
                                "_row_error": f"expected {len(headers)} fields, found {len(values)}"
                            },
                        )
                    )
                else:
                    rows.append((row_number, dict(zip(headers, values, strict=True))))
            return tuple(rows)
    except FileNotFoundError as error:
        raise DatasetValidationError(f"{path}: file was not found") from error
    except PermissionError as error:
        raise DatasetValidationError(f"{path}: permission denied") from error
    except UnicodeDecodeError as error:
        raise DatasetValidationError(f"{path}: file is not valid UTF-8") from error
    except csv.Error as error:
        raise DatasetValidationError(f"{path}: malformed CSV: {error}") from error
    except OSError as error:
        raise DatasetValidationError(f"{path}: unable to read file: {error}") from error


def _validate_article_row(
    row: dict[str, str], reviews: dict[str, _PermissionReview]
) -> list[str]:
    reasons: list[str] = []
    if "_row_error" in row:
        return [row["_row_error"]]
    for field in (
        "internal_article_id",
        "provider_name",
        "headline",
        "published_at",
        "publication_timezone_handling",
        "collected_at_utc",
        "dataset_version",
        "provenance_ref",
        "permission_review_id",
        "usage_notes",
    ):
        if not row[field].strip():
            reasons.append(f"{field} is required")
    try:
        validate_ticker(row["ticker"])
    except ValueError:
        reasons.append("ticker is invalid or missing")
    if not _is_timestamp(row["published_at"]):
        reasons.append("published_at must be ISO 8601 with timezone offset")
    if not _is_utc_timestamp(row["collected_at_utc"]):
        reasons.append("collected_at_utc must be an ISO 8601 UTC timestamp")
    review_id = row["permission_review_id"].strip()
    if review_id and review_id not in reviews:
        reasons.append("permission review ID is unknown")
    elif review_id:
        provider_name = reviews[review_id].values["provider_name"].strip()
        if provider_name.casefold() != row["provider_name"].strip().casefold():
            reasons.append("permission review provider does not match article provider")
    return reasons


def _permission_state(values: dict[str, str]) -> PermissionState:
    required = (
        "provider_name",
        "terms_url",
        "checked_at_utc",
        "attribution_requirement",
        "retention_requirement",
        "reviewer_notes",
        "written_approval_reference",
    )
    if any(not values[field].strip() for field in required):
        return "not_reviewed"
    if not _is_utc_timestamp(values["checked_at_utc"]):
        return "not_reviewed"
    statuses = [
        values[field].strip().lower()
        for field in (
            "research_use",
            "local_storage",
            "display",
            "redistribution",
            "evaluation_reporting",
        )
    ]
    if any(status not in _RIGHTS for status in statuses):
        return "not_reviewed"
    if values["account_plan_verified"].strip().lower() != "yes":
        return "unclear"
    if "prohibited" in statuses:
        return "prohibited"
    if (
        values["research_use"].strip().lower() == "allowed"
        and values["local_storage"].strip().lower() == "allowed"
        and values["evaluation_reporting"].strip().lower() == "allowed"
    ):
        return "review_cleared_for_local_evaluation"
    return "unclear"


def _article_permission_state(
    article: _Article, reviews: dict[str, _PermissionReview]
) -> PermissionState:
    review_id = article.values["permission_review_id"].strip()
    review = reviews.get(review_id)
    if review is None:
        return "not_reviewed"
    if (
        review.values["provider_name"].strip().casefold()
        != article.values["provider_name"].strip().casefold()
    ):
        return "unclear"
    return review.state


def _find_duplicate_pairs(articles: list[_Article]) -> list[DuplicatePair]:
    pairs: list[DuplicatePair] = []
    for index, first in enumerate(articles):
        first_headline = _normalize_headline(first.values["headline"])
        for second in articles[index + 1 :]:
            second_headline = _normalize_headline(second.values["headline"])
            similarity = SequenceMatcher(None, first_headline, second_headline).ratio()
            same_provider_id = (
                bool(first.values["provider_article_id"].strip())
                and first.values["provider_name"].strip().casefold()
                == second.values["provider_name"].strip().casefold()
                and first.values["provider_article_id"].strip()
                == second.values["provider_article_id"].strip()
            )
            same_source_url = bool(first.values["source_url"].strip()) and first.values[
                "source_url"
            ].strip().rstrip("/") == second.values["source_url"].strip().rstrip("/")
            if similarity == 1.0 or same_provider_id or same_source_url:
                kind: Literal["duplicate", "potential_duplicate"] = "duplicate"
            elif (
                min(len(first_headline), len(second_headline)) >= 25
                and similarity >= _SIMILARITY_THRESHOLD
            ):
                kind = "potential_duplicate"
            else:
                continue
            pairs.append(
                DuplicatePair(
                    first.internal_article_id,
                    second.internal_article_id,
                    kind,
                    similarity,
                    first.values["partition"].strip().lower()
                    != second.values["partition"].strip().lower()
                    and bool(first.values["partition"].strip())
                    and bool(second.values["partition"].strip()),
                )
            )
    return pairs


def _headline_groups(rows: list[dict[str, str]]) -> list[list[str]]:
    parents = list(range(len(rows)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for first_index, first in enumerate(rows):
        first_headline = _normalize_headline(first["headline"])
        for second_index in range(first_index + 1, len(rows)):
            second = rows[second_index]
            second_headline = _normalize_headline(second["headline"])
            same_identity = any(
                first[key] and first[key] == second[key]
                for key in ("_provider_key", "_source_url_key")
            )
            related_headline = first_headline == second_headline or (
                min(len(first_headline), len(second_headline)) >= 25
                and SequenceMatcher(None, first_headline, second_headline).ratio()
                >= _SIMILARITY_THRESHOLD
            )
            if same_identity or related_headline:
                first_root = root(first_index)
                second_root = root(second_index)
                parents[second_root] = first_root

    grouped: dict[int, list[str]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[root(index)].append(row["article_id"])
    return [
        group
        for _, group in sorted(grouped.items(), key=lambda item: tuple(sorted(item[1])))
    ]


def _normalize_headline(headline: str) -> str:
    lowered = _HEADLINE_PUNCTUATION.sub(" ", headline.casefold())
    return _ID_PATTERN.sub(" ", lowered).strip()


def _is_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def _is_utc_timestamp(value: str) -> bool:
    if not _is_timestamp(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return False
    return parsed.utcoffset() == UTC.utcoffset(parsed)


def _cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    count = len(pairs)
    observed = sum(first == second for first, second in pairs) / count
    first_counts = Counter(first for first, _ in pairs)
    second_counts = Counter(second for _, second in pairs)
    expected = sum(
        first_counts[label] * second_counts[label] for label in HUMAN_LABELS
    ) / (count * count)
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def _write_csv(
    path: str | Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in fieldnames} for row in rows
        )
