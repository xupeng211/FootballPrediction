"""Candidate provenance and non-production artifact writer.

The module is an implementation detail of the canonical training producer. It
does not know or mutate the production manifest; all producer references are
resolved lazily to keep the public training module import-compatible.
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

import joblib  # type: ignore[import-untyped]

from src.ml.inference.artifact_manifest import ArtifactManifest
from src.ml.inference.canonical_model_loader import (
    ModelArtifactUnavailableError,
    validate_canonical_model_envelope,
)

logger = logging.getLogger(__name__)


def _producer():
    """Resolve the canonical producer lazily to avoid an import cycle."""
    from src.ml.training import canonical_training_producer as producer  # noqa: PLC0415

    return producer


def build_provenance(
    split: Any,
    metrics: Mapping[str, Any] | None,
    contract: Any,
    *,
    seed: int,
    source_dataset_identity: str,
    source_binding: Any = None,
    estimator_type: str = "xgboost.XGBClassifier",
    hyperparameters: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build deterministic provenance without paths, credentials, or rows."""
    producer = _producer()
    if (
        not source_dataset_identity
        or Path(source_dataset_identity).is_absolute()
        or ".." in Path(source_dataset_identity).parts
    ):
        raise producer.TrainingContractError("source dataset identity must be a safe logical name")

    def class_distribution(frame) -> dict[str, int]:
        counts = frame[split.target_column].value_counts().to_dict()
        return {
            producer.RESULT_NAMES[label]: int(counts.get(label, 0))
            for label in producer.DEFAULT_CLASS_ORDER
        }

    train_ids = (
        split.train["match_id"].astype(str).tolist() if "match_id" in split.train.columns else []
    )
    reserved_ids = (
        split.validation["match_id"].astype(str).tolist()
        if "match_id" in split.validation.columns
        else []
    )
    if bool(train_ids) != bool(reserved_ids):
        raise producer.TrainingContractError(
            "training and reserved evaluation ID bindings are incomplete"
        )
    if set(train_ids).intersection(reserved_ids):
        raise producer.TrainingContractError("training and reserved evaluation IDs overlap")

    if source_binding is None:
        input_binding: dict[str, Any] = {
            "status": "UNVERIFIED_TEST_FIXTURE",
            "artifact_sha256": None,
            "receipt_sha256": None,
            "business_sha256": None,
        }
        frame_eligible_rows = len(split.train) + len(split.validation)
        frame_ineligible_rows = 0
    else:
        input_binding = {"status": "VERIFIED_CANONICAL_FRAME", **source_binding.as_dict()}
        if (
            source_binding.contract_id != contract.contract_id
            or source_binding.contract_version != contract.feature_contract_version
            or source_binding.feature_names != contract.ordered_features
            or source_binding.target_population
            != source_binding.eligible_rows + source_binding.ineligible_rows
            or source_binding.rows_accounted != source_binding.target_population
            or source_binding.eligible_rows != len(split.train) + len(split.validation)
            or source_binding.eligible_row_id_sha256
            != producer._row_id_hash(train_ids + reserved_ids)
        ):
            raise producer.TrainingContractError("canonical frame binding does not match split")
        frame_eligible_rows = source_binding.eligible_rows
        frame_ineligible_rows = source_binding.ineligible_rows

    producer_source_revision = producer._git_revision()
    if source_binding is not None and producer_source_revision == "unavailable":
        raise producer.TrainingContractError(
            "verified canonical training requires an exact producer Git revision"
        )

    payload = {
        "producer_schema_version": producer.PRODUCER_SCHEMA_VERSION,
        "producer_source_revision": producer_source_revision,
        "artifact_name": producer.CANDIDATE_ARTIFACT_NAME,
        "model_type": producer.CANDIDATE_MODEL_TYPE,
        "model_family": producer.CANDIDATE_MODEL_FAMILY,
        "model_version": producer.CANDIDATE_MODEL_VERSION,
        "contract_id": contract.contract_id,
        "feature_contract_version": contract.feature_contract_version,
        "feature_columns": list(contract.ordered_features),
        "feature_count": contract.feature_count,
        "class_order": list(producer.DEFAULT_CLASS_ORDER),
        "class_names": list(producer.RESULT_NAMES),
        "random_seed": seed,
        "estimator": {
            "class": estimator_type,
            "hyperparameters": dict(hyperparameters or {}),
        },
        "source_dataset_identity": source_dataset_identity,
        "input_binding": input_binding,
        "frame_eligible_rows": frame_eligible_rows,
        "training_protocol_rows": len(split.train) + len(split.validation),
        "trainer_admitted_rows": len(split.train),
        "trainer_rejected_rows": frame_ineligible_rows,
        "trainer_reserved_rows": len(split.validation),
        "frame_ineligible_rows": frame_ineligible_rows,
        "train_rows": len(split.train),
        "reserved_evaluation_rows": len(split.validation),
        "validation_rows": len(split.validation),
        "training_row_id_sha256": producer._row_id_hash(train_ids) if train_ids else None,
        "reserved_evaluation_row_id_sha256": (
            producer._row_id_hash(reserved_ids) if reserved_ids else None
        ),
        "train_class_distribution": class_distribution(split.train),
        "reserved_evaluation_class_distribution": class_distribution(split.validation),
        "train_date_range": producer._date_range(split.train_timestamps),
        "reserved_evaluation_date_range": producer._date_range(split.validation_timestamps),
        "split_policy": {
            "name": "chronological_reserved_evaluation_holdout/v1",
            "validation_fraction": split.validation_fraction,
            "boundary_rule": "strictly earlier target kickoff for fit rows than reserved rows",
            "equal_kickoff_rows_are_kept_in_one_partition": True,
            "reserved_evaluation_touched_by_fit": False,
        },
        "label_contract": {
            "name": "TRAINING_LABEL_POSTMATCH",
            "timing_class": "POSTMATCH_ONLY",
            "field": "target_label.outcome",
            "feature_label_intersection": [],
        },
        "preprocessing": {
            "identity": "sklearn.StandardScaler/v1",
            "fit_population": "training_partition_only",
            "fit_rows": len(split.train),
        },
        "fit_diagnostics": dict(metrics or {}),
    }
    if created_at is not None:
        payload["created_at"] = created_at
    payload["candidate_id"] = "canonical-prematch-vnext-" + producer._sha256_json(payload)[:24]
    payload["created_as"] = producer.CANDIDATE_CREATED_AS
    payload["activated"] = producer.CANDIDATE_ACTIVATED
    return payload


