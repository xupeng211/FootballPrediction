"""Canonical standings as-of engine-input registry boundary tests.

lifecycle: test-fixture

These tests only validate the source-controlled registry boundary. They do not
fetch data, connect to a database, write data, or start a standings runtime.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.ml.inference.feature_contract_registry import (
    FeatureContractRegistryError,
    load_feature_contract_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "config" / "model_feature_contracts.json"


def _document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_document(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_standings_asof_engine_input_boundary_is_canonical_and_frozen() -> None:
    boundary = load_feature_contract_registry().standings_asof_engine_input_boundary()

    assert boundary["contract_id"] == "standings-asof-engine-input/v1"
    assert boundary["version"] == "v1"
    assert boundary["status"] == "FROZEN"
    assert boundary["standings_contract"] == {
        "contract_id": "standings/premier-league-point-in-time/v1",
        "version": "v1",
    }
    assert boundary["model_as_of_contract"] == {
        "contract_id": "canonical-model-asof/v1",
        "version": "v1",
    }
    assert boundary["runtime_capture_contract"] == {
        "contract_id": "canonical-runtime-capture/v1",
        "version": "v1",
    }
    assert boundary["implementation_family"] == "PointInTimeStandingsEngine"
    assert boundary["evaluation_boundary"]["model_decision_time_is_asof_boundary"] == "YES"
    assert boundary["evaluation_boundary"]["target_kickoff_is_evaluation_boundary"] == "NO"
    assert boundary["fixture_universe"]["authority_proven_by_core"] == "NO"
    assert boundary["no_table_proof"]["core_derivable_reason_codes"] == [
        "SCHEDULE_NOT_YET_REACHED_AT_T"
    ]
    assert boundary["no_table_proof"]["source_dependent_status_proven_by_core"] == "NO"
    assert boundary["no_table_proof"]["evidence_reference_presence_is_external_truth_proof"] == "NO"
    assert boundary["engine_consumption_gates"] == {
        "requires_temporal_eligibility_proven": "YES",
        "requires_source_dependency_gates": "YES",
    }
    assert boundary["readiness"]["engine_consumer_implemented"] == "NO"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_input"].update(
                version="v2"
            ),
            "standings as-of engine input contract version malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_input"][
                "runtime_capture_contract"
            ].update(contract_id="canonical-runtime-capture/v2"),
            "runtime_capture_contract.contract_id malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_input"][
                "fixture_state_taxonomy"
            ].append("UNTRUSTED_STATE"),
            "standings as-of fixture states malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_input"].update(
                caller_source_closure_flags_accepted="YES"
            ),
            "standings as-of engine input boundary malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_input"][
                "no_table_proof"
            ].update(source_dependent_status_proven_by_core="YES"),
            "standings as-of no-table proof.source_dependent_status_proven_by_core malformed",
        ),
    ],
)
def test_standings_asof_engine_input_boundary_drift_fails_closed(
    tmp_path: Path, mutation, message: str
) -> None:
    document = deepcopy(_document())
    mutation(document)

    with pytest.raises(FeatureContractRegistryError, match=message):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_standings_asof_boundary_keeps_stream_closure_distinct() -> None:
    boundary = load_feature_contract_registry().standings_asof_engine_input_boundary()

    assert boundary["source_stream_closure"] == {
        "fixture_universe_reference_match": "STRUCTURALLY_VALID",
        "fixture_universe_closure": "NOT_PROVEN",
        "fixture_status_evidence_closure": "NOT_PROVEN",
        "result_evidence_closure": "NOT_PROVEN",
        "admin_adjustment_stream_closure": "NOT_PROVEN",
    }


def test_standings_asof_boundary_separates_schedule_and_source_proof() -> None:
    boundary = load_feature_contract_registry().standings_asof_engine_input_boundary()

    assert boundary["no_table_proof"]["source_dependent_reason_codes"] == [
        "PROVEN_POSTPONED_NOT_PLAYED_BY_T",
        "PROVEN_NOT_FINAL_BY_T",
        "PROVEN_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T",
    ]
    assert boundary["no_table_proof"]["schedule_not_yet_relation_proven_by_core"] == "YES"
    assert boundary["no_table_proof"]["structurally_valid_implies_temporal_proven"] == "NO"
    assert boundary["no_table_proof"]["structurally_valid_implies_runtime_eligible"] == "NO"
