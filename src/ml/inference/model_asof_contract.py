"""Pure validation for the canonical per-prediction model-as-of contract.

lifecycle: permanent
component: Specialized / Internal (canonical temporal contract validator; not a
source, capture, or runtime adapter)

The git-tracked model feature-contract registry remains the semantic authority.
This module validates that binding and validates one immutable prediction
context without fetching data, reading a database, consulting wall-clock time,
or inferring an observation timestamp.
"""

from datetime import UTC, datetime
from typing import Any

MODEL_ASOF_CONTRACT_ID = "canonical-model-asof/v1"
MODEL_ASOF_CONTRACT_VERSION = "v1"
_V1_FEATURE_COUNT = 20
_V_NEXT_FEATURE_COUNT = 17
MODEL_ASOF_FIELD_NAMES = frozenset(
    {
        "MODEL_DECISION_TIME_UTC",
        "FEATURE_AS_OF_UTC",
        "TARGET_KICKOFF_UTC",
        "SOURCE_EVENT_TIME_UTC",
        "SOURCE_EFFECTIVE_TIME_UTC",
        "SOURCE_OBSERVED_AT_UTC",
        "SOURCE_CAPTURED_AT_UTC",
        "PREDICTION_GENERATED_AT_UTC",
        "ODDS_SNAPSHOT_OBSERVED_AT_UTC",
    }
)
MODEL_ASOF_FIELD_DESCRIPTIONS = {
    "MODEL_DECISION_TIME_UTC": "logical_model_information_boundary",
    "FEATURE_AS_OF_UTC": "same_logical_information_boundary_as_model_decision_time",
    "TARGET_KICKOFF_UTC": "target_match_scheduling_context",
    "SOURCE_EVENT_TIME_UTC": "when_event_happened",
    "SOURCE_EFFECTIVE_TIME_UTC": "when_fact_or_disposition_became_effective",
    "SOURCE_OBSERVED_AT_UTC": "when_source_observed_or_published_fact",
    "SOURCE_CAPTURED_AT_UTC": "when_system_captured_or_persisted_source_record",
    "PREDICTION_GENERATED_AT_UTC": "output_execution_telemetry",
    "ODDS_SNAPSHOT_OBSERVED_AT_UTC": "when_used_market_snapshot_was_observed",
}
MODEL_ASOF_AVAILABILITY_FORMS = [
    "EXACT_OBSERVATION_TIMESTAMP",
    "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF",
    "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
]

