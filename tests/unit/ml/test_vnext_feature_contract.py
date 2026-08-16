"""V-next canonical feature-contract freeze tests.

lifecycle: test-fixture

These tests validate the single git-tracked contract registry. They do not
activate V-next, build a training frame, fetch data, or select ELO parameters.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.ml.feature_adapters.prematch import V26_6_PreMatchAdapter
from src.ml.inference.feature_contract_registry import (
    V1_CONTRACT_ID,
    VNEXT_CONTRACT_ID,
    FeatureContractRegistryError,
    load_feature_contract_registry,
)
from src.ml.training.canonical_training_producer import resolve_canonical_contract

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "config" / "model_feature_contracts.json"
MODEL_MANIFEST_PATH = REPO_ROOT / "config" / "model_artifacts.json"
V1_FEATURE_COUNT = 20
V_NEXT_FEATURE_COUNT = 17

V1_FEATURES = (
    "rolling_xg_home",
    "rolling_xg_away",
    "rolling_shots_on_target_home",
    "rolling_shots_on_target_away",
    "rolling_possession_home",
    "rolling_possession_away",
    "rolling_team_rating_home",
    "rolling_team_rating_away",
    "home_table_position",
    "away_table_position",
    "table_position_diff",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    "raw_elo_gap",
    "adjusted_elo_gap",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
)

V_NEXT_FEATURES = (
    "rolling_xg_home",
    "rolling_xg_away",
    "rolling_shots_on_target_home",
    "rolling_shots_on_target_away",
    "rolling_possession_home",
    "rolling_possession_away",
    "home_table_position",
    "away_table_position",
    "table_position_diff",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    "raw_elo_gap",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
)

REMOVED_FROM_V_NEXT = {
    "rolling_team_rating_home",
    "rolling_team_rating_away",
    "adjusted_elo_gap",
}


def _registry_document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_v1_contract_remains_frozen_and_default() -> None:
    registry = load_feature_contract_registry()
    contract = registry.get_by_contract_id(V1_CONTRACT_ID)

    assert contract.feature_count == V1_FEATURE_COUNT
    assert contract.ordered_features == V1_FEATURES
    assert contract.ordered_features == tuple(V26_6_PreMatchAdapter().get_required_features())
    assert contract.activation_status == "ACTIVE_DEFAULT"
    assert resolve_canonical_contract().contract_id == V1_CONTRACT_ID


def test_vnext_contract_is_exactly_17_and_not_activated() -> None:
    registry = load_feature_contract_registry()
    contract = registry.get_by_contract_id(VNEXT_CONTRACT_ID)

    assert contract.feature_count == V_NEXT_FEATURE_COUNT
    assert contract.ordered_features == V_NEXT_FEATURES
    assert not set(contract.ordered_features) & REMOVED_FROM_V_NEXT
    assert contract.activation_status == "DEFINED_NOT_ACTIVATED"
    assert len(contract.feature_statuses) == contract.feature_count
    assert tuple(status.feature_name for status in contract.feature_statuses) == V_NEXT_FEATURES


def test_v1_to_vnext_migration_covers_each_v1_feature_once() -> None:
    migrations = load_feature_contract_registry().migration_map()

    assert len(migrations) == len(V1_FEATURES) == V1_FEATURE_COUNT
    assert tuple(item.from_feature for item in migrations) == V1_FEATURES
    assert {item.from_feature for item in migrations} == set(V1_FEATURES)
    assert {
        item.from_feature for item in migrations if item.classification == "REMOVED"
    } == REMOVED_FROM_V_NEXT


def test_v1_to_vnext_migration_covers_each_vnext_feature_once(tmp_path: Path) -> None:
    document = _registry_document()
    document["migration_map"]["entries"][0]["to_feature"] = "rolling_xg_away"
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(FeatureContractRegistryError, match="target coverage"):
        load_feature_contract_registry(path)


def test_vnext_pending_families_remain_unavailable_or_ineligible() -> None:
    contract = load_feature_contract_registry().get_by_contract_id(VNEXT_CONTRACT_ID)
    statuses = {status.feature_name: status for status in contract.feature_statuses}

    for feature in ("rolling_shots_on_target_home", "rolling_shots_on_target_away"):
        assert statuses[feature].semantic_definition_status == "SEMANTICS_PENDING"
        assert statuses[feature].historical_source_status == "SOURCE_PENDING"
        assert statuses[feature].training_eligibility == "NOT_ELIGIBLE_SOURCE_CLOSURE"

    for feature in ("rolling_possession_home", "rolling_possession_away"):
        assert statuses[feature].historical_source_status == "UNAVAILABLE"
        assert statuses[feature].runtime_source_status == "UNAVAILABLE"
        assert statuses[feature].training_eligibility == "NOT_ELIGIBLE_SOURCE_UNAVAILABLE"

    for feature in ("home_table_position", "away_table_position", "table_position_diff"):
        assert statuses[feature].semantic_definition_status == "CONTRACT_PENDING"
        assert statuses[feature].training_eligibility == "NOT_ELIGIBLE_RULE_CLOSURE"

    assert statuses["raw_elo_gap"].semantic_definition_status == (
        "OWNER_PARAMETER_DECISION_REQUIRED"
    )
    assert statuses["raw_elo_gap"].training_eligibility == ("NOT_ELIGIBLE_OWNER_PARAMETER_CONTRACT")


def test_vnext_does_not_create_a_model_binding_or_reach_legacy_proxies() -> None:
    document = _registry_document()
    boundaries = document["decision_boundaries"]
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert boundaries["legacy_proxy_policy"]["canonical_v_next_reachability"] == "NO"
    assert boundaries["activation"]["v_next_default_activated"] == "NO"
    assert not any(
        artifact.get("model_type") == "canonical_prematch_vnext"
        for artifact in manifest["artifacts"]
    )
    assert resolve_canonical_contract().activation_status == "ACTIVE_DEFAULT"


def test_vnext_schema_metadata_fails_closed_when_status_matrix_is_removed(tmp_path: Path) -> None:
    document = _registry_document()
    document["contracts"][1].pop("feature_statuses")
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(FeatureContractRegistryError, match="feature status matrix"):
        load_feature_contract_registry(path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda document: document["contracts"][1]["feature_statuses"][0].update(
            {"runtime_source_status": "PROVEN"}
        ),
        lambda document: document["contracts"][1]["feature_statuses"][-1].update(
            {"training_eligibility": "ELIGIBLE"}
        ),
    ],
)
def test_vnext_feature_status_values_fail_closed(tmp_path: Path, mutate) -> None:
    document = deepcopy(_registry_document())
    mutate(document)
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(FeatureContractRegistryError, match="feature status values"):
        load_feature_contract_registry(path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda document: document["decision_boundaries"]["raw_elo"].update(
            {"training_eligible": "YES"}
        ),
        lambda document: document["decision_boundaries"]["raw_elo"]["parameter_sheet"][3].update(
            {"k_factor": 32}
        ),
        lambda document: document["decision_boundaries"]["activation"].update(
            {"v_next_default_activated": "YES"}
        ),
        lambda document: document["decision_boundaries"]["possession"].update(
            {"fallbacks_forbidden": ["50/50"]}
        ),
    ],
)
def test_v2_decision_boundaries_fail_closed_on_semantic_drift(tmp_path: Path, mutate) -> None:
    document = deepcopy(_registry_document())
    mutate(document)
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        FeatureContractRegistryError, match=r"decision|parameter|fallback|activation"
    ):
        load_feature_contract_registry(path)
