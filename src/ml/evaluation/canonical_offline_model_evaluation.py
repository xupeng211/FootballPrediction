"""Canonical, one-time offline evaluation for the frozen vnext candidate.

This module is deliberately separate from the historical VALUE_MVP research
surface and from the training producer.  It consumes one exact candidate and
one exact repository-external frame, reconstructs the producer's chronological
split without opening reserved labels, and exposes a small outcome-access gate.

The public execution order is:

``prepare_evaluation -> freeze_protocol -> infer_reserved -> open_outcomes``

The last operation is the only place where ``target_label.outcome`` is read.
No function in this module trains, tunes, selects, activates, backtests, or
uses odds.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd

from src.ml.inference.canonical_model_loader import validate_canonical_model_envelope
from src.ml.training import canonical_training_producer as producer

PROTOCOL_SCHEMA_VERSION = "canonical-offline-model-evaluation-protocol/v1"
ARTIFACT_SCHEMA_VERSION = "canonical-offline-model-evaluation-artifact/v1"
RECEIPT_SCHEMA_VERSION = "canonical-offline-model-evaluation-receipt/v1"
EVALUATION_ID = "canonical-offline-model-evaluation-20260823-candidate-a"
EVALUATION_TASK = "CANONICAL_OFFLINE_MODEL_EVALUATION"

EXPECTED_CANDIDATE_ID = "canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41"
EXPECTED_CANDIDATE_ARTIFACT_SHA256 = (
    "a841169d51d90ddfad89dfa48defbe8875d10e1c0ed6d205a06b15a307f7160c"
)
EXPECTED_CANDIDATE_METADATA_SHA256 = (
    "1b3343eb4f050f0b32372b66a1ba84c68656ddad745fc83083680f5a1fdf97df"
)
EXPECTED_CANDIDATE_SOURCE_REVISION = "00708a5a5b76481f312aaf110dd356bb749cb96c"
EXPECTED_FRAME_ARTIFACT_SHA256 = "206c65788d8f815f79e3281401fbca8e540a2ebd5f24af4421077ac428bc0524"
EXPECTED_FRAME_RECEIPT_SHA256 = "7dd88606ffc74f4ed1a015898b0950af98f41af65405df81aa5e59f3ce14b159"
EXPECTED_FRAME_BUSINESS_SHA256 = "b3650cb698bdb6bd6e8fcf22a6e1f78e7b6e80978eb3279d6c4a087c96c975b3"
EXPECTED_FRAME_CODE_REVISION = "1bd14026c9bea3098d36ecc91dd816d94b69ac54"
EXPECTED_RESERVED_ROW_ID_SHA256 = "ea42247460b9993b4963bf4c26a372d58498865526e1401312055125a466bbde"
EXPECTED_TRAINING_ROW_ID_SHA256 = "7d48e4b5d42493ddb54bab6a1a0c1185b7258b32500b8eccb3b2bef50df76baf"

CLASS_ORDER = (0, 1, 2)
CLASS_NAMES = ("AWAY", "DRAW", "HOME")
PROBABILITY_COLUMN_ORDER = ("P_AWAY", "P_DRAW", "P_HOME")
FEATURE_ORDER = tuple(producer.ACCEPTED_TRAINING_FEATURES)
RESERVED_STATUS_BEFORE = "UNTOUCHED_RESERVED_EVALUATION_HOLDOUT"
RESERVED_STATUS_AFTER = "CONSUMED_FOR_OFFLINE_EVALUATION"
CALIBRATION_BIN_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
BOOTSTRAP_SEED = 20260823
BOOTSTRAP_RESAMPLES = 5000
LOG_LOSS_EPSILON = 1e-15
PROBABILITY_SUM_ATOL = 1e-8
SHA256_HEX_LENGTH = 64
GIT_SHA_LENGTH = 40
FEATURE_COUNT = 9
CLASS_COUNT = 3
PROBABILITY_MATRIX_DIMENSIONS = 2
FRAME_ELIGIBLE_ROWS = 545
FRAME_INELIGIBLE_ROWS = 343
TRAINING_ROWS = 436
RESERVED_ROWS = 109
CALIBRATION_MIN_NONEMPTY_BIN_COUNT = 10
BOOTSTRAP_CONFIDENCE_LEVEL = 0.95
CLEARLY_MISALIGNED_CALIBRATION_GAP = 0.2
TRAINING_CLASS_COUNTS = (135, 97, 204)
TRAINING_CLASS_DISTRIBUTION = {"AWAY": 135, "DRAW": 97, "HOME": 204}


class EvaluationContractError(ValueError):
    """Raised when an evaluation input or invariant cannot be proven."""


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvaluationContractError("evaluation JSON is not canonical") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _assert_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EvaluationContractError(f"{label} is not a lowercase SHA-256")
    return value


def _assert_git_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != GIT_SHA_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EvaluationContractError(f"{label} is not a full Git SHA")
    return value


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _assert_external_path(path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        raise EvaluationContractError(f"{label} path must be absolute")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise EvaluationContractError(f"{label} path contains a symlink")
        current = current.parent
    try:
        path.resolve().relative_to(_repository_root())
    except ValueError:
        return path
    raise EvaluationContractError(f"{label} must be repository-external")


def _read_external_file(path_value: str | Path, label: str) -> tuple[Path, bytes]:
    path = _assert_external_path(path_value, label)
    try:
        before = path.stat()
        if not path.is_file() or path.is_symlink():
            raise EvaluationContractError(f"{label} must be an ordinary file")
        payload = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise EvaluationContractError(f"{label} is unreadable") from exc
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise EvaluationContractError(f"{label} changed while being read")
    return path.resolve(), payload


def _parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationContractError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EvaluationContractError(f"{label} must be a JSON object")
    return value


def protocol_sha256(protocol: Mapping[str, Any]) -> str:
    """Return the hash of the protocol's stable, content-only representation."""
    return _sha256_json(dict(protocol))


