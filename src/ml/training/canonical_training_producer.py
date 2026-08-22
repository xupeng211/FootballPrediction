"""Canonical prematch vnext offline candidate training producer.

lifecycle: permanent
component: Canonical

The producer consumes an explicit, already materialized pre-match feature
frame. It does not connect to PostgreSQL, fetch live data, discover model
files, or edit the tracked manifest. Feature identity and order come from the
versioned vnext registry projection; the production V1 runtime adapter is not
used as a compatibility fallback.

The output is a candidate envelope for review. A candidate path is required
explicitly and production paths are rejected. Activation and manifest updates
remain separate reviewed operations.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from src.constants.model_config import RESULT_MAP, RESULT_NAMES
from src.ml.feature_adapter import FeatureAdapterFactory, ModelType, V26_6_PreMatchAdapter
from src.ml.inference.canonical_model_loader import (
    CANONICAL_API_ARTIFACT_NAME,
    CANONICAL_API_MODEL_TYPE,
    validate_canonical_model_envelope,
)
from src.ml.inference.feature_contract_registry import (
    VNEXT_CONTRACT_ID,
    FeatureContract,
    FeatureContractRegistry,
)
from src.ml.training import canonical_candidate_artifact, canonical_frame_input

logger = logging.getLogger(__name__)

PRODUCER_SCHEMA_VERSION = "canonical-training-producer/v2"
CANDIDATE_SCHEMA_VERSION = "canonical-training-candidate/v1"
CANDIDATE_CREATED_AS = "NON_PRODUCTION_CANDIDATE"
CANDIDATE_ACTIVATED = "NO"
CANDIDATE_ARTIFACT_NAME = "canonical_prematch_vnext"
CANDIDATE_MODEL_TYPE = "canonical_prematch_vnext"
CANDIDATE_MODEL_FAMILY = "xgboost_multiclass_1x2"
CANDIDATE_MODEL_VERSION = "canonical-prematch-vnext-xgb/v1"
FRAME_SCHEMA_VERSION = "canonical-prematch-training-feature-frame/v1"
FRAME_RECEIPT_SCHEMA_VERSION = "canonical-prematch-training-feature-frame-receipt/v1"
DEFAULT_SEED = 42
DEFAULT_VALIDATION_FRACTION = 0.2
DEFAULT_MIN_TRAIN_ROWS = 20
DEFAULT_MIN_VALIDATION_ROWS = 5
DEFAULT_ESTIMATORS = 32
DEFAULT_MAX_DEPTH = 3
DEFAULT_LEARNING_RATE = 0.05
DEFAULT_TIMESTAMP_COLUMN = "match_date"
DEFAULT_TARGET_COLUMN = "result"
DEFAULT_CLASS_ORDER = tuple(sorted(RESULT_MAP.values()))
GIT_SHA_LENGTH = 40
SHA256_LENGTH = 64

ACCEPTED_TRAINING_FEATURES = (
    "rolling_xg_home",
    "rolling_xg_away",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
)

# These markers only apply to non-contract input columns. The canonical
# features themselves are allowed to contain ``rolling_*`` and ``*_fatigue``
# names; an extra raw/current-match signal is rejected instead of ignored.
_UNSAFE_EXTRA_MARKERS = (
    "home_score",
    "away_score",
    "final_score",
    "full_time",
    "postmatch",
    "post_match",
    "tactical",
    "current_match",
    "winner",
    "outcome",
    "home_xg",
    "away_xg",
    "home_possession",
    "away_possession",
    "home_shots",
    "away_shots",
    "home_corners",
    "away_corners",
    "home_yellow",
    "away_yellow",
    "home_red",
    "away_red",
    "future_",
)


class TrainingContractError(ValueError):
    """Raised when a training input cannot be proven canonical and safe."""


@dataclass(frozen=True)
class CanonicalFrameBinding:
    """Hashes and population facts copied from one validated frame/receipt."""

    artifact_sha256: str
    receipt_sha256: str
    business_sha256: str
    contract_id: str
    contract_version: str
    feature_names: tuple[str, ...]
    target_population: int
    rows_accounted: int
    eligible_rows: int
    ineligible_rows: int
    target_row_id_sha256: str
    eligible_row_id_sha256: str
    frame_code_revision: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe, path-free binding projection."""
        return {
            "artifact_sha256": self.artifact_sha256,
            "receipt_sha256": self.receipt_sha256,
            "business_sha256": self.business_sha256,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "feature_names": list(self.feature_names),
            "target_population": self.target_population,
            "rows_accounted": self.rows_accounted,
            "eligible_rows": self.eligible_rows,
            "ineligible_rows": self.ineligible_rows,
            "target_row_id_sha256": self.target_row_id_sha256,
            "eligible_row_id_sha256": self.eligible_row_id_sha256,
            "frame_code_revision": self.frame_code_revision,
        }