_MODEL_ASOF_BOUNDARY_FIELDS = {
    "contract_id",
    "version",
    "policy",
    "status",
    "field_names",
    "invariants",
    "availability_proof",
    "strict_value_evaluation",
    "historical_compatibility",
    "implementation_status",
    "fail_closed_reason_codes",
}
_MODEL_ASOF_INVARIANTS = {
    "feature_as_of_equals_model_decision_time": "YES",
    "target_kickoff_is_model_decision_time": "NO",
    "prematch_decision_requires_t_lt_kickoff": "YES",
    "prediction_generated_at_is_feature_authority": "NO",
    "prediction_generated_at_must_be_gte_decision_when_present": "YES",
    "source_event_time_is_observation_time": "NO",
    "source_captured_at_is_observation_time_by_default": "NO",
    "post_decision_information_allowed": "NO",
    "ambiguous_time_interval_fails_closed": "YES",
    "current_kickoff_exclusive_rows_relabelled_as_asof_rows": "NO",
    "points_feature_semantics_changed": "NO",
    "v1_active_default": "YES",
    "v1_order_changed": "NO",
    "v1_semantics_changed": "NO",
    "v_next_order_changed": "NO",
    "v_next_default_activated": "NO",
    "strict_value_evaluation_requires_shared_information_boundary": "YES",
}
_MODEL_ASOF_AVAILABILITY = {
    "unknown": "FAIL_CLOSED",
    "after_decision": "REJECT",
    "precision_overlap": "FAIL_CLOSED",
    "event_time_alone_proves_availability": "NO",
    "captured_at_substitutes_observed_at_by_default": "NO",
}
_MODEL_ASOF_STRICT_VALUE = {
    "odds_observed_at_field": "ODDS_SNAPSHOT_OBSERVED_AT_UTC",
    "odds_must_be_proven_observable_no_later_than_t": "YES",
    "odds_snapshot_must_equal_t": "NO",
    "odds_freshness_policy_status": "OWNER_DECISION_OR_FUTURE_CONTRACT_REQUIRED",
    "status": "NOT_READY",
}
_MODEL_ASOF_HISTORICAL = {
    "existing_standings_contract_id": "standings/premier-league-point-in-time/v1",
    "existing_cutoff": "SOURCE_EVENT_TIME_LT_TARGET_KICKOFF",
    "semantic": "KICKOFF_EXCLUSIVE_POINT_IN_TIME",
    "coverage": "887/888",
    "engine_gd_a03_parity": "888/888",
    "current_rows_are_kickoff_reference_projection": "YES",
    "automatic_training_eligibility_for_model_asof": "NO",
    "automatic_relabeling": "NO",
    "known_unavailable_target": "47_20232024_4193789",
    "known_unavailable_reason": "ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS",
}
_MODEL_ASOF_IMPLEMENTATION = {
    "runtime_capture_contract_implemented": "NO",
    "runtime_provider_implementation_started": "NO",
    "standings_runtime_implementation_started": "NO",
    "runtime_eligible": "NO",
    "training_eligible": "NO",
    "strict_decision_time_value_evaluation": "NOT_READY",
    "feature_frame_readiness": "NOT_READY",
    "real_training_readiness": "NOT_READY",
    "train_inference_numeric_parity": "NOT_PROVEN",
    "golden_dataset_complete": "NO",
}
_MODEL_ASOF_REASON_CODES = [
    "MODEL_DECISION_TIME_MISSING",
    "MODEL_DECISION_TIME_INVALID",
    "DECISION_TIME_NOT_PREMATCH",
    "FEATURE_AS_OF_MISSING",
    "FEATURE_AS_OF_INVALID",
    "FEATURE_AS_OF_MISMATCH",
    "TARGET_KICKOFF_MISSING",
    "TARGET_KICKOFF_INVALID",
    "PREDICTION_GENERATED_AT_INVALID",
    "PREDICTION_GENERATED_BEFORE_DECISION_BOUNDARY",
    "SOURCE_AVAILABILITY_TIME_UNPROVEN",
    "SOURCE_AVAILABLE_AFTER_DECISION",
    "SOURCE_TIME_PRECISION_AMBIGUOUS",
    "ODDS_DECISION_TIME_UNPROVEN",
    "CONTRACT_VERSION_MISMATCH",
]