def validate_protocol(protocol: Mapping[str, Any]) -> None:  # noqa: C901, PLR0912, PLR0915
    """Validate the immutable protocol and its task-specific subject identity."""
    required = {
        "schema_version",
        "evaluation_id",
        "task",
        "candidate",
        "frame",
        "population",
        "feature_contract",
        "model_output",
        "metrics",
        "baselines",
        "calibration",
        "uncertainty",
        "acceptance_rules",
        "forbidden_scope",
    }
    missing = required - set(protocol)
    if missing:
        raise EvaluationContractError(f"protocol is missing required fields: {sorted(missing)}")
    if protocol.get("schema_version") != PROTOCOL_SCHEMA_VERSION:
        raise EvaluationContractError("evaluation protocol schema version is invalid")
    if protocol.get("evaluation_id") != EVALUATION_ID or protocol.get("task") != EVALUATION_TASK:
        raise EvaluationContractError("evaluation protocol task identity is invalid")

    candidate = protocol["candidate"]
    frame = protocol["frame"]
    population = protocol["population"]
    feature_contract = protocol["feature_contract"]
    model_output = protocol["model_output"]
    metrics = protocol["metrics"]
    calibration = protocol["calibration"]
    uncertainty = protocol["uncertainty"]
    if not all(
        isinstance(value, Mapping) for value in (candidate, frame, population, feature_contract)
    ):
        raise EvaluationContractError("protocol identity sections must be objects")

    exact_candidate = {
        "candidate_id": EXPECTED_CANDIDATE_ID,
        "artifact_sha256": EXPECTED_CANDIDATE_ARTIFACT_SHA256,
        "metadata_sha256": EXPECTED_CANDIDATE_METADATA_SHA256,
        "source_revision": EXPECTED_CANDIDATE_SOURCE_REVISION,
    }
    for field, expected in exact_candidate.items():
        if candidate.get(field) != expected:
            raise EvaluationContractError(f"protocol candidate {field} is not frozen")
    exact_frame = {
        "artifact_sha256": EXPECTED_FRAME_ARTIFACT_SHA256,
        "receipt_sha256": EXPECTED_FRAME_RECEIPT_SHA256,
        "business_sha256": EXPECTED_FRAME_BUSINESS_SHA256,
        "code_revision": EXPECTED_FRAME_CODE_REVISION,
    }
    for field, expected in exact_frame.items():
        if frame.get(field) != expected:
            raise EvaluationContractError(f"protocol frame {field} is not frozen")

    expected_population = {
        "frame_eligible_rows": FRAME_ELIGIBLE_ROWS,
        "training_rows": TRAINING_ROWS,
        "reserved_evaluation_rows": RESERVED_ROWS,
        "reserved_evaluation_row_id_hash": EXPECTED_RESERVED_ROW_ID_SHA256,
        "training_row_id_hash": EXPECTED_TRAINING_ROW_ID_SHA256,
        "validation_fraction": 0.2,
        "temporal_partition": "chronological_reserved_evaluation_holdout/v1",
        "train_date_range": ["2022-09-03T11:30:00+00:00", "2024-02-17T17:30:00+00:00"],
        "reserved_date_range": ["2024-02-18T14:00:00+00:00", "2024-05-19T15:00:00+00:00"],
    }
    for field, expected in expected_population.items():
        if population.get(field) != expected:
            raise EvaluationContractError(f"protocol population {field} is not frozen")

    if feature_contract.get("contract_id") != "canonical_prematch/vnext-v1":
        raise EvaluationContractError("protocol feature contract ID is invalid")
    if feature_contract.get("version") != "canonical_prematch/vnext/v1":
        raise EvaluationContractError("protocol feature contract version is invalid")
    if (
        feature_contract.get("feature_count") != FEATURE_COUNT
        or tuple(feature_contract.get("feature_order", ())) != FEATURE_ORDER
    ):
        raise EvaluationContractError("protocol feature order is invalid")
    if tuple(model_output.get("class_order", ())) != CLASS_ORDER:
        raise EvaluationContractError("protocol model class order is invalid")
    if tuple(model_output.get("class_names", ())) != CLASS_NAMES:
        raise EvaluationContractError("protocol model class names are invalid")
    if tuple(model_output.get("probability_column_order", ())) != PROBABILITY_COLUMN_ORDER:
        raise EvaluationContractError("protocol probability column order is invalid")
    if metrics.get("primary_metric") != "multiclass_log_loss":
        raise EvaluationContractError("primary metric must be multiclass_log_loss")
    if tuple(metrics.get("secondary_metrics", ()))[:3] != (
        "multiclass_brier_score",
        "accuracy",
        "per_class_diagnostics",
    ):
        raise EvaluationContractError("secondary metric contract is invalid")
    if metrics.get("log_loss_epsilon") != LOG_LOSS_EPSILON:
        raise EvaluationContractError("log-loss epsilon is not frozen")
    if tuple(calibration.get("bin_edges", ())) != CALIBRATION_BIN_EDGES:
        raise EvaluationContractError("calibration binning is not frozen")
    if calibration.get("minimum_nonempty_bin_count") != CALIBRATION_MIN_NONEMPTY_BIN_COUNT:
        raise EvaluationContractError("calibration minimum count is not frozen")
    if uncertainty.get("method") != "deterministic_percentile_bootstrap":
        raise EvaluationContractError("uncertainty method is not frozen")
    if (
        uncertainty.get("resamples") != BOOTSTRAP_RESAMPLES
        or uncertainty.get("seed") != BOOTSTRAP_SEED
    ):
        raise EvaluationContractError("bootstrap identity is not frozen")
    if uncertainty.get("confidence_level") != BOOTSTRAP_CONFIDENCE_LEVEL:
        raise EvaluationContractError("bootstrap confidence level is not frozen")

    forbidden = tuple(str(item).upper() for item in protocol["forbidden_scope"])
    required_forbidden = (
        "TRAINING",
        "RETRAINING",
        "HYPERPARAMETER_TUNING",
        "BACKTEST",
        "BETTING_VALUE_EVALUATION",
        "ROI_EVALUATION",
        "CLV_EVALUATION",
        "PRODUCTION_ACTIVATION",
        "LIVE_FETCH",
        "PRODUCTION_DB_WRITE",
    )
    if not all(item in forbidden for item in required_forbidden):
        raise EvaluationContractError("protocol forbidden-scope boundary is incomplete")


def load_protocol(path_value: str | Path) -> tuple[dict[str, Any], str, Path]:
    """Load and validate the checked-in protocol without opening frame labels."""
    path = Path(path_value)
    if not path.is_absolute():
        raise EvaluationContractError("protocol path must be absolute")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise EvaluationContractError("evaluation protocol is unreadable") from exc
    protocol = _parse_json(payload, "evaluation protocol")
    validate_protocol(protocol)
    return protocol, protocol_sha256(protocol), path.resolve()


