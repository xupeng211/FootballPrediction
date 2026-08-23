"""Deterministic research evidence and durable attempt records."""

from __future__ import annotations

from dataclasses import InitVar, dataclass
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
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
ARTIFACT_FILENAME = "canonical-offline-model-evaluation.json"
RECEIPT_FILENAME = "canonical-offline-model-evaluation.receipt.json"
REPRODUCIBILITY_REPLAY_OF_CONSUMED_HOLDOUT = "REPRODUCIBILITY_REPLAY_OF_CONSUMED_HOLDOUT"
_OUTPUT_DESTINATION_FACTORY_TOKEN = object()


@dataclass(frozen=True)
class PreparedOutputDestination:
    """An atomically claimed, one-shot output directory for one evaluation."""

    path: Path
    device: int
    inode: int
    journal_path: Path
    artifact_path: Path
    receipt_path: Path
    _factory_token: InitVar[object]

    def __post_init__(self, factory_token: object) -> None:
        if factory_token is not _OUTPUT_DESTINATION_FACTORY_TOKEN:
            raise EvaluationContractError(
                "PreparedOutputDestination must be created by the canonical preparation factory"
            )

    def assert_current(self, *, require_empty_outputs: bool = True) -> None:
        """Reject replacement, symlink traversal, or stale output targets."""
        try:
            stat = self.path.stat()
        except OSError as exc:
            raise EvaluationContractError("evaluation output destination is unavailable") from exc
        if (
            self.path.is_symlink()
            or not self.path.is_dir()
            or stat.st_dev != self.device
            or stat.st_ino != self.inode
        ):
            raise EvaluationContractError("evaluation output destination was replaced")

        if require_empty_outputs:
            for path in (self.journal_path, self.artifact_path, self.receipt_path):
                if os.path.lexists(path):
                    raise EvaluationContractError(f"evaluation output already exists: {path.name}")
        elif self.journal_path.is_symlink() or (
            self.journal_path.exists() and not self.journal_path.is_file()
        ):
            raise EvaluationContractError("evaluation attempt journal path is not reusable")


def prepare_evaluation_output_destination(
    output_dir: str | Path,
) -> PreparedOutputDestination:
    """Atomically claim a fresh external directory before outcome access."""
    requested = _assert_external_path(output_dir, "evaluation output destination")
    try:
        directory = requested.resolve(strict=False)
    except OSError as exc:
        raise EvaluationContractError(
            "evaluation output destination identity is unavailable"
        ) from exc
    if not directory.parent.is_dir() or directory.parent.is_symlink():
        raise EvaluationContractError("evaluation output destination parent is unavailable")
    if os.path.lexists(directory):
        raise EvaluationContractError("evaluation output destination must be a new directory")
    try:
        directory.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise EvaluationContractError(
            "evaluation output destination must be a new directory"
        ) from exc
    except OSError as exc:
        raise EvaluationContractError("evaluation output destination cannot be created") from exc

    try:
        stat = directory.stat()
    except OSError as exc:
        raise EvaluationContractError("evaluation output destination cannot be inspected") from exc
    destination = PreparedOutputDestination(
        path=directory,
        device=stat.st_dev,
        inode=stat.st_ino,
        journal_path=directory / JOURNAL_FILENAME,
        artifact_path=directory / ARTIFACT_FILENAME,
        receipt_path=directory / RECEIPT_FILENAME,
        _factory_token=_OUTPUT_DESTINATION_FACTORY_TOKEN,
    )
    destination.assert_current()
    return destination


def _append_newline_json(path: Path, value: Mapping[str, Any]) -> bytes:
    payload = bytes(_canonical_json_bytes(dict(value))) + b"\n"
    descriptor = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "ab") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise EvaluationContractError("evaluation attempt journal write failed") from exc
    return payload


@dataclass(frozen=True)
class _JournalCapabilityRecord:
    """Private registry record for one post-fsync opaque capability."""

    journal_path: Path
    event_fields: Mapping[str, Any]
    payload: bytes
    device: int
    inode: int
    size: int
    journal_sha256: str


_JOURNAL_CAPABILITIES: dict[object, _JournalCapabilityRecord] = {}


def _validate_capability_event_identity(
    record: _JournalCapabilityRecord,
    *,
    evaluation_id: str,
    protocol_sha256: str | None,
    protocol_freeze_sha: str | None,
    reserved_row_count: int,
    reserved_row_id_hash: str | None,
) -> None:
    fields = record.event_fields
    if fields.get("event_type") != "OUTCOME_OPENING_STARTED":
        raise EvaluationContractError("journal capability event type is invalid")
    if fields.get("evaluation_id") != evaluation_id:
        raise EvaluationContractError("journal capability evaluation identity is invalid")
    if fields.get("evaluation_protocol_sha256") != protocol_sha256:
        raise EvaluationContractError("journal capability protocol identity is invalid")
    if fields.get("protocol_freeze_sha") != protocol_freeze_sha:
        raise EvaluationContractError("journal capability freeze identity is invalid")
    if fields.get("reserved_row_count") != reserved_row_count:
        raise EvaluationContractError("journal capability reserved row count is invalid")
    if (
        reserved_row_id_hash is not None
        and fields.get("reserved_row_id_hash") != reserved_row_id_hash
    ):
        raise EvaluationContractError("journal capability reserved row identity is invalid")


