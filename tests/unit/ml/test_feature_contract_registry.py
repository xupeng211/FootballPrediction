"""PR-2 versioned canonical inference feature-contract registry tests.

lifecycle: test-fixture

These tests are hermetic: they read the git-tracked registry or temporary JSON
documents only.  They never load a model, train, connect to a database, fetch
network data, or create model artifacts.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.ml.feature_adapter import V26_6_PreMatchAdapter
from src.ml.inference.feature_contract_registry import (
    FeatureContractNotFoundError,
    FeatureContractRegistry,
    FeatureContractRegistryError,
    load_feature_contract_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "config" / "model_feature_contracts.json"
CONTRACT_ID = "v26_7_aligned/v1"
MODEL_TYPE = "v26_7_aligned"
ARTIFACT_NAME = "v26_7_aligned"
CANONICAL_FEATURE_COUNT = 20


def _canonical_document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_document(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_canonical_contract_loads_and_preserves_identity_and_count() -> None:
    registry = load_feature_contract_registry()
    contract = registry.get_by_contract_id(CONTRACT_ID)

    assert contract.contract_id == CONTRACT_ID
    assert contract.artifact_name == ARTIFACT_NAME
    assert contract.model_type == MODEL_TYPE
    assert contract.feature_contract_version == "v26_6_pre_match/v1"
    assert contract.feature_count == CANONICAL_FEATURE_COUNT
    assert len(contract.ordered_features) == contract.feature_count


def test_canonical_model_lookup_requires_exact_binding() -> None:
    registry = load_feature_contract_registry()

    contract = registry.get_for_model(MODEL_TYPE, ARTIFACT_NAME)
    assert contract.contract_id == CONTRACT_ID
    with pytest.raises(FeatureContractNotFoundError):
        registry.get_for_model(MODEL_TYPE, "different_artifact")
    with pytest.raises(FeatureContractNotFoundError):
        registry.get_for_model("unknown_model", ARTIFACT_NAME)
    with pytest.raises(FeatureContractNotFoundError):
        registry.get_by_contract_id("unknown-contract/v1")


def test_registry_order_matches_current_canonical_inference_feature_producer() -> None:
    contract = load_feature_contract_registry().get_for_model(MODEL_TYPE, ARTIFACT_NAME)
    runtime_features = V26_6_PreMatchAdapter().get_required_features()

    # This is the drift guard: the registry is an independent source-controlled
    # declaration, while the adapter remains the runtime vector producer.
    assert list(contract.ordered_features) == runtime_features
    assert contract.feature_count == len(runtime_features)


def test_swapping_registry_features_is_detectable_as_order_drift(tmp_path: Path) -> None:
    document = _canonical_document()
    features = document["contracts"][0]["ordered_features"]
    features[0], features[1] = features[1], features[0]
    drifted = load_feature_contract_registry(
        _write_document(tmp_path, document)
    ).get_by_contract_id(CONTRACT_ID)

    runtime_features = V26_6_PreMatchAdapter().get_required_features()
    assert list(drifted.ordered_features) != runtime_features
    assert set(drifted.ordered_features) == set(runtime_features)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda doc: doc["contracts"][0].pop("ordered_features"), "malformed"),
        (lambda doc: doc["contracts"][0].update(feature_count=19), "mismatch"),
        (
            lambda doc: doc["contracts"][0]["ordered_features"].__setitem__(1, "rolling_xg_home"),
            "duplicate",
        ),
        (lambda doc: doc["contracts"][0].update(model_type=""), "binding malformed"),
    ],
)
def test_malformed_contracts_fail_closed(tmp_path: Path, mutation, message: str) -> None:
    document = _canonical_document()
    mutation(document)

    with pytest.raises(FeatureContractRegistryError, match=message):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_duplicate_contract_id_fails_closed(tmp_path: Path) -> None:
    document = _canonical_document()
    document["contracts"].append(deepcopy(document["contracts"][0]))

    with pytest.raises(FeatureContractRegistryError, match="duplicate feature contract id"):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_unsupported_registry_version_fails_closed(tmp_path: Path) -> None:
    document = _canonical_document()
    document["schema_version"] = "model-feature-contract-registry/v999"

    with pytest.raises(FeatureContractRegistryError, match="unsupported"):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_legacy_registry_requires_explicit_compatibility_flag(tmp_path: Path) -> None:
    document = _canonical_document()
    document["schema_version"] = "model-feature-contract-registry/v1"
    document.pop("migration_map")
    document.pop("decision_boundaries")
    path = _write_document(tmp_path, document)

    with pytest.raises(FeatureContractRegistryError, match="unsupported"):
        load_feature_contract_registry(path)

    registry = FeatureContractRegistry(path, allow_legacy_schema=True)
    assert registry.get_by_contract_id(CONTRACT_ID).feature_count == CANONICAL_FEATURE_COUNT


def test_registry_reader_is_inert_without_model_or_database_dependencies(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    registry = load_feature_contract_registry(REGISTRY_PATH)
    assert registry.get_by_contract_id(CONTRACT_ID).feature_count == CANONICAL_FEATURE_COUNT
    # tests/conftest.py may create empty safety directories; the reader must
    # not create any model files or populate those directories.
    assert not list((tmp_path / "models").rglob("*"))
    assert not list((tmp_path / "model_zoo").rglob("*"))
