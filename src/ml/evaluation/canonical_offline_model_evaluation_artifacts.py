"""Deterministic research evidence and durable attempt records."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Mapping

from src.ml.training import canonical_training_producer as producer

from .canonical_offline_model_evaluation_contract import (
    ARTIFACT_SCHEMA_VERSION,
    CLASS_NAMES,
    CLASS_ORDER,
    EVALUATION_ID,
    FEATURE_ORDER,
    LOG_LOSS_EPSILON,
    PROBABILITY_COLUMN_ORDER,
    RECEIPT_SCHEMA_VERSION,
    RESERVED_STATUS_AFTER,
    RESERVED_STATUS_BEFORE,
    EvaluationContractError,
    _assert_external_path,
    _assert_git_sha,
    _canonical_json_bytes,
    _parse_opened_at,
    _sha256_bytes,
    _sha256_json,
)
from .canonical_offline_model_evaluation_metrics import (
    _bootstrap_intervals,
    _calibration_summary,
    _class_distribution,
    _confusion_matrix,
    _per_class_metrics,
    _quality_status,
    _round_number,
    build_baselines,
    metric_bundle,
    validate_probability_matrix,
)

JOURNAL_FILENAME = "canonical-offline-model-evaluation.attempt.journal.jsonl"


def _append_newline_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = _canonical_json_bytes(dict(value)) + b"\n"
    try:
        with path.open("ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise EvaluationContractError("evaluation attempt journal write failed") from exc


def append_evaluation_journal_event(
    output_dir: str | Path,
    *,
    event_type: str,
    event_at: str,
    fields: Mapping[str, Any],
) -> Path:
    """Append and fsync one non-sensitive lifecycle event before returning."""
    directory = _assert_external_path(output_dir, "evaluation journal directory")
    directory.mkdir(parents=True, exist_ok=True)
    journal_path = directory / JOURNAL_FILENAME
    event: dict[str, Any] = {
        "event_type": event_type,
        "event_at": event_at,
        "evaluation_id": EVALUATION_ID,
    }
    event.update(dict(fields))
    _append_newline_json(journal_path, event)
    return journal_path


def build_evaluation_artifact(prepared: Any, labels: np.ndarray[Any, Any]) -> dict[str, Any]:
    """Build deterministic, row-bound research evidence after outcome access."""
    if not prepared.gate.protocol_frozen or not prepared.gate.outcomes_opened:
        raise EvaluationContractError(
            "evaluation artifact requires frozen protocol and opened outcomes"
        )
    if prepared.probabilities is None or prepared.opened_at is None:
        raise EvaluationContractError("evaluation inference evidence is incomplete")
    if prepared.source_head is None or prepared.protocol_freeze_sha is None:
        raise EvaluationContractError("evaluation Git binding is incomplete")
    _parse_opened_at(prepared.opened_at)
    labels = np.asarray(labels, dtype=int)
    if prepared.opened_labels is None or not np.array_equal(labels, prepared.opened_labels):
        raise EvaluationContractError("artifact labels are not the gate-opened labels")
    if labels.ndim != 1 or len(labels) != len(prepared.population.reserved_ids):
        raise EvaluationContractError("opened outcome labels are invalid")
    if not np.isin(labels, CLASS_ORDER).all():
        raise EvaluationContractError("opened outcome labels are invalid")

    candidate_probabilities = np.asarray(prepared.probabilities, dtype=float)
    validate_probability_matrix(
        candidate_probabilities, expected_rows=len(prepared.population.reserved_ids)
    )
    baseline_definitions, prior_probabilities, majority_probabilities, majority_class = (
        build_baselines(prepared.candidate, labels)
    )
    candidate_metrics = metric_bundle(candidate_probabilities, labels)
    prior_metrics = metric_bundle(prior_probabilities, labels)
    majority_metrics = metric_bundle(majority_probabilities, labels)
    predictions = np.argmax(candidate_probabilities, axis=1)
    deltas = {
        "log_loss_delta_vs_prior": candidate_metrics["multiclass_log_loss"]
        - prior_metrics["multiclass_log_loss"],
        "brier_delta_vs_prior": candidate_metrics["multiclass_brier_score"]
        - prior_metrics["multiclass_brier_score"],
        "accuracy_delta_vs_majority": candidate_metrics["accuracy"] - majority_metrics["accuracy"],
    }
    calibration = _calibration_summary(candidate_probabilities, labels, prepared.protocol)
    intervals = _bootstrap_intervals(
        candidate_probabilities,
        prior_probabilities,
        labels,
        majority_class,
        prepared.protocol,
    )

    prediction_rows: list[dict[str, Any]] = []
    for index, row_id in enumerate(prepared.population.reserved_ids):
        row = prepared.population.rows_by_id[row_id]
        actual = int(labels[index])
        predicted = int(predictions[index])
        prediction_rows.append(
            {
                "row_id": row_id,
                "kickoff_utc": row.kickoff_utc,
                "actual_class": actual,
                "actual_class_name": CLASS_NAMES[actual],
                "predicted_class": predicted,
                "predicted_class_name": CLASS_NAMES[predicted],
                "probabilities": {
                    column: _round_number(float(candidate_probabilities[index, class_index]))
                    for class_index, column in enumerate(PROBABILITY_COLUMN_ORDER)
                },
            }
        )

    entropy_values = -np.sum(
        np.clip(candidate_probabilities, LOG_LOSS_EPSILON, 1.0)
        * np.log(np.clip(candidate_probabilities, LOG_LOSS_EPSILON, 1.0)),
        axis=1,
    )
    confidence_values = np.max(candidate_probabilities, axis=1)
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "evaluation_id": EVALUATION_ID,
        "evaluation_protocol_version": prepared.protocol["schema_version"],
        "evaluation_protocol_sha256": prepared.protocol_sha256,
        "evaluation_code_revision": prepared.source_head,
        "protocol_freeze_sha": prepared.protocol_freeze_sha,
        "protocol_frozen_before_outcome_open": True,
        "candidate": prepared.candidate.identity(),
        "frame": {
            "artifact_sha256": prepared.population.frame_binding.artifact_sha256,
            "receipt_sha256": prepared.population.frame_binding.receipt_sha256,
            "business_sha256": prepared.population.frame_binding.business_sha256,
            "code_revision": prepared.population.frame_binding.frame_code_revision,
            "feature_contract_id": prepared.population.frame_binding.contract_id,
            "feature_contract_version": prepared.population.frame_binding.contract_version,
        },
        "feature_contract": {
            "feature_count": len(FEATURE_ORDER),
            "feature_order": list(FEATURE_ORDER),
        },
        "population": {
            "frame_eligible_rows": len(prepared.population.eligible_ids),
            "training_rows": len(prepared.population.training_ids),
            "reserved_evaluation_rows": len(prepared.population.reserved_ids),
            "evaluated_rows": len(labels),
            "training_row_id_hash": producer._row_id_hash(list(prepared.population.training_ids)),
            "reserved_row_id_hash": producer._row_id_hash(list(prepared.population.reserved_ids)),
            "reserved_row_ids": list(prepared.population.reserved_ids),
            "reserved_date_range": [
                prepared.population.rows_by_id[prepared.population.reserved_ids[0]].kickoff_utc,
                prepared.population.rows_by_id[prepared.population.reserved_ids[-1]].kickoff_utc,
            ],
            "temporal_partition": prepared.protocol["population"]["temporal_partition"],
        },
        "holdout": {
            "status_before": RESERVED_STATUS_BEFORE,
            "outcomes_opened": True,
            "outcome_opened_at": prepared.opened_at,
            "status_after": RESERVED_STATUS_AFTER,
        },
        "model_output": {
            "model_class_order": list(CLASS_ORDER),
            "class_names": list(CLASS_NAMES),
            "probability_column_order": list(PROBABILITY_COLUMN_ORDER),
            "probability_sanity": {
                "finite": True,
                "range_0_to_1": True,
                "row_sum_atol": prepared.protocol["model_output"]["sanity"]["row_sum_atol"],
                "max_row_sum_abs_error": _round_number(
                    float(np.max(np.abs(candidate_probabilities.sum(axis=1) - 1.0)))
                ),
            },
            "predicted_class_distribution": _class_distribution(predictions),
            "actual_class_distribution": _class_distribution(labels),
            "mean_predicted_probability_by_class": {
                column: _round_number(float(np.mean(candidate_probabilities[:, index])))
                for index, column in enumerate(PROBABILITY_COLUMN_ORDER)
            },
            "entropy_summary": {
                "mean": _round_number(float(np.mean(entropy_values))),
                "min": _round_number(float(np.min(entropy_values))),
                "max": _round_number(float(np.max(entropy_values))),
            },
            "confidence_summary": {
                "mean_max_probability": _round_number(float(np.mean(confidence_values))),
                "min_max_probability": _round_number(float(np.min(confidence_values))),
                "max_max_probability": _round_number(float(np.max(confidence_values))),
            },
        },
        "primary_metric": "multiclass_log_loss",
        "secondary_metrics": [
            "multiclass_brier_score",
            "accuracy",
            "per_class_recall",
            "per_class_precision",
            "confusion_matrix",
            "calibration_diagnostics",
        ],
        "candidate_metrics": candidate_metrics,
        "baseline_definitions": baseline_definitions,
        "baseline_metrics": {
            "training_class_prior": prior_metrics,
            "training_majority_class": majority_metrics,
        },
        "metric_deltas": deltas,
        "confusion_matrix": _confusion_matrix(labels, predictions),
        "per_class_metrics": _per_class_metrics(labels, predictions),
        "calibration_summary": calibration,
        "uncertainty_intervals": intervals,
        "model_offline_quality_status": _quality_status(deltas, intervals, calibration),
        "claims": {
            "model_quality_proven": False,
            "profitability_proven": False,
            "production_ready": False,
            "model_selected": False,
            "model_activated": False,
        },
        "safety": {
            "training_runs": 0,
            "hyperparameter_search_runs": 0,
            "new_candidates_created": 0,
            "model_selection_runs": 0,
            "backtest_runs": 0,
            "betting_value_evaluation_runs": 0,
            "model_activations": 0,
            "production_model_changed": False,
            "production_manifest_changed": False,
            "db_writes": 0,
            "raw_writes": 0,
            "live_fetch": 0,
            "repository_external": True,
            "non_production_research_evidence": True,
        },
        "prediction_rows": prediction_rows,
    }


def build_evaluation_receipt(
    artifact: Mapping[str, Any],
    artifact_bytes: bytes,
    *,
    protocol_freeze_sha: str,
    evaluation_source_head: str,
) -> dict[str, Any]:
    """Build a provenance receipt and reject source/freeze mismatches."""
    _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
    _assert_git_sha(evaluation_source_head, "evaluation source HEAD")
    if artifact.get("protocol_freeze_sha") != protocol_freeze_sha:
        raise EvaluationContractError("receipt protocol freeze SHA does not match artifact")
    if artifact.get("evaluation_code_revision") != evaluation_source_head:
        raise EvaluationContractError("receipt source HEAD does not match artifact")
    artifact_sha256 = _sha256_bytes(artifact_bytes)
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "evaluation_id": artifact["evaluation_id"],
        "evaluation_protocol_version": artifact["evaluation_protocol_version"],
        "evaluation_protocol_sha256": artifact["evaluation_protocol_sha256"],
        "evaluation_code_revision": evaluation_source_head,
        "protocol_freeze_sha": protocol_freeze_sha,
        "protocol_frozen_before_outcome_open": True,
        "candidate": artifact["candidate"],
        "frame": artifact["frame"],
        "reserved_evaluation_rows": artifact["population"]["reserved_evaluation_rows"],
        "reserved_row_id_hash": artifact["population"]["reserved_row_id_hash"],
        "reserved_date_range": artifact["population"]["reserved_date_range"],
        "primary_metric": artifact["primary_metric"],
        "holdout_status_before": artifact["holdout"]["status_before"],
        "holdout_status_after": artifact["holdout"]["status_after"],
        "outcomes_opened": artifact["holdout"]["outcomes_opened"],
        "outcome_opened_at": artifact["holdout"]["outcome_opened_at"],
        "artifact_sha256": artifact_sha256,
        "training_runs": 0,
        "hyperparameter_search_runs": 0,
        "new_candidates_created": 0,
        "model_selection_runs": 0,
        "backtest_runs": 0,
        "betting_value_evaluation_runs": 0,
        "model_activations": 0,
        "production_model_changed": False,
        "production_manifest_changed": False,
        "db_writes": 0,
        "raw_writes": 0,
        "live_fetch": 0,
        "repository_external": True,
        "non_production_research_evidence": True,
        "receipt_content_sha256": None,
    }
    receipt["receipt_content_sha256"] = _sha256_json(receipt)
    return receipt


def _write_new_bytes(path: Path, payload: bytes) -> None:
    if path.exists():
        raise EvaluationContractError(f"evaluation output already exists: {path.name}")
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        temporary_path = None
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise EvaluationContractError("evaluation artifact write failed") from exc


def write_evaluation_outputs(
    artifact: Mapping[str, Any],
    *,
    output_dir: str | Path,
    protocol_freeze_sha: str,
    evaluation_source_head: str,
) -> dict[str, Any]:
    """Write exactly one external artifact and receipt without manifest state."""
    directory = _assert_external_path(output_dir, "evaluation output directory")
    directory.mkdir(parents=True, exist_ok=True)
    artifact_path = directory / "canonical-offline-model-evaluation.json"
    receipt_path = directory / "canonical-offline-model-evaluation.receipt.json"
    artifact_bytes = _canonical_json_bytes(dict(artifact)) + b"\n"
    receipt = build_evaluation_receipt(
        artifact,
        artifact_bytes,
        protocol_freeze_sha=protocol_freeze_sha,
        evaluation_source_head=evaluation_source_head,
    )
    receipt_bytes = _canonical_json_bytes(receipt) + b"\n"
    _write_new_bytes(artifact_path, artifact_bytes)
    try:
        _write_new_bytes(receipt_path, receipt_bytes)
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise
    return {
        "artifact_path": str(artifact_path),
        "artifact_sha256": _sha256_bytes(artifact_bytes),
        "receipt_path": str(receipt_path),
        "receipt_sha256": _sha256_bytes(receipt_bytes),
        "artifact_bytes": artifact_bytes,
        "receipt_bytes": receipt_bytes,
    }


__all__ = [
    "JOURNAL_FILENAME",
    "append_evaluation_journal_event",
    "build_evaluation_artifact",
    "build_evaluation_receipt",
    "write_evaluation_outputs",
]
