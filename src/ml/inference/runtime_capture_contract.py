"""Pure canonical runtime-capture contract and content-integrity validator.

lifecycle: permanent
component: Specialized / Internal (canonical capture/replay contract validator;
not a provider, source adapter, storage pipeline, or feature generator)

The model-feature registry is the semantic authority for the contract binding.
This module validates explicit in-memory capture manifests and supplied payload
bytes only.  It never reads files, calls the network or database, consults the
wall clock, invokes Git, or creates capture artifacts.

The manifest digest follows the repository's ``StableValue.stableStringify``
convention: recursively sorted object keys, preserved array meaning, compact
UTF-8 JSON, and SHA-256.  Evidence entries and selected evidence IDs are
canonicalized in deterministic ID order because their order is non-semantic.
The self-referential ``CAPTURE_CONTENT_DIGEST`` field is excluded explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

from src.ml.inference.model_asof_contract import (
    MODEL_ASOF_CONTRACT_ID,
    MODEL_ASOF_CONTRACT_VERSION,
    ModelAsOfValidationError,
    _parse_model_asof_utc,
    validate_model_as_of_context,
)

RUNTIME_CAPTURE_CONTRACT_ID = "canonical-runtime-capture/v1"
RUNTIME_CAPTURE_CONTRACT_VERSION = "v1"
CAPTURE_TIME_RELATION_TO_T = "CAPTURE_MUST_BE_LTE_T"
PAYLOAD_DIGEST_ALGORITHM = "SHA-256"
MANIFEST_DIGEST_ALGORITHM = "SHA-256"
CANONICAL_SERIALIZATION_AUTHORITY = "STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON"
SELF_EXCLUDING_DIGEST_SCOPE = "SELF_EXCLUDING_CANONICAL_MANIFEST"
PAYLOAD_DIGEST_SCOPE = "EXACT_PAYLOAD_BYTES"
CANONICAL_FEATURE_CONTRACT_AUTHORITY = "CANONICAL_FEATURE_CONTRACT_REGISTRY"

_FEATURE_CONTRACT_REGISTRY_TRUST_TOKEN = object()


@dataclass(frozen=True, init=False)
class ValidatedFeatureContractBinding:
    """Immutable feature binding issued by the canonical registry layer."""

    contract_id: str
    feature_contract_version: str
    authority: str

    def __init__(
        self,
        contract_id: str,
        feature_contract_version: str,
        *,
        _trust_token: object,
    ) -> None:
        if _trust_token is not _FEATURE_CONTRACT_REGISTRY_TRUST_TOKEN:
            raise TypeError("feature contract binding must be issued by the canonical registry")
        object.__setattr__(self, "contract_id", contract_id)
        object.__setattr__(self, "feature_contract_version", feature_contract_version)
        object.__setattr__(self, "authority", CANONICAL_FEATURE_CONTRACT_AUTHORITY)

    @classmethod
    def _from_canonical_registry(
        cls,
        contract_id: str,
        feature_contract_version: str,
        *,
        _trust_token: object,
    ) -> ValidatedFeatureContractBinding:
        return cls(
            contract_id,
            feature_contract_version,
            _trust_token=_trust_token,
        )

    def matches(self, contract_id: str, feature_contract_version: str) -> bool:
        """Return whether the bound context references this exact registry entry."""
        return (
            self.contract_id == contract_id
            and self.feature_contract_version == feature_contract_version
        )


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
_CONTROL_CHAR_LIMIT = 32
_UTC_FIELDS = {
    "MODEL_DECISION_TIME_UTC",
    "FEATURE_AS_OF_UTC",
    "TARGET_KICKOFF_UTC",
    "PREDICTION_GENERATED_AT_UTC",
    "MANIFEST_FINALIZED_AT_UTC",
    "SOURCE_EVENT_TIME_UTC",
    "SOURCE_EFFECTIVE_TIME_UTC",
    "SOURCE_OBSERVED_AT_UTC",
    "SOURCE_CAPTURED_AT_UTC",
}

PREDICTION_CONTEXT_FIELDS = frozenset(
    {
        "PREDICTION_CONTEXT_ID",
        "MODEL_ASOF_CONTRACT_ID",
        "MODEL_ASOF_CONTRACT_VERSION",
        "MODEL_DECISION_TIME_UTC",
        "FEATURE_AS_OF_UTC",
        "TARGET_MATCH_ID",
        "TARGET_KICKOFF_UTC",
        "FEATURE_CONTRACT_ID",
        "FEATURE_CONTRACT_VERSION",
        "PREDICTION_GENERATED_AT_UTC",
        "POST_DECISION_INFORMATION_DEPENDENCY_COUNT",
    }
)
MANIFEST_FIELDS = frozenset(
    {
        "RUNTIME_CAPTURE_CONTRACT_ID",
        "RUNTIME_CAPTURE_CONTRACT_VERSION",
        "CAPTURE_INSTANCE_ID",
        "CAPTURE_CONTENT_DIGEST",
        "MANIFEST_FINALIZED_AT_UTC",
        "PREDICTION_CONTEXT",
        "PROVENANCE",
        "EVIDENCE",
        "SELECTED_EVIDENCE_IDS",
        "STATUS",
    }
)
EVIDENCE_ENTRY_FIELDS = frozenset(
    {
        "EVIDENCE_ID",
        "SOURCE_FAMILY",
        "SOURCE_AUTHORITY_ID",
        "SOURCE_RECORD_ID",
        "PAYLOAD_KIND",
        "PAYLOAD_CONTENT_DIGEST",
        "PAYLOAD_BYTE_LENGTH",
        "SOURCE_EVENT_TIME_UTC",
        "SOURCE_EFFECTIVE_TIME_UTC",
        "SOURCE_OBSERVED_AT_UTC",
        "SOURCE_CAPTURED_AT_UTC",
        "AVAILABILITY_PROOF_KIND",
        "AVAILABILITY_PROOF_DATA",
        "SOURCE_PROVENANCE_STATUS",
    }
)
PROVENANCE_FIELDS = frozenset(
    {
        "CAPTURE_CONTENT_PROVENANCE",
        "SOURCE_PROVIDER_PROVENANCE",
        "REPOSITORY_SOURCE_PROVENANCE",
        "ENGINE_IMPLEMENTATION_IDENTITY",
        "MODEL_ARTIFACT_IDENTITY",
    }
)
STATUS_FIELDS = frozenset(
    {
        "STRUCTURAL_CAPTURE_VALIDITY",
        "SOURCE_AUTHORITY_VALIDITY",
        "TEMPORAL_ELIGIBILITY_VALIDITY",
        "FEATURE_DEPENDENCY_COMPLETENESS",
    }
)
AVAILABILITY_PROOF_KINDS = (
    "EXACT_OBSERVATION_TIMESTAMP",
    "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF",
    "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T",
)
SOURCE_PROVENANCE_STATUSES = ("UNKNOWN", "EXTERNAL_CONTRACT_BOUND")
PAYLOAD_KINDS = frozenset({"BYTE_BLOB", "CANONICAL_JSON"})
STATUS_VALUES = {
    "STRUCTURAL_CAPTURE_VALIDITY": frozenset({"PROVEN", "NOT_PROVEN"}),
    "SOURCE_AUTHORITY_VALIDITY": frozenset({"PROVEN_BY_SOURCE_CONTRACT", "NOT_PROVEN", "UNKNOWN"}),
    "TEMPORAL_ELIGIBILITY_VALIDITY": frozenset({"PROVEN", "NOT_PROVEN"}),
    "FEATURE_DEPENDENCY_COMPLETENESS": frozenset({"PROVEN", "NOT_PROVEN"}),
}

_RUNTIME_CAPTURE_BOUNDARY_FIELDS = {
    "contract_id",
    "version",
    "policy",
    "status",
    "capture_time_relation_to_t",
    "manifest_finalization_after_t_allowed",
    "prediction_context_fields",
    "manifest_fields",
    "evidence_entry_fields",
    "availability_proof_kinds",
    "source_provenance_statuses",
    "content_integrity",
    "invariants",
    "status_semantics",
    "security",
    "implementation_status",
}
_RUNTIME_CAPTURE_CONTENT_INTEGRITY = {
    "payload_digest_algorithm": PAYLOAD_DIGEST_ALGORITHM,
    "manifest_digest_algorithm": MANIFEST_DIGEST_ALGORITHM,
    "canonical_serialization": CANONICAL_SERIALIZATION_AUTHORITY,
    "manifest_digest_field": "CAPTURE_CONTENT_DIGEST",
    "manifest_digest_scope": SELF_EXCLUDING_DIGEST_SCOPE,
    "payload_digest_scope": PAYLOAD_DIGEST_SCOPE,
    "evidence_ordering": "EVIDENCE_ID_ASCENDING_FOR_DIGEST",
    "selected_evidence_ordering": "EVIDENCE_ID_ASCENDING",
}
_RUNTIME_CAPTURE_INVARIANTS = {
    "prediction_context_immutable": "YES",
    "model_asof_contract_binding_required": "YES",
    "feature_contract_binding_required": "YES",
    "model_decision_time_bound_in_capture": "YES",
    "feature_as_of_bound_in_capture": "YES",
    "target_match_id_bound_in_capture": "YES",
    "target_kickoff_bound_in_capture": "YES",
    "capture_instance_distinct_from_content_digest": "YES",
    "decision_evidence_set_explicit": "YES",
    "captured_evidence_distinct_from_selected_evidence": "YES",
    "post_decision_evidence_selected_count": 0,
    "capture_establishes_source_authority": "NO",
    "caller_can_self_assert_source_authority": "NO",
    "source_authority_proof_requires_external_canonical_authority": "YES",
    "unknown_source_authority_upgraded": "NO",
    "feature_contract_reference_matched_distinct_from_authority_proven": "YES",
    "caller_arbitrary_feature_mapping_can_establish_canonical_authority": "NO",
    "source_captured_at_is_observed_at_by_default": "NO",
    "source_event_time_is_observed_at": "NO",
    "unbound_extra_evidence_becomes_selected": "NO",
    "missing_selected_evidence_accepted": "NO",
    "structural_capture_validity_distinct_from_source_completeness": "YES",
    "secret_bearing_metadata_allowed": "NO",
    "caller_supplied_git_sha_proves_repository_provenance": "NO",
    "source_normalization_replay_proven": "NO",
    "feature_numeric_replay_proven": "NO",
    "train_inference_replay_proven": "NO",
}
_RUNTIME_CAPTURE_SECURITY = {
    "secret_bearing_metadata_allowed": "NO",
    "metadata_minimization": "REQUIRED",
}
_RUNTIME_CAPTURE_IMPLEMENTATION = {
    "validator_implemented": "YES",
    "storage_implemented": "NO",
    "pipeline_implemented": "NO",
    "live_capture_proven": "NO",
    "source_normalization_replay": "NO",
    "feature_numeric_replay": "NO",
    "train_inference_replay": "NO",
}


class RuntimeCaptureValidationError(ValueError):
    """Raised when a runtime capture manifest or payload binding is invalid."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _exact_object(value: Any, fields: set[str] | frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise RuntimeCaptureValidationError("CAPTURE_SCHEMA_MISMATCH", f"{label} malformed")
    return value


