"""Canonical runtime-capture contract and content-integrity behavior tests.

lifecycle: permanent

These tests use synthetic in-memory bytes only.  They never read a capture file,
call a provider, touch the database, consult a clock, build features, or train.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.ml.inference.feature_contract_registry import load_feature_contract_registry
from src.ml.inference.runtime_capture_contract import (
    RUNTIME_CAPTURE_CONTRACT_ID,
    RUNTIME_CAPTURE_CONTRACT_VERSION,
    RuntimeCaptureValidationError,
    ValidatedFeatureContractBinding,
    compute_capture_content_digest,
    validate_runtime_capture_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_FEATURE_CONTRACT_BINDING = (
    load_feature_contract_registry().validated_feature_contract_binding("v26_7_aligned/v1")
)
DECISION_TIME = "2026-08-18T10:00:00Z"
TARGET_KICKOFF = "2026-08-18T20:00:00Z"
CAPTURED_AT = "2026-08-18T09:55:00Z"
OBSERVED_AT = "2026-08-18T09:50:00Z"
V1_FEATURE_COUNT = 20
V_NEXT_FEATURE_COUNT = 17


def _payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _entry(
    evidence_id: str = "evidence-1",
    payload: bytes = b"synthetic-payload-1",
    *,
    source_family: str = "RESULT",
    source_record_id: str | None = "record-1",
    observed_at: str | None = OBSERVED_AT,
    captured_at: str | None = CAPTURED_AT,
    proof_kind: str = "EXACT_OBSERVATION_TIMESTAMP",
    proof_data: dict | None = None,
    source_provenance_status: str = "UNKNOWN",
    source_authority_id: str | None = None,
) -> dict:
    if proof_data is None:
        proof_data = {"observed_at_field": "SOURCE_OBSERVED_AT_UTC"}
    return {
        "EVIDENCE_ID": evidence_id,
        "SOURCE_FAMILY": source_family,
        "SOURCE_AUTHORITY_ID": source_authority_id,
        "SOURCE_RECORD_ID": source_record_id,
        "PAYLOAD_KIND": "BYTE_BLOB",
        "PAYLOAD_CONTENT_DIGEST": _payload_digest(payload),
        "PAYLOAD_BYTE_LENGTH": len(payload),
        "SOURCE_EVENT_TIME_UTC": "2026-08-18T09:00:00Z",
        "SOURCE_EFFECTIVE_TIME_UTC": None,
        "SOURCE_OBSERVED_AT_UTC": observed_at,
        "SOURCE_CAPTURED_AT_UTC": captured_at,
        "AVAILABILITY_PROOF_KIND": proof_kind,
        "AVAILABILITY_PROOF_DATA": proof_data,
        "SOURCE_PROVENANCE_STATUS": source_provenance_status,
    }


def _manifest(
    entries: list[dict] | None = None,
    payloads: dict[str, bytes] | None = None,
    *,
    selected: list[str] | None = None,
    context_overrides: dict | None = None,
) -> tuple[dict, dict[str, bytes]]:
    if entries is None:
        entries = [_entry()]
    if payloads is None:
        payloads = {entry["EVIDENCE_ID"]: b"synthetic-payload-1" for entry in entries}
    context = {
        "PREDICTION_CONTEXT_ID": "prediction-context-1",
        "MODEL_ASOF_CONTRACT_ID": "canonical-model-asof/v1",
        "MODEL_ASOF_CONTRACT_VERSION": "v1",
        "MODEL_DECISION_TIME_UTC": DECISION_TIME,
        "FEATURE_AS_OF_UTC": DECISION_TIME,
        "TARGET_MATCH_ID": "47_20242025_0000001",
        "TARGET_KICKOFF_UTC": TARGET_KICKOFF,
        "FEATURE_CONTRACT_ID": "v26_7_aligned/v1",
        "FEATURE_CONTRACT_VERSION": "v26_6_pre_match/v1",
        "PREDICTION_GENERATED_AT_UTC": None,
        "POST_DECISION_INFORMATION_DEPENDENCY_COUNT": 0,
    }
    if context_overrides:
        context.update(context_overrides)
    manifest = {
        "RUNTIME_CAPTURE_CONTRACT_ID": RUNTIME_CAPTURE_CONTRACT_ID,
        "RUNTIME_CAPTURE_CONTRACT_VERSION": RUNTIME_CAPTURE_CONTRACT_VERSION,
        "CAPTURE_INSTANCE_ID": "capture-instance-1",
        "CAPTURE_CONTENT_DIGEST": "0" * 64,
        "MANIFEST_FINALIZED_AT_UTC": "2026-08-18T21:00:00Z",
        "PREDICTION_CONTEXT": context,
        "PROVENANCE": {
            "CAPTURE_CONTENT_PROVENANCE": "MANIFEST_AND_PAYLOAD_DIGESTS",
            "SOURCE_PROVIDER_PROVENANCE": "ENTRY_SOURCE_BINDING",
            "REPOSITORY_SOURCE_PROVENANCE": "EXTERNAL_BUILD_AUTHORITY_REQUIRED",
            "ENGINE_IMPLEMENTATION_IDENTITY": "EXTERNAL_BUILD_AUTHORITY_REQUIRED",
            "MODEL_ARTIFACT_IDENTITY": "FEATURE_CONTRACT_BINDING_ONLY",
        },
        "EVIDENCE": entries,
        "SELECTED_EVIDENCE_IDS": selected if selected is not None else [entries[0]["EVIDENCE_ID"]],
        "STATUS": {
            "STRUCTURAL_CAPTURE_VALIDITY": "PROVEN",
            "SOURCE_AUTHORITY_VALIDITY": "UNKNOWN",
            "TEMPORAL_ELIGIBILITY_VALIDITY": "PROVEN",
            "FEATURE_DEPENDENCY_COMPLETENESS": "NOT_PROVEN",
        },
    }
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    return manifest, payloads


def _validate(
    manifest: dict,
    payloads: dict[str, bytes] | None = None,
    *,
    feature_contract_binding=CANONICAL_FEATURE_CONTRACT_BINDING,
) -> dict:
    if payloads is None:
        payloads = {entry["EVIDENCE_ID"]: b"synthetic-payload-1" for entry in manifest["EVIDENCE"]}
    return validate_runtime_capture_manifest(
        manifest,
        payloads,
        feature_contract_binding=feature_contract_binding,
    )


def _raises(reason_code: str):
    return pytest.raises(RuntimeCaptureValidationError, match=reason_code)


def test_valid_prediction_context_binding_is_accepted() -> None:
    manifest, payloads = _manifest()
    result = _validate(manifest, payloads)
    assert result["valid"] is True
    assert result["post_decision_evidence_selected_count"] == 0


def test_wrong_model_asof_contract_id_is_rejected() -> None:
    manifest, payloads = _manifest(
        context_overrides={"MODEL_ASOF_CONTRACT_ID": "unknown-model-asof/v9"}
    )
    with _raises("CONTRACT_VERSION_MISMATCH"):
        _validate(manifest, payloads)


def test_feature_asof_mismatch_is_rejected_by_model_asof_authority() -> None:
    manifest, payloads = _manifest(context_overrides={"FEATURE_AS_OF_UTC": "2026-08-18T09:59:00Z"})
    with _raises("FEATURE_AS_OF_MISMATCH"):
        _validate(manifest, payloads)


def test_generated_at_before_decision_boundary_is_rejected() -> None:
    manifest, payloads = _manifest(
        context_overrides={"PREDICTION_GENERATED_AT_UTC": "2026-08-18T09:59:59Z"}
    )
    with _raises("PREDICTION_GENERATED_BEFORE_DECISION_BOUNDARY"):
        _validate(manifest, payloads)


def test_target_kickoff_remains_separate_from_decision_boundary() -> None:
    manifest, payloads = _manifest()
    context = manifest["PREDICTION_CONTEXT"]
    assert context["MODEL_DECISION_TIME_UTC"] != context["TARGET_KICKOFF_UTC"]
    assert _validate(manifest, payloads)["valid"] is True


@pytest.mark.parametrize("decision_time", [TARGET_KICKOFF, "2026-08-18T20:00:01Z"])
def test_decision_time_at_or_after_kickoff_is_rejected(decision_time: str) -> None:
    manifest, payloads = _manifest(
        context_overrides={
            "MODEL_DECISION_TIME_UTC": decision_time,
            "FEATURE_AS_OF_UTC": decision_time,
        }
    )
    with _raises("DECISION_TIME_NOT_PREMATCH"):
        _validate(manifest, payloads)


def test_duplicate_evidence_id_is_rejected() -> None:
    first = _entry("duplicate", b"first")
    second = _entry("duplicate", b"second", source_record_id="record-2")
    manifest, payloads = _manifest([first, second], {"duplicate": b"first"})
    with _raises("DUPLICATE_EVIDENCE_ID"):
        _validate(manifest, payloads)


def test_missing_referenced_payload_is_rejected() -> None:
    manifest, _ = _manifest()
    with _raises("SELECTED_EVIDENCE_MISSING"):
        _validate(manifest, {})


def test_payload_digest_mismatch_is_rejected() -> None:
    manifest, _ = _manifest()
    with _raises("PAYLOAD_DIGEST_MISMATCH"):
        _validate(manifest, {"evidence-1": b"synthetic-payload-2"})


def test_one_byte_payload_tamper_is_rejected() -> None:
    manifest, _ = _manifest()
    with _raises("PAYLOAD_DIGEST_MISMATCH"):
        _validate(manifest, {"evidence-1": b"synthetic-payload-2"})


def test_same_source_record_identity_conflict_is_rejected() -> None:
    first = _entry("evidence-1", b"first", source_record_id="same-record")
    second = _entry("evidence-2", b"second", source_record_id="same-record")
    manifest, payloads = _manifest(
        [first, second], {"evidence-1": b"first", "evidence-2": b"second"}
    )
    with _raises("SOURCE_RECORD_ID_CONFLICT"):
        _validate(manifest, payloads)


def test_selected_evidence_unknown_is_rejected() -> None:
    manifest, payloads = _manifest(selected=["missing-evidence"])
    with _raises("SELECTED_EVIDENCE_UNKNOWN"):
        _validate(manifest, payloads)


def test_unselected_extra_capture_does_not_become_selected_input() -> None:
    first = _entry("evidence-1", b"first")
    extra = _entry("evidence-2", b"second", source_record_id="record-2")
    manifest, payloads = _manifest(
        [first, extra], {"evidence-1": b"first", "evidence-2": b"second"}, selected=["evidence-1"]
    )
    result = _validate(manifest, payloads)
    assert result["selected_evidence_ids"] == ("evidence-1",)


def test_post_t_observed_evidence_is_rejected() -> None:
    entry = _entry(observed_at="2026-08-18T10:00:01Z")
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_AVAILABLE_AFTER_DECISION"):
        _validate(manifest, payloads)


def test_event_time_only_evidence_is_rejected() -> None:
    entry = _entry(observed_at=None)
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_AVAILABILITY_TIME_UNPROVEN"):
        _validate(manifest, payloads)


def test_captured_at_only_evidence_is_rejected() -> None:
    entry = _entry(observed_at=None, proof_kind="EXACT_OBSERVATION_TIMESTAMP")
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_AVAILABILITY_TIME_UNPROVEN"):
        _validate(manifest, payloads)


def test_ambiguous_interval_is_rejected() -> None:
    entry = _entry(
        proof_kind="BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
        proof_data={"start_utc": "2026-08-18T09:00:00Z", "end_utc": DECISION_TIME},
    )
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_TIME_PRECISION_AMBIGUOUS"):
        _validate(manifest, payloads)


def test_unknown_source_authority_is_not_upgraded() -> None:
    manifest, payloads = _manifest()
    result = _validate(manifest, payloads)
    assert result["source_authority_validity"] == "UNKNOWN"
    assert manifest["EVIDENCE"][0]["SOURCE_PROVENANCE_STATUS"] == "UNKNOWN"


def test_capture_identity_cannot_substitute_for_content_digest() -> None:
    manifest, payloads = _manifest()
    manifest["CAPTURE_CONTENT_DIGEST"] = manifest["CAPTURE_INSTANCE_ID"]
    with _raises("CAPTURE_DIGEST_INVALID"):
        _validate(manifest, payloads)


def test_manifest_permutation_has_deterministic_digest() -> None:
    first = _entry("evidence-b", b"second", source_record_id="record-b")
    second = _entry("evidence-a", b"first", source_record_id="record-a")
    manifest, payloads = _manifest(
        [first, second],
        {"evidence-a": b"first", "evidence-b": b"second"},
        selected=["evidence-b", "evidence-a"],
    )
    digest = manifest["CAPTURE_CONTENT_DIGEST"]
    permuted = deepcopy(manifest)
    permuted["EVIDENCE"] = list(reversed(permuted["EVIDENCE"]))
    permuted["SELECTED_EVIDENCE_IDS"] = list(reversed(permuted["SELECTED_EVIDENCE_IDS"]))
    assert compute_capture_content_digest(permuted) == digest
    assert _validate(permuted, payloads)["valid"] is True


def test_manifest_tamper_changes_digest_and_fails_closed() -> None:
    manifest, payloads = _manifest()
    manifest["CAPTURE_INSTANCE_ID"] = "capture-instance-tampered"
    with _raises("CAPTURE_CONTENT_DIGEST_MISMATCH"):
        _validate(manifest, payloads)


def test_capture_contract_version_tamper_is_rejected() -> None:
    manifest, payloads = _manifest()
    manifest["RUNTIME_CAPTURE_CONTRACT_VERSION"] = "v9"
    with _raises("CONTRACT_VERSION_MISMATCH"):
        _validate(manifest, payloads)


def test_unknown_feature_contract_is_rejected() -> None:
    manifest, payloads = _manifest(
        context_overrides={
            "FEATURE_CONTRACT_ID": "unknown-features/v9",
            "FEATURE_CONTRACT_VERSION": "v9",
        }
    )
    with _raises("CONTRACT_VERSION_MISMATCH"):
        _validate(manifest, payloads)


def test_caller_arbitrary_feature_mapping_cannot_establish_canonical_authority() -> None:
    manifest, payloads = _manifest(
        context_overrides={
            "FEATURE_CONTRACT_ID": "fake-feature-contract/v99",
            "FEATURE_CONTRACT_VERSION": "v99",
        }
    )
    with _raises("FEATURE_CONTRACT_BINDING_UNTRUSTED"):
        _validate(
            manifest,
            payloads,
            feature_contract_binding={"fake-feature-contract/v99": "v99"},
        )


def test_canonical_registry_feature_binding_proves_authority_without_mapping() -> None:
    manifest, payloads = _manifest()
    result = _validate(manifest, payloads)
    assert result["feature_contract_reference"] == "FEATURE_CONTRACT_REFERENCE_MATCHED"
    assert result["canonical_feature_contract_authority"] == (
        "CANONICAL_FEATURE_CONTRACT_AUTHORITY_PROVEN"
    )


def test_direct_feature_binding_construction_requires_registry_trust_token() -> None:
    with pytest.raises(TypeError, match="canonical registry"):
        ValidatedFeatureContractBinding("fake-feature-contract/v99", "v99", _trust_token=object())


def test_registry_preserves_v1_default_and_vnext_not_activated() -> None:
    registry = load_feature_contract_registry()
    contracts = registry.contracts()
    assert contracts[0].feature_count == V1_FEATURE_COUNT
    assert contracts[0].activation_status == "ACTIVE_DEFAULT"
    assert contracts[1].feature_count == V_NEXT_FEATURE_COUNT
    assert contracts[1].activation_status == "DEFINED_NOT_ACTIVATED"


def test_provider_defined_closing_cannot_satisfy_strict_decision_time_odds() -> None:
    entry = _entry(source_family="ODDS")
    manifest, payloads = _manifest([entry])
    with _raises("ODDS_DECISION_TIME_UNPROVEN"):
        _validate(manifest, payloads)


def test_secret_bearing_metadata_is_rejected() -> None:
    manifest, payloads = _manifest()
    manifest["AUTHORIZATION"] = "Bearer synthetic"
    with _raises("SECRET_METADATA_FORBIDDEN"):
        _validate(manifest, payloads)


def test_extra_unknown_manifest_field_is_rejected() -> None:
    manifest, payloads = _manifest()
    manifest["UNDECLARED_FIELD"] = "not allowed"
    with _raises("CAPTURE_SCHEMA_MISMATCH"):
        _validate(manifest, payloads)


def test_post_t_manifest_finalization_does_not_change_evidence_eligibility() -> None:
    manifest, payloads = _manifest()
    assert manifest["MANIFEST_FINALIZED_AT_UTC"] > DECISION_TIME
    assert _validate(manifest, payloads)["temporal_eligibility_validity"] == "PROVEN"


def test_source_normalization_replay_is_not_inferred() -> None:
    manifest, payloads = _manifest()
    result = _validate(manifest, payloads)
    assert result["source_normalization_replay"] == "NOT_PROVEN"


def test_training_and_runtime_readiness_are_not_inferred() -> None:
    manifest, payloads = _manifest()
    result = _validate(manifest, payloads)
    assert result["feature_numeric_replay"] == "NOT_PROVEN"
    assert result["train_inference_replay"] == "NOT_PROVEN"


def test_runtime_capture_registry_binding_is_canonical() -> None:
    registry = load_feature_contract_registry()
    boundary = registry.runtime_capture_boundary()
    assert boundary["contract_id"] == RUNTIME_CAPTURE_CONTRACT_ID
    assert boundary["version"] == RUNTIME_CAPTURE_CONTRACT_VERSION
    assert boundary["capture_time_relation_to_t"] == "CAPTURE_MUST_BE_LTE_T"


def test_captured_at_after_t_is_rejected_even_when_observed_before_t() -> None:
    entry = _entry(captured_at="2026-08-18T10:00:01Z")
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_AVAILABLE_AFTER_DECISION"):
        _validate(manifest, payloads)


def test_exact_effective_time_with_observation_proof_is_accepted() -> None:
    entry = _entry(
        observed_at=OBSERVED_AT,
        proof_kind="EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF",
        proof_data={
            "effective_time_field": "SOURCE_EFFECTIVE_TIME_UTC",
            "observed_at_field": "SOURCE_OBSERVED_AT_UTC",
        },
    )
    entry["SOURCE_EFFECTIVE_TIME_UTC"] = "2026-08-18T09:45:00Z"
    manifest, payloads = _manifest([entry])
    assert _validate(manifest, payloads)["valid"] is True


def test_interval_entirely_before_t_is_accepted() -> None:
    entry = _entry(
        proof_kind="BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
        proof_data={"start_utc": "2026-08-18T08:00:00Z", "end_utc": "2026-08-18T09:00:00Z"},
    )
    entry["SOURCE_OBSERVED_AT_UTC"] = None
    manifest, payloads = _manifest([entry])
    assert _validate(manifest, payloads)["valid"] is True


def test_payload_mapping_extra_unbound_entry_is_rejected() -> None:
    manifest, payloads = _manifest()
    payloads["not-in-manifest"] = b"unbound"
    with _raises("UNBOUND_EXTRA_EVIDENCE"):
        _validate(manifest, payloads)


def test_external_authority_status_requires_an_authority_binding() -> None:
    entry = _entry(source_provenance_status="EXTERNAL_CONTRACT_BOUND")
    manifest, payloads = _manifest([entry])
    with _raises("SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        _validate(manifest, payloads)


def test_source_authority_proven_status_requires_external_entry_proof() -> None:
    manifest, payloads = _manifest()
    manifest["STATUS"]["SOURCE_AUTHORITY_VALIDITY"] = "PROVEN_BY_SOURCE_CONTRACT"
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    with _raises("SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        _validate(manifest, payloads)


def test_fake_source_authority_positive_claim_fails_closed() -> None:
    entry = _entry(
        source_provenance_status="EXTERNAL_CONTRACT_BOUND",
        source_authority_id="fake-provider-authority/v1",
    )
    manifest, payloads = _manifest([entry])
    manifest["STATUS"]["SOURCE_AUTHORITY_VALIDITY"] = "PROVEN_BY_SOURCE_CONTRACT"
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    with _raises("SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        _validate(manifest, payloads)


def test_source_authority_positive_status_without_external_proof_fails_closed() -> None:
    manifest, payloads = _manifest()
    manifest["STATUS"]["SOURCE_AUTHORITY_VALIDITY"] = "PROVEN_BY_SOURCE_CONTRACT"
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    with _raises("SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        _validate(manifest, payloads)


def test_generic_capture_cannot_claim_feature_dependency_completeness() -> None:
    manifest, payloads = _manifest()
    manifest["STATUS"]["FEATURE_DEPENDENCY_COMPLETENESS"] = "PROVEN"
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    with _raises("FEATURE_DEPENDENCY_UNPROVEN"):
        _validate(manifest, payloads)


def test_caller_supplied_git_sha_is_not_repository_provenance() -> None:
    manifest, payloads = _manifest()
    manifest["PROVENANCE"]["REPOSITORY_SOURCE_PROVENANCE"] = "a" * 40
    with _raises("PROVENANCE_SCHEMA_MISMATCH"):
        _validate(manifest, payloads)


def test_context_mutation_requires_new_content_digest_and_is_detectable() -> None:
    manifest, payloads = _manifest()
    original_context_id = manifest["PREDICTION_CONTEXT"]["PREDICTION_CONTEXT_ID"]
    manifest["PREDICTION_CONTEXT"]["PREDICTION_CONTEXT_ID"] = "prediction-context-2"
    with _raises("CAPTURE_CONTENT_DIGEST_MISMATCH"):
        _validate(manifest, payloads)
    assert original_context_id != manifest["PREDICTION_CONTEXT"]["PREDICTION_CONTEXT_ID"]


def test_manifest_json_round_trip_preserves_digest() -> None:
    manifest, payloads = _manifest()
    round_tripped = json.loads(json.dumps(manifest, ensure_ascii=False))
    assert compute_capture_content_digest(round_tripped) == manifest["CAPTURE_CONTENT_DIGEST"]
    assert _validate(round_tripped, payloads)["valid"] is True