@dataclass(frozen=True)
class ValidatedTrainingData:
    """Validated input frame and the exact contract that authorized it."""

    frame: pd.DataFrame
    contract: FeatureContract
    timestamp_column: str
    target_column: str
    feature_cutoff_column: str | None
    timestamps: pd.Series
    source_binding: CanonicalFrameBinding | None = None
    frame_eligible_rows: int | None = None
    frame_ineligible_rows: int | None = None


@dataclass(frozen=True)
class TemporalSplit:
    """Non-overlapping chronological fit and reserved-evaluation partitions."""

    train: pd.DataFrame
    validation: pd.DataFrame
    train_timestamps: pd.Series
    validation_timestamps: pd.Series
    timestamp_column: str
    target_column: str
    feature_names: tuple[str, ...]
    validation_fraction: float


@dataclass(frozen=True)
class FittedCanonicalModel:
    """Estimator and preprocessor fitted using only the train partition."""

    model: Any
    scaler: StandardScaler
    class_order: tuple[int, ...]


@dataclass(frozen=True)
class CandidateArtifact:
    """Safe candidate output and its whole-file checksum."""

    path: Path
    sha256: str
    provenance: dict[str, Any]
    metadata_path: Path | None = None
    metadata_sha256: str | None = None


def resolve_canonical_contract(
    registry: FeatureContractRegistry | None = None,
) -> FeatureContract:
    """Resolve one exact API contract and prove runtime feature-order parity."""
    contract_registry = registry or FeatureContractRegistry()
    try:
        contract = contract_registry.get_for_model(
            CANONICAL_API_MODEL_TYPE,
            artifact_name=CANONICAL_API_ARTIFACT_NAME,
        )
        runtime_adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)
    except (ValueError, TypeError) as exc:
        raise TrainingContractError("canonical feature contract unavailable") from exc

    if type(runtime_adapter) is not V26_6_PreMatchAdapter:
        raise TrainingContractError("canonical runtime adapter binding is unexpected")

    runtime_features = tuple(runtime_adapter.get_required_features())
    if (
        contract.artifact_name != CANONICAL_API_ARTIFACT_NAME
        or contract.model_type != CANONICAL_API_MODEL_TYPE
        or contract.feature_count != len(runtime_features)
        or contract.ordered_features != runtime_features
        or len(set(contract.ordered_features)) != contract.feature_count
    ):
        raise TrainingContractError("canonical training/runtime feature contract mismatch")
    return contract


def resolve_training_contract(
    registry: FeatureContractRegistry | None = None,
) -> FeatureContract:
    """Resolve the non-activated V-next training projection exactly.

    The registry owns all 17 V-next feature decisions.  Training receives only
    the nine entries explicitly marked ``ACCEPTED_FOR_TRAINING``; blocked and
    excluded entries are never treated as optional columns or compatibility
    fallbacks.
    """
    contract_registry = registry or FeatureContractRegistry()
    try:
        registered = contract_registry.get_by_contract_id(VNEXT_CONTRACT_ID)
    except (ValueError, TypeError) as exc:
        raise TrainingContractError("canonical training feature contract unavailable") from exc

    accepted = tuple(
        status.feature_name
        for status in registered.feature_statuses
        if status.training_decision == "ACCEPTED_FOR_TRAINING"
    )
    if (
        registered.contract_id != VNEXT_CONTRACT_ID
        or registered.artifact_name != CANDIDATE_ARTIFACT_NAME
        or registered.model_type != CANDIDATE_MODEL_TYPE
        or registered.activation_status != "DEFINED_NOT_ACTIVATED"
        or accepted != ACCEPTED_TRAINING_FEATURES
        or len(accepted) != len(set(accepted))
    ):
        raise TrainingContractError("canonical training feature decision binding is invalid")

    return replace(registered, feature_count=len(accepted), ordered_features=accepted)


