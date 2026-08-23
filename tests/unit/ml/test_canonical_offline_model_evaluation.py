"""Tests for the frozen canonical offline evaluation boundary."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from src.ml.evaluation import canonical_offline_model_evaluation as evaluation
from src.ml.training import canonical_training_producer as producer

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = PROJECT_ROOT / "config" / "canonical_offline_model_evaluation_protocol.json"
SYNTHETIC_RESERVED_ROWS = 2


class _ExplodingLabel(dict):
    def __getitem__(self, key: str) -> Any:
        if key == "outcome":
            raise AssertionError("reserved outcome was accessed")
        return super().__getitem__(key)


class _IdentityScaler:
    n_features_in_ = 9

    def transform(self, values: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return values


class _FixedModel:
    classes_ = np.asarray([0, 1, 2])
    feature_names_in_ = np.asarray(evaluation.FEATURE_ORDER)
    n_features_in_ = 9

    def __init__(self, probabilities: np.ndarray[Any, Any]):
        self._probabilities = probabilities

    def predict_proba(self, values: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.tile(self._probabilities, (len(values), 1))


def _binding(row_ids: list[str]) -> producer.CanonicalFrameBinding:
    row_hash = producer._row_id_hash(row_ids)
    return producer.CanonicalFrameBinding(
        artifact_sha256=evaluation.EXPECTED_FRAME_ARTIFACT_SHA256,
        receipt_sha256=evaluation.EXPECTED_FRAME_RECEIPT_SHA256,
        business_sha256=evaluation.EXPECTED_FRAME_BUSINESS_SHA256,
        contract_id="canonical_prematch/vnext-v1",
        contract_version="canonical_prematch/vnext/v1",
        feature_names=evaluation.FEATURE_ORDER,
        target_population=len(row_ids),
        rows_accounted=len(row_ids),
        eligible_rows=len(row_ids),
        ineligible_rows=0,
        target_row_id_sha256=row_hash,
        eligible_row_id_sha256=row_hash,
        frame_code_revision=evaluation.EXPECTED_FRAME_CODE_REVISION,
    )


def _population() -> evaluation.EvaluationPopulation:
    training_ids = ("train-0", "train-1")
    reserved_ids = ("reserved-0", "reserved-1")
    all_ids = list(training_ids + reserved_ids)
    rows = {
        row_id: evaluation.EvaluationRow(
            row_id=row_id,
            kickoff_utc=f"2024-01-0{index + 1}T12:00:00+00:00",
            features=tuple(float(index + feature) for feature in range(9)),
        )
        for index, row_id in enumerate(all_ids)
    }
    labels = {
        training_ids[0]: evaluation._OpaqueOutcome(_ExplodingLabel(outcome=0)),
        training_ids[1]: evaluation._OpaqueOutcome(_ExplodingLabel(outcome=1)),
        reserved_ids[0]: evaluation._OpaqueOutcome({"outcome": 2}),
        reserved_ids[1]: evaluation._OpaqueOutcome({"outcome": 0}),
    }
    return evaluation.EvaluationPopulation(
        frame_binding=_binding(all_ids),
        rows_by_id=rows,
        labels_by_id=labels,
        training_ids=training_ids,
        reserved_ids=reserved_ids,
    )


def _candidate() -> evaluation.VerifiedCandidate:
    metadata = {
        "candidate_id": evaluation.EXPECTED_CANDIDATE_ID,
        "artifact_sha256": evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256,
        "metadata_sha256": evaluation.EXPECTED_CANDIDATE_METADATA_SHA256,
        "model_family": "xgboost_multiclass_1x2",
        "model_version": "canonical-prematch-vnext-xgb/v1",
        "code_revision": evaluation.EXPECTED_CANDIDATE_SOURCE_REVISION,
        "created_as": "NON_PRODUCTION_CANDIDATE",
        "activated": "NO",
        "provenance": {"train_class_distribution": {"AWAY": 135, "DRAW": 97, "HOME": 204}},
    }
    return evaluation.VerifiedCandidate(
        model=_FixedModel(np.asarray([0.25, 0.25, 0.5])),
        scaler=_IdentityScaler(),
        metadata=metadata,
        artifact_sha256=evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256,
        metadata_sha256=evaluation.EXPECTED_CANDIDATE_METADATA_SHA256,
        feature_names=evaluation.FEATURE_ORDER,
        class_order=evaluation.CLASS_ORDER,
    )


def test_protocol_is_frozen_and_primary_metric_is_log_loss() -> None:
    protocol, digest, path = evaluation.load_protocol(PROTOCOL_PATH)

    assert path == PROTOCOL_PATH.resolve()
    assert protocol["metrics"]["primary_metric"] == "multiclass_log_loss"
    assert protocol["candidate"]["artifact_sha256"] == evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256
    assert protocol["population"]["reserved_evaluation_rows"] == evaluation.RESERVED_ROWS
    assert digest == evaluation.protocol_sha256(protocol)


def test_outcome_access_is_forbidden_until_protocol_freeze_and_skips_train_rows() -> None:
    population = _population()
    gate = evaluation.OutcomeAccessGate(population)

    with pytest.raises(evaluation.EvaluationContractError, match="before protocol freeze"):
        gate.open_reserved_outcomes("2026-08-23T00:00:00Z")

    gate.freeze("a" * 64, "b" * 40)
    opened = gate.open_reserved_outcomes("2026-08-23T00:00:00Z")
    assert opened.tolist() == [2, 0]
    assert gate.outcomes_opened is True


def test_tampered_reserved_row_ids_are_rejected() -> None:
    population = _population()
    protocol, _, _ = evaluation.load_protocol(PROTOCOL_PATH)
    tampered = replace(population, reserved_ids=("reserved-tampered", "reserved-1"))

    with pytest.raises(evaluation.EvaluationContractError, match="row ID binding"):
        evaluation.validate_population_binding(tampered, protocol)


def test_tampered_candidate_bytes_are_rejected_before_deserialization(tmp_path: Path) -> None:
    protocol, _, _ = evaluation.load_protocol(PROTOCOL_PATH)
    candidate_path = tmp_path / "candidate.joblib"
    metadata_path = tmp_path / "candidate.joblib.metadata.json"
    candidate_path.write_bytes(b"tampered-candidate")
    metadata_path.write_text("{}", encoding="utf-8")

    with pytest.raises(evaluation.EvaluationContractError, match="candidate artifact hash"):
        evaluation.load_verified_candidate(candidate_path, metadata_path, protocol)


def test_probability_class_order_and_sanity_are_fail_closed() -> None:
    evaluation.validate_probability_matrix(np.asarray([[0.2, 0.3, 0.5]]), expected_rows=1)
    evaluation.validate_probability_matrix(
        np.asarray([[0.1, 0.2, 0.7]], dtype=np.float32), expected_rows=1
    )
    with pytest.raises(evaluation.EvaluationContractError, match="non-finite"):
        evaluation.validate_probability_matrix(np.asarray([[np.nan, 0.3, 0.7]]))
    with pytest.raises(evaluation.EvaluationContractError, match="sum"):
        evaluation.validate_probability_matrix(np.asarray([[0.2, 0.3, 0.4]]))

    assert evaluation.CLASS_ORDER == (0, 1, 2)
    assert evaluation.PROBABILITY_COLUMN_ORDER == ("P_AWAY", "P_DRAW", "P_HOME")


def test_primary_brier_and_accuracy_formulas() -> None:
    probabilities = np.asarray(
        [
            [0.6, 0.3, 0.1],
            [0.1, 0.8, 0.1],
            [0.2, 0.2, 0.6],
        ]
    )
    metrics = evaluation.metric_bundle(probabilities, np.asarray([0, 1, 2]))

    assert metrics["multiclass_log_loss"] == pytest.approx(
        (-np.log(0.6) - np.log(0.8) - np.log(0.6)) / 3
    )
    assert metrics["multiclass_brier_score"] == pytest.approx(
        ((0.4**2 + 0.3**2 + 0.1**2) + (0.1**2 + 0.2**2 + 0.1**2) + (0.2**2 + 0.2**2 + 0.4**2)) / 3
    )
    assert metrics["accuracy"] == pytest.approx(1.0)


def test_baseline_uses_training_metadata_only() -> None:
    _, prior_matrix, majority_matrix, majority_class = evaluation.build_baselines(
        _candidate(), np.asarray([0, 1, 2])
    )

    assert prior_matrix[0].tolist() == pytest.approx(
        [
            135 / evaluation.TRAINING_ROWS,
            97 / evaluation.TRAINING_ROWS,
            204 / evaluation.TRAINING_ROWS,
        ]
    )
    assert majority_class == evaluation.CLASS_ORDER[-1]
    assert np.all(majority_matrix == np.asarray([0.0, 0.0, 1.0]))


def test_calibration_binning_is_deterministic_and_marks_small_cells() -> None:
    protocol, _, _ = evaluation.load_protocol(PROTOCOL_PATH)
    probabilities = np.asarray([[0.55, 0.35, 0.10], [0.65, 0.20, 0.15]])
    labels = np.asarray([0, 1])

    first = evaluation._calibration_summary(probabilities, labels, protocol)
    second = evaluation._calibration_summary(probabilities, labels, protocol)

    assert first == second
    assert first["sample_status"] == "INSUFFICIENT_SAMPLE"
    assert sum(entry["count"] for entry in first["classwise"]["AWAY"]) == SYNTHETIC_RESERVED_ROWS


def test_candidate_metadata_binding_rejects_tampered_artifact_and_source_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol, _, _ = evaluation.load_protocol(PROTOCOL_PATH)
    metadata = {
        "candidate_id": evaluation.EXPECTED_CANDIDATE_ID,
        "model_family": "xgboost_multiclass_1x2",
        "model_version": "canonical-prematch-vnext-xgb/v1",
        "code_revision": evaluation.EXPECTED_CANDIDATE_SOURCE_REVISION,
        "feature_contract_id": "canonical_prematch/vnext-v1",
        "feature_contract_version": "canonical_prematch/vnext/v1",
        "feature_names": list(evaluation.FEATURE_ORDER),
        "feature_order": list(evaluation.FEATURE_ORDER),
        "training_frame_artifact_hash": evaluation.EXPECTED_FRAME_ARTIFACT_SHA256,
        "training_frame_receipt_hash": evaluation.EXPECTED_FRAME_RECEIPT_SHA256,
        "training_row_count": evaluation.TRAINING_ROWS,
        "training_row_id_hash": evaluation.EXPECTED_TRAINING_ROW_ID_SHA256,
        "reserved_evaluation_row_count": evaluation.RESERVED_ROWS,
        "reserved_evaluation_row_id_hash": evaluation.EXPECTED_RESERVED_ROW_ID_SHA256,
        "preprocessor_identity": "sklearn.StandardScaler/v1",
        "preprocessor_fit_population": "training_partition_only",
        "random_seed": 42,
        "model_artifact_sha256": evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256,
        "created_as": "NON_PRODUCTION_CANDIDATE",
        "activated": "NO",
        "hyperparameters": {
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
        },
        "provenance": {
            "candidate_id": evaluation.EXPECTED_CANDIDATE_ID,
            "producer_source_revision": evaluation.EXPECTED_CANDIDATE_SOURCE_REVISION,
            "frame_eligible_rows": evaluation.FRAME_ELIGIBLE_ROWS,
            "trainer_admitted_rows": evaluation.TRAINING_ROWS,
            "trainer_reserved_rows": evaluation.RESERVED_ROWS,
            "reserved_evaluation_rows": evaluation.RESERVED_ROWS,
            "train_date_range": ["2022-09-03T11:30:00+00:00", "2024-02-17T17:30:00+00:00"],
            "reserved_evaluation_date_range": [
                "2024-02-18T14:00:00+00:00",
                "2024-05-19T15:00:00+00:00",
            ],
            "train_class_distribution": {"AWAY": 135, "DRAW": 97, "HOME": 204},
            "reserved_evaluation_policy": {
                "outcome_access": "UNOPENED_UNTIL_OFFLINE_EVALUATION",
                "used_for_fit": False,
                "used_for_preprocessing": False,
                "used_for_tuning": False,
                "used_for_metrics": False,
            },
        },
    }
    monkeypatch.setattr(producer, "validate_candidate_metadata", lambda *_args, **_kwargs: None)
    evaluation.validate_candidate_metadata_binding(
        metadata,
        artifact_sha256=evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256,
        metadata_sha256=evaluation.EXPECTED_CANDIDATE_METADATA_SHA256,
        protocol=protocol,
    )

    with pytest.raises(evaluation.EvaluationContractError, match="artifact"):
        evaluation.validate_candidate_metadata_binding(
            metadata,
            artifact_sha256="f" * 64,
            metadata_sha256=evaluation.EXPECTED_CANDIDATE_METADATA_SHA256,
            protocol=protocol,
        )
    tampered = dict(metadata)
    tampered["code_revision"] = "f" * 40
    with pytest.raises(evaluation.EvaluationContractError, match="code_revision"):
        evaluation.validate_candidate_metadata_binding(
            tampered,
            artifact_sha256=evaluation.EXPECTED_CANDIDATE_ARTIFACT_SHA256,
            metadata_sha256=evaluation.EXPECTED_CANDIDATE_METADATA_SHA256,
            protocol=protocol,
        )


def test_artifact_provenance_holdout_consumption_and_no_production_mutation() -> None:
    protocol, protocol_hash, _ = evaluation.load_protocol(PROTOCOL_PATH)
    population = _population()
    prepared = evaluation.PreparedEvaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=_candidate(),
        population=population,
        gate=evaluation.OutcomeAccessGate(population),
    )
    prepared.freeze_protocol(source_head="a" * 40, protocol_freeze_sha="a" * 40)
    prepared.infer_reserved()
    labels = prepared.open_outcomes("2026-08-23T00:00:00Z")
    artifact = evaluation.build_evaluation_artifact(prepared, labels)

    assert artifact["protocol_frozen_before_outcome_open"] is True
    assert artifact["holdout"]["status_after"] == "CONSUMED_FOR_OFFLINE_EVALUATION"
    assert artifact["population"]["evaluated_rows"] == SYNTHETIC_RESERVED_ROWS
    assert artifact["safety"]["training_runs"] == 0
    assert artifact["safety"]["backtest_runs"] == 0
    assert artifact["safety"]["production_manifest_changed"] is False
    assert artifact["claims"]["model_selected"] is False
    assert "roi" not in json.dumps(artifact["prediction_rows"], sort_keys=True).lower()


def test_evaluation_output_cannot_target_repository_manifest() -> None:
    protocol, protocol_hash, _ = evaluation.load_protocol(PROTOCOL_PATH)
    population = _population()
    prepared = evaluation.PreparedEvaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=_candidate(),
        population=population,
        gate=evaluation.OutcomeAccessGate(population),
    )
    prepared.freeze_protocol(source_head="a" * 40, protocol_freeze_sha="a" * 40)
    prepared.infer_reserved()
    labels = prepared.open_outcomes("2026-08-23T00:00:00Z")
    artifact = evaluation.build_evaluation_artifact(prepared, labels)

    with pytest.raises(evaluation.EvaluationContractError, match="repository-external"):
        evaluation.write_evaluation_outputs(
            artifact,
            output_dir=PROJECT_ROOT / "config" / "offline-evaluation-attempt",
            protocol_freeze_sha="a" * 40,
            evaluation_source_head="a" * 40,
        )
