"""Canonical standings as-of engine consumer registry boundary tests.

lifecycle: test-fixture
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


def test_standings_asof_engine_consumer_boundary_is_canonical_and_frozen() -> None:
    boundary = load_feature_contract_registry().standings_asof_engine_consumer_boundary()

    assert boundary["contract_id"] == "standings-asof-engine-consumer/v1"
    assert boundary["version"] == "v1"
    assert boundary["status"] == "FROZEN"
    assert boundary["consumer_role"] == "CONSUMER_INTEGRATION"
    assert boundary["input_contract"] == {
        "contract_id": "standings-asof-engine-input/v1",
        "version": "v1",
    }
    assert boundary["ranking_contract"] == {
        "contract_id": "standings/premier-league-point-in-time/v1",
        "version": "v1",
    }
    assert boundary["model_as_of_contract"] == {
        "contract_id": "canonical-model-asof/v1",
        "version": "v1",
    }
    assert boundary["implementation_family"] == "PointInTimeStandingsEngine"
    assert boundary["boundary_policy"] == {
        "legacy": "KICKOFF_EXCLUSIVE",
        "asof": "MODEL_DECISION_TIME_INCLUSIVE",
        "legacy_result": "STRICT_LT_TARGET_KICKOFF",
        "asof_result": "LTE_MODEL_DECISION_TIME",
        "legacy_adjustment": "STRICT_LT_TARGET_KICKOFF",
        "asof_adjustment": "LTE_MODEL_DECISION_TIME",
    }
    assert boundary["consumption_gates"]["generic_caller_cutoff_allowed"] == "NO"
    assert boundary["consumption_gates"]["input_validator_invoked_by_consumer"] == "YES"
    assert (
        boundary["consumption_gates"]["source_dependent_no_table_allowed"]
        == "NO_WITHOUT_TRUSTED_PROOF"
    )
    assert boundary["readiness"]["consumer_implemented"] == "YES"
    assert boundary["readiness"]["runtime_eligible"] == "NO"
    assert boundary["readiness"]["training_eligible"] == "NO"
    assert boundary["source_authority"]["source_authority_validity"] == "NOT_PROVEN"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["decision_boundaries"][
                "standings_asof_engine_consumer"
            ].update(version="v2"),
            "standings as-of engine consumer contract version malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_consumer"][
                "input_contract"
            ].update(contract_id="standings-asof-engine-input/v2"),
            "input_contract.contract_id malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_consumer"][
                "ranking_contract"
            ].update(version="v2"),
            "ranking_contract.version malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_consumer"][
                "boundary_policy"
            ].update(asof="KICKOFF_EXCLUSIVE"),
            "boundary policy.asof malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_consumer"][
                "consumption_gates"
            ].update(structural_validity_alone_allows_consumption="YES"),
            "consumption gates.structural_validity_alone_allows_consumption malformed",
        ),
        (
            lambda document: document["decision_boundaries"]["standings_asof_engine_consumer"][
                "readiness"
            ].update(runtime_eligible="YES"),
            "consumer readiness.runtime_eligible malformed",
        ),
    ],
)
def test_standings_asof_engine_consumer_boundary_drift_fails_closed(
    tmp_path: Path, mutation, message: str
) -> None:
    document = deepcopy(_document())
    mutation(document)

    with pytest.raises(FeatureContractRegistryError, match=message):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_consumer_boundary_is_distinct_from_frozen_input_boundary() -> None:
    registry = load_feature_contract_registry()
    input_boundary = registry.standings_asof_engine_input_boundary()
    consumer_boundary = registry.standings_asof_engine_consumer_boundary()

    assert input_boundary["contract_id"] != consumer_boundary["contract_id"]
    assert input_boundary["readiness"]["engine_consumer_implemented"] == "NO"
    assert consumer_boundary["readiness"]["consumer_implemented"] == "YES"