def _text(value: Any, label: str, *, safe_id: bool = False) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(char) < _CONTROL_CHAR_LIMIT for char in value)
    ):
        raise RuntimeCaptureValidationError("CAPTURE_SCHEMA_MISMATCH", f"{label} malformed")
    if safe_id and _SAFE_ID.fullmatch(value) is None:
        raise RuntimeCaptureValidationError("CAPTURE_SCHEMA_MISMATCH", f"{label} malformed")
    return value


def _optional_text(value: Any, label: str, *, safe_id: bool = False) -> None:
    if value is not None:
        _text(value, label, safe_id=safe_id)


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RuntimeCaptureValidationError("CAPTURE_DIGEST_INVALID", f"{label} malformed")
    return value


def _parse_utc(value: Any, field: str) -> datetime:
    try:
        return _parse_model_asof_utc(value, field, "CAPTURE_TIMESTAMP_INVALID")
    except ModelAsOfValidationError as exc:
        raise RuntimeCaptureValidationError(exc.reason_code, str(exc)) from exc


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeCaptureValidationError(
            "CAPTURE_CANONICALIZATION_FAILED", "capture content is not canonical JSON"
        ) from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_secret_keys(value: Any) -> None:
    forbidden = {
        "AUTHORIZATION",
        "AUTH_HEADER",
        "API_KEY",
        "BEARER_TOKEN",
        "COOKIE",
        "COOKIES",
        "CREDENTIAL",
        "CREDENTIALS",
        "PASSWORD",
        "REFRESH_TOKEN",
        "SECRET",
        "SECRET_KEY",
        "SESSION_ID",
        "SIGNED_CREDENTIAL",
        "TOKEN",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key.upper() in forbidden:
                raise RuntimeCaptureValidationError(
                    "SECRET_METADATA_FORBIDDEN", f"secret-bearing field {key} is forbidden"
                )
            _reject_secret_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_keys(child)


def _canonical_manifest_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    projection = deepcopy(manifest)
    projection.pop("CAPTURE_CONTENT_DIGEST", None)
    if isinstance(projection.get("EVIDENCE"), list):
        projection["EVIDENCE"] = sorted(
            projection["EVIDENCE"], key=lambda entry: str(entry.get("EVIDENCE_ID", ""))
        )
    if isinstance(projection.get("SELECTED_EVIDENCE_IDS"), list):
        projection["SELECTED_EVIDENCE_IDS"] = sorted(projection["SELECTED_EVIDENCE_IDS"])
    return projection


def compute_capture_content_digest(manifest: dict[str, Any]) -> str:
    """Return the self-excluding canonical manifest content digest."""
    if not isinstance(manifest, dict):
        raise RuntimeCaptureValidationError("CAPTURE_SCHEMA_MISMATCH", "manifest must be an object")
    return _sha256_bytes(_canonical_json_bytes(_canonical_manifest_projection(manifest)))


def _validate_registry_texts(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for field, expected_value in expected.items():
        actual = value.get(field)
        if actual != expected_value:
            raise ValueError(f"{label}.{field} malformed")


def validate_runtime_capture_registry_boundary(  # noqa: C901, PLR0912 -- one frozen registry boundary is validated as an exact contract.
    boundary: Any, error_type: type[ValueError]
) -> None:
    """Validate the singular runtime-capture binding in the feature registry."""
    try:
        capture = _exact_object(
            boundary, _RUNTIME_CAPTURE_BOUNDARY_FIELDS, "runtime-capture boundary"
        )
    except RuntimeCaptureValidationError as exc:
        raise error_type(str(exc)) from exc

    def fail(message: str) -> None:
        raise error_type(message)

    expected_text = {
        "contract_id": RUNTIME_CAPTURE_CONTRACT_ID,
        "version": RUNTIME_CAPTURE_CONTRACT_VERSION,
        "policy": "IMMUTABLE_DECISION_EVIDENCE_CAPTURE",
        "status": "FROZEN",
        "capture_time_relation_to_t": CAPTURE_TIME_RELATION_TO_T,
        "manifest_finalization_after_t_allowed": "YES",
    }
    if any(capture.get(field) != value for field, value in expected_text.items()):
        fail("runtime-capture boundary binding malformed")

    if capture["prediction_context_fields"] != sorted(PREDICTION_CONTEXT_FIELDS):
        fail("runtime-capture prediction context fields malformed")
    if capture["manifest_fields"] != sorted(MANIFEST_FIELDS):
        fail("runtime-capture manifest fields malformed")
    if capture["evidence_entry_fields"] != sorted(EVIDENCE_ENTRY_FIELDS):
        fail("runtime-capture evidence entry fields malformed")
    if capture["availability_proof_kinds"] != list(AVAILABILITY_PROOF_KINDS):
        fail("runtime-capture availability proof kinds malformed")
    if capture["source_provenance_statuses"] != list(SOURCE_PROVENANCE_STATUSES):
        fail("runtime-capture source provenance statuses malformed")

    content_integrity = capture.get("content_integrity")
    if (
        not isinstance(content_integrity, dict)
        or content_integrity != _RUNTIME_CAPTURE_CONTENT_INTEGRITY
    ):
        fail("runtime-capture content integrity binding malformed")
    invariants = capture.get("invariants")
    if not isinstance(invariants, dict) or invariants != _RUNTIME_CAPTURE_INVARIANTS:
        fail("runtime-capture invariants malformed")
    security = capture.get("security")
    if not isinstance(security, dict) or security != _RUNTIME_CAPTURE_SECURITY:
        fail("runtime-capture security binding malformed")
    implementation = capture.get("implementation_status")
    if not isinstance(implementation, dict) or implementation != _RUNTIME_CAPTURE_IMPLEMENTATION:
        fail("runtime-capture implementation status malformed")
    status_semantics = capture.get("status_semantics")
    if not isinstance(status_semantics, dict) or set(status_semantics) != set(STATUS_FIELDS):
        fail("runtime-capture status semantics malformed")
    for field in STATUS_FIELDS:
        if status_semantics[field] != sorted(STATUS_VALUES[field]):
            fail(f"runtime-capture status semantics.{field} malformed")


def _validate_provenance(provenance: Any) -> None:
    values = _exact_object(provenance, PROVENANCE_FIELDS, "capture provenance")
    expected = {
        "CAPTURE_CONTENT_PROVENANCE": "MANIFEST_AND_PAYLOAD_DIGESTS",
        "SOURCE_PROVIDER_PROVENANCE": "ENTRY_SOURCE_BINDING",
        "REPOSITORY_SOURCE_PROVENANCE": "EXTERNAL_BUILD_AUTHORITY_REQUIRED",
        "ENGINE_IMPLEMENTATION_IDENTITY": "EXTERNAL_BUILD_AUTHORITY_REQUIRED",
        "MODEL_ARTIFACT_IDENTITY": "FEATURE_CONTRACT_BINDING_ONLY",
    }
    if values != expected:
        raise RuntimeCaptureValidationError(
            "PROVENANCE_SCHEMA_MISMATCH", "capture provenance cannot assert unverified Git identity"
        )


def _validate_status(status: Any) -> None:
    values = _exact_object(status, STATUS_FIELDS, "capture status")
    for field, allowed in STATUS_VALUES.items():
        if values[field] not in allowed:
            raise RuntimeCaptureValidationError(
                "CAPTURE_SCHEMA_MISMATCH", f"capture status.{field} malformed"
            )
    if values["STRUCTURAL_CAPTURE_VALIDITY"] != "PROVEN":
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH",
            "a validated manifest must declare structural validity PROVEN",
        )


def _validate_context(
    context: Any,
    feature_contract_binding: ValidatedFeatureContractBinding,
) -> dict[str, Any]:
    values = _exact_object(context, PREDICTION_CONTEXT_FIELDS, "prediction context")
    _text(values["PREDICTION_CONTEXT_ID"], "PREDICTION_CONTEXT_ID", safe_id=True)
    if values["MODEL_ASOF_CONTRACT_ID"] != MODEL_ASOF_CONTRACT_ID:
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH", "capture model-as-of contract ID is unknown"
        )
    if values["MODEL_ASOF_CONTRACT_VERSION"] != MODEL_ASOF_CONTRACT_VERSION:
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH", "capture model-as-of contract version is unknown"
        )
    _text(values["TARGET_MATCH_ID"], "TARGET_MATCH_ID", safe_id=True)
    feature_id = _text(values["FEATURE_CONTRACT_ID"], "FEATURE_CONTRACT_ID", safe_id=True)
    feature_version = _text(
        values["FEATURE_CONTRACT_VERSION"], "FEATURE_CONTRACT_VERSION", safe_id=True
    )
    if not isinstance(feature_contract_binding, ValidatedFeatureContractBinding):
        raise RuntimeCaptureValidationError(
            "FEATURE_CONTRACT_BINDING_UNTRUSTED",
            "feature contract binding must be issued by the canonical registry",
        )
    if not feature_contract_binding.matches(feature_id, feature_version):
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH", "capture feature contract binding is unknown"
        )
    dependency_count = values["POST_DECISION_INFORMATION_DEPENDENCY_COUNT"]
    if (
        isinstance(dependency_count, bool)
        or not isinstance(dependency_count, int)
        or dependency_count != 0
    ):
        raise RuntimeCaptureValidationError(
            "SOURCE_AVAILABLE_AFTER_DECISION", "post-decision dependency count must be zero"
        )
    if values["PREDICTION_GENERATED_AT_UTC"] is not None:
        _parse_utc(values["PREDICTION_GENERATED_AT_UTC"], "PREDICTION_GENERATED_AT_UTC")
    return values


