"""Validate real-news evaluation metadata and create a reproducible split."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from financial_news_sentiment.evaluation_dataset import (
    create_deterministic_split,
    report_to_json,
    validate_evaluation_dataset,
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

    args = parser.parse_args()
    if args.command == "validate":
        report = validate_evaluation_dataset(
            args.articles, args.annotations, args.permissions, args.adjudications
        )
        print(report_to_json(report))
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
    manifest = {
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


if __name__ == "__main__":
    main()
