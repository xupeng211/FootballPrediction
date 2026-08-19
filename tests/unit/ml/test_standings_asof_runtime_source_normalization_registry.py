"""Canonical registry tests for the generic normalization handoff authority.

lifecycle: permanent
"""

import json
from pathlib import Path

import pytest

from src.ml.inference.feature_contract_registry import (
    FeatureContractRegistryError,
    load_feature_contract_registry,
)
from src.ml.inference.standings_asof_runtime_source_normalization_registry_validator import (
    validate_standings_asof_runtime_source_normalization_registry_boundary,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "config" / "model_feature_contracts.json"


def _document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_document(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_normalization_boundary_is_singular_frozen_and_references_existing_authorities() -> None:
    document = _document()
    boundaries = document["decision_boundaries"]
    boundary = boundaries["standings_asof_runtime_source_normalization"]
    validate_standings_asof_runtime_source_normalization_registry_boundary(
        boundary, FeatureContractRegistryError
    )
    assert list(boundaries).count("standings_asof_runtime_source_normalization") == 1
    assert boundary["contract_id"] == "standings-asof-runtime-source-normalization/v1"
    assert boundary["status"] == "FROZEN"
    assert boundary["normalization_role"] == "RUNTIME_SOURCE_NORMALIZATION_HANDOFF_CONTRACT"
    assert boundary["runtime_capture_contract"] == {
        "contract_id": "canonical-runtime-capture/v1",
        "version": "v1",
    }
    assert boundary["standings_asof_engine_input_contract"] == {
        "contract_id": "standings-asof-engine-input/v1",
        "version": "v1",
    }
    assert boundary["standings_asof_engine_consumer_contract"] == {
        "contract_id": "standings-asof-engine-consumer/v1",
        "version": "v1",
    }
    assert boundary["implementation_status"]["source_specific_normalizer_implemented"] == "NO"
    assert (
        boundary["source_authority"]["generic_normalization_establishes_source_authority"] == "NO"
    )
    assert boundary["runtime_eligibility"]["runtime_eligible"] == "NO"


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("version",), "v2", "normalization contract version malformed"),
        (("status",), "ACTIVE", "normalization contract status malformed"),
        (
            ("ranking_contract", "contract_id"),
            "other-ranking/v1",
            "standings ranking reference.contract_id malformed",
        ),
        (
            ("source_authority", "digest_match_is_source_truth"),
            "YES",
            "source authority.digest_match_is_source_truth malformed",
        ),
        (
            ("source_stream_closure", "result_stream_closure"),
            "PROVEN",
            "normalization source-stream closure status malformed",
        ),
        (
            ("runtime_eligibility", "runtime_eligible"),
            "YES",
            "normalization runtime eligibility malformed",
        ),
    ],
)
def test_normalization_boundary_drift_fails_closed(
    tmp_path: Path, path: tuple[str, ...], value: str, message: str
) -> None:
    document = _document()
    boundary = document["decision_boundaries"]["standings_asof_runtime_source_normalization"]
    cursor = boundary
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(FeatureContractRegistryError, match=message):
        load_feature_contract_registry(_write_document(tmp_path, document))


def test_normalization_boundary_is_not_a_second_input_or_consumer_authority() -> None:
    registry = load_feature_contract_registry()
    document = _document()
    boundaries = document["decision_boundaries"]
    normalization = boundaries["standings_asof_runtime_source_normalization"]
    assert normalization["contract_id"] not in {
        boundaries["runtime_capture"]["contract_id"],
        boundaries["standings_asof_engine_input"]["contract_id"],
        boundaries["standings_asof_engine_consumer"]["contract_id"],
    }
    assert registry.standings_asof_engine_input_boundary()["status"] == "FROZEN"
    assert (
        boundaries["standings_asof_engine_input"]["readiness"]["engine_consumer_implemented"]
        == "NO"
    )
    assert (
        boundaries["standings_asof_engine_consumer"]["readiness"]["consumer_implemented"] == "YES"
    )


def test_normalization_boundary_requires_no_provider_or_runtime_pipeline() -> None:
    boundary = _document()["decision_boundaries"]["standings_asof_runtime_source_normalization"]
    assert boundary["security"] == {
        "provider_selected": "NO",
        "source_specific_payload_parser_count": 0,
        "raw_provider_credentials_allowed": "NO",
        "network_dependency": "NO",
        "database_dependency": "NO",
    }
    assert boundary["implementation_status"]["runtime_pipeline_implemented"] == "NO"