def _validate_evidence_shape(  # noqa: C901, PLR0912 -- proof-kind branches are fail-closed schema rules.
    entry: Any, index: int
) -> dict[str, Any]:
    label = f"EVIDENCE[{index}]"
    values = _exact_object(entry, EVIDENCE_ENTRY_FIELDS, label)
    _text(values["EVIDENCE_ID"], f"{label}.EVIDENCE_ID", safe_id=True)
    _text(values["SOURCE_FAMILY"], f"{label}.SOURCE_FAMILY", safe_id=True)
    _optional_text(values["SOURCE_AUTHORITY_ID"], f"{label}.SOURCE_AUTHORITY_ID", safe_id=True)
    _optional_text(values["SOURCE_RECORD_ID"], f"{label}.SOURCE_RECORD_ID", safe_id=True)
    if values["PAYLOAD_KIND"] not in PAYLOAD_KINDS:
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH", f"{label}.PAYLOAD_KIND malformed"
        )
    _hex64(values["PAYLOAD_CONTENT_DIGEST"], f"{label}.PAYLOAD_CONTENT_DIGEST")
    byte_length = values["PAYLOAD_BYTE_LENGTH"]
    if isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length < 0:
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH", f"{label}.PAYLOAD_BYTE_LENGTH malformed"
        )
    for field in (
        "SOURCE_EVENT_TIME_UTC",
        "SOURCE_EFFECTIVE_TIME_UTC",
        "SOURCE_OBSERVED_AT_UTC",
        "SOURCE_CAPTURED_AT_UTC",
    ):
        if values[field] is None:
            if field == "SOURCE_CAPTURED_AT_UTC":
                raise RuntimeCaptureValidationError(
                    "CAPTURE_TIMESTAMP_INVALID", f"{label}.{field} is required"
                )
        else:
            _parse_utc(values[field], f"{label}.{field}")
    if values["AVAILABILITY_PROOF_KIND"] not in AVAILABILITY_PROOF_KINDS:
        raise RuntimeCaptureValidationError(
            "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label}.AVAILABILITY_PROOF_KIND malformed"
        )
    proof_data = values["AVAILABILITY_PROOF_DATA"]
    if not isinstance(proof_data, dict):
        raise RuntimeCaptureValidationError(
            "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label}.AVAILABILITY_PROOF_DATA malformed"
        )
    kind = values["AVAILABILITY_PROOF_KIND"]
    if kind == "EXACT_OBSERVATION_TIMESTAMP":
        if (
            set(proof_data) != {"observed_at_field"}
            or proof_data["observed_at_field"] != "SOURCE_OBSERVED_AT_UTC"
        ):
            raise RuntimeCaptureValidationError(
                "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label} observation proof malformed"
            )
        if values["SOURCE_OBSERVED_AT_UTC"] is None:
            raise RuntimeCaptureValidationError(
                "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label} observation timestamp missing"
            )
    elif kind == "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF":
        if set(proof_data) != {"effective_time_field", "observed_at_field"} or proof_data != {
            "effective_time_field": "SOURCE_EFFECTIVE_TIME_UTC",
            "observed_at_field": "SOURCE_OBSERVED_AT_UTC",
        }:
            raise RuntimeCaptureValidationError(
                "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label} effective-time proof malformed"
            )
        if values["SOURCE_EFFECTIVE_TIME_UTC"] is None or values["SOURCE_OBSERVED_AT_UTC"] is None:
            raise RuntimeCaptureValidationError(
                "SOURCE_AVAILABILITY_TIME_UNPROVEN", f"{label} effective-time proof incomplete"
            )
    else:
        if set(proof_data) != {"start_utc", "end_utc"}:
            raise RuntimeCaptureValidationError(
                "SOURCE_TIME_PRECISION_AMBIGUOUS", f"{label} interval proof malformed"
            )
        start = _parse_utc(proof_data["start_utc"], f"{label}.AVAILABILITY_PROOF_DATA.start_utc")
        end = _parse_utc(proof_data["end_utc"], f"{label}.AVAILABILITY_PROOF_DATA.end_utc")
        if start >= end:
            raise RuntimeCaptureValidationError(
                "SOURCE_TIME_PRECISION_AMBIGUOUS", f"{label} interval is malformed"
            )
    if values["SOURCE_PROVENANCE_STATUS"] not in SOURCE_PROVENANCE_STATUSES:
        raise RuntimeCaptureValidationError(
            "PROVENANCE_SCHEMA_MISMATCH", f"{label}.SOURCE_PROVENANCE_STATUS malformed"
        )
    if (
        values["SOURCE_PROVENANCE_STATUS"] == "EXTERNAL_CONTRACT_BOUND"
        and values["SOURCE_AUTHORITY_ID"] is None
    ):
        raise RuntimeCaptureValidationError(
            "SOURCE_AUTHORITY_PROOF_UNAVAILABLE",
            f"{label} external authority binding is not trusted",
        )
    return values