def _canonical_json_bytes(value: Any) -> bytes:
    """Serialize metadata using the repository's stable JSON convention."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TrainingContractError("candidate metadata is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _row_id_hash(row_ids: list[str] | tuple[str, ...]) -> str:
    """Hash a sorted, duplicate-free ID set like the canonical JS contracts."""
    normalized = [str(row_id) for row_id in row_ids]
    if len(set(normalized)) != len(normalized):
        raise TrainingContractError("training row IDs are not unique")
    return _sha256_json(sorted(normalized))


def _assert_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TrainingContractError(f"{label} is not a lowercase SHA-256")
    return value


def _assert_full_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != GIT_SHA_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TrainingContractError(f"{label} is not a full Git SHA")
    return value


def _normalise_target(value: Any) -> int:
    """Map the established Away/Draw/Home labels to 0/1/2 without fallback."""
    if isinstance(value, Mapping):
        if "outcome" not in value:
            raise TrainingContractError("target label outcome is missing")
        value = value["outcome"]
    if isinstance(value, str):
        normalized = value.strip().upper()
        aliases: dict[str, int] = {
            "A": RESULT_MAP["A"],
            "AWAY": RESULT_MAP["A"],
            "AWAY_WIN": RESULT_MAP["A"],
            "D": RESULT_MAP["D"],
            "DRAW": RESULT_MAP["D"],
            "H": RESULT_MAP["H"],
            "HOME": RESULT_MAP["H"],
            "HOME_WIN": RESULT_MAP["H"],
        }
        if normalized in aliases:
            return aliases[normalized]
        raise TrainingContractError("unknown target class")

    if isinstance(value, (bool, np.bool_)):
        raise TrainingContractError("boolean target class is invalid")
    try:
        numeric = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TrainingContractError("target class is invalid") from exc
    if numeric != value or numeric not in DEFAULT_CLASS_ORDER:
        raise TrainingContractError("unknown target class")
    return numeric


def _validate_extra_columns(
    frame: pd.DataFrame,
    contract: FeatureContract,
    timestamp_column: str,
    target_column: str,
    feature_cutoff_column: str | None,
) -> None:
    feature_columns = tuple(
        column for column in frame.columns if column in contract.ordered_features
    )
    if feature_columns != contract.ordered_features:
        raise TrainingContractError("canonical training feature order is invalid")
    allowed_metadata = {timestamp_column, target_column, "match_id"}
    if feature_cutoff_column:
        allowed_metadata.add(feature_cutoff_column)
    extra_columns = set(frame.columns) - set(contract.ordered_features) - allowed_metadata
    if extra_columns:
        unsafe = [
            str(column)
            for column in extra_columns
            if any(marker in str(column).lower() for marker in _UNSAFE_EXTRA_MARKERS)
        ]
        if unsafe:
            raise TrainingContractError(f"unsafe non-contract training column: {unsafe[0]}")
        raise TrainingContractError("training frame contains non-contract feature columns")


def validate_training_frame(  # noqa: C901, PLR0912
    frame: pd.DataFrame,
    *,
    registry: FeatureContractRegistry | None = None,
    timestamp_column: str = DEFAULT_TIMESTAMP_COLUMN,
    target_column: str = DEFAULT_TARGET_COLUMN,
    feature_cutoff_column: str | None = None,
    validate_target: bool = True,
) -> ValidatedTrainingData:
    """Validate an explicit pre-match frame without filling missing values."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise TrainingContractError("training frame is empty")
    if not frame.columns.is_unique:
        raise TrainingContractError("training frame contains duplicate columns")

    contract = resolve_training_contract(registry)
    required = set(contract.ordered_features)
    missing = required - set(frame.columns)
    if missing:
        raise TrainingContractError("canonical training feature is missing")
    for column in (timestamp_column, target_column):
        if column not in frame.columns:
            raise TrainingContractError(f"training metadata column is missing: {column}")
    if feature_cutoff_column and feature_cutoff_column not in frame.columns:
        raise TrainingContractError("feature cutoff column is missing")

    _validate_extra_columns(
        frame,
        contract,
        timestamp_column,
        target_column,
        feature_cutoff_column,
    )
    validated = frame.copy(deep=True)
    timestamps = pd.to_datetime(validated[timestamp_column], utc=True, errors="coerce")
    if timestamps.isna().any():
        raise TrainingContractError("training timestamp is invalid")

    if feature_cutoff_column:
        cutoffs = pd.to_datetime(validated[feature_cutoff_column], utc=True, errors="coerce")
        if cutoffs.isna().any() or (cutoffs > timestamps).any():
            raise TrainingContractError("feature cutoff is after match time")

    for feature in contract.ordered_features:
        try:
            numeric = pd.to_numeric(validated[feature], errors="raise")
        except (TypeError, ValueError) as exc:
            raise TrainingContractError("canonical training feature is not numeric") from exc
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise TrainingContractError("canonical training feature contains non-finite values")
        validated[feature] = numeric.astype(float)

    if validate_target:
        validated[target_column] = validated[target_column].map(_normalise_target)
        if validated[target_column].isna().any():
            raise TrainingContractError("training target is missing")
        if set(validated[target_column].astype(int)) != set(DEFAULT_CLASS_ORDER):
            raise TrainingContractError("training frame does not contain all outcome classes")
    if "match_id" in validated.columns:
        match_ids = validated["match_id"].astype(str)
        if match_ids.duplicated().any():
            raise TrainingContractError("training frame contains duplicate match IDs")

    return ValidatedTrainingData(
        frame=validated,
        contract=contract,
        timestamp_column=timestamp_column,
        target_column=target_column,
        feature_cutoff_column=feature_cutoff_column,
        timestamps=timestamps,
    )


