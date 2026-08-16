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
STANDINGS_CONTRACT_ID = "standings/premier-league-point-in-time/v1"
STANDINGS_EVIDENCE_MEMO_SHA256 = "e09a80735f26d3fe3f949fcc115c853354c3f449dcf1ca6e9da7954846dbb357"

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


def test_vnext_feature_status_boundaries_remain_truthful() -> None:
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
        assert statuses[feature].v_next_status == "RETAINED_PROVEN"
        assert statuses[feature].semantic_definition_status == "SEMANTICS_FROZEN"
        assert statuses[feature].historical_source_status == "PROVEN_FOR_FROZEN_SCOPE"
        assert statuses[feature].runtime_source_status == "NOT_PROVEN"
        assert statuses[feature].training_eligibility == "NOT_READY_RUNTIME_PARITY"
        assert statuses[feature].reason_code == "RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN"

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


def test_standings_semantic_contract_is_frozen_without_runtime_or_training_readiness() -> None:
    document = _registry_document()
    standings = document["decision_boundaries"]["standings"]
    contract = standings["contract"]
    statuses = {
        status["feature_name"]: status for status in document["contracts"][1]["feature_statuses"]
    }

    assert standings["semantic_contract_status"] == "FROZEN"
    assert standings["historical_evidence_status"] == "EVIDENCE_CLOSED_FOR_FROZEN_SCOPE"
    assert standings["unresolved_evidence"] == []
    assert contract["contract_id"] == STANDINGS_CONTRACT_ID
    assert contract["version"] == "v1"
    assert contract["feature_bindings"] == [
        "home_table_position",
        "away_table_position",
        "table_position_diff",
    ]
    assert contract["competition_scope"] == {
        "competition": "Premier League",
        "league_id": 47,
        "frozen_seasons": ["2022/2023", "2023/2024", "2024/2025"],
        "target_population": 888,
    }
    assert [binding["season"] for binding in contract["season_rule_bindings"]] == [
        "2022/2023",
        "2023/2024",
        "2024/2025",
    ]
    assert all(
        binding["rule_identifier"] == "C.1-C.7,C.17,C.18,C.25-C.30"
        for binding in contract["season_rule_bindings"]
    )
    assert contract["ordering_rules"] == ["points", "goal_difference", "goals_scored"]
    assert contract["tie_representation"]["mode"] == (
        "COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS"
    )
    assert contract["tie_representation"]["examples"] == ["1,1,3", "4,5,5,7"]
    assert contract["tie_representation"]["forbidden_tie_breakers"] == [
        "alphabetical club name",
        "team ID",
        "provider order",
        "match ID",
        "database order",
        "filesystem order",
        "ingestion order",
    ]
    assert contract["table_position_diff_rule"] == {
        "orientation": "HOME_POSITION_MINUS_AWAY_POSITION",
        "formula": "home_table_position - away_table_position",
        "requires_both_positions": "YES",
        "unavailable_if_either_missing": "YES",
    }
    assert contract["strict_cutoff_rule"] == "SOURCE_EVENT_TIME_LT_TARGET_KICKOFF"
    assert contract["same_kickoff_rule"] == "EXCLUDED"
    assert contract["postponed_rule"] == "ACTUAL_PLAYED_EVENT_TIME_ONLY"
    assert contract["exception_rule"] == {
        "abandoned": "NOT_TABLE_ELIGIBLE",
        "awarded": "OFFICIAL_TABLE_ELIGIBILITY_REQUIRED",
        "replayed": "OFFICIAL_DISPOSITION_WITHOUT_DOUBLE_COUNT",
        "void": "NOT_TABLE_ELIGIBLE",
        "unknown_status": "FAIL_CLOSED",
    }
    assert contract["administrative_adjustment_rule"]["retroactive_allowed"] == "NO"
    assert (
        contract["administrative_adjustment_rule"]["overlap_reason_code"]
        == "ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS"
    )
    assert contract["evidence_provenance"]["memo_sha256"] == STANDINGS_EVIDENCE_MEMO_SHA256
    assert contract["evidence_provenance"]["target_row_evidence_coverage"] == "887/888"
    assert contract["evidence_provenance"]["expected_unavailable_targets"] == [
        "47_20232024_4193789"
    ]
    assert contract["missing_history_policy"]["reason_code"] == "MISSING_PRIOR_RESULT_EVIDENCE"
    assert contract["source_conflict_policy"]["action"] == "FAIL_CLOSED"
    assert contract["source_conflict_policy"]["majority_vote"] == "FORBIDDEN"
    assert "RESULT_SCORE_CONFLICT" in contract["fail_closed_reason_codes"]
    assert "EVENT_TIME_CONFLICT" in contract["fail_closed_reason_codes"]
    assert all(
        statuses[feature]["runtime_source_status"] == "NOT_PROVEN"
        and statuses[feature]["training_eligibility"] == "NOT_READY_RUNTIME_PARITY"
        for feature in ("home_table_position", "away_table_position", "table_position_diff")
    )


