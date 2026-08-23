"""Frozen identities and pre-outcome validation for canonical offline evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
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
# XGBoost emits float32 probabilities; retain the values and accept only the
# corresponding accumulation error when checking row normalization.
PROBABILITY_SUM_ATOL = 1e-6
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

# This object is deliberately private.  Keeping it in the contract module lets
# the gate authorize the only label accessor without exposing a public payload
# or a callable that can be used to bypass the gate.
_OUTCOME_ACCESS_TOKEN = object()


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
    ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
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
    baselines = protocol["baselines"]
    calibration = protocol["calibration"]
    uncertainty = protocol["uncertainty"]
    acceptance_rules = protocol["acceptance_rules"]
    if not all(
        isinstance(value, Mapping)
        for value in (
            candidate,
            frame,
            population,
            feature_contract,
            model_output,
            metrics,
            baselines,
            calibration,
            uncertainty,
            acceptance_rules,
        )
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
    expected_population: dict[str, Any] = {
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
    if model_output.get("probability_source") != "candidate.model.predict_proba":
        raise EvaluationContractError("protocol probability source is invalid")
    if tuple(model_output.get("class_order", ())) != CLASS_ORDER:
        raise EvaluationContractError("protocol model class order is invalid")
    if tuple(model_output.get("class_names", ())) != CLASS_NAMES:
        raise EvaluationContractError("protocol model class names are invalid")
    if tuple(model_output.get("probability_column_order", ())) != PROBABILITY_COLUMN_ORDER:
        raise EvaluationContractError("protocol probability column order is invalid")
    sanity = model_output.get("sanity")
    if sanity != {"finite": True, "range": "[0,1]", "row_sum_atol": PROBABILITY_SUM_ATOL}:
        raise EvaluationContractError("protocol probability sanity rules are invalid")
    if metrics.get("primary_metric") != "multiclass_log_loss":
        raise EvaluationContractError("primary metric must be multiclass_log_loss")
    if tuple(metrics.get("secondary_metrics", ())) != (
        "multiclass_brier_score",
        "accuracy",
        "per_class_diagnostics",
        "confusion_matrix",
        "calibration_diagnostics",
    ):
        raise EvaluationContractError("secondary metric contract is invalid")
    if metrics.get("log_loss_definition") != "mean(-log(max(P(actual), 1e-15)))":
        raise EvaluationContractError("log-loss definition is invalid")
    if metrics.get("log_loss_epsilon") != LOG_LOSS_EPSILON:
        raise EvaluationContractError("log-loss epsilon is not frozen")
    if metrics.get("brier_definition") != "mean(sum_k((P_k - one_hot_k)^2))":
        raise EvaluationContractError("Brier definition is invalid")
    if metrics.get("accuracy_definition") != "mean(argmax(P) == actual_class)":
        raise EvaluationContractError("accuracy definition is invalid")
    if metrics.get("direction") != {
        "multiclass_log_loss": "lower_is_better",
        "multiclass_brier_score": "lower_is_better",
        "accuracy": "higher_is_better",
    }:
        raise EvaluationContractError("metric directions are invalid")
    if baselines != {
        "training_class_prior": {
            "definition": "constant probability vector from 436 training rows only",
            "counts": TRAINING_CLASS_DISTRIBUTION,
            "probability_order": list(PROBABILITY_COLUMN_ORDER),
        },
        "training_majority_class": {
            "definition": "constant argmax class from 436 training rows only",
            "class": "HOME",
            "class_index": 2,
        },
        "reserved_outcomes_may_enter_baseline": False,
        "bookmaker_odds_baseline": False,
    }:
        raise EvaluationContractError("baseline definitions are not frozen")
    if tuple(calibration.get("bin_edges", ())) != CALIBRATION_BIN_EDGES:
        raise EvaluationContractError("calibration binning is not frozen")
    if calibration.get("minimum_nonempty_bin_count") != CALIBRATION_MIN_NONEMPTY_BIN_COUNT:
        raise EvaluationContractError("calibration minimum count is not frozen")
    if calibration.get("method") != "fixed_probability_bins":
        raise EvaluationContractError("calibration method is not frozen")
    if calibration.get("report") != (
        "class-wise counts, predicted mean, observed frequency, absolute gap, and pooled weighted gap"
    ):
        raise EvaluationContractError("calibration report is not frozen")
    if calibration.get("interpretation") != (
        "descriptive_only; mark INSUFFICIENT_SAMPLE when any occupied cell is below the minimum count"
    ):
        raise EvaluationContractError("calibration interpretation is not frozen")
    if uncertainty.get("method") != "deterministic_percentile_bootstrap":
        raise EvaluationContractError("uncertainty method is not frozen")
    if (
        uncertainty.get("resamples") != BOOTSTRAP_RESAMPLES
        or uncertainty.get("seed") != BOOTSTRAP_SEED
    ):
        raise EvaluationContractError("bootstrap identity is not frozen")
    if uncertainty.get("confidence_level") != BOOTSTRAP_CONFIDENCE_LEVEL:
        raise EvaluationContractError("bootstrap confidence level is not frozen")
    if uncertainty.get("resample_unit") != "reserved_row_with_replacement":
        raise EvaluationContractError("bootstrap resampling unit is not frozen")
    if uncertainty.get("interval") != "linear_percentile":
        raise EvaluationContractError("bootstrap interval rule is not frozen")
    if uncertainty.get("comparisons") != [
        "candidate_log_loss_minus_training_prior_log_loss",
        "candidate_brier_minus_training_prior_brier",
        "candidate_accuracy_minus_training_majority_accuracy",
    ]:
        raise EvaluationContractError("bootstrap comparisons are not frozen")
    if uncertainty.get("claim_boundary") != (
        "uncertainty estimate only; not a proof of generalization or profitability"
    ):
        raise EvaluationContractError("bootstrap claim boundary is not frozen")

    if acceptance_rules.get("quality_status_vocabulary") != [
        "PROMISING",
        "MIXED",
        "WEAK",
        "CLEARLY_UNDERPERFORMING",
    ]:
        raise EvaluationContractError("quality status vocabulary is not frozen")
    for field in (
        "model_quality_proven",
        "profitability_proven",
        "production_ready",
        "model_selected",
    ):
        if acceptance_rules.get(field) is not False:
            raise EvaluationContractError(f"acceptance claim boundary is invalid: {field}")
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
    canonical_path = (
        _repository_root() / "config" / "canonical_offline_model_evaluation_protocol.json"
    ).resolve()
    if path.resolve() != canonical_path:
        raise EvaluationContractError(
            "evaluation protocol must be the checked-in canonical protocol"
        )
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
    exact = {
        "candidate_id": candidate["candidate_id"],
        "model_family": "xgboost_multiclass_1x2",
        "model_version": "canonical-prematch-vnext-xgb/v1",
        "code_revision": candidate["source_revision"],
        "feature_contract_id": "canonical_prematch/vnext-v1",
        "feature_contract_version": "canonical_prematch/vnext/v1",
        "feature_names": list(FEATURE_ORDER),
        "feature_order": list(FEATURE_ORDER),
        "training_frame_artifact_hash": EXPECTED_FRAME_ARTIFACT_SHA256,
        "training_frame_receipt_hash": EXPECTED_FRAME_RECEIPT_SHA256,
        "training_row_count": TRAINING_ROWS,
        "training_row_id_hash": EXPECTED_TRAINING_ROW_ID_SHA256,
        "reserved_evaluation_row_count": RESERVED_ROWS,
        "reserved_evaluation_row_id_hash": EXPECTED_RESERVED_ROW_ID_SHA256,
        "preprocessor_identity": "sklearn.StandardScaler/v1",
        "preprocessor_fit_population": "training_partition_only",
        "random_seed": 42,
        "model_artifact_sha256": artifact_sha256,
        "created_as": "NON_PRODUCTION_CANDIDATE",
        "activated": "NO",
    }
    for field, expected in exact.items():
        _metadata_value(metadata, field, expected)
    if metadata_sha256 != candidate["metadata_sha256"]:
        raise EvaluationContractError("candidate metadata file hash mismatch")
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
    if metadata.get("hyperparameters") != expected_hyperparameters:
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
        """Return non-sensitive identity fields for the evidence artifact."""
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
    candidate_path: str | Path, metadata_path: str | Path, protocol: Mapping[str, Any]
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
    if classes is None:
        raise EvaluationContractError("candidate model class order is unavailable")
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
    del candidate_file, metadata_file
    return VerifiedCandidate(
        model, scaler, metadata, artifact_sha256, metadata_sha256, FEATURE_ORDER, class_order
    )


@dataclass(frozen=True)
class EvaluationRow:
    """One eligible row's identity, kickoff, and nine frozen feature values."""

    row_id: str
    kickoff_utc: str
    features: tuple[float, ...]