def load_canonical_feature_frame(
    artifact_path: str | Path,
    receipt_path: str | Path,
    *,
    registry: FeatureContractRegistry | None = None,
) -> ValidatedTrainingData:
    """Load the repository-external canonical frame through its input module."""
    return canonical_frame_input.load_canonical_feature_frame(
        artifact_path, receipt_path, registry=registry
    )


def _choose_temporal_boundary(
    timestamps: pd.Series, desired: int, minimum_train: int, minimum_valid: int
) -> int:
    """Choose a timestamp boundary without splitting equal-time rows."""
    count = len(timestamps)
    candidates = [
        index
        for index in range(minimum_train, count - minimum_valid + 1)
        if timestamps.iloc[index - 1] < timestamps.iloc[index]
    ]
    if not candidates:
        raise TrainingContractError("training data has no non-overlapping temporal boundary")
    return min(candidates, key=lambda index: (abs(index - desired), index))


def chronological_split(
    data: ValidatedTrainingData,
    *,
    validation_fraction: float = DEFAULT_VALIDATION_FRACTION,
    min_train_rows: int = DEFAULT_MIN_TRAIN_ROWS,
    min_validation_rows: int = DEFAULT_MIN_VALIDATION_ROWS,
) -> TemporalSplit:
    """Sort deterministically and split earlier rows from later rows."""
    if not 0 < validation_fraction < 1:
        raise TrainingContractError("validation fraction must be between zero and one")
    if min_train_rows < 1 or min_validation_rows < 1:
        raise TrainingContractError("minimum split row counts must be positive")
    if len(data.frame) < min_train_rows + min_validation_rows:
        raise TrainingContractError("training data has too few rows for temporal split")

    ordered = data.frame.copy(deep=True)
    ordered["__canonical_timestamp"] = data.timestamps.to_numpy()
    ordered["__canonical_input_order"] = np.arange(len(ordered), dtype=np.int64)
    sort_columns = ["__canonical_timestamp"]
    if "match_id" in ordered.columns:
        ordered["__canonical_match_id"] = ordered["match_id"].astype(str)
        sort_columns.append("__canonical_match_id")
    else:
        sort_columns.append("__canonical_input_order")
    ordered = ordered.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    timestamps = ordered["__canonical_timestamp"]
    desired = int(len(ordered) * (1.0 - validation_fraction))
    boundary = _choose_temporal_boundary(
        timestamps,
        desired,
        min_train_rows,
        min_validation_rows,
    )

    train = ordered.iloc[:boundary].drop(
        columns=["__canonical_timestamp", "__canonical_input_order", "__canonical_match_id"],
        errors="ignore",
    )
    validation = ordered.iloc[boundary:].drop(
        columns=["__canonical_timestamp", "__canonical_input_order", "__canonical_match_id"],
        errors="ignore",
    )
    train_timestamps = timestamps.iloc[:boundary].reset_index(drop=True)
    validation_timestamps = timestamps.iloc[boundary:].reset_index(drop=True)
    if train_timestamps.max() >= validation_timestamps.min():
        raise TrainingContractError("temporal split overlaps train and validation timestamps")
    return TemporalSplit(
        train=train.reset_index(drop=True),
        validation=validation.reset_index(drop=True),
        train_timestamps=train_timestamps,
        validation_timestamps=validation_timestamps,
        timestamp_column=data.timestamp_column,
        target_column=data.target_column,
        feature_names=data.contract.ordered_features,
        validation_fraction=validation_fraction,
    )