def _model_asof_evidence(entry: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "SOURCE_EVENT_TIME_UTC": entry["SOURCE_EVENT_TIME_UTC"],
        "SOURCE_EFFECTIVE_TIME_UTC": entry["SOURCE_EFFECTIVE_TIME_UTC"],
        "SOURCE_OBSERVED_AT_UTC": entry["SOURCE_OBSERVED_AT_UTC"],
        "SOURCE_CAPTURED_AT_UTC": entry["SOURCE_CAPTURED_AT_UTC"],
        "availability_proof": entry["AVAILABILITY_PROOF_KIND"],
    }
    if entry["AVAILABILITY_PROOF_KIND"] == "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T":
        result["SOURCE_AVAILABILITY_INTERVAL_START_UTC"] = entry["AVAILABILITY_PROOF_DATA"][
            "start_utc"
        ]
        result["SOURCE_AVAILABILITY_INTERVAL_END_UTC"] = entry["AVAILABILITY_PROOF_DATA"]["end_utc"]
    if entry["SOURCE_FAMILY"].upper().startswith("ODDS"):
        result["kind"] = "odds"
    return result


def _validate_payloads(entries: list[dict[str, Any]], payloads: Mapping[str, bytes]) -> None:
    if not isinstance(payloads, Mapping) or any(not isinstance(key, str) for key in payloads):
        raise RuntimeCaptureValidationError(
            "PAYLOAD_BINDING_INVALID", "payloads must map string IDs to bytes"
        )
    entry_ids = {entry["EVIDENCE_ID"] for entry in entries}
    if set(payloads) != entry_ids:
        missing = sorted(entry_ids - set(payloads))
        extra = sorted(set(payloads) - entry_ids)
        if missing:
            raise RuntimeCaptureValidationError(
                "SELECTED_EVIDENCE_MISSING", f"payloads missing evidence {missing[0]}"
            )
        raise RuntimeCaptureValidationError(
            "UNBOUND_EXTRA_EVIDENCE", f"payloads contain unbound evidence {extra[0]}"
        )
    for entry in entries:
        payload = payloads[entry["EVIDENCE_ID"]]
        if not isinstance(payload, bytes):
            raise RuntimeCaptureValidationError(
                "PAYLOAD_BINDING_INVALID", f"payload {entry['EVIDENCE_ID']} must be bytes"
            )
        if len(payload) != entry["PAYLOAD_BYTE_LENGTH"]:
            raise RuntimeCaptureValidationError(
                "PAYLOAD_LENGTH_MISMATCH", f"payload {entry['EVIDENCE_ID']} byte length mismatch"
            )
        if _sha256_bytes(payload) != entry["PAYLOAD_CONTENT_DIGEST"]:
            raise RuntimeCaptureValidationError(
                "PAYLOAD_DIGEST_MISMATCH", f"payload {entry['EVIDENCE_ID']} digest mismatch"
            )


