"""Fail-closed registry validation for the frozen standings as-of input boundary.

lifecycle: permanent
component: Specialized / Internal (canonical registry validator; not an authority)
"""

from __future__ import annotations

from typing import Any

_STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID = "standings-asof-engine-input/v1"
_STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION = "v1"
_STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_STATUS = "FROZEN"
_STANDINGS_ASOF_FIXTURE_STATES = [
    "RESULT_AVAILABLE_AT_T",
    "NO_TABLE_RESULT_AT_T",
    "REQUIRED_EVIDENCE_MISSING_AT_T",
    "ASOF_STATE_AMBIGUOUS",
    "TARGET_FIXTURE_EXCLUDED",
]
_STANDINGS_ASOF_NO_TABLE_REASONS = [
    "SCHEDULE_NOT_YET_REACHED_AT_T",
    "PROVEN_POSTPONED_NOT_PLAYED_BY_T",
    "PROVEN_NOT_FINAL_BY_T",
    "PROVEN_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T",
]
_STANDINGS_ASOF_CORE_DERIVABLE_NO_TABLE_REASONS = [
    "SCHEDULE_NOT_YET_REACHED_AT_T",
]
_STANDINGS_ASOF_SOURCE_DEPENDENT_NO_TABLE_REASONS = [
    "PROVEN_POSTPONED_NOT_PLAYED_BY_T",
    "PROVEN_NOT_FINAL_BY_T",
    "PROVEN_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T",
    "PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T",
]
_STANDINGS_ASOF_ADJUSTMENT_STATES = [
    "EFFECTIVE_AND_AVAILABLE_AT_T",
    "KNOWN_NOT_EFFECTIVE_AT_T",
    "ASOF_ADJUSTMENT_AMBIGUOUS",
]
_STANDINGS_ASOF_AVAILABILITY_FORMS = [
    "EXACT_OBSERVATION_TIMESTAMP",
    "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF",
    "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
]
_STANDINGS_ASOF_FAIL_CLOSED_REASONS = [
    "STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH",
    "MODEL_ASOF_BINDING_MISMATCH",
    "ASOF_DECISION_TIME_INVALID",
    "TARGET_KICKOFF_IDENTITY_CONFLICT",
    "FIXTURE_UNIVERSE_INCOMPLETE",
    "FIXTURE_ASOF_STATE_MISSING",
    "FIXTURE_ASOF_STATE_DUPLICATE",
    "FIXTURE_ASOF_STATE_UNKNOWN",
    "RESULT_AVAILABLE_AT_T_UNPROVEN",
    "REQUIRED_EVIDENCE_MISSING_AT_T",
    "ASOF_STATE_AMBIGUOUS",
    "POST_DECISION_STANDINGS_EVIDENCE",
    "STANDINGS_SOURCE_CLOSURE_UNPROVEN",
    "ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS",
    "TARGET_FIXTURE_NOT_EXCLUDED",
]