def _default_estimator(
    *,
    seed: int,
    estimators: int,
    max_depth: int,
    learning_rate: float,
) -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(DEFAULT_CLASS_ORDER),
        n_estimators=estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=1.0,
        colsample_bytree=1.0,
        eval_metric="mlogloss",
        random_state=seed,
        n_jobs=1,
    )


def _model_class_order(model: Any) -> tuple[int, ...]:
    classes = getattr(model, "classes_", None)
    if classes is None:
        raise TrainingContractError("estimator does not expose class order")
    try:
        order = tuple(int(value) for value in classes)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TrainingContractError("estimator class order is invalid") from exc
    if order != DEFAULT_CLASS_ORDER:
        raise TrainingContractError("estimator class order does not match serving")
    return order


def _validate_estimator_feature_metadata(model: Any, feature_names: tuple[str, ...]) -> None:
    count = getattr(model, "n_features_in_", None)
    if count is not None and int(count) != len(feature_names):
        raise TrainingContractError("estimator feature count does not match contract")
    declared = getattr(model, "feature_names_in_", None)
    if declared is not None and tuple(str(value) for value in declared) != feature_names:
        raise TrainingContractError("estimator feature order does not match contract")


def fit_canonical_model(
    split: TemporalSplit,
    *,
    seed: int = DEFAULT_SEED,
    estimators: int = DEFAULT_ESTIMATORS,
    max_depth: int = DEFAULT_MAX_DEPTH,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    estimator_factory: Callable[[], Any] | None = None,
) -> FittedCanonicalModel:
    """Fit scaler and estimator on fit rows only.

    ``split.validation`` is deliberately reserved for the next evaluation
    business node.  It is transformed neither for fitting nor passed through
    the estimator's ``eval_set`` hook in this producer.
    """
    if estimators < 1 or max_depth < 1 or learning_rate <= 0:
        raise TrainingContractError("estimator hyperparameters are invalid")
    scaler = StandardScaler()
    x_train = pd.DataFrame(
        scaler.fit_transform(split.train.loc[:, list(split.feature_names)]),
        columns=split.feature_names,
    )
    y_train = split.train[split.target_column].map(_normalise_target).astype(int)
    if set(y_train) != set(DEFAULT_CLASS_ORDER):
        raise TrainingContractError("training partition does not contain all outcome classes")
    model = (
        estimator_factory()
        if estimator_factory is not None
        else _default_estimator(
            seed=seed,
            estimators=estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
        )
    )
    model.fit(x_train, y_train, verbose=False)
    class_order = _model_class_order(model)
    _validate_estimator_feature_metadata(model, split.feature_names)
    return FittedCanonicalModel(model=model, scaler=scaler, class_order=class_order)


def evaluate_canonical_model(
    fitted: FittedCanonicalModel,
    split: TemporalSplit,
) -> dict[str, Any]:
    """Evaluate probabilities only on the later, unseen validation rows."""
    x_validation = pd.DataFrame(
        fitted.scaler.transform(split.validation.loc[:, list(split.feature_names)]),
        columns=split.feature_names,
    )
    y_validation = split.validation[split.target_column].map(_normalise_target).to_numpy()
    probabilities = np.asarray(fitted.model.predict_proba(x_validation), dtype=float)
    if probabilities.shape != (len(split.validation), len(DEFAULT_CLASS_ORDER)):
        raise TrainingContractError("estimator probability shape is incompatible")
    if not np.isfinite(probabilities).all() or not np.allclose(probabilities.sum(axis=1), 1.0):
        raise TrainingContractError("estimator probabilities are invalid")
    predictions = np.asarray(fitted.model.predict(x_validation), dtype=int)
    if not np.isin(predictions, DEFAULT_CLASS_ORDER).all():
        raise TrainingContractError("estimator prediction class is invalid")

    one_hot = np.eye(len(DEFAULT_CLASS_ORDER), dtype=float)[y_validation]
    return {
        "accuracy": float(accuracy_score(y_validation, predictions)),
        "log_loss": float(log_loss(y_validation, probabilities, labels=list(DEFAULT_CLASS_ORDER))),
        "multiclass_brier": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "class_order": list(fitted.class_order),
        "class_names": list(RESULT_NAMES),
    }


def _git_revision() -> str:
    """Return a safe source revision or a non-sensitive unavailable marker."""
    try:
        root = Path(__file__).resolve().parents[3]
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return (
        revision
        if len(revision) == GIT_SHA_LENGTH and all(c in "0123456789abcdef" for c in revision)
        else "unavailable"
    )


