"""Behavior tests for the canonical API training producer.

lifecycle: test-fixture
scope: PR-6 canonical v26_7_aligned candidate production

All model bytes in this file are deterministic test candidates under
``tmp_path``. No database, network, tracked manifest, or production path is
used.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import cast

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd
import pytest

from src.ml.feature_adapter import V26_6_PreMatchAdapter
from src.ml.inference.artifact_manifest import ArtifactManifest, ReadinessManager
from src.ml.inference.canonical_model_loader import (
    CANONICAL_API_ARTIFACT_NAME,
    CANONICAL_API_MODEL_TYPE,
    CanonicalModelLoader,
    ModelArtifactUnavailableError,
    validate_canonical_model_envelope,
)
from src.ml.inference.feature_contract_registry import FeatureContract, FeatureContractRegistry
from src.ml.training import canonical_training_producer as producer
from src.ml.training.__main__ import main as producer_cli_main

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / "config" / "model_feature_contracts.json"
MANIFEST_PATH = PROJECT_ROOT / "config" / "model_artifacts.json"
EXPECTED_FEATURE_COUNT = 20


def _feature_names() -> tuple[str, ...]:
    return tuple(
        FeatureContractRegistry()
        .get_for_model(
            CANONICAL_API_MODEL_TYPE,
            artifact_name=CANONICAL_API_ARTIFACT_NAME,
        )
        .ordered_features
    )


def _frame(rows: int = 45) -> pd.DataFrame:
    features = _feature_names()
    records: list[dict[str, object]] = []
    for index in range(rows):
        record: dict[str, object] = {
            "match_id": f"match-{index:03d}",
            "match_date": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=index),
            "result": (index % 3),
        }
        record.update(
            {name: float(index + feature_index + 1) for feature_index, name in enumerate(features)}
        )
        records.append(record)
    return pd.DataFrame(records)


def test_training_contract_is_exact_registry_and_runtime_order() -> None:
    contract = producer.resolve_canonical_contract()

    assert contract.contract_id == "v26_7_aligned/v1"
    assert contract.feature_contract_version == "v26_6_pre_match/v1"
    assert contract.feature_count == EXPECTED_FEATURE_COUNT
    assert contract.ordered_features == tuple(V26_6_PreMatchAdapter().get_required_features())


def test_mismatched_registry_binding_fails_closed() -> None:
    canonical = FeatureContractRegistry().get_for_model(
        CANONICAL_API_MODEL_TYPE,
        artifact_name=CANONICAL_API_ARTIFACT_NAME,
    )

    class MismatchedRegistry:
        def get_for_model(self, _model_type: str, *, artifact_name: str) -> FeatureContract:
            del artifact_name
            return replace(canonical, model_type="unrelated_model")

    with pytest.raises(producer.TrainingContractError, match="mismatch"):
        producer.resolve_canonical_contract(cast("FeatureContractRegistry", MismatchedRegistry()))


def test_missing_or_nonfinite_required_feature_fails_closed() -> None:
    frame = _frame()
    frame = frame.drop(columns=[_feature_names()[0]])
    with pytest.raises(producer.TrainingContractError, match="feature"):
        producer.validate_training_frame(frame)

    frame = _frame()
    frame.loc[0, _feature_names()[1]] = np.nan
    with pytest.raises(producer.TrainingContractError, match="feature"):
        producer.validate_training_frame(frame)


def test_unsafe_extra_columns_are_rejected_and_safe_extra_columns_do_not_reorder() -> None:
    frame = _frame()
    frame["league_name"] = "test-league"
    validated = producer.validate_training_frame(frame)
    split = producer.chronological_split(
        validated,
        min_train_rows=20,
        min_validation_rows=5,
    )
    assert split.feature_names == _feature_names()
    assert list(split.train.loc[:, list(split.feature_names)].columns) == list(_feature_names())

    unsafe = _frame()
    unsafe["home_score"] = 3
    with pytest.raises(producer.TrainingContractError, match="unsafe"):
        producer.validate_training_frame(unsafe)


def test_feature_cutoff_after_match_and_unknown_target_fail_closed() -> None:
    frame = _frame()
    frame["feature_as_of"] = frame["match_date"] + pd.Timedelta(hours=1)
    with pytest.raises(producer.TrainingContractError, match="cutoff"):
        producer.validate_training_frame(frame, feature_cutoff_column="feature_as_of")

    frame = _frame()
    frame.loc[0, "result"] = "not-a-result"
    with pytest.raises(producer.TrainingContractError, match="target"):
        producer.validate_training_frame(frame)


def test_temporal_split_is_deterministic_and_non_overlapping() -> None:
    frame = _frame()
    first = producer.chronological_split(
        producer.validate_training_frame(
            frame.sample(frac=1, random_state=99).reset_index(drop=True)
        ),
        validation_fraction=0.2,
        min_train_rows=20,
        min_validation_rows=5,
    )
    second = producer.chronological_split(
        producer.validate_training_frame(
            frame.sample(frac=1, random_state=99).reset_index(drop=True)
        ),
        validation_fraction=0.2,
        min_train_rows=20,
        min_validation_rows=5,
    )

    assert first.train["match_id"].tolist() == second.train["match_id"].tolist()
    assert first.validation["match_id"].tolist() == second.validation["match_id"].tolist()
    assert first.train_timestamps.max() < first.validation_timestamps.min()
    assert first.train["match_date"].max() < first.validation["match_date"].min()


def test_fit_evaluate_proves_train_only_preprocessing_and_class_order() -> None:
    split = producer.chronological_split(
        producer.validate_training_frame(_frame()),
        validation_fraction=0.2,
        min_train_rows=20,
        min_validation_rows=5,
    )
    fitted = producer.fit_canonical_model(split, estimators=4, max_depth=2)
    metrics = producer.evaluate_canonical_model(fitted, split)

    assert fitted.class_order == (0, 1, 2)
    assert tuple(int(value) for value in fitted.model.classes_) == (0, 1, 2)
    assert fitted.model.n_features_in_ == len(_feature_names())
    assert tuple(fitted.model.feature_names_in_) == _feature_names()
    assert fitted.scaler.n_samples_seen_ == len(split.train)
    assert metrics["class_order"] == [0, 1, 2]
    assert set(metrics["class_names"]) == {"AWAY", "DRAW", "HOME"}
    assert set(metrics) >= {"accuracy", "log_loss", "multiclass_brier"}


def test_candidate_is_loader_compatible_atomic_and_hash_bound(tmp_path: Path) -> None:
    before_manifest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    before_registry = hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
    output = tmp_path / "candidate" / "v26_7_aligned_candidate.pkl"

    candidate = producer.produce_candidate(
        _frame(),
        output,
        min_train_rows=20,
        min_validation_rows=5,
        estimators=4,
        max_depth=2,
        source_dataset_identity="pr6-test-frame",
    )

    assert candidate.path == output
    assert candidate.path.is_file()
    assert candidate.sha256 == ArtifactManifest.compute_sha256(output)
    envelope = joblib.load(output)
    assert envelope["artifact_name"] == CANONICAL_API_ARTIFACT_NAME
    assert envelope["model_type"] == CANONICAL_API_MODEL_TYPE
    assert envelope["contract_id"] == "v26_7_aligned/v1"
    assert envelope["feature_contract_version"] == "v26_6_pre_match/v1"
    assert envelope["feature_columns"] == list(_feature_names())
    assert (
        envelope["provenance"]["train_date_range"][1]
        < envelope["provenance"]["validation_date_range"][0]
    )
    assert validate_canonical_model_envelope(envelope).feature_names == _feature_names()

    wrong_consumer = dict(envelope)
    wrong_consumer["required_for"] = "cli"
    with pytest.raises(ModelArtifactUnavailableError, match="canonical model unavailable"):
        validate_canonical_model_envelope(wrong_consumer)

    without_provenance = dict(envelope)
    without_provenance.pop("provenance")
    with pytest.raises(producer.TrainingContractError, match="provenance"):
        producer.atomic_write_candidate(without_provenance, tmp_path / "missing-provenance.pkl")

    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == before_manifest
    assert hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest() == before_registry


def test_final_candidate_loads_through_actual_loader_in_isolated_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "candidate.pkl"
    candidate = producer.produce_candidate(
        _frame(),
        output,
        min_train_rows=20,
        min_validation_rows=5,
        estimators=4,
        max_depth=2,
    )
    store = tmp_path / "candidate_store"
    store.mkdir()
    stored = store / "candidate.pkl"
    stored.write_bytes(candidate.path.read_bytes())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 2,
                "artifact_root": "candidate_store",
                "model_zoo_root": "candidate_store",
                "artifacts": [
                    {
                        "name": CANONICAL_API_ARTIFACT_NAME,
                        "path": "candidate_store/candidate.pkl",
                        "required_for": "api",
                        "status": "active",
                        "checksum_sha256": ArtifactManifest.compute_sha256(stored),
                        "model_type": CANONICAL_API_MODEL_TYPE,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    isolated_registry = tmp_path / "registry.json"
    isolated_registry.write_bytes(REGISTRY_PATH.read_bytes())

    monkeypatch.chdir(tmp_path)
    readiness = ReadinessManager(manifest_path=manifest)
    loader = CanonicalModelLoader(
        manifest=ArtifactManifest(manifest),
        registry=FeatureContractRegistry(isolated_registry),
        readiness_manager=readiness,
    )
    loaded = loader.load()
    assert loaded.artifact_name == CANONICAL_API_ARTIFACT_NAME
    assert loaded.model_type == CANONICAL_API_MODEL_TYPE
    assert loaded.feature_names == _feature_names()
    assert readiness.service_ready()[0] is True


def test_failed_validation_or_serialization_leaves_no_final_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "candidate.pkl"
    bad_envelope = {
        "model": object(),
        "scaler": None,
        "model_type": CANONICAL_API_MODEL_TYPE,
        "feature_columns": ["wrong"],
    }
    with pytest.raises(producer.TrainingContractError):
        producer.atomic_write_candidate(bad_envelope, output)
    assert not output.exists()

    split = producer.chronological_split(
        producer.validate_training_frame(_frame()),
        min_train_rows=20,
        min_validation_rows=5,
    )
    fitted = producer.fit_canonical_model(split, estimators=2, max_depth=2)
    envelope = producer.build_candidate_envelope(
        fitted,
        producer.resolve_canonical_contract(),
        {"producer_schema_version": producer.PRODUCER_SCHEMA_VERSION},
    )

    def fail_dump(*_args, **_kwargs):
        raise OSError("synthetic serialization failure")

    monkeypatch.setattr(producer.joblib, "dump", fail_dump)  # type: ignore[attr-defined]
    with pytest.raises(producer.TrainingContractError, match="write"):
        producer.atomic_write_candidate(envelope, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))

    monkeypatch.undo()

    def fail_hash(_path):
        raise OSError("synthetic hash failure")

    monkeypatch.setattr(
        producer.ArtifactManifest,  # type: ignore[attr-defined]
        "compute_sha256",
        fail_hash,
    )
    with pytest.raises(producer.TrainingContractError, match="checksum"):
        producer.atomic_write_candidate(envelope, output)
    assert not output.exists()


def test_production_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(producer.TrainingContractError, match="production"):
        producer.atomic_write_candidate({}, tmp_path / "model_zoo" / "production" / "model.pkl")


def test_cli_dry_run_does_not_fit_or_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "features.csv"
    _frame().to_csv(input_path, index=False)

    exit_code = producer_cli_main(
        [
            "--input",
            str(input_path),
            "--dry-run",
            "--json",
            "--min-train-rows",
            "20",
            "--min-validation-rows",
            "5",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["mode"] == "canonical_training_dry_run"
    assert output["model_fit_success"] is False
    assert output["final_candidate_exists"] is False
    assert not list(tmp_path.glob("*.pkl"))