def _metadata_value(metadata: Mapping[str, Any], field: str, expected: Any) -> None:
    if metadata.get(field) != expected:
        raise EvaluationContractError(f"candidate metadata binding mismatch: {field}")


def validate_candidate_metadata_binding(  # noqa: C901
    metadata: Mapping[str, Any],
    *,
    artifact_sha256: str,
    metadata_sha256: str,
    protocol: Mapping[str, Any],
) -> None:
    """Check the complete candidate sidecar identity against the frozen protocol."""
    producer.validate_candidate_metadata(metadata, model_sha256=artifact_sha256)
    candidate = protocol["candidate"]
    _metadata_value(metadata, "candidate_id", candidate["candidate_id"])
    _metadata_value(metadata, "model_family", "xgboost_multiclass_1x2")
    _metadata_value(metadata, "model_version", "canonical-prematch-vnext-xgb/v1")
    _metadata_value(metadata, "code_revision", candidate["source_revision"])
    _metadata_value(metadata, "feature_contract_id", "canonical_prematch/vnext-v1")
    _metadata_value(metadata, "feature_contract_version", "canonical_prematch/vnext/v1")
    _metadata_value(metadata, "feature_names", list(FEATURE_ORDER))
    _metadata_value(metadata, "feature_order", list(FEATURE_ORDER))
    _metadata_value(metadata, "training_frame_artifact_hash", EXPECTED_FRAME_ARTIFACT_SHA256)
    _metadata_value(metadata, "training_frame_receipt_hash", EXPECTED_FRAME_RECEIPT_SHA256)
    _metadata_value(metadata, "training_row_count", TRAINING_ROWS)
    _metadata_value(metadata, "training_row_id_hash", EXPECTED_TRAINING_ROW_ID_SHA256)
    _metadata_value(metadata, "reserved_evaluation_row_count", RESERVED_ROWS)
    _metadata_value(metadata, "reserved_evaluation_row_id_hash", EXPECTED_RESERVED_ROW_ID_SHA256)
    _metadata_value(metadata, "preprocessor_identity", "sklearn.StandardScaler/v1")
    _metadata_value(metadata, "preprocessor_fit_population", "training_partition_only")
    _metadata_value(metadata, "random_seed", 42)
    _metadata_value(metadata, "model_artifact_sha256", artifact_sha256)
    _metadata_value(metadata, "created_as", "NON_PRODUCTION_CANDIDATE")
    _metadata_value(metadata, "activated", "NO")
    if metadata_sha256 != candidate["metadata_sha256"]:
        raise EvaluationContractError("candidate metadata file hash mismatch")

    hyperparameters = metadata.get("hyperparameters")
    expected_hyperparameters = {
        "objective": "multi:softprob",
        "num_class": 3,
        "n_estimators": 32,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "eval_metric": "mlogloss",
        "random_state": 42,
        "n_jobs": 1,
        "validation_fraction": 0.2,
    }
    if hyperparameters != expected_hyperparameters:
        raise EvaluationContractError("candidate hyperparameters are not frozen")

    provenance = metadata.get("provenance")
    if not isinstance(provenance, Mapping):
        raise EvaluationContractError("candidate provenance is missing")
    if provenance.get("producer_source_revision") != EXPECTED_CANDIDATE_SOURCE_REVISION:
        raise EvaluationContractError("candidate producer source revision was rewritten")
    if (
        provenance.get("frame_eligible_rows") != FRAME_ELIGIBLE_ROWS
        or provenance.get("trainer_admitted_rows") != TRAINING_ROWS
    ):
        raise EvaluationContractError("candidate population provenance is invalid")
    if (
        provenance.get("trainer_reserved_rows") != RESERVED_ROWS
        or provenance.get("reserved_evaluation_rows") != RESERVED_ROWS
    ):
        raise EvaluationContractError("candidate reserved-row provenance is invalid")
    if provenance.get("train_date_range") != [
        "2022-09-03T11:30:00+00:00",
        "2024-02-17T17:30:00+00:00",
    ]:
        raise EvaluationContractError("candidate training date range is invalid")
    if provenance.get("reserved_evaluation_date_range") != [
        "2024-02-18T14:00:00+00:00",
        "2024-05-19T15:00:00+00:00",
    ]:
        raise EvaluationContractError("candidate reserved date range is invalid")
    if provenance.get("train_class_distribution") != TRAINING_CLASS_DISTRIBUTION:
        raise EvaluationContractError("candidate training class distribution is invalid")
    policy = provenance.get("reserved_evaluation_policy")
    if (
        not isinstance(policy, Mapping)
        or policy.get("outcome_access") != "UNOPENED_UNTIL_OFFLINE_EVALUATION"
    ):
        raise EvaluationContractError("candidate holdout access policy is invalid")
    if any(
        policy.get(field) is not False
        for field in (
            "used_for_fit",
            "used_for_preprocessing",
            "used_for_tuning",
            "used_for_metrics",
        )
    ):
        raise EvaluationContractError("candidate holdout was used before evaluation")


@dataclass(frozen=True)
class VerifiedCandidate:
    """The exact, non-production candidate loaded from hash-bound bytes."""

    model: Any
    scaler: Any
    metadata: dict[str, Any]
    artifact_sha256: str
    metadata_sha256: str
    feature_names: tuple[str, ...]
    class_order: tuple[int, ...]

    def identity(self) -> dict[str, Any]:
        return {
            "candidate_id": self.metadata["candidate_id"],
            "artifact_sha256": self.artifact_sha256,
            "metadata_sha256": self.metadata_sha256,
            "model_family": self.metadata["model_family"],
            "model_version": self.metadata["model_version"],
            "source_revision": self.metadata["code_revision"],
            "created_as": self.metadata["created_as"],
            "activated": self.metadata["activated"],
        }