def build_candidate_envelope(
    fitted: Any,
    contract: Any,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a non-production candidate envelope with exact vnext identity."""
    producer = _producer()
    envelope = {
        "model": fitted.model,
        "scaler": fitted.scaler,
        "artifact_name": producer.CANDIDATE_ARTIFACT_NAME,
        "model_type": producer.CANDIDATE_MODEL_TYPE,
        "required_for": "api",
        "contract_id": contract.contract_id,
        "feature_contract_version": contract.feature_contract_version,
        "feature_columns": list(contract.ordered_features),
        "schema_version": producer.PRODUCER_SCHEMA_VERSION,
        "candidate_id": provenance.get("candidate_id"),
        "model_family": producer.CANDIDATE_MODEL_FAMILY,
        "model_version": producer.CANDIDATE_MODEL_VERSION,
        "created_as": producer.CANDIDATE_CREATED_AS,
        "activated": producer.CANDIDATE_ACTIVATED,
        "provenance": dict(provenance),
    }
    try:
        validate_canonical_model_envelope(
            envelope,
            artifact_name=producer.CANDIDATE_ARTIFACT_NAME,
            model_type=producer.CANDIDATE_MODEL_TYPE,
            contract=contract,
        )
    except ModelArtifactUnavailableError as exc:
        raise producer.TrainingContractError(
            "candidate envelope is incompatible with canonical loader"
        ) from exc
    return envelope


def _reject_production_path(path: Path) -> None:
    """Reject repository and production-looking candidate destinations."""
    producer = _producer()
    if not path.is_absolute():
        raise producer.TrainingContractError("candidate output path must be absolute")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise producer.TrainingContractError("candidate output path contains a symlink")
        current = current.parent
    repository_root = Path(producer.__file__).resolve().parents[3]
    try:
        path.resolve().relative_to(repository_root)
    except ValueError:
        pass
    else:
        raise producer.TrainingContractError("candidate output must be repository-external")
    parts = tuple(part.lower() for part in path.resolve().parts)
    if "config" in parts:
        raise producer.TrainingContractError("tracked configuration is not a candidate output")
    if any(
        parts[index : index + 2] == ("model_zoo", "production") for index in range(len(parts) - 1)
    ) or any(part in {"models", "model_zoo"} for part in parts):
        raise producer.TrainingContractError("production artifact path is not a candidate output")


def _candidate_metadata(provenance: Mapping[str, Any], model_sha256: str) -> dict[str, Any]:
    """Build the sidecar metadata package without serializing model objects."""
    producer = _producer()
    input_binding = provenance.get("input_binding", {})
    preprocessing = provenance.get("preprocessing", {})
    estimator = provenance.get("estimator", {})
    metadata: dict[str, Any] = {
        "schema_version": producer.CANDIDATE_SCHEMA_VERSION,
        "candidate_id": provenance.get("candidate_id"),
        "model_family": producer.CANDIDATE_MODEL_FAMILY,
        "model_version": producer.CANDIDATE_MODEL_VERSION,
        "code_revision": provenance.get("producer_source_revision"),
        "feature_contract_id": provenance.get("contract_id"),
        "feature_contract_version": provenance.get("feature_contract_version"),
        "feature_names": provenance.get("feature_columns"),
        "feature_order": provenance.get("feature_columns"),
        "training_frame_artifact_hash": input_binding.get("artifact_sha256"),
        "training_frame_receipt_hash": input_binding.get("receipt_sha256"),
        "training_row_count": provenance.get("train_rows"),
        "training_row_id_hash": provenance.get("training_row_id_sha256"),
        "reserved_evaluation_row_count": provenance.get("reserved_evaluation_rows"),
        "reserved_evaluation_row_id_hash": provenance.get("reserved_evaluation_row_id_sha256"),
        "label_contract": provenance.get("label_contract"),
        "split_policy": provenance.get("split_policy"),
        "preprocessor_identity": preprocessing.get("identity"),
        "preprocessor_fit_population": preprocessing.get("fit_population"),
        "hyperparameters": estimator.get("hyperparameters"),
        "random_seed": provenance.get("random_seed"),
        "model_artifact_sha256": model_sha256,
        "created_as": producer.CANDIDATE_CREATED_AS,
        "activated": producer.CANDIDATE_ACTIVATED,
        "provenance": dict(provenance),
        "metadata_content_sha256": None,
    }
    metadata["metadata_content_sha256"] = producer._sha256_json(metadata)
    return metadata


def validate_candidate_metadata(
    metadata: Mapping[str, Any], *, model_sha256: str | None = None
) -> None:
    """Validate the auditable sidecar and its binding to model bytes."""
    producer = _producer()
    required = {
        "schema_version",
        "candidate_id",
        "model_family",
        "model_version",
        "code_revision",
        "feature_contract_id",
        "feature_contract_version",
        "feature_names",
        "feature_order",
        "training_frame_artifact_hash",
        "training_frame_receipt_hash",
        "training_row_count",
        "training_row_id_hash",
        "reserved_evaluation_row_count",
        "reserved_evaluation_row_id_hash",
        "label_contract",
        "split_policy",
        "preprocessor_identity",
        "preprocessor_fit_population",
        "hyperparameters",
        "random_seed",
        "model_artifact_sha256",
        "created_as",
        "activated",
        "provenance",
        "metadata_content_sha256",
    }
    missing = required - set(metadata)
    if missing:
        raise producer.TrainingContractError("candidate metadata is incomplete")
    if metadata.get("schema_version") != producer.CANDIDATE_SCHEMA_VERSION:
        raise producer.TrainingContractError("candidate metadata schema is invalid")
    if metadata.get("created_as") != producer.CANDIDATE_CREATED_AS:
        raise producer.TrainingContractError("candidate metadata is not non-production")
    if metadata.get("activated") != producer.CANDIDATE_ACTIVATED:
        raise producer.TrainingContractError("candidate metadata activation flag is invalid")
    declared_model_hash = producer._assert_sha256(
        metadata.get("model_artifact_sha256"), "candidate model artifact hash"
    )
    if model_sha256 is not None and declared_model_hash != model_sha256:
        raise producer.TrainingContractError("candidate metadata model hash mismatch")
    declared_content_hash = producer._assert_sha256(
        metadata.get("metadata_content_sha256"), "candidate metadata hash"
    )
    content = dict(metadata)
    content["metadata_content_sha256"] = None
    if declared_content_hash != producer._sha256_json(content):
        raise producer.TrainingContractError("candidate metadata content hash mismatch")


def _atomic_write_bytes(payload: bytes, path: Path) -> None:
    """Write one new external file atomically and durably."""
    producer = _producer()
    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        temporary_path = None
        try:
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
        except (AttributeError, OSError):
            directory_fd = None
        if directory_fd is not None:
            try:
                try:
                    os.fsync(directory_fd)
                except OSError:
                    logger.debug("candidate directory fsync unavailable: %s", path.parent)
            finally:
                os.close(directory_fd)
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise producer.TrainingContractError("candidate sidecar write failed") from exc


def atomic_write_candidate(  # noqa: C901, PLR0915
    envelope: Mapping[str, Any],
    output_path: str | Path,
    *,
    contract: Any = None,
) -> Any:
    """Serialize a model and its provenance sidecar without activation."""
    producer = _producer()
    path = Path(output_path)
    if not path.name:
        raise producer.TrainingContractError("candidate output path is invalid")
    _reject_production_path(path)
    metadata_path = path.with_name(f"{path.name}.metadata.json")
    _reject_production_path(metadata_path)
    if path.exists() or metadata_path.exists():
        raise producer.TrainingContractError("candidate output already exists")
    try:
        validate_canonical_model_envelope(
            envelope,
            artifact_name=producer.CANDIDATE_ARTIFACT_NAME,
            model_type=producer.CANDIDATE_MODEL_TYPE,
            contract=contract,
        )
    except ModelArtifactUnavailableError as exc:
        raise producer.TrainingContractError("candidate envelope validation failed") from exc
    provenance = envelope.get("provenance")
    if not isinstance(provenance, Mapping):
        raise producer.TrainingContractError("candidate provenance is missing")

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(file_descriptor, "wb") as handle:
            joblib.dump(dict(envelope), handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        temporary_path = None
        try:
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
        except (AttributeError, OSError):
            directory_fd = None
        if directory_fd is not None:
            try:
                try:
                    os.fsync(directory_fd)
                except OSError:
                    logger.debug("candidate directory fsync unavailable: %s", path.parent)
            finally:
                os.close(directory_fd)
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise producer.TrainingContractError("candidate artifact write failed") from exc

    try:
        checksum = ArtifactManifest.compute_sha256(path)
    except (OSError, ValueError) as exc:
        path.unlink(missing_ok=True)
        raise producer.TrainingContractError("candidate checksum computation failed") from exc
    try:
        metadata = _candidate_metadata(provenance, checksum)
        metadata_bytes = producer._canonical_json_bytes(metadata) + b"\n"
        _atomic_write_bytes(metadata_bytes, metadata_path)
        validate_candidate_metadata(metadata, model_sha256=checksum)
        metadata_checksum = ArtifactManifest.compute_sha256(metadata_path)
    except Exception:
        path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise
    return producer.CandidateArtifact(
        path=path,
        sha256=checksum,
        provenance=dict(provenance),
        metadata_path=metadata_path,
        metadata_sha256=metadata_checksum,
    )