class ModelAsOfValidationError(ValueError):
    """Raised when a prediction context violates canonical model-as-of/v1."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _exact_object(
    value: Any, fields: set[str] | frozenset[str], label: str, error_type: type[ValueError]
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise error_type(f"{label} malformed")
    return value


def _text(
    value: Any, label: str, error_type: type[ValueError], expected: str | None = None
) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or (expected is not None and value != expected)
    ):
        raise error_type(f"{label} malformed")


def _text_fields(
    value: dict[str, Any], fields: set[str], label: str, error_type: type[ValueError]
) -> None:
    for field in fields:
        _text(value[field], f"{label}.{field}", error_type)


def _text_list(
    value: Any,
    label: str,
    error_type: type[ValueError],
    expected: list[str] | None = None,
) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise error_type(f"{label} malformed")
    if expected is not None and value != expected:
        raise error_type(f"{label} malformed")


def _validate_expected_texts(
    value: dict[str, Any], expected: dict[str, str], label: str, error_type: type[ValueError]
) -> None:
    for field, expected_value in expected.items():
        _text(value[field], f"{label}.{field}", error_type, expected_value)


def validate_model_asof_registry_boundary(boundary: Any, error_type: type[ValueError]) -> None:
    """Validate the one model-as-of boundary stored in the canonical registry."""
    model_as_of = _exact_object(
        boundary, _MODEL_ASOF_BOUNDARY_FIELDS, "model-as-of decision boundary", error_type
    )
    _text(model_as_of["contract_id"], "model-as-of contract id", error_type, MODEL_ASOF_CONTRACT_ID)
    _text(
        model_as_of["version"],
        "model-as-of contract version",
        error_type,
        MODEL_ASOF_CONTRACT_VERSION,
    )
    _text(model_as_of["policy"], "model-as-of policy", error_type, "EXPLICIT_PER_PREDICTION_AS_OF")
    _text(model_as_of["status"], "model-as-of status", error_type, "FROZEN")

    field_names = _exact_object(
        model_as_of["field_names"], MODEL_ASOF_FIELD_NAMES, "model-as-of field taxonomy", error_type
    )
    _validate_expected_texts(
        field_names, MODEL_ASOF_FIELD_DESCRIPTIONS, "model-as-of field taxonomy", error_type
    )

    invariants = _exact_object(
        model_as_of["invariants"],
        set(_MODEL_ASOF_INVARIANTS) | {"v1_feature_count", "v_next_feature_count"},
        "model-as-of invariants",
        error_type,
    )
    _validate_expected_texts(
        invariants, _MODEL_ASOF_INVARIANTS, "model-as-of invariant", error_type
    )
    if (
        isinstance(invariants["v1_feature_count"], bool)
        or invariants["v1_feature_count"] != _V1_FEATURE_COUNT
    ):
        raise error_type("model-as-of invariant.v1_feature_count malformed")
    if (
        isinstance(invariants["v_next_feature_count"], bool)
        or invariants["v_next_feature_count"] != _V_NEXT_FEATURE_COUNT
    ):
        raise error_type("model-as-of invariant.v_next_feature_count malformed")

    availability = _exact_object(
        model_as_of["availability_proof"],
        {
            "allowed_forms",
            "unknown",
            "after_decision",
            "precision_overlap",
            "event_time_alone_proves_availability",
            "captured_at_substitutes_observed_at_by_default",
        },
        "model-as-of availability proof",
        error_type,
    )
    _text_list(
        availability["allowed_forms"],
        "model-as-of availability proof.allowed_forms",
        error_type,
        MODEL_ASOF_AVAILABILITY_FORMS,
    )
    _validate_expected_texts(
        availability, _MODEL_ASOF_AVAILABILITY, "model-as-of availability proof", error_type
    )

    strict_value = _exact_object(
        model_as_of["strict_value_evaluation"],
        {
            "odds_observed_at_field",
            "odds_must_be_proven_observable_no_later_than_t",
            "odds_snapshot_must_equal_t",
            "odds_freshness_policy_status",
            "status",
        },
        "model-as-of strict value evaluation",
        error_type,
    )
    _validate_expected_texts(
        strict_value, _MODEL_ASOF_STRICT_VALUE, "model-as-of strict value evaluation", error_type
    )

    historical = _exact_object(
        model_as_of["historical_compatibility"],
        set(_MODEL_ASOF_HISTORICAL),
        "model-as-of historical compatibility",
        error_type,
    )
    _validate_expected_texts(
        historical, _MODEL_ASOF_HISTORICAL, "model-as-of historical compatibility", error_type
    )

    implementation = _exact_object(
        model_as_of["implementation_status"],
        set(_MODEL_ASOF_IMPLEMENTATION),
        "model-as-of implementation status",
        error_type,
    )
    _validate_expected_texts(
        implementation, _MODEL_ASOF_IMPLEMENTATION, "model-as-of implementation status", error_type
    )
    _text_list(
        model_as_of["fail_closed_reason_codes"],
        "model-as-of fail-closed reason codes",
        error_type,
        _MODEL_ASOF_REASON_CODES,
    )


def _parse_model_asof_utc(value: Any, field: str, reason_code: str) -> datetime:
    """Parse one exact UTC timestamp without consulting wall-clock state."""
    if not isinstance(value, str) or not value.strip():
        raise ModelAsOfValidationError(reason_code, f"{field} must be an absolute UTC timestamp")
    if value.endswith("Z"):
        normalized = f"{value[:-1]}+00:00"
    elif value.endswith("+00:00"):
        normalized = value
    else:
        raise ModelAsOfValidationError(reason_code, f"{field} must use UTC Z or +00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ModelAsOfValidationError(reason_code, f"{field} is malformed") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ModelAsOfValidationError(reason_code, f"{field} must be absolute UTC")
    return parsed.astimezone(UTC)


def _required_model_asof_timestamp(
    context: dict[str, Any], field: str, missing_reason: str, invalid_reason: str
) -> datetime:
    if field not in context or context[field] is None:
        raise ModelAsOfValidationError(missing_reason, f"{field} is required")
    return _parse_model_asof_utc(context[field], field, invalid_reason)


def _optional_model_asof_timestamp(
    evidence: dict[str, Any], field: str, invalid_reason: str
) -> datetime | None:
    value = evidence.get(field)
    if value is None:
        return None
    return _parse_model_asof_utc(value, field, invalid_reason)


def _validate_model_asof_evidence(  # noqa: C901
    evidence: Any, decision_time: datetime
) -> None:
    """Validate one source evidence proof against T; unknown evidence fails closed."""
    if not isinstance(evidence, dict):
        raise ModelAsOfValidationError(
            "SOURCE_AVAILABILITY_TIME_UNPROVEN", "source evidence must be an object"
        )

    kind = evidence.get("kind")
    is_odds = (
        kind == "odds"
        or "ODDS_SNAPSHOT_OBSERVED_AT_UTC" in evidence
        or evidence.get("provider_defined_closing") is True
    )
    if is_odds:
        raise ModelAsOfValidationError(
            "ODDS_DECISION_TIME_UNPROVEN",
            "strict value evaluation is not ready and no bound odds temporal contract exists",
        )

    source_event_time = _optional_model_asof_timestamp(
        evidence, "SOURCE_EVENT_TIME_UTC", "SOURCE_TIME_PRECISION_AMBIGUOUS"
    )
    source_effective_time = _optional_model_asof_timestamp(
        evidence, "SOURCE_EFFECTIVE_TIME_UTC", "SOURCE_TIME_PRECISION_AMBIGUOUS"
    )
    source_observed_at = _optional_model_asof_timestamp(
        evidence, "SOURCE_OBSERVED_AT_UTC", "SOURCE_TIME_PRECISION_AMBIGUOUS"
    )
    _optional_model_asof_timestamp(
        evidence, "SOURCE_CAPTURED_AT_UTC", "SOURCE_TIME_PRECISION_AMBIGUOUS"
    )

    for field, value in (
        ("SOURCE_EVENT_TIME_UTC", source_event_time),
        ("SOURCE_EFFECTIVE_TIME_UTC", source_effective_time),
    ):
        if value is not None and value > decision_time:
            raise ModelAsOfValidationError("SOURCE_AVAILABLE_AFTER_DECISION", f"{field} is after T")
    if source_observed_at is not None and source_observed_at > decision_time:
        raise ModelAsOfValidationError(
            "SOURCE_AVAILABLE_AFTER_DECISION", "source evidence was observed after T"
        )

    proof = evidence.get("availability_proof")
    interval_start = _optional_model_asof_timestamp(
        evidence,
        "SOURCE_AVAILABILITY_INTERVAL_START_UTC",
        "SOURCE_TIME_PRECISION_AMBIGUOUS",
    )
    interval_end = _optional_model_asof_timestamp(
        evidence,
        "SOURCE_AVAILABILITY_INTERVAL_END_UTC",
        "SOURCE_TIME_PRECISION_AMBIGUOUS",
    )
    if interval_start is not None or interval_end is not None:
        if interval_start is None or interval_end is None or interval_start >= interval_end:
            raise ModelAsOfValidationError(
                "SOURCE_TIME_PRECISION_AMBIGUOUS", "source availability interval is malformed"
            )
        if interval_end < decision_time and proof == "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T":
            return
        if interval_start > decision_time:
            raise ModelAsOfValidationError(
                "SOURCE_AVAILABLE_AFTER_DECISION", "source availability starts after T"
            )
        raise ModelAsOfValidationError(
            "SOURCE_TIME_PRECISION_AMBIGUOUS", "source availability interval overlaps T"
        )

    if proof == "EXACT_OBSERVATION_TIMESTAMP" and source_observed_at is not None:
        return
    if (
        proof == "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF"
        and source_effective_time is not None
        and source_observed_at is not None
    ):
        return
    raise ModelAsOfValidationError(
        "SOURCE_AVAILABILITY_TIME_UNPROVEN",
        "event/effective/captured time does not prove information availability by T",
    )


def validate_model_as_of_context(  # noqa: C901
    context: dict[str, Any], *, require_prematch: bool = True
) -> bool:
    """Validate one immutable prediction context against canonical model-asof/v1."""
    if not isinstance(context, dict):
        raise ModelAsOfValidationError(
            "CONTRACT_VERSION_MISMATCH", "prediction context must be an object"
        )

    if context.get("MODEL_ASOF_CONTRACT_ID") != MODEL_ASOF_CONTRACT_ID:
        raise ModelAsOfValidationError(
            "CONTRACT_VERSION_MISMATCH", "prediction context model-as-of contract ID is unknown"
        )
    if context.get("MODEL_ASOF_CONTRACT_VERSION") != MODEL_ASOF_CONTRACT_VERSION:
        raise ModelAsOfValidationError(
            "CONTRACT_VERSION_MISMATCH",
            "prediction context model-as-of contract version is unknown",
        )

    decision_time = _required_model_asof_timestamp(
        context,
        "MODEL_DECISION_TIME_UTC",
        "MODEL_DECISION_TIME_MISSING",
        "MODEL_DECISION_TIME_INVALID",
    )
    feature_as_of = _required_model_asof_timestamp(
        context,
        "FEATURE_AS_OF_UTC",
        "FEATURE_AS_OF_MISSING",
        "FEATURE_AS_OF_INVALID",
    )
    target_kickoff = _required_model_asof_timestamp(
        context,
        "TARGET_KICKOFF_UTC",
        "TARGET_KICKOFF_MISSING",
        "TARGET_KICKOFF_INVALID",
    )

    if feature_as_of != decision_time:
        raise ModelAsOfValidationError(
            "FEATURE_AS_OF_MISMATCH", "FEATURE_AS_OF_UTC must equal MODEL_DECISION_TIME_UTC"
        )
    if require_prematch and decision_time >= target_kickoff:
        raise ModelAsOfValidationError(
            "DECISION_TIME_NOT_PREMATCH", "prematch MODEL_DECISION_TIME_UTC must be before kickoff"
        )

    generated_at = context.get("PREDICTION_GENERATED_AT_UTC")
    if generated_at is not None:
        generated_time = _parse_model_asof_utc(
            generated_at, "PREDICTION_GENERATED_AT_UTC", "PREDICTION_GENERATED_AT_INVALID"
        )
        if generated_time < decision_time:
            raise ModelAsOfValidationError(
                "PREDICTION_GENERATED_BEFORE_DECISION_BOUNDARY",
                "prediction output cannot be generated before the logical decision boundary",
            )

    dependency_count = context.get("POST_DECISION_INFORMATION_DEPENDENCY_COUNT", 0)
    if (
        isinstance(dependency_count, bool)
        or not isinstance(dependency_count, int)
        or dependency_count < 0
    ):
        raise ModelAsOfValidationError(
            "CONTRACT_VERSION_MISMATCH", "post-decision dependency count is malformed"
        )
    if dependency_count != 0:
        raise ModelAsOfValidationError(
            "SOURCE_AVAILABLE_AFTER_DECISION", "post-decision information dependency is present"
        )

    evidence = context.get("evidence", [])
    if not isinstance(evidence, list):
        raise ModelAsOfValidationError(
            "SOURCE_AVAILABILITY_TIME_UNPROVEN", "evidence must be a list"
        )
    for item in evidence:
        _validate_model_asof_evidence(item, decision_time)
    return True
