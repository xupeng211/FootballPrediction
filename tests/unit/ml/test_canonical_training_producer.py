"""Behavior tests for the canonical vnext offline candidate producer.

lifecycle: test-fixture
scope: CANONICAL_TRAINING_CANDIDATE_PRODUCTION

The production-path assertions in this file deliberately use temporary
repository-external paths. The canonical-frame loader test uses a compact
contract-shaped fixture and stubs the already-tested JavaScript frame
validator; the real 888-row frame is validated separately before training.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import joblib  # type: ignore[import-untyped]
import numpy as np
import pandas as pd
import pytest

from src.ml.inference.artifact_manifest import ArtifactManifest
from src.ml.inference.canonical_model_loader import (
    ModelArtifactUnavailableError,
    validate_canonical_model_envelope,
)
from src.ml.training import canonical_frame_input
from src.ml.training import canonical_training_producer as producer
from src.ml.training.__main__ import main as producer_cli_main

if TYPE_CHECKING:
    from src.ml.inference.feature_contract_registry import FeatureContract, FeatureContractRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / "config" / "model_feature_contracts.json"
MANIFEST_PATH = PROJECT_ROOT / "config" / "model_artifacts.json"
FEATURES = producer.ACCEPTED_TRAINING_FEATURES
EXPECTED_FEATURE_COUNT = 9
EXPECTED_LEGACY_FEATURE_COUNT = 20
FIXTURE_ROWS = 45
FIXTURE_ELIGIBLE_ROWS = 3
FIXTURE_INELIGIBLE_ROWS = 1
FIT_ROWS = 36
RESERVED_ROWS = 9


def _frame(rows: int = FIXTURE_ROWS) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for index in range(rows):
        record: dict[str, object] = {
            "match_id": f"match-{index:03d}",
            "match_date": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=index),
            "result": index % 3,
        }
        record.update(
            {name: float(index + feature_index + 1) for feature_index, name in enumerate(FEATURES)}
        )
        records.append(record)
    return pd.DataFrame(records)


def _frame_binding(frame: pd.DataFrame) -> producer.CanonicalFrameBinding:
    row_ids = frame["match_id"].astype(str).tolist()
    row_hash = producer._row_id_hash(row_ids)
    return producer.CanonicalFrameBinding(
        artifact_sha256="a" * 64,
        receipt_sha256="b" * 64,
        business_sha256="c" * 64,
        contract_id="canonical_prematch/vnext-v1",
        contract_version="canonical_prematch/vnext/v1",
        feature_names=FEATURES,
        target_population=len(row_ids),
        rows_accounted=len(row_ids),
        eligible_rows=len(row_ids),
        ineligible_rows=0,
        target_row_id_sha256=row_hash,
        eligible_row_id_sha256=row_hash,
        frame_code_revision="d" * 40,
    )


def _canonical_files(
    tmp_path: Path,
    *,
    postmatch_score: int = 1,
) -> tuple[Path, Path]:
    contract = producer.resolve_training_contract()
    rows: list[dict[str, Any]] = []
    for index, outcome in enumerate((0, 1, 2)):
        kickoff = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=index)
        rows.append(
            {
                "canonical_match_id": f"canonical-{index}",
                "target_kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                "feature_as_of_utc": (kickoff - pd.Timedelta(hours=1))
                .isoformat()
                .replace("+00:00", "Z"),
                "training_eligibility": {"status": "ELIGIBLE", "reason_codes": []},
                "features": {
                    name: {"availability_status": "AVAILABLE", "value": float(index + offset + 1)}
                    for offset, name in enumerate(contract.ordered_features)
                },
                "target_label": {
                    "status": "AVAILABLE",
                    "outcome": outcome,
                    "score": postmatch_score + index,
                },
            }
        )
    rows.append(
        {
            "canonical_match_id": "canonical-ineligible",
            "target_kickoff_utc": "2024-01-04T12:00:00Z",
            "feature_as_of_utc": "2024-01-03T12:00:00Z",
            "training_eligibility": {
                "status": "INELIGIBLE",
                "reason_codes": ["FEATURE_UNAVAILABLE:rolling_xg_home"],
            },
            "features": {},
            "target_label": {"status": "UNAVAILABLE", "score": postmatch_score + 99},
        }
    )
    artifact: dict[str, Any] = {
        "schema_version": producer.FRAME_SCHEMA_VERSION,
        "feature_contract": {
            "contract_id": contract.contract_id,
            "feature_contract_version": contract.feature_contract_version,
            "training_feature_order": list(contract.ordered_features),
            "training_feature_count": contract.feature_count,
        },
        "real_training_readiness": "READY_FOR_OFFLINE_CANDIDATE_INPUT",
        "business_content_sha256": "e" * 64,
        "population_accounting": {
            "target_population": 4,
            "rows_accounted": 4,
            "training_eligible": 3,
            "training_ineligible": 1,
        },
        "rows": rows,
    }
    receipt: dict[str, Any] = {
        "schema_version": producer.FRAME_RECEIPT_SCHEMA_VERSION,
        "artifact_sha256": "",
        "output_business_sha256": artifact["business_content_sha256"],
        "target_population": 4,
        "rows_accounted": 4,
        "training_eligible": 3,
        "training_ineligible": 1,
        "training_runs": 0,
        "live_fetch": 0,
        "db_writes": 0,
        "raw_writes": 0,
        "backtest_runs": 0,
        "model_activations": 0,
        "code_revision": "f" * 40,
    }
    artifact_path = tmp_path / "frame.json"
    receipt_path = tmp_path / "frame.receipt.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    receipt["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return artifact_path, receipt_path


def test_training_contract_accepts_only_the_frozen_nine_features() -> None:
    contract = producer.resolve_training_contract()

    assert contract.contract_id == "canonical_prematch/vnext-v1"
    assert contract.feature_contract_version == "canonical_prematch/vnext/v1"
    assert contract.feature_count == EXPECTED_FEATURE_COUNT
    assert contract.ordered_features == FEATURES
    assert producer.resolve_canonical_contract().feature_count == EXPECTED_LEGACY_FEATURE_COUNT


def test_wrong_contract_binding_fails_closed() -> None:
    canonical = producer.resolve_training_contract()

    class WrongRegistry:
        def get_by_contract_id(self, _contract_id: str) -> FeatureContract:
            return replace(canonical, artifact_name="wrong-artifact")

    with pytest.raises(producer.TrainingContractError, match="binding"):
        producer.resolve_training_contract(cast("FeatureContractRegistry", WrongRegistry()))


def test_wrong_feature_contract_and_feature_order_are_rejected() -> None:
    old_features = producer.resolve_canonical_contract().ordered_features
    old_frame = _frame().drop(columns=list(FEATURES))
    old_frame = old_frame.assign(**dict.fromkeys(old_features, 1.0))
    with pytest.raises(producer.TrainingContractError, match=r"non-contract|missing"):
        producer.validate_training_frame(old_frame)

    wrong_order = _frame()[["match_id", "match_date", "result", *reversed(FEATURES)]]
    with pytest.raises(producer.TrainingContractError, match="order"):
        producer.validate_training_frame(wrong_order)


def test_missing_nonfinite_and_postmatch_columns_fail_closed() -> None:
    frame = _frame().drop(columns=[FEATURES[0]])
    with pytest.raises(producer.TrainingContractError, match="feature"):
        producer.validate_training_frame(frame)

    frame = _frame()
    frame.loc[0, FEATURES[1]] = np.nan
    with pytest.raises(producer.TrainingContractError, match="feature"):
        producer.validate_training_frame(frame)

    frame = _frame()
    frame["home_score"] = 3
    with pytest.raises(producer.TrainingContractError, match=r"unsafe|non-contract"):
        producer.validate_training_frame(frame)


def test_canonical_frame_loader_excludes_ineligible_rows_and_isolates_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_path, receipt_path = _canonical_files(tmp_path)
    monkeypatch.setattr(
        canonical_frame_input, "_validate_frame_files_with_canonical_contract", lambda *_: None
    )

    data = producer.load_canonical_feature_frame(artifact_path, receipt_path)

    assert len(data.frame) == FIXTURE_ELIGIBLE_ROWS
    assert data.frame_eligible_rows == FIXTURE_ELIGIBLE_ROWS
    assert data.frame_ineligible_rows == FIXTURE_INELIGIBLE_ROWS
    assert list(data.frame.loc[:, list(FEATURES)].columns) == list(FEATURES)
    assert "score" not in data.frame.columns
    assert data.source_binding is not None
    assert data.source_binding.target_population == FIXTURE_ELIGIBLE_ROWS + FIXTURE_INELIGIBLE_ROWS
    assert data.source_binding.ineligible_rows == FIXTURE_INELIGIBLE_ROWS

    changed_artifact, changed_receipt = _canonical_files(tmp_path / "changed", postmatch_score=999)
    changed = producer.load_canonical_feature_frame(changed_artifact, changed_receipt)
    pd.testing.assert_frame_equal(
        data.frame.loc[:, list(FEATURES)].reset_index(drop=True),
        changed.frame.loc[:, list(FEATURES)].reset_index(drop=True),
    )


def test_canonical_frame_loader_rejects_wrong_order_and_internal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_path, receipt_path = _canonical_files(tmp_path)
    monkeypatch.setattr(
        canonical_frame_input, "_validate_frame_files_with_canonical_contract", lambda *_: None
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["feature_contract"]["training_feature_order"] = list(reversed(FEATURES))
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(producer.TrainingContractError, match="contract binding"):
        producer.load_canonical_feature_frame(artifact_path, receipt_path)

    with pytest.raises(producer.TrainingContractError, match="repository-external"):
        producer.load_canonical_feature_frame(
            PROJECT_ROOT / "config" / "model_feature_contracts.json", receipt_path
        )


def test_temporal_split_is_deterministic_and_strictly_non_overlapping() -> None:
    validated = producer.validate_training_frame(_frame().sample(frac=1, random_state=99))
    first = producer.chronological_split(
        validated, validation_fraction=0.2, min_train_rows=20, min_validation_rows=5
    )
    second = producer.chronological_split(
        validated, validation_fraction=0.2, min_train_rows=20, min_validation_rows=5
    )

    assert first.train["match_id"].tolist() == second.train["match_id"].tolist()
    assert first.validation["match_id"].tolist() == second.validation["match_id"].tolist()
    assert len(first.train) == FIT_ROWS
    assert len(first.validation) == RESERVED_ROWS
    assert first.train_timestamps.max() < first.validation_timestamps.min()
    assert first.train["match_date"].max() < first.validation["match_date"].min()


def test_fit_does_not_touch_reserved_evaluation_rows_or_pass_eval_set() -> None:
    split = producer.chronological_split(
        producer.validate_training_frame(_frame()),
        validation_fraction=0.2,
        min_train_rows=20,
        min_validation_rows=5,
    )

    class SpyEstimator:
        def fit(self, features: pd.DataFrame, labels: pd.Series, **kwargs: Any) -> None:
            self.fit_rows = len(features)
            self.fit_labels = labels.tolist()
            self.fit_kwargs = kwargs
            self.classes_ = np.array([0, 1, 2])
            self.n_features_in_ = len(features.columns)
            self.feature_names_in_ = np.asarray(features.columns)

    spy = SpyEstimator()
    fitted = producer.fit_canonical_model(split, estimator_factory=lambda: spy)

    assert spy.fit_rows == len(split.train)
    assert len(spy.fit_labels) == len(split.train)
    assert spy.fit_kwargs == {"verbose": False}
    assert fitted.scaler.n_samples_seen_ == len(split.train)
    assert not hasattr(spy, "eval_set")


def test_candidate_is_bound_to_frame_ids_metadata_and_explicit_vnext_loader(
    tmp_path: Path,
) -> None:
    before_manifest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    before_registry = hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
    frame = _frame()
    binding = _frame_binding(frame)
    output = tmp_path / "candidate-a.joblib"

    candidate = producer.produce_candidate(
        frame,
        output,
        min_train_rows=20,
        min_validation_rows=5,
        estimators=4,
        max_depth=2,
        source_dataset_identity="fixture-canonical-frame",
        source_binding=binding,
    )
    envelope = joblib.load(output)
    contract = producer.resolve_training_contract()
    loaded = validate_canonical_model_envelope(
        envelope,
        artifact_name=producer.CANDIDATE_ARTIFACT_NAME,
        model_type=producer.CANDIDATE_MODEL_TYPE,
        contract=contract,
    )
    metadata = json.loads(candidate.metadata_path.read_text(encoding="utf-8"))

    assert loaded.feature_names == FEATURES
    assert envelope["contract_id"] == "canonical_prematch/vnext-v1"
    assert envelope["feature_columns"] == list(FEATURES)
    assert envelope["created_as"] == producer.CANDIDATE_CREATED_AS
    assert envelope["activated"] == "NO"
    assert candidate.provenance["input_binding"]["artifact_sha256"] == "a" * 64
    assert candidate.provenance["frame_eligible_rows"] == FIXTURE_ROWS
    assert candidate.provenance["trainer_admitted_rows"] == FIT_ROWS
    assert candidate.provenance["trainer_reserved_rows"] == RESERVED_ROWS
    assert candidate.provenance["trainer_rejected_rows"] == 0
    assert (
        candidate.provenance["training_row_id_sha256"]
        != candidate.provenance["reserved_evaluation_row_id_sha256"]
    )
    assert metadata["training_frame_artifact_hash"] == "a" * 64
    assert metadata["training_frame_receipt_hash"] == "b" * 64
    assert metadata["training_row_count"] == FIT_ROWS
    assert metadata["reserved_evaluation_row_count"] == RESERVED_ROWS
    assert metadata["feature_order"] == list(FEATURES)
    producer.validate_candidate_metadata(metadata, model_sha256=candidate.sha256)

    # The candidate projection is intentionally not the production V1 loader
    # binding; activation remains a separate manifest operation.
    with pytest.raises(ModelArtifactUnavailableError, match="canonical model unavailable"):
        validate_canonical_model_envelope(envelope)
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == before_manifest
    assert hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest() == before_registry


def test_same_seed_has_same_provenance_and_predictions(tmp_path: Path) -> None:
    frame = _frame()
    binding = _frame_binding(frame)
    first = producer.produce_candidate(
        frame,
        tmp_path / "first.joblib",
        min_train_rows=20,
        min_validation_rows=5,
        estimators=4,
        max_depth=2,
        source_binding=binding,
    )
    second = producer.produce_candidate(
        frame,
        tmp_path / "second.joblib",
        min_train_rows=20,
        min_validation_rows=5,
        estimators=4,
        max_depth=2,
        source_binding=binding,
    )
    first_env = joblib.load(first.path)
    second_env = joblib.load(second.path)
    split = producer.chronological_split(
        producer.validate_training_frame(frame), min_train_rows=20, min_validation_rows=5
    )
    x_reserved = split.validation.loc[:, list(FEATURES)]
    first_prob = first_env["model"].predict_proba(first_env["scaler"].transform(x_reserved))
    second_prob = second_env["model"].predict_proba(second_env["scaler"].transform(x_reserved))

    assert first.provenance == second.provenance
    assert np.array_equal(first_prob, second_prob)
    assert first.provenance["random_seed"] == producer.DEFAULT_SEED


def test_candidate_tamper_is_detected_and_failed_writes_leave_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = _frame()
    candidate = producer.produce_candidate(
        frame,
        tmp_path / "candidate.joblib",
        min_train_rows=20,
        min_validation_rows=5,
        estimators=2,
        max_depth=2,
        source_binding=_frame_binding(frame),
    )
    metadata = json.loads(candidate.metadata_path.read_text(encoding="utf-8"))
    producer.validate_candidate_metadata(metadata, model_sha256=candidate.sha256)

    tampered = dict(metadata)
    tampered["activated"] = "YES"
    with pytest.raises(producer.TrainingContractError, match="activation"):
        producer.validate_candidate_metadata(tampered, model_sha256=candidate.sha256)

    tampered_model = tmp_path / "tampered.joblib"
    tampered_model.write_bytes(candidate.path.read_bytes() + b"tamper")
    with pytest.raises(producer.TrainingContractError, match="model hash"):
        producer.validate_candidate_metadata(
            metadata, model_sha256=ArtifactManifest.compute_sha256(tampered_model)
        )

    output = tmp_path / "failed.joblib"
    bad_envelope = {"model": object(), "model_type": producer.CANDIDATE_MODEL_TYPE}
    with pytest.raises(producer.TrainingContractError):
        producer.atomic_write_candidate(
            bad_envelope, output, contract=producer.resolve_training_contract()
        )
    assert not output.exists()

    def fail_dump(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("synthetic serialization failure")

    split = producer.chronological_split(
        producer.validate_training_frame(frame), min_train_rows=20, min_validation_rows=5
    )
    contract = producer.resolve_training_contract()
    fitted = producer.fit_canonical_model(split, estimators=2, max_depth=2)
    envelope = producer.build_candidate_envelope(
        fitted,
        contract,
        producer.build_provenance(
            split,
            None,
            contract,
            seed=producer.DEFAULT_SEED,
            source_dataset_identity="fixture",
            source_binding=_frame_binding(frame),
        ),
    )
    monkeypatch.setattr(producer.joblib, "dump", fail_dump)
    with pytest.raises(producer.TrainingContractError, match="write"):
        producer.atomic_write_candidate(envelope, output, contract=contract)
    assert not output.exists()
    assert not list(tmp_path.glob(".failed.joblib.*.tmp"))


def test_production_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(producer.TrainingContractError, match="production"):
        producer.atomic_write_candidate({}, tmp_path / "model_zoo" / "production" / "model.joblib")


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
    assert output["feature_count"] == EXPECTED_FEATURE_COUNT
    assert output["train_rows"] == FIT_ROWS
    assert output["reserved_evaluation_rows"] == RESERVED_ROWS
    assert output["model_fit_success"] is False
    assert output["final_candidate_exists"] is False
    assert not list(tmp_path.glob("*.joblib"))