def _validate_source_authority_claims(
    status: dict[str, Any], entries: list[dict[str, Any]]
) -> None:
    """Reject positive claims until a source-specific trust boundary exists."""
    positive_manifest_claim = status["SOURCE_AUTHORITY_VALIDITY"] == "PROVEN_BY_SOURCE_CONTRACT"
    positive_entry_claim = any(
        entry["SOURCE_PROVENANCE_STATUS"] == "EXTERNAL_CONTRACT_BOUND" for entry in entries
    )
    if positive_manifest_claim or positive_entry_claim:
        raise RuntimeCaptureValidationError(
            "SOURCE_AUTHORITY_PROOF_UNAVAILABLE",
            "generic capture validation has no trusted external source-authority binding",
        )


def validate_runtime_capture_manifest(  # noqa: C901, PLR0912 -- ordered fail-closed manifest validation.
    manifest: dict[str, Any],
    payloads: Mapping[str, bytes],
    *,
    feature_contract_binding: ValidatedFeatureContractBinding,
) -> dict[str, Any]:
    """Validate a manifest and exact payload bytes without I/O or wall-clock state.

    ``feature_contract_binding`` is issued by the already validated canonical
    feature registry.  Requiring its immutable trust-boundary type keeps this
    validator pure without allowing an arbitrary caller mapping to masquerade
    as canonical feature authority.
    """
    _reject_secret_keys(manifest)
    values = _exact_object(manifest, MANIFEST_FIELDS, "runtime capture manifest")
    if values["RUNTIME_CAPTURE_CONTRACT_ID"] != RUNTIME_CAPTURE_CONTRACT_ID:
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH", "runtime capture contract ID is unknown"
        )
    if values["RUNTIME_CAPTURE_CONTRACT_VERSION"] != RUNTIME_CAPTURE_CONTRACT_VERSION:
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH", "runtime capture contract version is unknown"
        )
    _text(values["CAPTURE_INSTANCE_ID"], "CAPTURE_INSTANCE_ID", safe_id=True)
    _hex64(values["CAPTURE_CONTENT_DIGEST"], "CAPTURE_CONTENT_DIGEST")
    _parse_utc(values["MANIFEST_FINALIZED_AT_UTC"], "MANIFEST_FINALIZED_AT_UTC")
    _validate_provenance(values["PROVENANCE"])
    _validate_status(values["STATUS"])
    context = _validate_context(values["PREDICTION_CONTEXT"], feature_contract_binding)

    raw_entries = values["EVIDENCE"]
    if not isinstance(raw_entries, list):
        raise RuntimeCaptureValidationError("CAPTURE_SCHEMA_MISMATCH", "EVIDENCE must be a list")
    entries = [_validate_evidence_shape(entry, index) for index, entry in enumerate(raw_entries)]
    _validate_source_authority_claims(values["STATUS"], entries)
    if values["STATUS"]["FEATURE_DEPENDENCY_COMPLETENESS"] == "PROVEN":
        raise RuntimeCaptureValidationError(
            "FEATURE_DEPENDENCY_UNPROVEN",
            "generic capture validation has no feature dependency authority",
        )
    evidence_ids = [entry["EVIDENCE_ID"] for entry in entries]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise RuntimeCaptureValidationError("DUPLICATE_EVIDENCE_ID", "duplicate evidence ID")
    source_record_ids = [
        entry["SOURCE_RECORD_ID"] for entry in entries if entry["SOURCE_RECORD_ID"]
    ]
    if len(set(source_record_ids)) != len(source_record_ids):
        raise RuntimeCaptureValidationError(
            "SOURCE_RECORD_ID_CONFLICT", "duplicate source record identity in capture"
        )

    selected = values["SELECTED_EVIDENCE_IDS"]
    if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH", "selected evidence IDs malformed"
        )
    if len(set(selected)) != len(selected):
        raise RuntimeCaptureValidationError(
            "DUPLICATE_EVIDENCE_ID", "selected evidence IDs duplicate"
        )
    unknown_selected = sorted(set(selected) - set(evidence_ids))
    if unknown_selected:
        raise RuntimeCaptureValidationError(
            "SELECTED_EVIDENCE_UNKNOWN", f"selected evidence {unknown_selected[0]} is unknown"
        )

    _validate_payloads(entries, payloads)
    by_id = {entry["EVIDENCE_ID"]: entry for entry in entries}
    decision_time = _parse_utc(context["MODEL_DECISION_TIME_UTC"], "MODEL_DECISION_TIME_UTC")
    selected_entries = [by_id[evidence_id] for evidence_id in selected]
    for entry in selected_entries:
        captured_at = _parse_utc(entry["SOURCE_CAPTURED_AT_UTC"], "SOURCE_CAPTURED_AT_UTC")
        if captured_at > decision_time:
            raise RuntimeCaptureValidationError(
                "SOURCE_AVAILABLE_AFTER_DECISION",
                f"selected evidence {entry['EVIDENCE_ID']} was captured after T",
            )

    model_context = dict(context)
    model_context["evidence"] = [_model_asof_evidence(entry) for entry in selected_entries]
    try:
        validate_model_as_of_context(model_context)
    except ModelAsOfValidationError as exc:
        raise RuntimeCaptureValidationError(exc.reason_code, str(exc)) from exc

    expected_digest = compute_capture_content_digest(values)
    if expected_digest != values["CAPTURE_CONTENT_DIGEST"]:
        raise RuntimeCaptureValidationError(
            "CAPTURE_CONTENT_DIGEST_MISMATCH", "capture content digest mismatch"
        )
    return {
        "valid": True,
        "capture_instance_id": values["CAPTURE_INSTANCE_ID"],
        "capture_content_digest": expected_digest,
        "selected_evidence_ids": tuple(sorted(selected)),
        "post_decision_evidence_selected_count": 0,
        "structural_capture_validity": "PROVEN",
        "source_authority_validity": values["STATUS"]["SOURCE_AUTHORITY_VALIDITY"],
        "feature_contract_reference": "FEATURE_CONTRACT_REFERENCE_MATCHED",
        "canonical_feature_contract_authority": "CANONICAL_FEATURE_CONTRACT_AUTHORITY_PROVEN",
        "temporal_eligibility_validity": "PROVEN",
        "feature_dependency_completeness": values["STATUS"]["FEATURE_DEPENDENCY_COMPLETENESS"],
        "source_normalization_replay": "NOT_PROVEN",
        "feature_numeric_replay": "NOT_PROVEN",
        "train_inference_replay": "NOT_PROVEN",
    }


__all__ = [
    "AVAILABILITY_PROOF_KINDS",
    "CANONICAL_SERIALIZATION_AUTHORITY",
    "CAPTURE_TIME_RELATION_TO_T",
    "EVIDENCE_ENTRY_FIELDS",
    "MANIFEST_DIGEST_ALGORITHM",
    "MANIFEST_FIELDS",
    "MODEL_ASOF_CONTRACT_ID",
    "PAYLOAD_DIGEST_ALGORITHM",
    "PREDICTION_CONTEXT_FIELDS",
    "PROVENANCE_FIELDS",
    "RUNTIME_CAPTURE_CONTRACT_ID",
    "RUNTIME_CAPTURE_CONTRACT_VERSION",
    "RuntimeCaptureValidationError",
    "ValidatedFeatureContractBinding",
    "compute_capture_content_digest",
    "validate_runtime_capture_manifest",
    "validate_runtime_capture_registry_boundary",
]
