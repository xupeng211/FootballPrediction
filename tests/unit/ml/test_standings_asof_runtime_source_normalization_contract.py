"""Generic runtime-capture to standings-as-of normalization handoff tests.

lifecycle: permanent

All evidence and payloads are synthetic in-memory values. These tests do not
call a provider, network, database, clock, source parser, or runtime pipeline.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.ml.inference.feature_contract_boundary_validator import (
    validate_runtime_capture_manifest_against_canonical_registry,
)
from src.ml.inference.runtime_capture_contract import (
    RUNTIME_CAPTURE_CONTRACT_ID,
    RUNTIME_CAPTURE_CONTRACT_VERSION,
    compute_capture_content_digest,
)
from src.ml.inference.standings_asof_runtime_source_normalization_contract import (
    NormalizationValidationError,
    canonical_code_point_sorted,
    compute_fact_binding_digest,
    compute_normalization_content_digest,
    compute_output_input_binding_digest,
    source_record_ref_for_evidence_ids,
    validate_normalization_envelope_against_runtime_capture,
    validate_normalization_envelope_structure,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
VECTOR_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "standings_asof_runtime_source_normalization_digest_vectors.json"
)
ORDERING_VECTOR_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "standings_asof_runtime_source_normalization_ordering_vectors.json"
)
DECISION_TIME = "2026-08-18T12:00:00Z"
TARGET_KICKOFF = "2026-08-18T13:00:00Z"
DIGEST_VECTOR_COUNT = 20
ORDERING_VECTOR_COUNT = 23


def _payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _entry(
    evidence_id: str,
    payload: bytes,
    *,
    source_record_id: str | None,
    source_family: str = "GENERIC_TEST",
    source_provenance_status: str = "UNKNOWN",
) -> dict:
    return {
        "EVIDENCE_ID": evidence_id,
        "SOURCE_FAMILY": source_family,
        "SOURCE_AUTHORITY_ID": "authority-text-only",
        "SOURCE_RECORD_ID": source_record_id,
        "PAYLOAD_KIND": "BYTE_BLOB",
        "PAYLOAD_CONTENT_DIGEST": _payload_digest(payload),
        "PAYLOAD_BYTE_LENGTH": len(payload),
        "SOURCE_EVENT_TIME_UTC": "2026-08-18T09:00:00Z",
        "SOURCE_EFFECTIVE_TIME_UTC": None,
        "SOURCE_OBSERVED_AT_UTC": "2026-08-18T10:30:00Z",
        "SOURCE_CAPTURED_AT_UTC": "2026-08-18T11:00:00Z",
        "AVAILABILITY_PROOF_KIND": "EXACT_OBSERVATION_TIMESTAMP",
        "AVAILABILITY_PROOF_DATA": {"observed_at_field": "SOURCE_OBSERVED_AT_UTC"},
        "SOURCE_PROVENANCE_STATUS": source_provenance_status,
    }


def _capture_manifest(
    *,
    entries: list[dict] | None = None,
    selected: list[str] | None = None,
    context_overrides: dict | None = None,
) -> tuple[dict, dict[str, bytes]]:
    payloads = {
        "e-target": b"target-payload",
        "e-result": b"result-payload",
        "e-odds": b"odds-payload",
    }
    if entries is None:
        entries = [
            _entry("e-target", payloads["e-target"], source_record_id="record-target"),
            _entry("e-result", payloads["e-result"], source_record_id="record-result"),
            _entry(
                "e-odds",
                payloads["e-odds"],
                source_record_id=None,
                source_family="OTHER_FEATURE_TEST",
            ),
        ]
    context = {
        "PREDICTION_CONTEXT_ID": "prediction-context-1",
        "MODEL_ASOF_CONTRACT_ID": "canonical-model-asof/v1",
        "MODEL_ASOF_CONTRACT_VERSION": "v1",
        "MODEL_DECISION_TIME_UTC": DECISION_TIME,
        "FEATURE_AS_OF_UTC": DECISION_TIME,
        "TARGET_MATCH_ID": "target",
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
        "SELECTED_EVIDENCE_IDS": selected or [entry["EVIDENCE_ID"] for entry in entries],
        "STATUS": {
            "STRUCTURAL_CAPTURE_VALIDITY": "PROVEN",
            "SOURCE_AUTHORITY_VALIDITY": "UNKNOWN",
            "TEMPORAL_ELIGIBILITY_VALIDITY": "PROVEN",
            "FEATURE_DEPENDENCY_COMPLETENESS": "NOT_PROVEN",
        },
    }
    manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(manifest)
    return manifest, payloads


def _fact(binding_id: str, role: str, identity: str, evidence_ids: list[str], **extra) -> dict:
    binding = {
        "BINDING_ID": binding_id,
        "SEMANTIC_ROLE": role,
        "DOMAIN_IDENTITY": identity,
        "SOURCE_EVIDENCE_IDS": list(evidence_ids),
        "CANONICAL_MATCH_ID": None,
        "ADJUSTMENT_ID": None,
        "AVAILABILITY_EVIDENCE_ID": None,
        "NORMALIZED_FACT_DIGEST": None,
        "DERIVATION": "SOURCE_ATTESTED",
        **extra,
    }
    binding["NORMALIZED_FACT_DIGEST"] = compute_fact_binding_digest(binding)
    return binding


def _envelope(manifest: dict, *, standings_ids: list[str] | None = None) -> dict:
    selected = list(manifest["SELECTED_EVIDENCE_IDS"])
    standings_ids = standings_ids or ["e-target", "e-result"]
    by_id = {entry["EVIDENCE_ID"]: entry for entry in manifest["EVIDENCE"]}
    attestations = [deepcopy(by_id[evidence_id]) for evidence_id in standings_ids]
    facts = [
        _fact(
            "fact-target-fixture",
            "FIXTURE",
            "fixture:target",
            ["e-target"],
            CANONICAL_MATCH_ID="target",
        ),
        _fact(
            "fact-prior-fixture",
            "FIXTURE",
            "fixture:prior",
            ["e-result"],
            CANONICAL_MATCH_ID="prior",
        ),
        _fact(
            "fact-prior-result",
            "RESULT",
            "result:prior",
            ["e-result"],
            CANONICAL_MATCH_ID="prior",
            AVAILABILITY_EVIDENCE_ID="e-result",
        ),
    ]
    output = {
        "STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID": "standings-asof-engine-input/v1",
        "STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION": "v1",
        "STANDINGS_RANKING_CONTRACT_ID": "standings/premier-league-point-in-time/v1",
        "STANDINGS_RANKING_CONTRACT_VERSION": "v1",
        "CANONICAL_INPUT_DIGEST": "0" * 64,
        "MODEL_DECISION_TIME_UTC": DECISION_TIME,
        "FEATURE_AS_OF_UTC": DECISION_TIME,
        "TARGET_MATCH_ID": "target",
        "TARGET_KICKOFF_UTC": TARGET_KICKOFF,
        "FIXTURE_UNIVERSE_REFERENCE_ID": "fixture-universe-normalization-test",
        "FIXTURE_STATE_IDS": ["target", "prior"],
        "ADMINISTRATIVE_ADJUSTMENT_IDS": [],
        "OUTPUT_INPUT_BINDING_DIGEST": None,
    }
    output["OUTPUT_INPUT_BINDING_DIGEST"] = compute_output_input_binding_digest(output)
    envelope = {
        "NORMALIZATION_CONTRACT_ID": "standings-asof-runtime-source-normalization/v1",
        "NORMALIZATION_CONTRACT_VERSION": "v1",
        "NORMALIZATION_INSTANCE_ID": "normalization-instance-1",
        "NORMALIZATION_CONTENT_DIGEST": "0" * 64,
        "PREDICTION_CONTEXT": {
            "PREDICTION_CONTEXT_ID": manifest["PREDICTION_CONTEXT"]["PREDICTION_CONTEXT_ID"],
            "MODEL_ASOF_CONTRACT_ID": "canonical-model-asof/v1",
            "MODEL_ASOF_CONTRACT_VERSION": "v1",
            "MODEL_DECISION_TIME_UTC": DECISION_TIME,
            "FEATURE_AS_OF_UTC": DECISION_TIME,
            "TARGET_MATCH_ID": "target",
            "TARGET_KICKOFF_UTC": TARGET_KICKOFF,
        },
        "RUNTIME_CAPTURE_BINDING": {
            "RUNTIME_CAPTURE_CONTRACT_ID": RUNTIME_CAPTURE_CONTRACT_ID,
            "RUNTIME_CAPTURE_CONTRACT_VERSION": RUNTIME_CAPTURE_CONTRACT_VERSION,
            "CAPTURE_INSTANCE_ID": manifest["CAPTURE_INSTANCE_ID"],
            "CAPTURE_CONTENT_DIGEST": manifest["CAPTURE_CONTENT_DIGEST"],
            "CAPTURE_SELECTED_EVIDENCE_IDS": selected,
        },
        "STANDINGS_EVIDENCE_IDS": standings_ids,
        "EVIDENCE_ATTESTATIONS": attestations,
        "FACT_BINDINGS": facts,
        "OUTPUT_STANDINGS_INPUT_BINDING": output,
        "STATUS": {
            "NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY": "PROVEN",
            "CAPTURE_BINDING_VALIDITY": "PROVEN",
            "OUTPUT_INPUT_BINDING_VALIDITY": "NOT_PROVEN",
            "SOURCE_SEMANTIC_NORMALIZATION_VALIDITY": "NOT_PROVEN",
            "SOURCE_AUTHORITY_VALIDITY": "NOT_PROVEN",
            "SOURCE_STREAM_COMPLETENESS": "NOT_PROVEN",
            "RUNTIME_NUMERIC_ELIGIBILITY": "NO",
        },
    }
    envelope["NORMALIZATION_CONTENT_DIGEST"] = compute_normalization_content_digest(envelope)
    return envelope


def _refresh_digest(envelope: dict) -> None:
    envelope["NORMALIZATION_CONTENT_DIGEST"] = compute_normalization_content_digest(envelope)


def _validate(envelope: dict, manifest: dict, payloads: dict[str, bytes]) -> dict:
    return validate_normalization_envelope_against_runtime_capture(envelope, manifest, payloads)


def _raises(code: str):
    return pytest.raises(NormalizationValidationError, match=code)


def test_valid_capture_binding_and_subset_are_proven_without_source_authority() -> None:
    manifest, payloads = _capture_manifest()
    result = _validate(_envelope(manifest), manifest, payloads)
    assert result["valid"] is True
    assert result["capture_validation"]["selected_evidence_ids"] == (
        "e-odds",
        "e-result",
        "e-target",
    )
    assert result["statuses"]["CAPTURE_BINDING_VALIDITY"] == "PROVEN"
    assert result["statuses"]["SOURCE_SEMANTIC_NORMALIZATION_VALIDITY"] == "NOT_PROVEN"
    assert result["statuses"]["SOURCE_AUTHORITY_VALIDITY"] == "NOT_PROVEN"


@pytest.mark.parametrize(
    ("target", "mutation", "code"),
    [
        (
            "envelope",
            lambda value: value["RUNTIME_CAPTURE_BINDING"].update(
                RUNTIME_CAPTURE_CONTRACT_ID="canonical-runtime-capture/v2"
            ),
            "CONTRACT_VERSION_MISMATCH",
        ),
        (
            "manifest",
            lambda value: value.update(CAPTURE_INSTANCE_ID="capture-instance-other"),
            "CAPTURE_IDENTITY_MISMATCH",
        ),
        (
            "manifest",
            lambda value: value.update(CAPTURE_CONTENT_DIGEST="f" * 64),
            "CAPTURE_BINDING_INVALID",
        ),
        (
            "manifest",
            lambda value: value["PREDICTION_CONTEXT"].update(
                MODEL_DECISION_TIME_UTC="2026-08-18T11:59:59Z",
                FEATURE_AS_OF_UTC="2026-08-18T11:59:59Z",
            ),
            "CAPTURE_CONTEXT_MISMATCH",
        ),
        (
            "manifest",
            lambda value: value["PREDICTION_CONTEXT"].update(TARGET_MATCH_ID="target-other"),
            "CAPTURE_CONTEXT_MISMATCH",
        ),
        (
            "manifest",
            lambda value: value["PREDICTION_CONTEXT"].update(
                TARGET_KICKOFF_UTC="2026-08-18T14:00:00Z"
            ),
            "CAPTURE_CONTEXT_MISMATCH",
        ),
        (
            "manifest",
            lambda value: value["PREDICTION_CONTEXT"].update(
                FEATURE_AS_OF_UTC="2026-08-18T11:59:59Z"
            ),
            "CAPTURE_BINDING_INVALID",
        ),
        (
            "manifest",
            lambda value: value.update(SELECTED_EVIDENCE_IDS=["e-target", "e-result"]),
            "CAPTURE_SELECTION_MISMATCH",
        ),
    ],
)
def test_n01_n08_capture_binding_tamper_fails_closed(target: str, mutation, code: str) -> None:
    actual_manifest, payloads = _capture_manifest()
    envelope = _envelope(actual_manifest)
    mutation(envelope if target == "envelope" else actual_manifest)
    if target == "envelope":
        _refresh_digest(envelope)
    else:
        if code != "CAPTURE_BINDING_INVALID":
            actual_manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(
                actual_manifest
            )
        if code == "CAPTURE_SELECTION_MISMATCH":
            envelope["RUNTIME_CAPTURE_BINDING"]["CAPTURE_CONTENT_DIGEST"] = actual_manifest[
                "CAPTURE_CONTENT_DIGEST"
            ]
            _refresh_digest(envelope)
    with _raises(code):
        _validate(envelope, actual_manifest, payloads)


def test_n09_n10_selected_subset_is_strict_but_non_standings_selection_is_allowed() -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest, standings_ids=["e-result", "e-target"])
    assert _validate(envelope, manifest, payloads)["valid"] is True
    envelope["STANDINGS_EVIDENCE_IDS"] = ["e-unselected"]
    with _raises("STANDINGS_EVIDENCE_NOT_SELECTED"):
        validate_normalization_envelope_structure(envelope)


@pytest.mark.parametrize(
    "field",
    [
        "PAYLOAD_CONTENT_DIGEST",
        "SOURCE_EVENT_TIME_UTC",
        "SOURCE_OBSERVED_AT_UTC",
        "SOURCE_EFFECTIVE_TIME_UTC",
        "SOURCE_CAPTURED_AT_UTC",
        "AVAILABILITY_PROOF_KIND",
        "AVAILABILITY_PROOF_DATA",
        "SOURCE_FAMILY",
        "SOURCE_RECORD_ID",
    ],
)
def test_n11_n19_attestation_projection_cannot_rewrite_capture(field: str) -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest)
    attestation = envelope["EVIDENCE_ATTESTATIONS"][0]
    if field == "AVAILABILITY_PROOF_KIND":
        attestation[field] = "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T"
        attestation["AVAILABILITY_PROOF_DATA"] = {
            "start_utc": "2026-08-18T09:00:00Z",
            "end_utc": "2026-08-18T10:00:00Z",
        }
    else:
        attestation[field] = (
            {"observed_at_field": "SOURCE_CAPTURED_AT_UTC"}
            if field == "AVAILABILITY_PROOF_DATA"
            else "2026-08-18T11:30:00Z"
            if field.endswith("_UTC")
            else "evidence-other"
            if field in {"SOURCE_FAMILY", "SOURCE_RECORD_ID"}
            else "f" * 64
            if field == "PAYLOAD_CONTENT_DIGEST"
            else "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF"
        )
    _refresh_digest(envelope)
    expected_code = (
        "NORMALIZATION_SCHEMA_MISMATCH"
        if field == "AVAILABILITY_PROOF_DATA"
        else "ATTESTATION_CAPTURE_MISMATCH"
    )
    with _raises(expected_code):
        _validate(envelope, manifest, payloads)


def test_n20_n25_source_authority_spoofing_does_not_upgrade_generic_status() -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest)
    assert (
        _validate(envelope, manifest, payloads)["statuses"]["SOURCE_AUTHORITY_VALIDITY"]
        == "NOT_PROVEN"
    )
    envelope["EVIDENCE_ATTESTATIONS"][0]["SOURCE_PROVENANCE_STATUS"] = "EXTERNAL_CONTRACT_BOUND"
    _refresh_digest(envelope)
    with _raises("SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        validate_normalization_envelope_structure(envelope)

    envelope = _envelope(manifest)
    envelope["callerTrusted"] = True
    with _raises("NORMALIZATION_SCHEMA_MISMATCH"):
        validate_normalization_envelope_structure(envelope)

    positive_manifest, positive_payloads = _capture_manifest()
    positive_manifest["STATUS"]["SOURCE_AUTHORITY_VALIDITY"] = "PROVEN_BY_SOURCE_CONTRACT"
    positive_manifest["CAPTURE_CONTENT_DIGEST"] = compute_capture_content_digest(positive_manifest)
    with pytest.raises(ValueError, match="SOURCE_AUTHORITY_PROOF_UNAVAILABLE"):
        validate_runtime_capture_manifest_against_canonical_registry(
            positive_manifest, positive_payloads
        )


def test_n26_n32_source_record_and_proof_refs_are_traceable() -> None:
    manifest, _payloads = _capture_manifest()
    envelope = _envelope(manifest)
    with _raises("FACT_EVIDENCE_NOT_SELECTED"):
        tampered = deepcopy(envelope)
        tampered["FACT_BINDINGS"][0]["SOURCE_EVIDENCE_IDS"] = ["e-odds"]
        _refresh_digest(tampered)
        validate_normalization_envelope_structure(tampered)

    attestations = {
        "e-target": {"SOURCE_RECORD_ID": None},
        "e-result": {"SOURCE_RECORD_ID": None},
    }
    fallback_one = source_record_ref_for_evidence_ids("a" * 64, ["e-target"], attestations)
    fallback_two = source_record_ref_for_evidence_ids("a" * 64, ["e-target"], attestations)
    fallback_changed = source_record_ref_for_evidence_ids("b" * 64, ["e-target"], attestations)
    assert fallback_one == fallback_two
    assert fallback_one != fallback_changed
    assert fallback_one.startswith("capture:")


@pytest.mark.parametrize(
    "reason",
    [
        "PROVEN_POSTPONED_NOT_PLAYED_BY_T",
        "PROVEN_NOT_FINAL_BY_T",
        "PROVEN_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T",
        "PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T",
    ],
)
def test_n33_n38_source_dependent_no_table_remains_not_proven(reason: str) -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest)
    envelope["FACT_BINDINGS"][0]["DOMAIN_IDENTITY"] = f"source-status:{reason}"
    envelope["FACT_BINDINGS"][0]["NORMALIZED_FACT_DIGEST"] = compute_fact_binding_digest(
        envelope["FACT_BINDINGS"][0]
    )
    _refresh_digest(envelope)
    result = _validate(envelope, manifest, payloads)
    assert result["statuses"]["SOURCE_SEMANTIC_NORMALIZATION_VALIDITY"] == "NOT_PROVEN"
    assert result["statuses"]["SOURCE_AUTHORITY_VALIDITY"] == "NOT_PROVEN"
    assert result["statuses"]["SOURCE_STREAM_COMPLETENESS"] == "NOT_PROVEN"


def _apply_vector_operation(value: dict, operation: dict) -> dict:
    if operation["type"] == "REORDER_TOP_LEVEL":
        items = list(value.items())[::-1]
        value.clear()
        value.update(items)
        return value
    cursor = value
    parts = operation["path"].split(".")
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    last = parts[-1]
    if operation["type"] == "REVERSE":
        cursor[int(last) if isinstance(cursor, list) else last].reverse()
    elif operation["type"] == "SET":
        cursor[int(last) if isinstance(cursor, list) else last] = operation["value"]
    else:
        raise AssertionError(f"unknown vector operation {operation['type']}")
    return value


def test_shared_python_js_digest_vectors_have_expected_sha256_values() -> None:
    vectors = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    assert vectors["lifecycle"] == "test-fixture"
    assert len(vectors["vectors"]) == DIGEST_VECTOR_COUNT
    for vector in vectors["vectors"]:
        value = deepcopy(vectors["base"])
        for operation in vector["operations"]:
            _apply_vector_operation(value, operation)
        assert compute_normalization_content_digest(value) == vector["expected_digest"], vector[
            "id"
        ]


def test_permutation_and_timestamps_are_deterministic_and_input_is_not_mutated() -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest)
    envelope["STANDINGS_EVIDENCE_IDS"].reverse()
    envelope["EVIDENCE_ATTESTATIONS"].reverse()
    envelope["FACT_BINDINGS"].reverse()
    envelope["RUNTIME_CAPTURE_BINDING"]["CAPTURE_SELECTED_EVIDENCE_IDS"].reverse()
    _refresh_digest(envelope)
    before = deepcopy(envelope)
    result = _validate(envelope, manifest, payloads)
    assert result["valid"] is True
    assert envelope == before


def test_direct_code_point_order_matches_frozen_lexical_ascending() -> None:
    values = [
        "A-evidence",
        "a-evidence",
        "evidence-1",
        "evidence_1",
        "evidence.1",
        "evidence:1",
        "evidence/1",
        "Z-evidence",
        "z-evidence",
        "0-evidence",
        "9-evidence",
    ]
    assert canonical_code_point_sorted(values) == [
        "0-evidence",
        "9-evidence",
        "A-evidence",
        "Z-evidence",
        "a-evidence",
        "evidence-1",
        "evidence.1",
        "evidence/1",
        "evidence:1",
        "evidence_1",
        "z-evidence",
    ]
    assert canonical_code_point_sorted(["😀", "😁"]) == ["😀", "😁"]


def test_shared_ordering_adversarial_digest_vectors_match_python_serializer() -> None:
    vectors = json.loads(ORDERING_VECTOR_PATH.read_text(encoding="utf-8"))
    assert vectors["lifecycle"] == "test-fixture"
    assert len(vectors["vectors"]) == ORDERING_VECTOR_COUNT
    for vector in vectors["vectors"]:
        value = deepcopy(vectors["base"])
        for operation in vector["operations"]:
            _apply_vector_operation(value, operation)
        assert compute_normalization_content_digest(value) == vector["expected_digest"], vector[
            "id"
        ]


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        (
            "PAYLOAD_CONTENT_DIGEST",
            "f" * 64,
        ),
        (
            "SOURCE_OBSERVED_AT_UTC",
            "2026-08-18T11:30:00Z",
        ),
        (
            "AVAILABILITY_PROOF_KIND",
            "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
        ),
    ],
)
def test_f206_f208_capture_attestation_metadata_cannot_be_rewritten(
    field: str, tampered_value: object
) -> None:
    manifest, payloads = _capture_manifest()
    envelope = _envelope(manifest)
    attestation = envelope["EVIDENCE_ATTESTATIONS"][0]
    if field == "AVAILABILITY_PROOF_KIND":
        attestation[field] = tampered_value
        attestation["AVAILABILITY_PROOF_DATA"] = {
            "start_utc": "2026-08-18T09:00:00Z",
            "end_utc": "2026-08-18T10:00:00Z",
        }
    else:
        attestation[field] = tampered_value
    _refresh_digest(envelope)
    with _raises("ATTESTATION_CAPTURE_MISMATCH"):
        _validate(envelope, manifest, payloads)