def test_all_standings_features_reference_one_contract_identity() -> None:
    document = _registry_document()
    standings = document["decision_boundaries"]["standings"]["contract"]
    statuses = {
        status["feature_name"]: status for status in document["contracts"][1]["feature_statuses"]
    }

    assert standings["contract_id"] == STANDINGS_CONTRACT_ID
    assert standings["feature_bindings"] == [
        "home_table_position",
        "away_table_position",
        "table_position_diff",
    ]
    for feature in ("home_table_position", "away_table_position", "table_position_diff"):
        assert statuses[feature]["semantic_definition_status"] == "SEMANTICS_FROZEN"
        assert statuses[feature]["historical_source_status"] == "PROVEN_FOR_FROZEN_SCOPE"


def test_standings_contract_rejects_legacy_estimated_positions() -> None:
    document = _registry_document()
    forbidden = document["decision_boundaries"]["legacy_proxy_policy"]["proxies_rejected"]

    assert "estimated standings" in forbidden
    assert (
        document["decision_boundaries"]["standings"]["contract"]["missing_history_policy"]["action"]
        == "UNAVAILABLE"
    )


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
        lambda document: document["contracts"][1]["feature_statuses"][6].update(
            {
                "v_next_status": "RETAINED_PENDING",
                "semantic_definition_status": "CONTRACT_PENDING",
                "historical_source_status": "HISTORY_PENDING",
                "runtime_source_status": "CONTRACT_PENDING",
                "training_eligibility": "NOT_ELIGIBLE_RULE_CLOSURE",
                "reason_code": "STANDINGS_RULE_HISTORY_CLOSURE_REQUIRED",
            }
        ),
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
        lambda document: document["decision_boundaries"]["standings"]["contract"].update(
            {"contract_id": "standings/other/v1"}
        ),
        lambda document: document["decision_boundaries"]["standings"]["contract"].update(
            {"feature_bindings": ["home_table_position"]}
        ),
        lambda document: document["decision_boundaries"]["standings"]["contract"].update(
            {"ordering_rules": ["points", "goals_scored", "goal_difference"]}
        ),
        lambda document: document["decision_boundaries"]["standings"]["contract"][
            "evidence_provenance"
        ].update({"memo_sha256": "0" * 64}),
        lambda document: document["decision_boundaries"]["standings"]["contract"][
            "tie_representation"
        ].update({"mode": "ALPHABETICAL_TIE_BREAK"}),
        lambda document: document["decision_boundaries"]["standings"]["contract"].update(
            {"same_kickoff_rule": "INCLUDED"}
        ),
        lambda document: document["decision_boundaries"]["standings"]["contract"][
            "administrative_adjustment_rule"
        ].update({"retroactive_allowed": "YES"}),
        lambda document: document["decision_boundaries"]["standings"]["contract"].pop(
            "missing_history_policy"
        ),
    ],
)
def test_v2_decision_boundaries_fail_closed_on_semantic_drift(tmp_path: Path, mutate) -> None:
    document = deepcopy(_registry_document())
    mutate(document)
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        FeatureContractRegistryError, match=r"decision|parameter|fallback|activation|standings"
    ):
        load_feature_contract_registry(path)