def load_verified_candidate(  # noqa: C901
    candidate_path: str | Path,
    metadata_path: str | Path,
    protocol: Mapping[str, Any],
) -> VerifiedCandidate:
    """Hash, validate, and deserialize exactly one candidate without manifest use."""
    candidate_file, candidate_bytes = _read_external_file(candidate_path, "candidate artifact")
    metadata_file, metadata_bytes = _read_external_file(metadata_path, "candidate metadata")
    artifact_sha256 = _sha256_bytes(candidate_bytes)
    metadata_sha256 = _sha256_bytes(metadata_bytes)
    expected = protocol["candidate"]
    if artifact_sha256 != expected["artifact_sha256"]:
        raise EvaluationContractError("candidate artifact hash mismatch")
    if metadata_sha256 != expected["metadata_sha256"]:
        raise EvaluationContractError("candidate metadata hash mismatch")
    metadata = _parse_json(metadata_bytes, "candidate metadata")
    validate_candidate_metadata_binding(
        metadata,
        artifact_sha256=artifact_sha256,
        metadata_sha256=metadata_sha256,
        protocol=protocol,
    )
    try:
        envelope = joblib.load(io.BytesIO(candidate_bytes))
    except Exception as exc:
        raise EvaluationContractError("candidate artifact cannot be deserialized") from exc
    try:
        contract = producer.resolve_training_contract()
        validate_canonical_model_envelope(
            envelope,
            artifact_name=producer.CANDIDATE_ARTIFACT_NAME,
            model_type=producer.CANDIDATE_MODEL_TYPE,
            contract=contract,
        )
    except Exception as exc:
        raise EvaluationContractError(
            "candidate envelope does not match the training contract"
        ) from exc
    model = envelope.get("model") if isinstance(envelope, Mapping) else None
    scaler = envelope.get("scaler") if isinstance(envelope, Mapping) else None
    if model is None or scaler is None:
        raise EvaluationContractError("candidate model or preprocessor is missing")
    classes = getattr(model, "classes_", None)
    try:
        class_order = tuple(int(value) for value in classes)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvaluationContractError("candidate model class order is unavailable") from exc
    if class_order != CLASS_ORDER:
        raise EvaluationContractError("candidate model class order is not Away/Draw/Home")
    declared_features = tuple(str(value) for value in getattr(model, "feature_names_in_", ()))
    if declared_features and declared_features != FEATURE_ORDER:
        raise EvaluationContractError("candidate model feature order is invalid")
    if int(getattr(model, "n_features_in_", len(FEATURE_ORDER))) != len(FEATURE_ORDER):
        raise EvaluationContractError("candidate model feature count is invalid")
    if int(getattr(scaler, "n_features_in_", len(FEATURE_ORDER))) != len(FEATURE_ORDER):
        raise EvaluationContractError("candidate preprocessor feature count is invalid")
    # The local variables are intentionally retained only as identity evidence;
    # the paths are not written into the artifact or printed.
    del candidate_file, metadata_file
    return VerifiedCandidate(
        model=model,
        scaler=scaler,
        metadata=metadata,
        artifact_sha256=artifact_sha256,
        metadata_sha256=metadata_sha256,
        feature_names=FEATURE_ORDER,
        class_order=class_order,
    )


@dataclass(frozen=True)
class EvaluationRow:
    """One eligible row's identity, kickoff, and nine frozen feature values."""

    row_id: str
    kickoff_utc: str
    features: tuple[float, ...]


@dataclass(frozen=True)
class _OpaqueOutcome:
    """A label payload that has no outcome accessor before the gate opens."""

    payload: Mapping[str, Any]

    def open(self) -> int:
        # This is the only call site that semantically reads target_label.outcome.
        return producer._normalise_target(self.payload)


@dataclass(frozen=True)
class EvaluationPopulation:
    """Eligible frame rows partitioned into fit and reserved identities."""

    frame_binding: producer.CanonicalFrameBinding
    rows_by_id: dict[str, EvaluationRow]
    labels_by_id: dict[str, _OpaqueOutcome]
    training_ids: tuple[str, ...]
    reserved_ids: tuple[str, ...]

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        """Return the complete eligible ID sequence without touching labels."""
        return tuple(self.rows_by_id)


def _timestamp_text(value: Any, label: str) -> str:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise EvaluationContractError(f"{label} is not a valid timestamp") from exc
    if timestamp.tzinfo is None:
        raise EvaluationContractError(f"{label} has no timezone")
    return timestamp.tz_convert("UTC").isoformat()


