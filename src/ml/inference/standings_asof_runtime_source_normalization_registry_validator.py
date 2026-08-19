"""Fail-closed validation for the generic standings normalization handoff boundary.

lifecycle: permanent
component: Specialized / Internal (registry validator; not a source authority)

This boundary describes the capture-to-normalization-to-standings-input handoff.
It deliberately records what the generic layer cannot prove: provider semantics,
source authority, stream closure, runtime eligibility, and training eligibility.
"""

from __future__ import annotations

from typing import Any

NORMALIZATION_CONTRACT_ID = "standings-asof-runtime-source-normalization/v1"
NORMALIZATION_CONTRACT_VERSION = "v1"
NORMALIZATION_CONTRACT_STATUS = "FROZEN"


def validate_standings_asof_runtime_source_normalization_registry_boundary(  # noqa: C901, PLR0915 -- one frozen registry boundary is validated as an exact contract.
    boundary: Any, error_type: type[ValueError]
) -> None:
    """Validate the singular frozen normalization handoff boundary."""

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

    def reference(value: Any, label: str, expected_id: str) -> None:
        ref = exact(value, {"contract_id", "version"}, label)
        text(ref["contract_id"], f"{label}.contract_id", expected_id)
        text(ref["version"], f"{label}.version", "v1")

    root = exact(
        boundary,
        {
            "contract_id",
            "version",
            "status",
            "normalization_role",
            "runtime_capture_contract",
            "model_as_of_contract",
            "standings_asof_engine_input_contract",
            "standings_asof_engine_consumer_contract",
            "ranking_contract",
            "envelope",
            "proof_layers",
            "fact_binding_taxonomy",
            "lineage",
            "source_authority",
            "source_stream_closure",
            "implementation_status",
            "runtime_eligibility",
            "security",
        },
        "standings runtime-source normalization boundary",
    )
    text(root["contract_id"], "normalization contract id", NORMALIZATION_CONTRACT_ID)
    text(root["version"], "normalization contract version", NORMALIZATION_CONTRACT_VERSION)
    text(root["status"], "normalization contract status", NORMALIZATION_CONTRACT_STATUS)
    text(
        root["normalization_role"],
        "normalization role",
        "RUNTIME_SOURCE_NORMALIZATION_HANDOFF_CONTRACT",
    )

    reference(
        root["runtime_capture_contract"],
        "runtime capture reference",
        "canonical-runtime-capture/v1",
    )
    reference(root["model_as_of_contract"], "model as-of reference", "canonical-model-asof/v1")
    reference(
        root["standings_asof_engine_input_contract"],
        "standings input reference",
        "standings-asof-engine-input/v1",
    )
    reference(
        root["standings_asof_engine_consumer_contract"],
        "standings consumer reference",
        "standings-asof-engine-consumer/v1",
    )
    reference(
        root["ranking_contract"],
        "standings ranking reference",
        "standings/premier-league-point-in-time/v1",
    )

    envelope = exact(
        root["envelope"],
        {
            "identity_fields",
            "content_digest_algorithm",
            "content_digest_scope",
            "canonical_serialization",
            "timestamp_normalization",
            "non_semantic_array_ordering",
            "secret_fields_forbidden",
        },
        "normalization envelope",
    )
    if envelope["identity_fields"] != [
        "NORMALIZATION_CONTRACT_ID",
        "NORMALIZATION_CONTRACT_VERSION",
        "NORMALIZATION_INSTANCE_ID",
        "NORMALIZATION_CONTENT_DIGEST",
    ]:
        raise error_type("normalization envelope identity fields malformed")
    text(envelope["content_digest_algorithm"], "normalization envelope digest algorithm", "SHA-256")
    text(
        envelope["content_digest_scope"],
        "normalization envelope digest scope",
        "SELF_EXCLUDING_CANONICAL_NORMALIZATION_ENVELOPE",
    )
    text(
        envelope["canonical_serialization"],
        "normalization envelope canonical serialization",
        "STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON",
    )
    text(
        envelope["timestamp_normalization"],
        "normalization envelope timestamp normalization",
        "ISO_8601_UTC_SECONDS_OPTIONAL_1_TO_6_FRACTION_Z_OR_PLUS_00_00_TO_MILLISECONDS",
    )
    if envelope["non_semantic_array_ordering"] != {
        "STANDINGS_EVIDENCE_IDS": "LEXICAL_ASCENDING",
        "CAPTURE_SELECTED_EVIDENCE_IDS": "LEXICAL_ASCENDING",
        "EVIDENCE_ATTESTATIONS": "EVIDENCE_ID_ASCENDING",
        "FACT_BINDINGS": "BINDING_ID_ASCENDING",
        "SOURCE_EVIDENCE_IDS": "LEXICAL_ASCENDING",
        "FIXTURE_STATE_IDS": "LEXICAL_ASCENDING",
        "ADMINISTRATIVE_ADJUSTMENT_IDS": "LEXICAL_ASCENDING",
    }:
        raise error_type("normalization envelope array ordering malformed")
    if envelope["secret_fields_forbidden"] != "YES":
        raise error_type("normalization envelope secret policy malformed")

    proof_layers = exact(
        root["proof_layers"],
        {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "implications"},
        "normalization proof layers",
    )
    expected_layers = {
        "L1": "CAPTURE_STRUCTURAL_AND_CONTENT_INTEGRITY",
        "L2": "CAPTURE_SELECTED_EVIDENCE_BINDING",
        "L3": "NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY",
        "L4": "SOURCE_PAYLOAD_TO_DOMAIN_FACT_SEMANTIC_TRUTH",
        "L5": "SOURCE_AUTHORITY",
        "L6": "SOURCE_STREAM_CLOSURE",
        "L7": "STANDINGS_ASOF_INPUT_CONTRACT_VALIDITY",
        "L8": "RUNTIME_FEATURE_ELIGIBILITY",
    }
    for key, expected in expected_layers.items():
        text(proof_layers[key], f"proof layer {key}", expected)
    if proof_layers["implications"] != {
        "L1_IMPLIES_L4": "NO",
        "L2_IMPLIES_L4": "NO",
        "L3_IMPLIES_L4": "NO",
        "L1_IMPLIES_L5": "NO",
        "L2_IMPLIES_L5": "NO",
        "L3_IMPLIES_L5": "NO",
        "L4_IMPLIES_L5": "NO",
        "L5_IMPLIES_L6": "NO",
        "L7_IMPLIES_L8": "NO",
        "DIGEST_MATCH_IMPLIES_SOURCE_TRUTH": "NO",
    }:
        raise error_type("normalization proof implications malformed")

    if root["fact_binding_taxonomy"] != {
        "roles": [
            "FIXTURE_UNIVERSE",
            "FIXTURE",
            "FIXTURE_STATUS",
            "RESULT",
            "ADMIN_ADJUSTMENT",
            "TARGET_IDENTITY",
        ],
        "required_fields": [
            "BINDING_ID",
            "SEMANTIC_ROLE",
            "DOMAIN_IDENTITY",
            "SOURCE_EVIDENCE_IDS",
            "NORMALIZED_FACT_DIGEST",
        ],
        "source_lineage_required_for_source_attested": "YES",
        "core_derived_source_authority_proven": "NO",
    }:
        raise error_type("normalization fact-binding taxonomy malformed")

    if root["lineage"] != {
        "standings_evidence_subset_of_capture_selected": "YES",
        "unselected_capture_evidence_may_enter_standings": "NO",
        "selected_non_standings_evidence_auto_promoted": "NO",
        "source_record_ref_non_null_rule": "EXACT_SOURCE_RECORD_ID_FOR_SINGLE_EVIDENCE",
        "source_record_ref_multi_evidence_rule": "DETERMINISTIC_CAPTURE_RECORD_SET_DIGEST",
        "source_record_ref_null_fallback": "CAPTURE_CONTENT_DIGEST_AND_EVIDENCE_ID_SET",
        "fallback_proves_source_authority": "NO",
        "availability_proof_ref_rule": "EXACT_PRIMARY_AVAILABILITY_EVIDENCE_ID",
        "availability_metadata_rewritten_by_bridge": "NO",
    }:
        raise error_type("normalization lineage rules malformed")

    source_authority = exact(
        root["source_authority"],
        {
            "generic_capture_establishes_source_authority",
            "generic_normalization_establishes_source_authority",
            "source_authority_id_string_is_proof",
            "caller_boolean_is_proof",
            "digest_match_is_source_truth",
            "future_source_specific_authority_required",
        },
        "normalization source authority",
    )
    for field in (
        "generic_capture_establishes_source_authority",
        "generic_normalization_establishes_source_authority",
        "source_authority_id_string_is_proof",
        "caller_boolean_is_proof",
        "digest_match_is_source_truth",
    ):
        text(source_authority[field], f"source authority.{field}", "NO")
    text(
        source_authority["future_source_specific_authority_required"],
        "source authority future boundary",
        "YES",
    )

    if root["source_stream_closure"] != {
        "fixture_universe_closure": "NOT_PROVEN",
        "fixture_status_stream_closure": "NOT_PROVEN",
        "result_stream_closure": "NOT_PROVEN",
        "admin_adjustment_stream_closure": "NOT_PROVEN",
        "source_dependent_no_table_semantic_truth": "NOT_PROVEN",
    }:
        raise error_type("normalization source-stream closure status malformed")

    if root["implementation_status"] != {
        "contract_defined": "YES",
        "normalization_envelope_validator_implemented": "YES",
        "capture_binding_validator_implemented": "YES",
        "standings_input_binding_validator_implemented": "YES",
        "cross_language_digest_parity_proven": "YES",
        "source_specific_normalizer_implemented": "NO",
        "source_specific_authority_contract_implemented": "NO",
        "source_semantic_normalization_proven": "NO",
        "source_stream_closure_proven": "NO",
        "runtime_pipeline_implemented": "NO",
    }:
        raise error_type("normalization implementation status malformed")

    if root["runtime_eligibility"] != {
        "runtime_eligible": "NO",
        "training_eligible": "NO",
        "runtime_source_to_standings_normalization_proven": "NO",
        "runtime_numeric_eligibility": "NO",
    }:
        raise error_type("normalization runtime eligibility malformed")
    if root["security"] != {
        "provider_selected": "NO",
        "source_specific_payload_parser_count": 0,
        "raw_provider_credentials_allowed": "NO",
        "network_dependency": "NO",
        "database_dependency": "NO",
    }:
        raise error_type("normalization security boundary malformed")


__all__ = [
    "NORMALIZATION_CONTRACT_ID",
    "NORMALIZATION_CONTRACT_STATUS",
    "NORMALIZATION_CONTRACT_VERSION",
    "validate_standings_asof_runtime_source_normalization_registry_boundary",
]
