"""Fail-closed validation for the canonical standings as-of consumer boundary.

lifecycle: permanent
component: Specialized / Internal (canonical registry validator; not an authority)
"""

from __future__ import annotations

from typing import Any

STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID = "standings-asof-engine-consumer/v1"
STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION = "v1"
STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_STATUS = "FROZEN"


def validate_standings_asof_engine_consumer_registry_boundary(  # noqa: C901
    boundary: Any, error_type: type[ValueError]
) -> None:
    """Validate the singular frozen consumer/integration boundary."""

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

    root = exact(
        boundary,
        {
            "contract_id",
            "version",
            "status",
            "consumer_role",
            "input_contract",
            "ranking_contract",
            "model_as_of_contract",
            "runtime_capture_contract",
            "implementation_family",
            "implementation_binding",
            "boundary_policy",
            "consumption_gates",
            "output",
            "readiness",
            "source_authority",
        },
        "standings as-of engine consumer boundary",
    )
    text(
        root["contract_id"],
        "standings as-of engine consumer contract id",
        STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID,
    )
    text(
        root["version"],
        "standings as-of engine consumer contract version",
        STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION,
    )
    text(
        root["status"],
        "standings as-of engine consumer status",
        STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_STATUS,
    )
    text(root["consumer_role"], "standings as-of engine consumer role", "CONSUMER_INTEGRATION")

    for field, expected_id, expected_version in [
        ("input_contract", "standings-asof-engine-input/v1", "v1"),
        ("ranking_contract", "standings/premier-league-point-in-time/v1", "v1"),
        ("model_as_of_contract", "canonical-model-asof/v1", "v1"),
        ("runtime_capture_contract", "canonical-runtime-capture/v1", "v1"),
    ]:
        reference = exact(
            root[field],
            {"contract_id", "version"},
            f"{field} reference",
        )
        text(reference["contract_id"], f"{field}.contract_id", expected_id)
        text(reference["version"], f"{field}.version", expected_version)

    text(
        root["implementation_family"],
        "standings as-of engine consumer implementation family",
        "PointInTimeStandingsEngine",
    )
    implementation_binding = exact(
        root["implementation_binding"],
        {"implementation_id", "binding_source", "source_commit_proof"},
        "standings as-of engine consumer implementation binding",
    )
    text(
        implementation_binding["implementation_id"],
        "standings as-of engine consumer implementation id",
        "PointInTimeStandingsEngine",
    )
    text(
        implementation_binding["binding_source"],
        "standings as-of engine consumer implementation binding source",
        "EXISTING_ENGINE_IMPLEMENTATION_BINDING",
    )
    text(
        implementation_binding["source_commit_proof"],
        "standings as-of engine consumer source commit proof",
        "EXTERNAL_AUDIT_ONLY",
    )

    boundary_policy = exact(
        root["boundary_policy"],
        {
            "legacy",
            "asof",
            "legacy_result",
            "asof_result",
            "legacy_adjustment",
            "asof_adjustment",
        },
        "standings as-of engine consumer boundary policy",
    )
    for field, expected in {
        "legacy": "KICKOFF_EXCLUSIVE",
        "asof": "MODEL_DECISION_TIME_INCLUSIVE",
        "legacy_result": "STRICT_LT_TARGET_KICKOFF",
        "asof_result": "LTE_MODEL_DECISION_TIME",
        "legacy_adjustment": "STRICT_LT_TARGET_KICKOFF",
        "asof_adjustment": "LTE_MODEL_DECISION_TIME",
    }.items():
        text(boundary_policy[field], f"boundary policy.{field}", expected)

    gates = exact(
        root["consumption_gates"],
        {
            "generic_caller_cutoff_allowed",
            "input_validator_invoked_by_consumer",
            "caller_can_self_assert_validation",
            "caller_can_self_assert_eligibility",
            "source_dependent_no_table_allowed",
            "structural_validity_alone_allows_consumption",
            "blocked_input_computation",
            "unproven_state_can_be_filtered_away",
        },
        "standings as-of engine consumer consumption gates",
    )
    for field, expected in {
        "generic_caller_cutoff_allowed": "NO",
        "input_validator_invoked_by_consumer": "YES",
        "caller_can_self_assert_validation": "NO",
        "caller_can_self_assert_eligibility": "NO",
        "source_dependent_no_table_allowed": "NO_WITHOUT_TRUSTED_PROOF",
        "structural_validity_alone_allows_consumption": "NO",
        "blocked_input_computation": "NO",
        "unproven_state_can_be_filtered_away": "NO",
    }.items():
        text(gates[field], f"consumption gates.{field}", expected)

    output = exact(
        root["output"],
        {
            "asof_context_bound",
            "consumer_provenance_digest_algorithm",
            "t_bound_in_provenance",
            "target_kickoff_bound_in_provenance",
            "unavailable_positions",
            "unavailable_computation_status",
        },
        "standings as-of engine consumer output",
    )
    for field, expected in {
        "asof_context_bound": "YES",
        "consumer_provenance_digest_algorithm": "SHA-256",
        "t_bound_in_provenance": "YES",
        "target_kickoff_bound_in_provenance": "YES",
        "unavailable_positions": "NULL",
        "unavailable_computation_status": "NOT_EXECUTED",
    }.items():
        text(output[field], f"consumer output.{field}", expected)

    readiness = exact(
        root["readiness"],
        {
            "consumer_implemented",
            "semantic_numeric_computation",
            "runtime_source_authority_proven",
            "runtime_numeric_eligibility",
            "runtime_eligible",
            "training_eligible",
        },
        "standings as-of engine consumer readiness",
    )
    for field, expected in {
        "consumer_implemented": "YES",
        "semantic_numeric_computation": "YES",
        "runtime_source_authority_proven": "NO",
        "runtime_numeric_eligibility": "NO",
        "runtime_eligible": "NO",
        "training_eligible": "NO",
    }.items():
        text(readiness[field], f"consumer readiness.{field}", expected)

    source_authority = exact(
        root["source_authority"],
        {
            "source_authority_validity",
            "source_stream_completeness",
            "runtime_source_to_standings_normalization_proven",
            "target_identity_authority_implemented",
        },
        "standings as-of engine consumer source authority",
    )
    for field, expected in {
        "source_authority_validity": "NOT_PROVEN",
        "source_stream_completeness": "NOT_PROVEN",
        "runtime_source_to_standings_normalization_proven": "NO",
        "target_identity_authority_implemented": "NO",
    }.items():
        text(source_authority[field], f"source authority.{field}", expected)


__all__ = [
    "STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID",
    "STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_STATUS",
    "STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION",
    "validate_standings_asof_engine_consumer_registry_boundary",
]