def _date_range(timestamps: pd.Series) -> list[str]:
    return [timestamps.min().isoformat(), timestamps.max().isoformat()]


def build_provenance(
    split: TemporalSplit,
    metrics: Mapping[str, Any] | None,
    contract: FeatureContract,
    *,
    seed: int,
    source_dataset_identity: str,
    source_binding: CanonicalFrameBinding | None = None,
    estimator_type: str = "xgboost.XGBClassifier",
    hyperparameters: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build provenance through the dedicated candidate artifact module."""
    return canonical_candidate_artifact.build_provenance(
        split,
        metrics,
        contract,
        seed=seed,
        source_dataset_identity=source_dataset_identity,
        source_binding=source_binding,
        estimator_type=estimator_type,
        hyperparameters=hyperparameters,
        created_at=created_at,
    )


def build_candidate_envelope(
    fitted: FittedCanonicalModel,
    contract: FeatureContract,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a candidate envelope through the dedicated artifact module."""
    return canonical_candidate_artifact.build_candidate_envelope(fitted, contract, provenance)


def validate_candidate_metadata(
    metadata: Mapping[str, Any], *, model_sha256: str | None = None
) -> None:
    """Validate candidate metadata through the dedicated artifact module."""
    canonical_candidate_artifact.validate_candidate_metadata(metadata, model_sha256=model_sha256)


def atomic_write_candidate(
    envelope: Mapping[str, Any],
    output_path: str | Path,
    *,
    contract: FeatureContract | None = None,
) -> CandidateArtifact:
    """Serialize a model and sidecar through the dedicated artifact module."""
    return canonical_candidate_artifact.atomic_write_candidate(
        envelope, output_path, contract=contract
    )


def produce_candidate(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    registry: FeatureContractRegistry | None = None,
    timestamp_column: str = DEFAULT_TIMESTAMP_COLUMN,
    target_column: str = DEFAULT_TARGET_COLUMN,
    feature_cutoff_column: str | None = None,
    validation_fraction: float = DEFAULT_VALIDATION_FRACTION,
    min_train_rows: int = DEFAULT_MIN_TRAIN_ROWS,
    min_validation_rows: int = DEFAULT_MIN_VALIDATION_ROWS,
    seed: int = DEFAULT_SEED,
    estimators: int = DEFAULT_ESTIMATORS,
    max_depth: int = DEFAULT_MAX_DEPTH,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    source_dataset_identity: str = "explicit-offline-feature-frame",
    source_binding: CanonicalFrameBinding | None = None,
) -> CandidateArtifact:
    """Run the complete safe candidate pipeline and self-verify final bytes."""
    data = validate_training_frame(
        frame,
        registry=registry,
        timestamp_column=timestamp_column,
        target_column=target_column,
        feature_cutoff_column=feature_cutoff_column,
        validate_target=False,
    )
    split = chronological_split(
        data,
        validation_fraction=validation_fraction,
        min_train_rows=min_train_rows,
        min_validation_rows=min_validation_rows,
    )
    fitted = fit_canonical_model(
        split,
        seed=seed,
        estimators=estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
    )
    provenance = build_provenance(
        split,
        None,
        data.contract,
        seed=seed,
        source_dataset_identity=source_dataset_identity,
        source_binding=source_binding,
        estimator_type=type(fitted.model).__module__ + "." + type(fitted.model).__name__,
        hyperparameters={
            "objective": "multi:softprob",
            "num_class": len(DEFAULT_CLASS_ORDER),
            "n_estimators": estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": 1.0,
            "colsample_bytree": 1.0,
            "eval_metric": "mlogloss",
            "random_state": seed,
            "n_jobs": 1,
            "validation_fraction": validation_fraction,
        },
    )
    envelope = build_candidate_envelope(fitted, data.contract, provenance)
    candidate = atomic_write_candidate(envelope, output_path, contract=data.contract)

    # Validate the bytes that actually reached the final candidate path. A
    # serialization failure therefore cannot be reported as a successful run.
    try:
        serialized_envelope = joblib.load(candidate.path)
        validate_canonical_model_envelope(
            serialized_envelope,
            artifact_name=CANDIDATE_ARTIFACT_NAME,
            model_type=CANDIDATE_MODEL_TYPE,
            contract=data.contract,
        )
    except Exception as exc:
        candidate.path.unlink(missing_ok=True)
        if candidate.metadata_path is not None:
            candidate.metadata_path.unlink(missing_ok=True)
        raise TrainingContractError("final candidate self-validation failed") from exc
    return candidate