def _load_population(  # noqa: C901, PLR0912, PLR0915
    frame_path: str | Path,
    receipt_path: str | Path,
    protocol: Mapping[str, Any],
) -> EvaluationPopulation:
    """Load features and row identity while retaining labels behind an opaque wrapper."""
    frame_file, frame_bytes = _read_external_file(frame_path, "frame artifact")
    receipt_file, receipt_bytes = _read_external_file(receipt_path, "frame receipt")
    if _sha256_bytes(frame_bytes) != protocol["frame"]["artifact_sha256"]:
        raise EvaluationContractError("frame artifact hash mismatch")
    if _sha256_bytes(receipt_bytes) != protocol["frame"]["receipt_sha256"]:
        raise EvaluationContractError("frame receipt hash mismatch")
    receipt = _parse_json(receipt_bytes, "frame receipt")
    if receipt.get("output_business_sha256") != protocol["frame"]["business_sha256"]:
        raise EvaluationContractError("frame business hash mismatch")
    if receipt.get("code_revision") != protocol["frame"]["code_revision"]:
        raise EvaluationContractError("frame code revision mismatch")

    # This existing loader invokes the canonical JS frame contract.  That
    # contract checks label timing/status/provenance but does not read the
    # outcome value.  The Python projection below never calls .get('outcome').
    data = producer.load_canonical_feature_frame(frame_file, receipt_file)
    if data.source_binding is None:
        raise EvaluationContractError("frame source binding is missing")
    frame_binding = data.source_binding
    if frame_binding.artifact_sha256 != protocol["frame"]["artifact_sha256"]:
        raise EvaluationContractError("frame source artifact binding mismatch")
    if frame_binding.receipt_sha256 != protocol["frame"]["receipt_sha256"]:
        raise EvaluationContractError("frame source receipt binding mismatch")
    if frame_binding.business_sha256 != protocol["frame"]["business_sha256"]:
        raise EvaluationContractError("frame source business binding mismatch")
    if frame_binding.frame_code_revision != protocol["frame"]["code_revision"]:
        raise EvaluationContractError("frame source code binding mismatch")
    if (
        data.frame_eligible_rows != FRAME_ELIGIBLE_ROWS
        or data.frame_ineligible_rows != FRAME_INELIGIBLE_ROWS
    ):
        raise EvaluationContractError(
            f"frame eligibility population is not {FRAME_ELIGIBLE_ROWS}/{FRAME_INELIGIBLE_ROWS}"
        )

    labels_by_id: dict[str, _OpaqueOutcome] = {}
    rows_by_id: dict[str, EvaluationRow] = {}
    split_records: list[dict[str, Any]] = []
    for _, row in data.frame.iterrows():
        row_id = str(row["match_id"])
        raw_label = row[producer.DEFAULT_TARGET_COLUMN]
        if not isinstance(raw_label, Mapping):
            raise EvaluationContractError("eligible frame label payload is malformed")
        labels_by_id[row_id] = _OpaqueOutcome(raw_label)
        kickoff_utc = _timestamp_text(row["match_date"], f"{row_id}.kickoff")
        feature_values = tuple(float(row[name]) for name in FEATURE_ORDER)
        if not np.isfinite(np.asarray(feature_values, dtype=float)).all():
            raise EvaluationContractError("frame feature values are non-finite")
        rows_by_id[row_id] = EvaluationRow(row_id, kickoff_utc, feature_values)
        split_record = {
            "match_id": row_id,
            "match_date": kickoff_utc,
            "feature_as_of_utc": _timestamp_text(
                row["feature_as_of_utc"], f"{row_id}.feature_as_of"
            ),
            "result": None,
        }
        split_record.update(dict(zip(FEATURE_ORDER, feature_values, strict=True)))
        split_records.append(split_record)

    if len(rows_by_id) != FRAME_ELIGIBLE_ROWS or len(labels_by_id) != len(rows_by_id):
        raise EvaluationContractError("frame eligible row identity count is invalid")
    split_data = producer.validate_training_frame(
        pd.DataFrame(split_records),
        feature_cutoff_column="feature_as_of_utc",
        validate_target=False,
    )
    split_policy = protocol["population"]["temporal_partition"]
    if split_policy != "chronological_reserved_evaluation_holdout/v1":
        raise EvaluationContractError("unsupported evaluation split policy")
    split = producer.chronological_split(
        split_data,
        validation_fraction=float(protocol["population"]["validation_fraction"]),
        min_train_rows=20,
        min_validation_rows=5,
    )
    training_ids = tuple(str(value) for value in split.train["match_id"].tolist())
    reserved_ids = tuple(str(value) for value in split.validation["match_id"].tolist())
    if len(training_ids) != TRAINING_ROWS or len(reserved_ids) != RESERVED_ROWS:
        raise EvaluationContractError(
            f"chronological split did not produce {TRAINING_ROWS}/{RESERVED_ROWS} rows"
        )
    if set(training_ids).intersection(reserved_ids):
        raise EvaluationContractError("training and reserved rows overlap")
    del frame_file, receipt_file
    return EvaluationPopulation(
        frame_binding=frame_binding,
        rows_by_id=rows_by_id,
        labels_by_id=labels_by_id,
        training_ids=training_ids,
        reserved_ids=reserved_ids,
    )


def validate_population_binding(
    population: EvaluationPopulation, protocol: Mapping[str, Any]
) -> None:
    """Rebuild and compare all row identities before any outcome is opened."""
    expected = protocol["population"]
    eligible_hash = producer._row_id_hash(list(population.eligible_ids))
    training_hash = producer._row_id_hash(list(population.training_ids))
    reserved_hash = producer._row_id_hash(list(population.reserved_ids))
    if training_hash != expected["training_row_id_hash"]:
        raise EvaluationContractError("training row ID binding mismatch")
    if reserved_hash != expected["reserved_evaluation_row_id_hash"]:
        raise EvaluationContractError("reserved row ID binding mismatch")
    if eligible_hash != producer._row_id_hash(
        list(population.training_ids + population.reserved_ids)
    ):
        raise EvaluationContractError(
            "training/reserved rows do not reconstruct eligible population"
        )
    if population.frame_binding.eligible_row_id_sha256 != eligible_hash:
        raise EvaluationContractError("frame eligible row ID binding mismatch")
    if population.frame_binding.eligible_rows != expected["frame_eligible_rows"]:
        raise EvaluationContractError("frame eligible count mismatch")
    if (
        len(population.training_ids) != expected["training_rows"]
        or len(population.reserved_ids) != expected["reserved_evaluation_rows"]
    ):
        raise EvaluationContractError("evaluation row counts mismatch")
    train_dates = [population.rows_by_id[row_id].kickoff_utc for row_id in population.training_ids]
    reserved_dates = [
        population.rows_by_id[row_id].kickoff_utc for row_id in population.reserved_ids
    ]
    if [min(train_dates), max(train_dates)] != expected["train_date_range"]:
        raise EvaluationContractError("training date range mismatch")
    if [min(reserved_dates), max(reserved_dates)] != expected["reserved_date_range"]:
        raise EvaluationContractError("reserved date range mismatch")


class OutcomeAccessGate:
    """One-way gate for the first semantic read of reserved outcomes."""

    def __init__(self, population: EvaluationPopulation):
        self._population = population
        self.protocol_frozen = False
        self.outcomes_opened = False
        self.protocol_sha256: str | None = None
        self.protocol_freeze_sha: str | None = None

    def freeze(self, protocol_sha256_value: str, protocol_freeze_sha: str) -> None:
        """Record the frozen protocol identity before allowing outcome access."""
        if self.outcomes_opened:
            raise EvaluationContractError("protocol cannot be frozen after outcome access")
        _assert_sha256(protocol_sha256_value, "protocol hash")
        _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
        self.protocol_sha256 = protocol_sha256_value
        self.protocol_freeze_sha = protocol_freeze_sha
        self.protocol_frozen = True

    def open_reserved_outcomes(self, opened_at: str) -> np.ndarray:
        """Open exactly the reserved labels once, after the freeze marker exists."""
        if not self.protocol_frozen:
            raise EvaluationContractError("reserved outcomes are forbidden before protocol freeze")
        if self.outcomes_opened:
            raise EvaluationContractError(
                "reserved outcomes may only be opened once per evaluation"
            )
        _parse_opened_at(opened_at)
        labels: list[int] = []
        for row_id in self._population.reserved_ids:
            label = self._population.labels_by_id.get(row_id)
            if label is None:
                raise EvaluationContractError("reserved row label binding is missing")
            labels.append(label.open())
        self.outcomes_opened = True
        return np.asarray(labels, dtype=int)