def validate_standings_asof_engine_input_registry_boundary(
    boundary: Any, error_type: type[ValueError]
) -> None:
    """Validate the singular frozen standings as-of input boundary."""

    def exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != fields:
            raise error_type(f"{label} malformed")
        return value

    def text(value: Any, label: str, expected: str | None = None) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or (expected is not None and value != expected)
        ):
            raise error_type(f"{label} malformed")

    def text_list(value: Any, label: str, expected: list[str]) -> None:
        if not isinstance(value, list) or value != expected:
            raise error_type(f"{label} malformed")

    def exact_values(value: Any, expected: dict[str, str], label: str) -> None:
        for field, expected_value in expected.items():
            text(value[field], f"{label}.{field}", expected_value)

    root = exact(
        boundary,
        {
            "contract_id",
            "version",
            "status",
            "standings_contract",
            "model_as_of_contract",
            "runtime_capture_contract",
            "implementation_family",
            "evaluation_boundary",
            "fixture_universe",
            "source_stream_closure",
            "fixture_state_taxonomy",
            "no_table_result_reason_codes",
            "no_table_proof",
            "engine_consumption_gates",
            "adjustment_state_taxonomy",
            "availability_proof",
            "trust_boundary",
            "readiness",
            "fail_closed_reason_codes",
            "digest",
        },
        "standings as-of engine input boundary",
    )
    text(
        root["contract_id"],
        "standings as-of engine input contract id",
        _STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
    )
    text(
        root["version"],
        "standings as-of engine input contract version",
        _STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
    )
    text(
        root["status"],
        "standings as-of engine input status",
        _STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_STATUS,
    )

    for field, expected_id, expected_version in [
        ("standings_contract", "standings/premier-league-point-in-time/v1", "v1"),
        ("model_as_of_contract", "canonical-model-asof/v1", "v1"),
        ("runtime_capture_contract", "canonical-runtime-capture/v1", "v1"),
    ]:
        reference = exact(root[field], {"contract_id", "version"}, f"{field} reference")
        text(reference["contract_id"], f"{field}.contract_id", expected_id)
        text(reference["version"], f"{field}.version", expected_version)
    text(
        root["implementation_family"],
        "standings as-of implementation family",
        "PointInTimeStandingsEngine",
    )

    evaluation_boundary = exact(
        root["evaluation_boundary"],
        {
            "model_decision_time_field",
            "feature_as_of_field",
            "target_kickoff_field",
            "model_decision_time_is_asof_boundary",
            "target_kickoff_is_evaluation_boundary",
            "prematch_requires_t_lt_target_kickoff",
            "target_kickoff_relabeling_forbidden",
            "prefilter_only_proves_asof_compatibility",
        },
        "standings as-of evaluation boundary",
    )
    exact_values(
        evaluation_boundary,
        {
            "model_decision_time_field": "MODEL_DECISION_TIME_UTC",
            "feature_as_of_field": "FEATURE_AS_OF_UTC",
            "target_kickoff_field": "TARGET_KICKOFF_UTC",
            "model_decision_time_is_asof_boundary": "YES",
            "target_kickoff_is_evaluation_boundary": "NO",
            "prematch_requires_t_lt_target_kickoff": "YES",
            "target_kickoff_relabeling_forbidden": "YES",
            "prefilter_only_proves_asof_compatibility": "NO",
        },
        "standings as-of evaluation boundary",
    )

    fixture_universe = exact(
        root["fixture_universe"],
        {
            "required",
            "reference_match_required",
            "full_state_coverage",
            "target_exclusion",
            "authority_proven_by_core",
            "status_authority_proven_by_core",
        },
        "standings as-of fixture universe",
    )
    exact_values(
        fixture_universe,
        {
            "required": "YES",
            "reference_match_required": "YES",
            "full_state_coverage": "EXACTLY_ONE_STATE_PER_FIXTURE",
            "target_exclusion": "EXACTLY_ONE_TARGET_FIXTURE_EXCLUDED",
            "authority_proven_by_core": "NO",
            "status_authority_proven_by_core": "NO",
        },
        "standings as-of fixture universe",
    )
    source_stream_closure = exact(
        root["source_stream_closure"],
        {
            "fixture_universe_reference_match",
            "fixture_universe_closure",
            "fixture_status_evidence_closure",
            "result_evidence_closure",
            "admin_adjustment_stream_closure",
        },
        "standings as-of source stream closure",
    )
    exact_values(
        source_stream_closure,
        {
            "fixture_universe_reference_match": "STRUCTURALLY_VALID",
            "fixture_universe_closure": "NOT_PROVEN",
            "fixture_status_evidence_closure": "NOT_PROVEN",
            "result_evidence_closure": "NOT_PROVEN",
            "admin_adjustment_stream_closure": "NOT_PROVEN",
        },
        "standings as-of source stream closure",
    )
    text_list(
        root["fixture_state_taxonomy"],
        "standings as-of fixture states",
        _STANDINGS_ASOF_FIXTURE_STATES,
    )
    text_list(
        root["no_table_result_reason_codes"],
        "standings as-of no-table reasons",
        _STANDINGS_ASOF_NO_TABLE_REASONS,
    )
    no_table_proof = exact(
        root["no_table_proof"],
        {
            "core_derivable_reason_codes",
            "source_dependent_reason_codes",
            "schedule_not_yet_relation_proven_by_core",
            "source_dependent_status_proven_by_core",
            "evidence_reference_presence_is_external_truth_proof",
            "source_semantic_reason_name_is_core_proof",
            "structurally_valid_implies_temporal_proven",
            "structurally_valid_implies_runtime_eligible",
        },
        "standings as-of no-table proof",
    )
    text_list(
        no_table_proof["core_derivable_reason_codes"],
        "standings as-of core-derivable no-table reasons",
        _STANDINGS_ASOF_CORE_DERIVABLE_NO_TABLE_REASONS,
    )
    text_list(
        no_table_proof["source_dependent_reason_codes"],
        "standings as-of source-dependent no-table reasons",
        _STANDINGS_ASOF_SOURCE_DEPENDENT_NO_TABLE_REASONS,
    )
    exact_values(
        no_table_proof,
        {
            "schedule_not_yet_relation_proven_by_core": "YES",
            "source_dependent_status_proven_by_core": "NO",
            "evidence_reference_presence_is_external_truth_proof": "NO",
            "source_semantic_reason_name_is_core_proof": "NO",
            "structurally_valid_implies_temporal_proven": "NO",
            "structurally_valid_implies_runtime_eligible": "NO",
        },
        "standings as-of no-table proof",
    )
    engine_consumption_gates = exact(
        root["engine_consumption_gates"],
        {"requires_temporal_eligibility_proven", "requires_source_dependency_gates"},
        "standings as-of engine consumption gates",
    )
    exact_values(
        engine_consumption_gates,
        {
            "requires_temporal_eligibility_proven": "YES",
            "requires_source_dependency_gates": "YES",
        },
        "standings as-of engine consumption gates",
    )
    text_list(
        root["adjustment_state_taxonomy"],
        "standings as-of adjustment states",
        _STANDINGS_ASOF_ADJUSTMENT_STATES,
    )

    availability = exact(
        root["availability_proof"],
        {
            "allowed_forms",
            "event_time_alone_proves_availability",
            "captured_at_alone_proves_availability",
            "post_t_evidence_allowed",
            "ambiguous_interval_fails_closed",
        },
        "standings as-of availability proof",
    )
    text_list(
        availability["allowed_forms"],
        "standings as-of availability forms",
        _STANDINGS_ASOF_AVAILABILITY_FORMS,
    )
    exact_values(
        availability,
        {
            "event_time_alone_proves_availability": "NO",
            "captured_at_alone_proves_availability": "NO",
            "post_t_evidence_allowed": "NO",
            "ambiguous_interval_fails_closed": "YES",
        },
        "standings as-of availability proof",
    )

    trust_boundary = exact(
        root["trust_boundary"],
        {
            "core_establishes_runtime_source_authority",
            "fixture_universe_authority_proven_by_core",
            "fixture_status_stream_authority_proven_by_core",
            "result_stream_authority_proven_by_core",
            "admin_adjustment_stream_authority_proven_by_core",
            "runtime_capture_to_js_proven",
            "source_normalization_replay_proven",
            "caller_source_closure_flags_accepted",
            "caller_source_commit_proves_provenance",
        },
        "standings as-of trust boundary",
    )
    exact_values(
        trust_boundary,
        {
            "core_establishes_runtime_source_authority": "NO",
            "fixture_universe_authority_proven_by_core": "NO",
            "fixture_status_stream_authority_proven_by_core": "NO",
            "result_stream_authority_proven_by_core": "NO",
            "admin_adjustment_stream_authority_proven_by_core": "NO",
            "runtime_capture_to_js_proven": "NO",
            "source_normalization_replay_proven": "NO",
            "caller_source_closure_flags_accepted": "NO",
            "caller_source_commit_proves_provenance": "NO",
        },
        "standings as-of trust boundary",
    )

    readiness = exact(
        root["readiness"],
        {
            "engine_consumer_implemented",
            "runtime_source_to_standings_normalization_proven",
            "standings_source_closure_proven",
            "historical_asof_numeric_parity_proven",
            "runtime_eligible",
            "training_eligible",
        },
        "standings as-of readiness",
    )
    exact_values(
        readiness,
        {
            "engine_consumer_implemented": "NO",
            "runtime_source_to_standings_normalization_proven": "NO",
            "standings_source_closure_proven": "NO",
            "historical_asof_numeric_parity_proven": "NO",
            "runtime_eligible": "NO",
            "training_eligible": "NO",
        },
        "standings as-of readiness",
    )
    text_list(
        root["fail_closed_reason_codes"],
        "standings as-of fail-closed reasons",
        _STANDINGS_ASOF_FAIL_CLOSED_REASONS,
    )

    digest = exact(
        root["digest"],
        {
            "algorithm",
            "canonical_serialization",
            "fixture_state_ordering",
            "adjustment_state_ordering",
        },
        "standings as-of digest",
    )
    exact_values(
        digest,
        {
            "algorithm": "SHA-256",
            "canonical_serialization": "STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON",
            "fixture_state_ordering": "canonicalMatchId_ASCENDING",
            "adjustment_state_ordering": "adjustmentId_ASCENDING",
        },
        "standings as-of digest",
    )


__all__ = ["validate_standings_asof_engine_input_registry_boundary"]
