"""Validate real-news evaluation metadata and create a reproducible split."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from financial_news_sentiment.evaluation_dataset import (
    DatasetValidationError,
    create_deterministic_split,
    report_to_json,
    validate_evaluation_dataset,
)
from financial_news_sentiment.evaluation_workflow import (
    collect_finnhub_once,
    disagreement_report,
    export_annotator_sheet,
    freeze_split,
    import_annotator_sheet,
    import_permitted_csv,
    sha256_file,
    validate_split_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="validate provenance and annotations"
    )
    _add_dataset_arguments(validate)

    split = commands.add_parser(
        "split", help="write permission-cleared development and held-out CSV files"
    )
    _add_dataset_arguments(split)
    split.add_argument("--development-output", type=Path, required=True)
    split.add_argument("--heldout-output", type=Path, required=True)
    split.add_argument("--manifest-output", type=Path, required=True)
    split.add_argument("--seed", type=int, required=True)
    split.add_argument("--heldout-fraction", type=float, default=0.2)

    validate_split = commands.add_parser(
        "validate-split",
        help="verify split files against source annotations, permissions, and manifest",
    )
    _add_dataset_arguments(validate_split)
    validate_split.add_argument("--development", type=Path, required=True)
    validate_split.add_argument("--heldout", type=Path, required=True)
    validate_split.add_argument("--split-manifest", type=Path, required=True)

    collect = commands.add_parser(
        "collect-finnhub",
        help="make one permission-gated Finnhub request for an explicit date range",
    )
    collect.add_argument("--permissions", type=Path, required=True)
    collect.add_argument("--permission-review-id", required=True)
    collect.add_argument("--ticker", required=True)
    collect.add_argument("--from-date", type=date.fromisoformat, required=True)
    collect.add_argument("--to-date", type=date.fromisoformat, required=True)
    collect.add_argument("--dataset-version", required=True)
    collect.add_argument("--articles-output", type=Path, required=True)
    collect.add_argument("--exclusions-output", type=Path, required=True)

    import_csv = commands.add_parser(
        "import-csv",
        help="import a permitted offline source CSV into the provenance schema",
    )
    import_csv.add_argument("--input", type=Path, required=True)
    import_csv.add_argument("--permissions", type=Path, required=True)
    import_csv.add_argument("--permission-review-id", required=True)
    import_csv.add_argument("--provider-name", required=True)
    import_csv.add_argument("--dataset-version", required=True)
    import_csv.add_argument("--provenance-ref", required=True)
    import_csv.add_argument("--articles-output", type=Path, required=True)
    import_csv.add_argument("--exclusions-output", type=Path, required=True)

    export = commands.add_parser(
        "export-annotations",
        help="write a prediction-free annotator sheet",
    )
    export.add_argument("--articles", type=Path, required=True)
    export.add_argument("--annotations", type=Path, required=True)
    export.add_argument("--permissions", type=Path, required=True)
    export.add_argument("--permission-review-id", required=True)
    export.add_argument("--role", choices=("primary", "second"), required=True)
    export.add_argument("--guide-version", required=True)
    export.add_argument(
        "--selection-csv",
        type=Path,
        help="optional CSV with internal_article_id column, e.g. a preselected second-label subset",
    )
    export.add_argument("--output", type=Path, required=True)

    import_annotations = commands.add_parser(
        "import-annotations",
        help="validate and append one annotator's independently completed sheet",
    )
    import_annotations.add_argument("--sheet", type=Path, required=True)
    import_annotations.add_argument("--articles", type=Path, required=True)
    import_annotations.add_argument("--annotations", type=Path, required=True)
    import_annotations.add_argument("--annotator-code", required=True)
    import_annotations.add_argument(
        "--role", choices=("primary", "second"), required=True
    )
    import_annotations.add_argument("--guide-version", required=True)
    import_annotations.add_argument("--annotated-at-utc")

    disagreements = commands.add_parser(
        "disagreements",
        help="report independent labels before adjudication",
    )
    disagreements.add_argument("--articles", type=Path, required=True)
    disagreements.add_argument("--annotations", type=Path, required=True)

    freeze = commands.add_parser(
        "freeze",
        help="freeze a validated, independently annotated real-news split",
    )
    _add_dataset_arguments(freeze)
    freeze.add_argument("--development", type=Path, required=True)
    freeze.add_argument("--heldout", type=Path, required=True)
    freeze.add_argument("--split-manifest", type=Path, required=True)
    freeze.add_argument("--freeze-manifest", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "validate":
        report = validate_evaluation_dataset(
            args.articles, args.annotations, args.permissions, args.adjudications
        )
        print(report_to_json(report))
        return

    if args.command == "validate-split":
        print(
            json.dumps(
                validate_split_artifacts(
                    articles_path=args.articles,
                    annotations_path=args.annotations,
                    permissions_path=args.permissions,
                    development_path=args.development,
                    heldout_path=args.heldout,
                    split_manifest_path=args.split_manifest,
                    adjudications_path=args.adjudications,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.command == "collect-finnhub":
        _check_distinct_output_paths(
            args.articles_output,
            args.exclusions_output,
            forbidden=(args.permissions,),
        )
        imported, excluded = collect_finnhub_once(
            articles_path=args.articles_output,
            permissions_path=args.permissions,
            permission_review_id=args.permission_review_id,
            ticker=args.ticker,
            start_date=args.from_date,
            end_date=args.to_date,
            dataset_version=args.dataset_version,
            exclusions_path=args.exclusions_output,
        )
        print(json.dumps({"imported": imported, "excluded": excluded}, indent=2))
        return

    if args.command == "import-csv":
        _check_distinct_output_paths(
            args.articles_output,
            args.exclusions_output,
            forbidden=(args.input, args.permissions),
        )
        imported, excluded = import_permitted_csv(
            source_path=args.input,
            articles_path=args.articles_output,
            permissions_path=args.permissions,
            permission_review_id=args.permission_review_id,
            provider_name=args.provider_name,
            dataset_version=args.dataset_version,
            provenance_ref=args.provenance_ref,
            exclusions_path=args.exclusions_output,
        )
        print(json.dumps({"imported": imported, "excluded": excluded}, indent=2))
        return

    if args.command == "export-annotations":
        count = export_annotator_sheet(
            articles_path=args.articles,
            annotations_path=args.annotations,
            permissions_path=args.permissions,
            permission_review_id=args.permission_review_id,
            output_path=args.output,
            guide_version=args.guide_version,
            role=args.role,
            selection_path=args.selection_csv,
        )
        print(json.dumps({"exported": count}, indent=2))
        return

    if args.command == "import-annotations":
        imported, missing = import_annotator_sheet(
            sheet_path=args.sheet,
            articles_path=args.articles,
            annotations_path=args.annotations,
            annotator_code=args.annotator_code,
            role=args.role,
            guide_version=args.guide_version,
            annotated_at_utc=args.annotated_at_utc,
        )
        print(
            json.dumps(
                {"imported": imported, "unlabeled_or_uncertain": missing}, indent=2
            )
        )
        return

    if args.command == "disagreements":
        print(
            json.dumps(
                disagreement_report(args.articles, args.annotations),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "freeze":
        manifest = freeze_split(
            articles_path=args.articles,
            annotations_path=args.annotations,
            permissions_path=args.permissions,
            development_path=args.development,
            heldout_path=args.heldout,
            split_manifest_path=args.split_manifest,
            freeze_manifest_path=args.freeze_manifest,
            adjudications_path=args.adjudications,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return

    input_paths = {
        path.resolve()
        for path in (
            args.articles,
            args.annotations,
            args.permissions,
            args.adjudications,
        )
        if path is not None
    }
    output_paths = {
        args.development_output.resolve(),
        args.heldout_output.resolve(),
        args.manifest_output.resolve(),
    }
    if len(output_paths) != 3 or input_paths & output_paths:
        parser.error("output paths must be distinct from each other and all inputs")
    if any(path.exists() for path in output_paths):
        parser.error(
            "split output paths already exist; use a new dataset/split version"
        )

    development_count, heldout_count = create_deterministic_split(
        args.articles,
        args.annotations,
        args.permissions,
        args.development_output,
        args.heldout_output,
        seed=args.seed,
        heldout_fraction=args.heldout_fraction,
        adjudications_path=args.adjudications,
    )
    development_labels = Counter()
    heldout_labels = Counter()
    development_ids: list[str] = []
    heldout_ids: list[str] = []
    with args.articles.open(encoding="utf-8", newline="") as stream:
        source_versions = sorted(
            {
                row["dataset_version"].strip()
                for row in csv.DictReader(stream)
                if row["dataset_version"].strip()
            }
        )
    for path, counts in (
        (args.development_output, development_labels),
        (args.heldout_output, heldout_labels),
    ):
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                counts[row["human_label"]] += 1
                (
                    development_ids if path == args.development_output else heldout_ids
                ).append(row["article_id"])
    source_files = {
        "articles": args.articles,
        "annotations": args.annotations,
        "permissions": args.permissions,
    }
    if args.adjudications is not None:
        source_files["adjudications"] = args.adjudications
    manifest = {
        "dataset_category": "manually_labeled_real_news",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "article_dataset_versions": source_versions,
        "split_rule": "seeded random assignment of exact/near-duplicate headline groups",
        "seed": args.seed,
        "heldout_fraction_target": args.heldout_fraction,
        "development_size": development_count,
        "heldout_size": heldout_count,
        "development_article_ids": development_ids,
        "heldout_article_ids": heldout_ids,
        "development_class_counts": dict(development_labels),
        "heldout_class_counts": dict(heldout_labels),
        "source_sha256": {key: sha256_file(path) for key, path in source_files.items()},
        "development_sha256": sha256_file(args.development_output),
        "heldout_sha256": sha256_file(args.heldout_output),
        "labels_used": "primary label unless independently agreed or adjudicated",
        "heldout_use": "final evaluation only; do not tune thresholds or models",
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


def _add_dataset_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--articles", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--permissions", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path)


def _check_distinct_output_paths(
    first: Path, second: Path, *, forbidden: tuple[Path, ...]
) -> None:
    outputs = {first.resolve(), second.resolve()}
    if len(outputs) != 2 or outputs & {path.resolve() for path in forbidden}:
        raise SystemExit("output paths must be distinct from each other and all inputs")


if __name__ == "__main__":
    try:
        main()
    except DatasetValidationError as error:
        raise SystemExit(f"dataset workflow error: {error}") from None