@dataclass
class PreparedEvaluation:
    """Prepared candidate and population state awaiting the one-way outcome gate."""

    protocol: dict[str, Any]
    protocol_sha256: str
    candidate: VerifiedCandidate
    population: EvaluationPopulation
    gate: OutcomeAccessGate
    source_head: str | None = None
    protocol_freeze_sha: str | None = None
    probabilities: np.ndarray[Any, Any] | None = None
    opened_at: str | None = None

    def freeze_protocol(self, *, source_head: str, protocol_freeze_sha: str) -> None:
        """Bind the evaluation source HEAD and protocol freeze SHA."""
        _assert_git_sha(source_head, "evaluation source HEAD")
        _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
        self.source_head = source_head
        self.protocol_freeze_sha = protocol_freeze_sha
        self.gate.freeze(self.protocol_sha256, protocol_freeze_sha)

    def infer_reserved(self) -> np.ndarray[Any, Any]:
        """Run candidate inference without reading any outcome value."""
        if not self.gate.protocol_frozen:
            raise EvaluationContractError("protocol must be frozen before inference")
        matrix = np.asarray(
            [
                self.population.rows_by_id[row_id].features
                for row_id in self.population.reserved_ids
            ],
            dtype=float,
        )
        try:
            transformed = self.candidate.scaler.transform(matrix)
            probabilities = np.asarray(self.candidate.model.predict_proba(transformed), dtype=float)
        except Exception as exc:
            raise EvaluationContractError("candidate probability inference failed") from exc
        validate_probability_matrix(probabilities, expected_rows=len(self.population.reserved_ids))
        self.probabilities = probabilities
        return probabilities.copy()

    def open_outcomes(self, opened_at: str) -> np.ndarray[Any, Any]:
        """Open outcomes only after inference has completed."""
        if self.probabilities is None:
            raise EvaluationContractError("candidate inference must complete before outcome access")
        self.opened_at = opened_at
        return self.gate.open_reserved_outcomes(opened_at)


def prepare_evaluation(
    *,
    candidate_path: str | Path,
    metadata_path: str | Path,
    frame_path: str | Path,
    receipt_path: str | Path,
    protocol_path: str | Path,
) -> PreparedEvaluation:
    """Prepare all identity evidence without opening a reserved outcome."""
    protocol, protocol_hash, _ = load_protocol(protocol_path)
    candidate = load_verified_candidate(candidate_path, metadata_path, protocol)
    population = _load_population(frame_path, receipt_path, protocol)
    validate_population_binding(population, protocol)
    return PreparedEvaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=candidate,
        population=population,
        gate=OutcomeAccessGate(population),
    )


def validate_probability_matrix(
    probabilities: np.ndarray[Any, Any], *, expected_rows: int | None = None
) -> None:
    """Fail closed on finite, range-valid, row-normalized multiclass output."""
    if probabilities.ndim != PROBABILITY_MATRIX_DIMENSIONS or probabilities.shape[1] != CLASS_COUNT:
        raise EvaluationContractError("probability matrix shape is invalid")
    if expected_rows is not None and probabilities.shape[0] != expected_rows:
        raise EvaluationContractError("probability row count is invalid")
    if not np.isfinite(probabilities).all():
        raise EvaluationContractError("probability matrix contains non-finite values")
    if float(probabilities.min()) < 0.0 or float(probabilities.max()) > 1.0:
        raise EvaluationContractError("probability matrix is outside [0,1]")
    row_sums = probabilities.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=PROBABILITY_SUM_ATOL, rtol=0.0):
        raise EvaluationContractError("probability rows do not sum to one")


def _validate_labels(labels: np.ndarray[Any, Any], expected_rows: int) -> None:
    if labels.ndim != 1 or len(labels) != expected_rows or not np.isin(labels, CLASS_ORDER).all():
        raise EvaluationContractError("opened outcome labels are invalid")