class _OpaqueOutcome:
    """A label payload whose only accessor requires the private gate token."""

    __slots__ = ("__open",)

    def __init__(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise EvaluationContractError("opaque outcome payload is malformed")

        def open_payload(token: object) -> int:
            if token is not _OUTCOME_ACCESS_TOKEN:
                raise EvaluationContractError(
                    "reserved outcome access requires the evaluation gate"
                )
            # This is the only call site that semantically reads target_label.outcome.
            return producer._normalise_target(payload)

        self.__open = open_payload

    def open(self, token: object) -> int:
        if token is not _OUTCOME_ACCESS_TOKEN:
            raise EvaluationContractError("reserved outcome access requires the evaluation gate")
        return self.__open(token)


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
        """Return eligible row IDs without touching target outcomes."""
        return tuple(self.rows_by_id)


def _timestamp_text(value: Any, label: str) -> str:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise EvaluationContractError(f"{label} is not a valid timestamp") from exc
    if timestamp.tzinfo is None:
        raise EvaluationContractError(f"{label} has no timezone")
    return str(timestamp.tz_convert("UTC").isoformat())


def _load_population(  # noqa: C901, PLR0912
    frame_path: str | Path, receipt_path: str | Path, protocol: Mapping[str, Any]
) -> EvaluationPopulation:
    """Load row identity and features while retaining labels behind an opaque wrapper."""
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
    data = producer.load_canonical_feature_frame(frame_file, receipt_file)
    if data.source_binding is None:
        raise EvaluationContractError("frame source binding is missing")
    binding = data.source_binding
    for field, expected in {
        "artifact_sha256": protocol["frame"]["artifact_sha256"],
        "receipt_sha256": protocol["frame"]["receipt_sha256"],
        "business_sha256": protocol["frame"]["business_sha256"],
        "frame_code_revision": protocol["frame"]["code_revision"],
    }.items():
        if getattr(binding, field) != expected:
            raise EvaluationContractError(f"frame source {field} binding mismatch")
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
        record: dict[str, Any] = {
            "match_id": row_id,
            "match_date": kickoff_utc,
            "feature_as_of_utc": _timestamp_text(
                row["feature_as_of_utc"], f"{row_id}.feature_as_of"
            ),
            "result": None,
        }
        feature_mapping: dict[str, float] = dict(
            zip([str(name) for name in FEATURE_ORDER], feature_values, strict=True)
        )
        record.update(feature_mapping)
        split_records.append(record)
    if len(rows_by_id) != FRAME_ELIGIBLE_ROWS or len(labels_by_id) != len(rows_by_id):
        raise EvaluationContractError("frame eligible row identity count is invalid")
    split_data = producer.validate_training_frame(
        pd.DataFrame(split_records),
        feature_cutoff_column="feature_as_of_utc",
        validate_target=False,
    )
    if (
        protocol["population"]["temporal_partition"]
        != "chronological_reserved_evaluation_holdout/v1"
    ):
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
    return EvaluationPopulation(binding, rows_by_id, labels_by_id, training_ids, reserved_ids)


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
    if [min(train_dates), max(train_dates)] != expected["train_date_range"] or [
        min(reserved_dates),
        max(reserved_dates),
    ] != expected["reserved_date_range"]:
        raise EvaluationContractError("evaluation date range mismatch")


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
