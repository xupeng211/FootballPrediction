"""Canonical per-prediction model-as-of contract tests.

lifecycle: test-fixture

These tests are pure and hermetic.  They do not read the database, access a
provider, persist captures, build features, train, backtest, or activate
V-next.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.ml.inference.feature_contract_boundary_validator import (
    ModelAsOfValidationError,
    validate_model_as_of_context,
)
from src.ml.inference.feature_contract_registry import (
    FeatureContractRegistryError,
    load_feature_contract_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "config" / "model_feature_contracts.json"
MODEL_ASOF_CONTRACT_ID = "canonical-model-asof/v1"
MODEL_ASOF_CONTRACT_VERSION = "v1"
V1_FEATURE_COUNT = 20
V_NEXT_FEATURE_COUNT = 17
DECISION_TIME = "2026-08-17T12:00:00Z"
TARGET_KICKOFF = "2026-08-17T20:00:00Z"


def _context(**overrides: object) -> dict:
    context = {
        "MODEL_ASOF_CONTRACT_ID": MODEL_ASOF_CONTRACT_ID,
        "MODEL_ASOF_CONTRACT_VERSION": MODEL_ASOF_CONTRACT_VERSION,
        "MODEL_DECISION_TIME_UTC": DECISION_TIME,
        "FEATURE_AS_OF_UTC": DECISION_TIME,
        "TARGET_KICKOFF_UTC": TARGET_KICKOFF,
        "PREDICTION_GENERATED_AT_UTC": "2026-08-17T12:00:01Z",
        "POST_DECISION_INFORMATION_DEPENDENCY_COUNT": 0,
        "evidence": [],
    }
    context.update(overrides)
    return context


def _raises_reason(reason_code: str):
    return pytest.raises(ModelAsOfValidationError, match=reason_code)


def _registry_document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_registry_document(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_exact_valid_utc_model_decision_time_is_accepted() -> None:
    assert validate_model_as_of_context(_context()) is True


def test_missing_model_decision_time_is_rejected() -> None:
    context = _context()
    context.pop("MODEL_DECISION_TIME_UTC")
    with _raises_reason("MODEL_DECISION_TIME_MISSING"):
        validate_model_as_of_context(context)


def test_non_utc_timezone_timestamp_is_rejected() -> None:
    with _raises_reason("MODEL_DECISION_TIME_INVALID"):
        validate_model_as_of_context(_context(MODEL_DECISION_TIME_UTC="2026-08-17T20:00:00+08:00"))


@pytest.mark.parametrize("decision_time", ["2026-08-17T20:00:01Z", TARGET_KICKOFF])
def test_prematch_decision_at_or_after_kickoff_is_rejected(decision_time: str) -> None:
    with _raises_reason("DECISION_TIME_NOT_PREMATCH"):
        validate_model_as_of_context(
            _context(
                MODEL_DECISION_TIME_UTC=decision_time,
                FEATURE_AS_OF_UTC=decision_time,
            )
        )


def test_feature_as_of_must_equal_model_decision_time() -> None:
    with _raises_reason("FEATURE_AS_OF_MISMATCH"):
        validate_model_as_of_context(_context(FEATURE_AS_OF_UTC="2026-08-17T11:59:59Z"))


def test_prediction_generated_before_decision_boundary_is_rejected() -> None:
    with _raises_reason("PREDICTION_GENERATED_BEFORE_DECISION_BOUNDARY"):
        validate_model_as_of_context(_context(PREDICTION_GENERATED_AT_UTC="2026-08-17T11:59:59Z"))


def test_prediction_generated_at_does_not_define_or_move_the_feature_boundary() -> None:
    assert (
        validate_model_as_of_context(_context(PREDICTION_GENERATED_AT_UTC="2026-08-17T19:00:00Z"))
        is True
    )


def test_target_kickoff_remains_distinct_from_decision_time() -> None:
    context = _context()
    assert context["TARGET_KICKOFF_UTC"] != context["MODEL_DECISION_TIME_UTC"]
    assert validate_model_as_of_context(context) is True


def test_event_time_before_t_alone_does_not_prove_availability() -> None:
    with _raises_reason("SOURCE_AVAILABILITY_TIME_UNPROVEN"):
        validate_model_as_of_context(
            _context(evidence=[{"SOURCE_EVENT_TIME_UTC": "2026-08-17T10:00:00Z"}])
        )


def test_exact_observed_at_at_or_before_t_can_prove_availability() -> None:
    evidence = {
        "SOURCE_EVENT_TIME_UTC": "2026-08-17T10:00:00Z",
        "SOURCE_OBSERVED_AT_UTC": DECISION_TIME,
        "availability_proof": "EXACT_OBSERVATION_TIMESTAMP",
    }
    assert validate_model_as_of_context(_context(evidence=[evidence])) is True


def test_observed_at_after_t_is_rejected() -> None:
    evidence = {
        "SOURCE_OBSERVED_AT_UTC": "2026-08-17T12:00:01Z",
        "availability_proof": "EXACT_OBSERVATION_TIMESTAMP",
    }
    with _raises_reason("SOURCE_AVAILABLE_AFTER_DECISION"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_future_result_observed_after_t_is_rejected() -> None:
    evidence = {
        "kind": "result",
        "SOURCE_EVENT_TIME_UTC": "2026-08-17T10:00:00Z",
        "SOURCE_OBSERVED_AT_UTC": "2026-08-17T12:00:01Z",
        "availability_proof": "EXACT_OBSERVATION_TIMESTAMP",
    }
    with _raises_reason("SOURCE_AVAILABLE_AFTER_DECISION"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_later_administrative_effective_time_is_rejected() -> None:
    evidence = {
        "SOURCE_EFFECTIVE_TIME_UTC": "2026-08-17T12:00:01Z",
        "SOURCE_OBSERVED_AT_UTC": "2026-08-17T12:00:01Z",
        "availability_proof": "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF",
    }
    with _raises_reason("SOURCE_AVAILABLE_AFTER_DECISION"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_interval_entirely_before_t_can_prove_availability() -> None:
    evidence = {
        "SOURCE_AVAILABILITY_INTERVAL_START_UTC": "2026-08-17T10:00:00Z",
        "SOURCE_AVAILABILITY_INTERVAL_END_UTC": "2026-08-17T11:00:00Z",
        "availability_proof": "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
    }
    assert validate_model_as_of_context(_context(evidence=[evidence])) is True


def test_interval_overlapping_t_fails_closed() -> None:
    evidence = {
        "SOURCE_AVAILABILITY_INTERVAL_START_UTC": "2026-08-17T11:00:00Z",
        "SOURCE_AVAILABILITY_INTERVAL_END_UTC": "2026-08-17T13:00:00Z",
        "availability_proof": "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
    }
    with _raises_reason("SOURCE_TIME_PRECISION_AMBIGUOUS"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_captured_at_alone_cannot_substitute_for_observed_at() -> None:
    evidence = {
        "SOURCE_EVENT_TIME_UTC": "2026-08-17T10:00:00Z",
        "SOURCE_CAPTURED_AT_UTC": DECISION_TIME,
    }
    with _raises_reason("SOURCE_AVAILABILITY_TIME_UNPROVEN"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_provider_defined_closing_cannot_prove_exact_decision_time_odds() -> None:
    evidence = {
        "provider_defined_closing": True,
        "ODDS_SNAPSHOT_OBSERVED_AT_UTC": DECISION_TIME,
        "exact_timestamp_proven": False,
    }
    with _raises_reason("ODDS_DECISION_TIME_UNPROVEN"):
        validate_model_as_of_context(_context(evidence=[evidence]))


def test_registry_binding_preserves_v1_and_vnext_boundaries() -> None:
    registry = load_feature_contract_registry()
    boundary = registry.model_as_of_boundary()
    assert boundary["contract_id"] == MODEL_ASOF_CONTRACT_ID
    assert boundary["version"] == MODEL_ASOF_CONTRACT_VERSION
    assert boundary["invariants"]["v1_feature_count"] == V1_FEATURE_COUNT
    assert boundary["invariants"]["v1_active_default"] == "YES"
    assert boundary["invariants"]["v1_order_changed"] == "NO"
    assert boundary["invariants"]["v1_semantics_changed"] == "NO"
    assert boundary["invariants"]["v_next_feature_count"] == V_NEXT_FEATURE_COUNT
    assert boundary["invariants"]["v_next_default_activated"] == "NO"
    assert boundary["invariants"]["points_feature_semantics_changed"] == "NO"


def test_kickoff_exclusive_rows_are_not_silently_relabelled() -> None:
    boundary = load_feature_contract_registry().model_as_of_boundary()
    assert boundary["historical_compatibility"]["existing_cutoff"] == (
        "SOURCE_EVENT_TIME_LT_TARGET_KICKOFF"
    )
    assert boundary["historical_compatibility"]["automatic_relabeling"] == "NO"
    assert (
        boundary["historical_compatibility"]["automatic_training_eligibility_for_model_asof"]
        == "NO"
    )


def test_post_decision_dependency_is_rejected() -> None:
    with _raises_reason("SOURCE_AVAILABLE_AFTER_DECISION"):
        validate_model_as_of_context(_context(POST_DECISION_INFORMATION_DEPENDENCY_COUNT=1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MODEL_ASOF_CONTRACT_ID", "unknown-model-asof/v9"),
        ("MODEL_ASOF_CONTRACT_VERSION", "v9"),
    ],
)
def test_unknown_context_contract_binding_fails_closed(field: str, value: str) -> None:
    with _raises_reason("CONTRACT_VERSION_MISMATCH"):
        validate_model_as_of_context(_context(**{field: value}))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document["decision_boundaries"]["model_as_of"].update(
            contract_id="canonical-model-asof/v9"
        ),
        lambda document: document["decision_boundaries"]["model_as_of"].update(version="v9"),
        lambda document: document["decision_boundaries"]["model_as_of"]["field_names"].update(
            MODEL_DECISION_TIME_UTC="prediction_generated_at"
        ),
        lambda document: document["decision_boundaries"]["model_as_of"]["invariants"].update(
            feature_as_of_equals_model_decision_time="NO"
        ),
    ],
)
def test_registry_contract_tamper_fails_closed(tmp_path: Path, mutation) -> None:
    document = deepcopy(_registry_document())
    mutation(document)
    with pytest.raises(FeatureContractRegistryError):
        load_feature_contract_registry(_write_registry_document(tmp_path, document))