def _per_row_log_loss(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    clipped = np.clip(probabilities, LOG_LOSS_EPSILON, 1.0)
    return -np.log(clipped[np.arange(len(labels)), labels])


def _per_row_brier(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    one_hot = np.eye(len(CLASS_ORDER), dtype=float)[labels]
    return np.sum((probabilities - one_hot) ** 2, axis=1)


def metric_bundle(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> dict[str, float]:
    """Compute the frozen primary and secondary metrics."""
    validate_probability_matrix(probabilities, expected_rows=len(labels))
    _validate_labels(labels, len(probabilities))
    predictions = np.argmax(probabilities, axis=1)
    return {
        "multiclass_log_loss": float(np.mean(_per_row_log_loss(probabilities, labels))),
        "multiclass_brier_score": float(np.mean(_per_row_brier(probabilities, labels))),
        "accuracy": float(np.mean(predictions == labels)),
    }


def _class_distribution(values: np.ndarray[Any, Any]) -> dict[str, int]:
    return {
        name: int(np.sum(values == class_index)) for class_index, name in enumerate(CLASS_NAMES)
    }


def _confusion_matrix(
    labels: np.ndarray[Any, Any], predictions: np.ndarray[Any, Any]
) -> list[list[int]]:
    matrix = np.zeros((len(CLASS_ORDER), len(CLASS_ORDER)), dtype=int)
    for actual, predicted in zip(labels, predictions, strict=True):
        matrix[int(actual), int(predicted)] += 1
    return matrix.tolist()


def _per_class_metrics(
    labels: np.ndarray[Any, Any], predictions: np.ndarray[Any, Any]
) -> dict[str, dict[str, Any]]:
    matrix = np.asarray(_confusion_matrix(labels, predictions), dtype=int)
    result: dict[str, dict[str, Any]] = {}
    for class_index, name in enumerate(CLASS_NAMES):
        true_positive = int(matrix[class_index, class_index])
        support = int(matrix[class_index, :].sum())
        predicted_count = int(matrix[:, class_index].sum())
        recall = true_positive / support if support else None
        precision = true_positive / predicted_count if predicted_count else None
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        result[name] = {
            "support": support,
            "predicted_count": predicted_count,
            "recall": _round_number(recall),
            "precision": _round_number(precision),
            "f1": _round_number(f1),
        }
    return result


def _round_number(value: float | None) -> float | None:
    return None if value is None else round(float(value), 12)


def _calibration_summary(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    edges = tuple(float(value) for value in protocol["calibration"]["bin_edges"])
    minimum_count = int(protocol["calibration"]["minimum_nonempty_bin_count"])
    classwise: dict[str, list[dict[str, Any]]] = {}
    nonempty_counts: list[int] = []
    pooled_abs_gap_numerator = 0.0
    pooled_count = 0
    for class_index, class_name in enumerate(CLASS_NAMES):
        values = probabilities[:, class_index]
        actual = (labels == class_index).astype(float)
        bins: list[dict[str, Any]] = []
        for index in range(len(edges) - 1):
            low, high = edges[index], edges[index + 1]
            mask = (values >= low) & ((values <= high) if high == 1.0 else (values < high))
            count = int(np.sum(mask))
            entry: dict[str, Any] = {"bin": [low, high], "count": count}
            if count:
                predicted_mean = float(np.mean(values[mask]))
                observed_frequency = float(np.mean(actual[mask]))
                absolute_gap = abs(predicted_mean - observed_frequency)
                entry.update(
                    {
                        "predicted_mean": _round_number(predicted_mean),
                        "observed_frequency": _round_number(observed_frequency),
                        "absolute_gap": _round_number(absolute_gap),
                    }
                )
                nonempty_counts.append(count)
                pooled_abs_gap_numerator += absolute_gap * count
                pooled_count += count
            bins.append(entry)
        classwise[class_name] = bins
    minimum_nonempty = min(nonempty_counts) if nonempty_counts else 0
    status = "INSUFFICIENT_SAMPLE" if minimum_nonempty < minimum_count else "DESCRIPTIVE_ONLY"
    return {
        "method": "fixed_probability_bins",
        "bin_edges": list(edges),
        "minimum_nonempty_bin_count": minimum_count,
        "sample_status": status,
        "minimum_observed_nonempty_bin_count": minimum_nonempty,
        "overall": {
            "pooled_probability_class_cells": pooled_count,
            "weighted_mean_absolute_gap": _round_number(
                pooled_abs_gap_numerator / pooled_count if pooled_count else None
            ),
        },
        "classwise": classwise,
    }


def _bootstrap_intervals(
    candidate_probabilities: np.ndarray[Any, Any],
    prior_probabilities: np.ndarray[Any, Any],
    labels: np.ndarray[Any, Any],
    majority_class: int,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    resamples = int(protocol["uncertainty"]["resamples"])
    seed = int(protocol["uncertainty"]["seed"])
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(labels), size=(resamples, len(labels)))
    candidate_ll = _per_row_log_loss(candidate_probabilities, labels)
    prior_ll = _per_row_log_loss(prior_probabilities, labels)
    candidate_brier = _per_row_brier(candidate_probabilities, labels)
    prior_brier = _per_row_brier(prior_probabilities, labels)
    candidate_predictions = np.argmax(candidate_probabilities, axis=1)
    candidate_delta_ll = np.mean((candidate_ll - prior_ll)[indices], axis=1)
    candidate_delta_brier = np.mean((candidate_brier - prior_brier)[indices], axis=1)
    accuracy_delta = np.mean((candidate_predictions[indices] == labels[indices]), axis=1) - np.mean(
        labels[indices] == majority_class, axis=1
    )

    def interval(values: np.ndarray[Any, Any]) -> dict[str, Any]:
        lower, upper = np.percentile(values, [2.5, 97.5], method="linear")
        return {
            "lower": _round_number(float(lower)),
            "upper": _round_number(float(upper)),
            "confidence_level": BOOTSTRAP_CONFIDENCE_LEVEL,
            "method": "percentile",
            "resamples": resamples,
            "seed": seed,
        }

    return {
        "log_loss_delta": interval(candidate_delta_ll),
        "brier_delta": interval(candidate_delta_brier),
        "accuracy_delta": interval(accuracy_delta),
    }


def _class_prior_from_metadata(metadata: Mapping[str, Any]) -> np.ndarray[Any, Any]:
    distribution = metadata.get("provenance", {}).get("train_class_distribution")
    if distribution != TRAINING_CLASS_DISTRIBUTION:
        raise EvaluationContractError("training class prior provenance is invalid")
    counts = np.asarray(TRAINING_CLASS_COUNTS, dtype=float)
    if counts.sum() != TRAINING_ROWS:
        raise EvaluationContractError("training class prior count is invalid")
    return counts / counts.sum()


def build_baselines(
    candidate: VerifiedCandidate,
    labels: np.ndarray[Any, Any],
) -> tuple[dict[str, Any], np.ndarray[Any, Any], np.ndarray[Any, Any], int]:
    """Build constant baselines solely from the candidate's 436-row metadata."""
    prior = _class_prior_from_metadata(candidate.metadata)
    prior_probabilities = np.tile(prior, (len(labels), 1))
    majority_class = int(np.argmax(prior))
    majority_probabilities = np.eye(len(CLASS_ORDER), dtype=float)[majority_class]
    majority_matrix = np.tile(majority_probabilities, (len(labels), 1))
    return (
        {
            "training_class_prior": {
                "definition": "constant HOME/DRAW/AWAY probability vector from training rows only",
                "source": "candidate_metadata.provenance.train_class_distribution",
                "counts": dict(zip(CLASS_NAMES, TRAINING_CLASS_COUNTS, strict=True)),
                "probabilities": {
                    column: _round_number(float(value))
                    for column, value in zip(PROBABILITY_COLUMN_ORDER, prior, strict=True)
                },
            },
            "training_majority_class": {
                "definition": "constant argmax class from training rows only",
                "source": "candidate_metadata.provenance.train_class_distribution",
                "class_index": majority_class,
                "class_name": CLASS_NAMES[majority_class],
            },
        },
        prior_probabilities,
        majority_matrix,
        majority_class,
    )


def _quality_status(
    deltas: Mapping[str, float],
    intervals: Mapping[str, Mapping[str, Any]],
    calibration: Mapping[str, Any],
) -> str:
    log_loss_delta = float(deltas["log_loss_delta_vs_prior"])
    brier_delta = float(deltas["brier_delta_vs_prior"])
    accuracy_delta = float(deltas["accuracy_delta_vs_majority"])
    log_interval = intervals["log_loss_delta"]
    brier_interval = intervals["brier_delta"]
    clearly_adverse = float(log_interval["lower"]) > 0 and float(brier_interval["lower"]) > 0
    clearly_misaligned = (
        calibration.get("sample_status") == "DESCRIPTIVE_ONLY"
        and float(calibration["overall"]["weighted_mean_absolute_gap"] or 0.0)
        > CLEARLY_MISALIGNED_CALIBRATION_GAP
    )
    if log_loss_delta < 0 and brier_delta < 0 and accuracy_delta >= 0 and not clearly_misaligned:
        return "MIXED" if clearly_adverse else "PROMISING"
    if log_loss_delta > 0 and brier_delta > 0:
        return "CLEARLY_UNDERPERFORMING" if clearly_adverse else "WEAK"
    return "MIXED"


def build_evaluation_artifact(
    prepared: PreparedEvaluation,
    labels: np.ndarray[Any, Any],
) -> dict[str, Any]:
    """Build the deterministic, row-bound research evidence after outcome access."""
    if not prepared.gate.protocol_frozen or not prepared.gate.outcomes_opened:
        raise EvaluationContractError(
            "evaluation artifact requires frozen protocol and opened outcomes"
        )
    if prepared.probabilities is None or prepared.opened_at is None:
        raise EvaluationContractError("evaluation inference evidence is incomplete")
    _validate_labels(labels, len(prepared.population.reserved_ids))
    candidate_probabilities = prepared.probabilities
    prior_definition, prior_probabilities, majority_probabilities, majority_class = build_baselines(
        prepared.candidate, labels
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
    baseline_metrics = {
        "training_class_prior": prior_metrics,
        "training_majority_class": majority_metrics,
    }
    prediction_rows = []
    for index, row_id in enumerate(prepared.population.reserved_ids):
        row = prepared.population.rows_by_id[row_id]
        prediction_rows.append(
            {
                "row_id": row_id,
                "kickoff_utc": row.kickoff_utc,
                "actual_class": int(labels[index]),
                "actual_class_name": CLASS_NAMES[int(labels[index])],
                "predicted_class": int(predictions[index]),
                "predicted_class_name": CLASS_NAMES[int(predictions[index])],
                "probabilities": {
                    column: _round_number(float(candidate_probabilities[index, class_index]))
                    for class_index, column in enumerate(PROBABILITY_COLUMN_ORDER)
                },
            }
        )
    actual_distribution = _class_distribution(labels)
    predicted_distribution = _class_distribution(predictions)
    entropy = -np.sum(
        np.clip(candidate_probabilities, LOG_LOSS_EPSILON, 1.0)
        * np.log(np.clip(candidate_probabilities, LOG_LOSS_EPSILON, 1.0)),
        axis=1,
    )
    confidence = np.max(candidate_probabilities, axis=1)
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "evaluation_id": EVALUATION_ID,
        "evaluation_protocol_version": PROTOCOL_SCHEMA_VERSION,
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
                "row_sum_atol": PROBABILITY_SUM_ATOL,
                "max_row_sum_abs_error": _round_number(
                    float(np.max(np.abs(candidate_probabilities.sum(axis=1) - 1.0)))
                ),
            },
            "predicted_class_distribution": predicted_distribution,
            "actual_class_distribution": actual_distribution,
            "mean_predicted_probability_by_class": {
                column: _round_number(float(np.mean(candidate_probabilities[:, index])))
                for index, column in enumerate(PROBABILITY_COLUMN_ORDER)
            },
            "entropy_summary": {
                "mean": _round_number(float(np.mean(entropy))),
                "min": _round_number(float(np.min(entropy))),
                "max": _round_number(float(np.max(entropy))),
            },
            "confidence_summary": {
                "mean_max_probability": _round_number(float(np.mean(confidence))),
                "min_max_probability": _round_number(float(np.min(confidence))),
                "max_max_probability": _round_number(float(np.max(confidence))),
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
        "baseline_definitions": prior_definition,
        "baseline_metrics": baseline_metrics,
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


def _parse_opened_at(value: str) -> datetime:
    if not isinstance(value, str):
        raise EvaluationContractError("outcome-open timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvaluationContractError("outcome-open timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise EvaluationContractError("outcome-open timestamp must include timezone")
    return parsed.astimezone(UTC)


def build_evaluation_receipt(
    artifact: Mapping[str, Any],
    artifact_bytes: bytes,
    *,
    protocol_freeze_sha: str,
    evaluation_source_head: str,
) -> dict[str, Any]:
    """Build a hash-bound receipt with no model bytes or raw source payload."""
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
    """Write one repository-external artifact and receipt without touching manifest state."""
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


def current_git_head(repository_root: Path | None = None) -> str:
    """Return the full source HEAD used to execute the evaluation."""
    root = repository_root or _repository_root()
    try:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvaluationContractError("evaluation source HEAD is unavailable") from exc
    return _assert_git_sha(value, "evaluation source HEAD")


def assert_clean_worktree(repository_root: Path | None = None) -> None:
    root = repository_root or _repository_root()
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "-uno"], cwd=root, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvaluationContractError("evaluation worktree status is unavailable") from exc
    if status:
        raise EvaluationContractError("evaluation source worktree is dirty")


def run_evaluation(
    *,
    candidate_path: str | Path,
    metadata_path: str | Path,
    frame_path: str | Path,
    receipt_path: str | Path,
    protocol_path: str | Path,
    source_head: str,
    protocol_freeze_sha: str,
    outcome_opened_at: str,
) -> dict[str, Any]:
    """Execute the exact one-way evaluation sequence and return its artifact payload."""
    prepared = prepare_evaluation(
        candidate_path=candidate_path,
        metadata_path=metadata_path,
        frame_path=frame_path,
        receipt_path=receipt_path,
        protocol_path=protocol_path,
    )
    prepared.freeze_protocol(source_head=source_head, protocol_freeze_sha=protocol_freeze_sha)
    prepared.infer_reserved()
    labels = prepared.open_outcomes(outcome_opened_at)
    return build_evaluation_artifact(prepared, labels)


__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "CALIBRATION_BIN_EDGES",
    "CLASS_NAMES",
    "CLASS_ORDER",
    "EVALUATION_ID",
    "PROBABILITY_COLUMN_ORDER",
    "RESERVED_STATUS_AFTER",
    "RESERVED_STATUS_BEFORE",
    "EvaluationContractError",
    "EvaluationPopulation",
    "OutcomeAccessGate",
    "PreparedEvaluation",
    "build_baselines",
    "build_evaluation_artifact",
    "build_evaluation_receipt",
    "current_git_head",
    "load_protocol",
    "load_verified_candidate",
    "metric_bundle",
    "prepare_evaluation",
    "protocol_sha256",
    "run_evaluation",
    "validate_candidate_metadata_binding",
    "validate_population_binding",
    "validate_probability_matrix",
    "validate_protocol",
    "write_evaluation_outputs",
]