def _consume_journal_capability(
    capability: object,
    *,
    evaluation_id: str,
    protocol_sha256: str | None,
    protocol_freeze_sha: str | None,
    reserved_row_count: int,
    reserved_row_id_hash: str | None,
) -> Path:
    """Consume a registry-issued capability after exact file identity checks."""
    try:
        record = _JOURNAL_CAPABILITIES.get(capability)
    except TypeError as exc:
        raise EvaluationContractError(
            "reserved outcomes require a post-fsync journal capability (opaque)"
        ) from exc
    if record is None:
        raise EvaluationContractError(
            "reserved outcomes require a post-fsync journal capability (opaque)"
        )
    _validate_capability_event_identity(
        record,
        evaluation_id=evaluation_id,
        protocol_sha256=protocol_sha256,
        protocol_freeze_sha=protocol_freeze_sha,
        reserved_row_count=reserved_row_count,
        reserved_row_id_hash=reserved_row_id_hash,
    )
    path = record.journal_path
    try:
        stat = path.stat()
        journal_bytes = path.read_bytes()
    except OSError as exc:
        raise EvaluationContractError("durable evaluation journal is unavailable") from exc
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.st_dev != record.device
        or stat.st_ino != record.inode
        or stat.st_size != record.size
        or _sha256_bytes(journal_bytes) != record.journal_sha256
        or not journal_bytes.endswith(record.payload)
    ):
        raise EvaluationContractError("durable evaluation journal was replaced")
    del _JOURNAL_CAPABILITIES[capability]
    return path


def append_evaluation_journal_event(
    output_destination: PreparedOutputDestination,
    *,
    event_type: str,
    event_at: str,
    fields: Mapping[str, Any],
    allow_existing_outputs: bool = False,
) -> Path:
    """Append and fsync one non-sensitive lifecycle event before returning."""
    journal_path, _ = _append_evaluation_journal_event(
        output_destination,
        event_type=event_type,
        event_at=event_at,
        fields=fields,
        issue_capability=False,
        require_empty_outputs=not allow_existing_outputs,
    )
    return journal_path


def _append_evaluation_journal_event_with_capability(
    output_destination: PreparedOutputDestination,
    *,
    event_type: str,
    event_at: str,
    fields: Mapping[str, Any],
) -> tuple[Path, object]:
    """Append an event and issue a one-use post-fsync capability."""
    journal_path, capability = _append_evaluation_journal_event(
        output_destination,
        event_type=event_type,
        event_at=event_at,
        fields=fields,
        issue_capability=True,
        require_empty_outputs=True,
    )
    if capability is None:
        raise EvaluationContractError("opening journal capability was not issued")
    return journal_path, capability


def _append_evaluation_journal_event(
    output_destination: PreparedOutputDestination,
    *,
    event_type: str,
    event_at: str,
    fields: Mapping[str, Any],
    issue_capability: bool,
    require_empty_outputs: bool,
) -> tuple[Path, object | None]:
    """Append an event and optionally issue its opaque post-fsync capability."""
    if not isinstance(output_destination, PreparedOutputDestination):
        raise EvaluationContractError("evaluation journal requires a claimed output destination")
    output_destination.assert_current(require_empty_outputs=require_empty_outputs)
    journal_path = output_destination.journal_path
    event: dict[str, Any] = {
        "event_type": event_type,
        "event_at": event_at,
        "evaluation_id": EVALUATION_ID,
    }
    event.update(dict(fields))
    payload = _append_newline_json(journal_path, event)
    if not issue_capability:
        return journal_path, None
    try:
        stat = journal_path.stat()
        journal_bytes = journal_path.read_bytes()
    except OSError as exc:
        raise EvaluationContractError("evaluation attempt journal read failed") from exc
    capability = object()
    _JOURNAL_CAPABILITIES[capability] = _JournalCapabilityRecord(
        journal_path=journal_path,
        event_fields=MappingProxyType(dict(event)),
        payload=payload,
        device=stat.st_dev,
        inode=stat.st_ino,
        size=stat.st_size,
        journal_sha256=_sha256_bytes(journal_bytes),
    )
    return journal_path, capability


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
    artifact = {
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
            "status_before": prepared.holdout_status_before,
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
    if prepared.replay_of_consumed_holdout:
        artifact["evaluation_attempt"] = REPRODUCIBILITY_REPLAY_OF_CONSUMED_HOLDOUT
    return artifact


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
    if "evaluation_attempt" in artifact:
        receipt["evaluation_attempt"] = artifact["evaluation_attempt"]
    receipt["receipt_content_sha256"] = _sha256_json(receipt)
    return receipt


def _write_new_bytes(path: Path, payload: bytes) -> None:
    if os.path.lexists(path):
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
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise EvaluationContractError(f"evaluation output already exists: {path.name}") from exc
        temporary_path.unlink()
        temporary_path = None
    except EvaluationContractError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise EvaluationContractError("evaluation artifact write failed") from exc


def write_evaluation_outputs(
    artifact: Mapping[str, Any],
    *,
    output_destination: PreparedOutputDestination,
    protocol_freeze_sha: str,
    evaluation_source_head: str,
) -> dict[str, Any]:
    """Write exactly one external artifact and receipt without manifest state."""
    if not isinstance(output_destination, PreparedOutputDestination):
        raise EvaluationContractError("evaluation outputs require a claimed output destination")
    output_destination.assert_current(require_empty_outputs=False)
    artifact_path = output_destination.artifact_path
    receipt_path = output_destination.receipt_path
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
    "ARTIFACT_FILENAME",
    "JOURNAL_FILENAME",
    "RECEIPT_FILENAME",
    "PreparedOutputDestination",
    "append_evaluation_journal_event",
    "build_evaluation_artifact",
    "build_evaluation_receipt",
    "prepare_evaluation_output_destination",
    "write_evaluation_outputs",
]
