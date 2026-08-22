"""Safe CLI for the canonical training producer.

lifecycle: permanent
component: Canonical CLI adapter

This entrypoint only accepts an explicit offline feature frame and an explicit
non-production candidate path. It delegates all contract, split, model,
envelope, atomic-write, and provenance rules to the one producer module.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import pandas as pd

from src.ml.training import canonical_training_producer as producer

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def _load_input_frame(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise producer.TrainingContractError("training input file is missing")
    suffix = path.suffix.lower()
    readers: dict[str, Callable[..., pd.DataFrame]] = {
        ".csv": pd.read_csv,
        ".json": pd.read_json,
        ".jsonl": lambda value: pd.read_json(value, lines=True),
        ".parquet": pd.read_parquet,
    }
    if suffix not in readers:
        raise producer.TrainingContractError("training input format is unsupported")
    try:
        return readers[suffix](path)
    except (OSError, ValueError, TypeError) as exc:
        raise producer.TrainingContractError("training input file is unreadable") from exc


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical prematch vnext offline candidate producer"
    )
    parser.add_argument(
        "--input", required=True, help="explicit CSV/JSON/JSONL/Parquet feature frame"
    )
    parser.add_argument(
        "--receipt",
        help="repository-external canonical feature-frame receipt (required for canonical JSON frame)",
    )
    parser.add_argument("--output", help="non-production candidate artifact path")
    parser.add_argument("--timestamp-column", default=producer.DEFAULT_TIMESTAMP_COLUMN)
    parser.add_argument("--target-column", default=producer.DEFAULT_TARGET_COLUMN)
    parser.add_argument("--feature-cutoff-column", default=None)
    parser.add_argument("--source-dataset-identity", default="explicit-offline-feature-frame")
    parser.add_argument(
        "--validation-fraction", type=float, default=producer.DEFAULT_VALIDATION_FRACTION
    )
    parser.add_argument("--min-train-rows", type=int, default=producer.DEFAULT_MIN_TRAIN_ROWS)
    parser.add_argument(
        "--min-validation-rows", type=int, default=producer.DEFAULT_MIN_VALIDATION_ROWS
    )
    parser.add_argument("--seed", type=int, default=producer.DEFAULT_SEED)
    parser.add_argument("--estimators", type=int, default=producer.DEFAULT_ESTIMATORS)
    parser.add_argument("--depth", type=int, default=producer.DEFAULT_MAX_DEPTH)
    parser.add_argument("--learning-rate", type=float, default=producer.DEFAULT_LEARNING_RATE)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and split only; no fit or write"
    )
    parser.add_argument("--json", action="store_true", help="emit one JSON summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate or produce one safe canonical candidate."""
    args = _parse_args(argv)
    input_path = Path(args.input)
    if args.receipt:
        data = producer.load_canonical_feature_frame(input_path, Path(args.receipt))
    else:
        frame = _load_input_frame(input_path)
        data = producer.validate_training_frame(
            frame,
            timestamp_column=args.timestamp_column,
            target_column=args.target_column,
            feature_cutoff_column=args.feature_cutoff_column,
        )
    split = producer.chronological_split(
        data,
        validation_fraction=args.validation_fraction,
        min_train_rows=args.min_train_rows,
        min_validation_rows=args.min_validation_rows,
    )
    if args.dry_run:
        summary = {
            "mode": "canonical_training_dry_run",
            "training_data_valid": True,
            "feature_contract_valid": True,
            "temporal_split_valid": True,
            "model_fit_success": False,
            "oos_evaluation_success": False,
            "artifact_envelope_valid": False,
            "final_candidate_exists": False,
            "candidate_sha256_computed": False,
            "provenance_complete": False,
            "feature_count": data.contract.feature_count,
            "feature_columns": list(data.contract.ordered_features),
            "train_rows": len(split.train),
            "reserved_evaluation_rows": len(split.validation),
            "frame_eligible_rows": data.frame_eligible_rows,
            "frame_ineligible_rows": data.frame_ineligible_rows,
            "train_date_range": producer._date_range(split.train_timestamps),
            "reserved_evaluation_date_range": producer._date_range(split.validation_timestamps),
        }
        sys.stdout.write(
            f"{json.dumps(summary, ensure_ascii=False, sort_keys=True) if args.json else summary}\n"
        )
        return 0
    if not args.output:
        raise producer.TrainingContractError("--output is required unless --dry-run is used")
    candidate = producer.produce_candidate(
        data.frame,
        args.output,
        timestamp_column=args.timestamp_column,
        target_column=args.target_column,
        feature_cutoff_column=data.feature_cutoff_column or args.feature_cutoff_column,
        validation_fraction=args.validation_fraction,
        min_train_rows=args.min_train_rows,
        min_validation_rows=args.min_validation_rows,
        seed=args.seed,
        estimators=args.estimators,
        max_depth=args.depth,
        learning_rate=args.learning_rate,
        source_dataset_identity=args.source_dataset_identity,
        source_binding=data.source_binding,
    )
    summary = {
        "mode": "canonical_training_candidate",
        "training_data_valid": True,
        "feature_contract_valid": True,
        "temporal_split_valid": True,
        "model_fit_success": True,
        "oos_evaluation_success": False,
        "artifact_envelope_valid": True,
        "final_candidate_exists": candidate.path.exists(),
        "candidate_sha256_computed": bool(candidate.sha256),
        "provenance_complete": True,
        "candidate_sha256": candidate.sha256,
        "artifact_name": producer.CANDIDATE_ARTIFACT_NAME,
        "model_type": producer.CANDIDATE_MODEL_TYPE,
        "contract_id": data.contract.contract_id,
        "feature_count": data.contract.feature_count,
        "candidate_path": str(candidate.path),
        "candidate_metadata_path": str(candidate.metadata_path)
        if candidate.metadata_path
        else None,
        "candidate_metadata_sha256": candidate.metadata_sha256,
        "train_rows": candidate.provenance.get("train_rows"),
        "reserved_evaluation_rows": candidate.provenance.get("reserved_evaluation_rows"),
        "frame_eligible_rows": candidate.provenance.get("frame_eligible_rows"),
        "trainer_rejected_rows": candidate.provenance.get("trainer_rejected_rows"),
        "provenance": candidate.provenance,
    }
    sys.stdout.write(
        f"{json.dumps(summary, ensure_ascii=False, sort_keys=True) if args.json else summary}\n"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except producer.TrainingContractError as exc:
        logger.warning("canonical training producer blocked: %s", exc)
        raise SystemExit(1) from exc
