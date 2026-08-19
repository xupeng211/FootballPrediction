"""Pure runtime-capture to standings-as-of normalization-envelope binding.

lifecycle: permanent
component: Specialized / Internal (generic normalization handoff validator;
not a provider, source parser, source authority, storage pipeline, or runtime)

This module validates a language-neutral envelope against an already validated
runtime-capture manifest.  It deliberately proves identity and content
integrity only.  It never interprets a provider payload, grants source
authority, proves stream closure, or writes a capture/normalization artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any

from src.ml.inference.model_asof_contract import (
    MODEL_ASOF_CONTRACT_ID,
    MODEL_ASOF_CONTRACT_VERSION,
    ModelAsOfValidationError,
    _parse_model_asof_utc,
)
from src.ml.inference.runtime_capture_contract import (
    EVIDENCE_ENTRY_FIELDS,
    RUNTIME_CAPTURE_CONTRACT_ID,
    RUNTIME_CAPTURE_CONTRACT_VERSION,
)

NORMALIZATION_CONTRACT_ID = "standings-asof-runtime-source-normalization/v1"
NORMALIZATION_CONTRACT_VERSION = "v1"
NORMALIZATION_CONTRACT_STATUS = "FROZEN"
NORMALIZATION_CONTENT_DIGEST_ALGORITHM = "SHA-256"
NORMALIZATION_CONTENT_DIGEST_SCOPE = "SELF_EXCLUDING_CANONICAL_NORMALIZATION_ENVELOPE"
CANONICAL_SERIALIZATION = "STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON"
STANDINGS_INPUT_CONTRACT_ID = "standings-asof-engine-input/v1"
STANDINGS_INPUT_CONTRACT_VERSION = "v1"
STANDINGS_CONTRACT_ID = "standings/premier-league-point-in-time/v1"
STANDINGS_CONTRACT_VERSION = "v1"

NORMALIZATION_ENVELOPE_FIELDS = frozenset(
    {
        "NORMALIZATION_CONTRACT_ID",
        "NORMALIZATION_CONTRACT_VERSION",
        "NORMALIZATION_INSTANCE_ID",
        "NORMALIZATION_CONTENT_DIGEST",
        "PREDICTION_CONTEXT",
        "RUNTIME_CAPTURE_BINDING",
        "STANDINGS_EVIDENCE_IDS",
        "EVIDENCE_ATTESTATIONS",
        "FACT_BINDINGS",
        "OUTPUT_STANDINGS_INPUT_BINDING",
        "STATUS",
    }
)
PREDICTION_CONTEXT_FIELDS = frozenset(
    {
        "PREDICTION_CONTEXT_ID",
        "MODEL_ASOF_CONTRACT_ID",
        "MODEL_ASOF_CONTRACT_VERSION",
        "MODEL_DECISION_TIME_UTC",
        "FEATURE_AS_OF_UTC",
        "TARGET_MATCH_ID",
        "TARGET_KICKOFF_UTC",
    }
)
RUNTIME_CAPTURE_BINDING_FIELDS = frozenset(
    {
        "RUNTIME_CAPTURE_CONTRACT_ID",
        "RUNTIME_CAPTURE_CONTRACT_VERSION",
        "CAPTURE_INSTANCE_ID",
        "CAPTURE_CONTENT_DIGEST",
        "CAPTURE_SELECTED_EVIDENCE_IDS",
    }
)
FACT_BINDING_FIELDS = frozenset(
    {
        "BINDING_ID",
        "SEMANTIC_ROLE",
        "DOMAIN_IDENTITY",
        "SOURCE_EVIDENCE_IDS",
        "CANONICAL_MATCH_ID",
        "ADJUSTMENT_ID",
        "AVAILABILITY_EVIDENCE_ID",
        "NORMALIZED_FACT_DIGEST",
        "DERIVATION",
    }
)
OUTPUT_STANDINGS_INPUT_BINDING_FIELDS = frozenset(
    {
        "STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID",
        "STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION",
        "STANDINGS_RANKING_CONTRACT_ID",
        "STANDINGS_RANKING_CONTRACT_VERSION",
        "CANONICAL_INPUT_DIGEST",
        "MODEL_DECISION_TIME_UTC",
        "FEATURE_AS_OF_UTC",
        "TARGET_MATCH_ID",
        "TARGET_KICKOFF_UTC",
        "FIXTURE_UNIVERSE_REFERENCE_ID",
        "FIXTURE_STATE_IDS",
        "ADMINISTRATIVE_ADJUSTMENT_IDS",
        "OUTPUT_INPUT_BINDING_DIGEST",
    }
)
STATUS_FIELDS = frozenset(
    {
        "NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY",
        "CAPTURE_BINDING_VALIDITY",
        "OUTPUT_INPUT_BINDING_VALIDITY",
        "SOURCE_SEMANTIC_NORMALIZATION_VALIDITY",
        "SOURCE_AUTHORITY_VALIDITY",
        "SOURCE_STREAM_COMPLETENESS",
        "RUNTIME_NUMERIC_ELIGIBILITY",
    }
)
FACT_BINDING_ROLES = frozenset(
    {
        "FIXTURE_UNIVERSE",
        "FIXTURE",
        "FIXTURE_STATUS",
        "RESULT",
        "ADMIN_ADJUSTMENT",
        "TARGET_IDENTITY",
    }
)
DERIVATIONS = frozenset({"SOURCE_ATTESTED", "CORE_DERIVED"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$")
_TIMESTAMP_KEYS = frozenset({"start_utc", "end_utc"})
_SECRET_KEYS = frozenset(
    {
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
)


def canonical_code_point_sorted(values: list[str], *, key=None) -> list[str]:
    """Return Unicode code-point lexicographic ascending order.

    Python strings compare by Unicode code points, matching the frozen
    normalization contract for every schema-permitted identifier.  This helper
    keeps that ordering rule explicit at the normalization boundary rather than
    relying on scattered sort assumptions.
    """
    return sorted(values, key=key)


class NormalizationValidationError(ValueError):
    """Raised when a normalization envelope or bridge is invalid."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _exact_object(value: Any, fields: set[str] | frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise NormalizationValidationError("NORMALIZATION_SCHEMA_MISMATCH", f"{label} malformed")
    return value


def _text(value: Any, label: str, *, safe_id: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NormalizationValidationError("NORMALIZATION_SCHEMA_MISMATCH", f"{label} malformed")
    if safe_id and _SAFE_ID.fullmatch(value) is None:
        raise NormalizationValidationError("NORMALIZATION_SCHEMA_MISMATCH", f"{label} malformed")
    return value


def _optional_text(value: Any, label: str, *, safe_id: bool = False) -> None:
    if value is not None:
        _text(value, label, safe_id=safe_id)


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise NormalizationValidationError("NORMALIZATION_DIGEST_INVALID", f"{label} malformed")
    return value


def _timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise NormalizationValidationError("NORMALIZATION_TIMESTAMP_INVALID", f"{label} malformed")
    try:
        parsed = _parse_model_asof_utc(value, label, "NORMALIZATION_TIMESTAMP_INVALID")
    except ModelAsOfValidationError as exc:
        raise NormalizationValidationError(exc.reason_code, str(exc)) from exc
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key.upper() in _SECRET_KEYS:
                raise NormalizationValidationError(
                    "SECRET_METADATA_FORBIDDEN", f"secret-bearing field {key} is forbidden"
                )
            _reject_secret_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_keys(child)


def _canonicalize_tree(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            child_key: _canonicalize_tree(value[child_key], child_key)
            for child_key in canonical_code_point_sorted(value)
        }
    if isinstance(value, list):
        return [_canonicalize_tree(child, key) for child in value]
    if isinstance(value, str) and (
        key is not None and (key.endswith("_UTC") or key in _TIMESTAMP_KEYS)
    ):
        return _timestamp(value, key)
    return value


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
        raise NormalizationValidationError(
            "NORMALIZATION_CANONICALIZATION_FAILED", "value is not canonical JSON"
        ) from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _sorted_unique_ids(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise NormalizationValidationError("NORMALIZATION_SCHEMA_MISMATCH", f"{label} malformed")
    if any(_SAFE_ID.fullmatch(item or "") is None for item in value):
        raise NormalizationValidationError("NORMALIZATION_SCHEMA_MISMATCH", f"{label} malformed")
    if len(set(value)) != len(value):
        raise NormalizationValidationError(
            "NORMALIZATION_DUPLICATE_ID", f"{label} must contain unique IDs"
        )
    return canonical_code_point_sorted(value)


def _ordered_projection(  # noqa: C901 -- canonical projection keeps each non-semantic array rule explicit.
    envelope: dict[str, Any], *, include_digest: bool = False
) -> dict[str, Any]:
    projection = deepcopy(envelope)
    if not include_digest:
        projection.pop("NORMALIZATION_CONTENT_DIGEST", None)
    capture = projection.get("RUNTIME_CAPTURE_BINDING")
    if isinstance(capture, dict) and isinstance(capture.get("CAPTURE_SELECTED_EVIDENCE_IDS"), list):
        capture["CAPTURE_SELECTED_EVIDENCE_IDS"] = canonical_code_point_sorted(
            capture["CAPTURE_SELECTED_EVIDENCE_IDS"]
        )
    if isinstance(projection.get("STANDINGS_EVIDENCE_IDS"), list):
        projection["STANDINGS_EVIDENCE_IDS"] = canonical_code_point_sorted(
            projection["STANDINGS_EVIDENCE_IDS"]
        )
    if isinstance(projection.get("EVIDENCE_ATTESTATIONS"), list):
        projection["EVIDENCE_ATTESTATIONS"] = canonical_code_point_sorted(
            projection["EVIDENCE_ATTESTATIONS"], key=lambda row: row.get("EVIDENCE_ID", "")
        )
    if isinstance(projection.get("FACT_BINDINGS"), list):
        for binding in projection["FACT_BINDINGS"]:
            if isinstance(binding, dict) and isinstance(binding.get("SOURCE_EVIDENCE_IDS"), list):
                binding["SOURCE_EVIDENCE_IDS"] = canonical_code_point_sorted(
                    binding["SOURCE_EVIDENCE_IDS"]
                )
        projection["FACT_BINDINGS"] = canonical_code_point_sorted(
            projection["FACT_BINDINGS"], key=lambda row: row.get("BINDING_ID", "")
        )
    output = projection.get("OUTPUT_STANDINGS_INPUT_BINDING")
    if isinstance(output, dict):
        for field in ("FIXTURE_STATE_IDS", "ADMINISTRATIVE_ADJUSTMENT_IDS"):
            if isinstance(output.get(field), list):
                output[field] = canonical_code_point_sorted(output[field])
    return _canonicalize_tree(projection)


def compute_normalization_content_digest(envelope: dict[str, Any]) -> str:
    """Compute the self-excluding canonical normalization-envelope digest."""
    if not isinstance(envelope, dict):
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", "envelope must be an object"
        )
    return _sha256_json(_ordered_projection(envelope))


def compute_fact_binding_digest(binding: dict[str, Any]) -> str:
    """Compute the self-excluding digest for one normalized fact binding."""
    projection = deepcopy(binding)
    projection.pop("NORMALIZED_FACT_DIGEST", None)
    if isinstance(projection.get("SOURCE_EVIDENCE_IDS"), list):
        projection["SOURCE_EVIDENCE_IDS"] = canonical_code_point_sorted(
            projection["SOURCE_EVIDENCE_IDS"]
        )
    return _sha256_json(_canonicalize_tree(projection))


def compute_output_input_binding_digest(binding: dict[str, Any]) -> str:
    """Compute the self-excluding digest for the candidate standings input binding."""
    projection = deepcopy(binding)
    projection.pop("OUTPUT_INPUT_BINDING_DIGEST", None)
    for field in ("FIXTURE_STATE_IDS", "ADMINISTRATIVE_ADJUSTMENT_IDS"):
        if isinstance(projection.get(field), list):
            projection[field] = canonical_code_point_sorted(projection[field])
    return _sha256_json(_canonicalize_tree(projection))


def source_record_ref_for_evidence_ids(
    capture_content_digest: str,
    evidence_ids: list[str],
    attestations_by_id: Mapping[str, dict[str, Any]],
) -> str:
    """Return the deterministic sourceRecordRef bridge for a lineage set."""
    ids = canonical_code_point_sorted(evidence_ids)
    records = [attestations_by_id[evidence_id].get("SOURCE_RECORD_ID") for evidence_id in ids]
    non_null = [record for record in records if record is not None]
    if len(ids) == 1 and len(non_null) == 1:
        return non_null[0]
    if non_null:
        return f"capture-record-set:{_sha256_json([[evidence_id, attestations_by_id[evidence_id].get('SOURCE_RECORD_ID')] for evidence_id in ids])}"
    return f"capture:{capture_content_digest}:{'|'.join(ids)}"


def _validate_context(context: Any) -> dict[str, Any]:
    values = _exact_object(context, PREDICTION_CONTEXT_FIELDS, "PREDICTION_CONTEXT")
    _text(values["PREDICTION_CONTEXT_ID"], "PREDICTION_CONTEXT_ID", safe_id=True)
    if values["MODEL_ASOF_CONTRACT_ID"] != MODEL_ASOF_CONTRACT_ID:
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "model-as-of contract ID mismatch"
        )
    if values["MODEL_ASOF_CONTRACT_VERSION"] != MODEL_ASOF_CONTRACT_VERSION:
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "model-as-of contract version mismatch"
        )
    _text(values["TARGET_MATCH_ID"], "TARGET_MATCH_ID", safe_id=True)
    decision = _timestamp(values["MODEL_DECISION_TIME_UTC"], "MODEL_DECISION_TIME_UTC")
    feature = _timestamp(values["FEATURE_AS_OF_UTC"], "FEATURE_AS_OF_UTC")
    kickoff = _timestamp(values["TARGET_KICKOFF_UTC"], "TARGET_KICKOFF_UTC")
    if decision != feature:
        raise NormalizationValidationError(
            "NORMALIZATION_CONTEXT_MISMATCH", "FEATURE_AS_OF_UTC must equal T"
        )
    if datetime.fromisoformat(decision.replace("Z", "+00:00")) >= datetime.fromisoformat(
        kickoff.replace("Z", "+00:00")
    ):
        raise NormalizationValidationError(
            "NORMALIZATION_CONTEXT_MISMATCH", "T must be before target kickoff"
        )
    return {
        **values,
        "MODEL_DECISION_TIME_UTC": decision,
        "FEATURE_AS_OF_UTC": feature,
        "TARGET_KICKOFF_UTC": kickoff,
    }


def _validate_capture_binding(value: Any) -> dict[str, Any]:
    binding = _exact_object(value, RUNTIME_CAPTURE_BINDING_FIELDS, "RUNTIME_CAPTURE_BINDING")
    if (
        binding["RUNTIME_CAPTURE_CONTRACT_ID"] != RUNTIME_CAPTURE_CONTRACT_ID
        or binding["RUNTIME_CAPTURE_CONTRACT_VERSION"] != RUNTIME_CAPTURE_CONTRACT_VERSION
    ):
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "runtime-capture contract binding mismatch"
        )
    _text(binding["CAPTURE_INSTANCE_ID"], "CAPTURE_INSTANCE_ID", safe_id=True)
    digest = _hex64(binding["CAPTURE_CONTENT_DIGEST"], "CAPTURE_CONTENT_DIGEST")
    if binding["CAPTURE_INSTANCE_ID"] == digest:
        raise NormalizationValidationError(
            "CAPTURE_IDENTITY_COLLISION", "capture instance must differ from content digest"
        )
    selected = _sorted_unique_ids(
        binding["CAPTURE_SELECTED_EVIDENCE_IDS"], "CAPTURE_SELECTED_EVIDENCE_IDS"
    )
    return {**binding, "CAPTURE_SELECTED_EVIDENCE_IDS": selected}


def _validate_attestation(  # noqa: C901, PLR0912 -- proof-kind branches are fail-closed schema rules.
    value: Any, index: int
) -> dict[str, Any]:
    label = f"EVIDENCE_ATTESTATIONS[{index}]"
    attestation = deepcopy(_exact_object(value, EVIDENCE_ENTRY_FIELDS, label))
    _text(attestation["EVIDENCE_ID"], f"{label}.EVIDENCE_ID", safe_id=True)
    _text(attestation["SOURCE_FAMILY"], f"{label}.SOURCE_FAMILY", safe_id=True)
    _optional_text(attestation["SOURCE_AUTHORITY_ID"], f"{label}.SOURCE_AUTHORITY_ID", safe_id=True)
    _optional_text(attestation["SOURCE_RECORD_ID"], f"{label}.SOURCE_RECORD_ID", safe_id=True)
    _text(attestation["PAYLOAD_KIND"], f"{label}.PAYLOAD_KIND", safe_id=True)
    if attestation["PAYLOAD_KIND"] not in {"BYTE_BLOB", "CANONICAL_JSON"}:
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", f"{label}.PAYLOAD_KIND unsupported"
        )
    _hex64(attestation["PAYLOAD_CONTENT_DIGEST"], f"{label}.PAYLOAD_CONTENT_DIGEST")
    if (
        isinstance(attestation["PAYLOAD_BYTE_LENGTH"], bool)
        or not isinstance(attestation["PAYLOAD_BYTE_LENGTH"], int)
        or attestation["PAYLOAD_BYTE_LENGTH"] < 0
    ):
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", f"{label}.PAYLOAD_BYTE_LENGTH malformed"
        )
    for field in (
        "SOURCE_EVENT_TIME_UTC",
        "SOURCE_EFFECTIVE_TIME_UTC",
        "SOURCE_OBSERVED_AT_UTC",
        "SOURCE_CAPTURED_AT_UTC",
    ):
        if attestation[field] is not None:
            attestation[field] = _timestamp(attestation[field], f"{label}.{field}")
    if attestation["SOURCE_CAPTURED_AT_UTC"] is None:
        raise NormalizationValidationError(
            "NORMALIZATION_TIMESTAMP_INVALID", f"{label}.SOURCE_CAPTURED_AT_UTC is required"
        )
    proof_kind = attestation["AVAILABILITY_PROOF_KIND"]
    _text(proof_kind, f"{label}.AVAILABILITY_PROOF_KIND", safe_id=True)
    proof_data = attestation["AVAILABILITY_PROOF_DATA"]
    if not isinstance(proof_data, dict):
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", f"{label}.AVAILABILITY_PROOF_DATA malformed"
        )
    if proof_kind == "EXACT_OBSERVATION_TIMESTAMP":
        if (
            proof_data != {"observed_at_field": "SOURCE_OBSERVED_AT_UTC"}
            or attestation["SOURCE_OBSERVED_AT_UTC"] is None
        ):
            raise NormalizationValidationError(
                "NORMALIZATION_SCHEMA_MISMATCH", f"{label} observation proof malformed"
            )
    elif proof_kind == "EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF":
        if (
            proof_data
            != {
                "effective_time_field": "SOURCE_EFFECTIVE_TIME_UTC",
                "observed_at_field": "SOURCE_OBSERVED_AT_UTC",
            }
            or attestation["SOURCE_EFFECTIVE_TIME_UTC"] is None
            or attestation["SOURCE_OBSERVED_AT_UTC"] is None
        ):
            raise NormalizationValidationError(
                "NORMALIZATION_SCHEMA_MISMATCH", f"{label} effective proof malformed"
            )
    elif proof_kind == "BOUNDED_INTERVAL_ENTIRELY_BEFORE_T":
        if set(proof_data) != {"start_utc", "end_utc"}:
            raise NormalizationValidationError(
                "NORMALIZATION_SCHEMA_MISMATCH", f"{label} interval proof malformed"
            )
        proof_data = {
            "start_utc": _timestamp(proof_data["start_utc"], f"{label}.start_utc"),
            "end_utc": _timestamp(proof_data["end_utc"], f"{label}.end_utc"),
        }
        attestation["AVAILABILITY_PROOF_DATA"] = proof_data
    else:
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", f"{label} proof kind unsupported"
        )
    if attestation["SOURCE_PROVENANCE_STATUS"] != "UNKNOWN":
        raise NormalizationValidationError(
            "SOURCE_AUTHORITY_PROOF_UNAVAILABLE",
            "generic normalization cannot upgrade source provenance",
        )
    return attestation


def _validate_fact_binding(value: Any, index: int, standings_ids: set[str]) -> dict[str, Any]:
    label = f"FACT_BINDINGS[{index}]"
    binding = _exact_object(value, FACT_BINDING_FIELDS, label)
    _text(binding["BINDING_ID"], f"{label}.BINDING_ID", safe_id=True)
    if (
        binding["SEMANTIC_ROLE"] not in FACT_BINDING_ROLES
        or binding["DERIVATION"] not in DERIVATIONS
    ):
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH", f"{label} role/derivation malformed"
        )
    _text(binding["DOMAIN_IDENTITY"], f"{label}.DOMAIN_IDENTITY", safe_id=True)
    source_ids = _sorted_unique_ids(binding["SOURCE_EVIDENCE_IDS"], f"{label}.SOURCE_EVIDENCE_IDS")
    if binding["DERIVATION"] == "SOURCE_ATTESTED" and not source_ids:
        raise NormalizationValidationError(
            "FACT_LINEAGE_MISSING", f"{label} source lineage is required"
        )
    if not set(source_ids).issubset(standings_ids):
        raise NormalizationValidationError(
            "FACT_EVIDENCE_NOT_SELECTED", f"{label} references unselected evidence"
        )
    _optional_text(binding["CANONICAL_MATCH_ID"], f"{label}.CANONICAL_MATCH_ID", safe_id=True)
    _optional_text(binding["ADJUSTMENT_ID"], f"{label}.ADJUSTMENT_ID", safe_id=True)
    _optional_text(
        binding["AVAILABILITY_EVIDENCE_ID"], f"{label}.AVAILABILITY_EVIDENCE_ID", safe_id=True
    )
    if (
        binding["AVAILABILITY_EVIDENCE_ID"] is not None
        and binding["AVAILABILITY_EVIDENCE_ID"] not in source_ids
    ):
        raise NormalizationValidationError(
            "AVAILABILITY_EVIDENCE_UNBOUND", f"{label} availability evidence is not in lineage"
        )
    _hex64(binding["NORMALIZED_FACT_DIGEST"], f"{label}.NORMALIZED_FACT_DIGEST")
    if compute_fact_binding_digest(binding) != binding["NORMALIZED_FACT_DIGEST"]:
        raise NormalizationValidationError("FACT_DIGEST_MISMATCH", f"{label} digest mismatch")
    return {**binding, "SOURCE_EVIDENCE_IDS": source_ids}


def _validate_output_binding(
    value: Any, context: dict[str, Any], state_ids: list[str], adjustment_ids: list[str]
) -> dict[str, Any]:
    binding = deepcopy(
        _exact_object(
            value, OUTPUT_STANDINGS_INPUT_BINDING_FIELDS, "OUTPUT_STANDINGS_INPUT_BINDING"
        )
    )
    if (
        binding["STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID"] != STANDINGS_INPUT_CONTRACT_ID
        or binding["STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION"]
        != STANDINGS_INPUT_CONTRACT_VERSION
    ):
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "standings input contract binding mismatch"
        )
    if (
        binding["STANDINGS_RANKING_CONTRACT_ID"] != STANDINGS_CONTRACT_ID
        or binding["STANDINGS_RANKING_CONTRACT_VERSION"] != STANDINGS_CONTRACT_VERSION
    ):
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "standings ranking contract binding mismatch"
        )
    _hex64(binding["CANONICAL_INPUT_DIGEST"], "CANONICAL_INPUT_DIGEST")
    for field in ("MODEL_DECISION_TIME_UTC", "FEATURE_AS_OF_UTC", "TARGET_KICKOFF_UTC"):
        binding[field] = _timestamp(binding[field], field)
    for field in ("MODEL_DECISION_TIME_UTC", "FEATURE_AS_OF_UTC", "TARGET_KICKOFF_UTC"):
        if binding[field] != context[field]:
            raise NormalizationValidationError(
                "OUTPUT_INPUT_CONTEXT_MISMATCH", f"output binding {field} mismatch"
            )
    _text(
        binding["TARGET_MATCH_ID"], "OUTPUT_STANDINGS_INPUT_BINDING.TARGET_MATCH_ID", safe_id=True
    )
    if binding["TARGET_MATCH_ID"] != context["TARGET_MATCH_ID"]:
        raise NormalizationValidationError(
            "OUTPUT_INPUT_CONTEXT_MISMATCH", "output target mismatch"
        )
    _text(binding["FIXTURE_UNIVERSE_REFERENCE_ID"], "FIXTURE_UNIVERSE_REFERENCE_ID", safe_id=True)
    binding["FIXTURE_STATE_IDS"] = _sorted_unique_ids(
        binding["FIXTURE_STATE_IDS"], "FIXTURE_STATE_IDS"
    )
    if binding["FIXTURE_STATE_IDS"] != state_ids:
        raise NormalizationValidationError(
            "OUTPUT_INPUT_BINDING_MISMATCH", "fixture state identity set is not canonical"
        )
    binding["ADMINISTRATIVE_ADJUSTMENT_IDS"] = _sorted_unique_ids(
        binding["ADMINISTRATIVE_ADJUSTMENT_IDS"], "ADMINISTRATIVE_ADJUSTMENT_IDS"
    )
    if binding["ADMINISTRATIVE_ADJUSTMENT_IDS"] != adjustment_ids:
        raise NormalizationValidationError(
            "OUTPUT_INPUT_BINDING_MISMATCH", "adjustment identity set is not canonical"
        )
    _hex64(binding["OUTPUT_INPUT_BINDING_DIGEST"], "OUTPUT_INPUT_BINDING_DIGEST")
    if compute_output_input_binding_digest(binding) != binding["OUTPUT_INPUT_BINDING_DIGEST"]:
        raise NormalizationValidationError(
            "OUTPUT_INPUT_BINDING_DIGEST_MISMATCH", "output binding digest mismatch"
        )
    return binding


def _validate_status(value: Any) -> dict[str, Any]:
    status = _exact_object(value, STATUS_FIELDS, "STATUS")
    expected = {
        "NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY": "PROVEN",
        "CAPTURE_BINDING_VALIDITY": "PROVEN",
        "OUTPUT_INPUT_BINDING_VALIDITY": "NOT_PROVEN",
        "SOURCE_SEMANTIC_NORMALIZATION_VALIDITY": "NOT_PROVEN",
        "SOURCE_AUTHORITY_VALIDITY": "NOT_PROVEN",
        "SOURCE_STREAM_COMPLETENESS": "NOT_PROVEN",
        "RUNTIME_NUMERIC_ELIGIBILITY": "NO",
    }
    if status != expected:
        raise NormalizationValidationError(
            "NORMALIZATION_STATUS_MISMATCH", "generic envelope status overclaims readiness"
        )
    return dict(status)


def validate_normalization_envelope_structure(envelope: dict[str, Any]) -> dict[str, Any]:
    """Validate the envelope without trusting any caller-supplied status."""
    _reject_secret_keys(envelope)
    values = _exact_object(envelope, NORMALIZATION_ENVELOPE_FIELDS, "normalization envelope")
    if (
        values["NORMALIZATION_CONTRACT_ID"] != NORMALIZATION_CONTRACT_ID
        or values["NORMALIZATION_CONTRACT_VERSION"] != NORMALIZATION_CONTRACT_VERSION
    ):
        raise NormalizationValidationError(
            "CONTRACT_VERSION_MISMATCH", "normalization contract identity mismatch"
        )
    _text(values["NORMALIZATION_INSTANCE_ID"], "NORMALIZATION_INSTANCE_ID", safe_id=True)
    _hex64(values["NORMALIZATION_CONTENT_DIGEST"], "NORMALIZATION_CONTENT_DIGEST")
    context = _validate_context(values["PREDICTION_CONTEXT"])
    capture = _validate_capture_binding(values["RUNTIME_CAPTURE_BINDING"])
    standings_ids = _sorted_unique_ids(values["STANDINGS_EVIDENCE_IDS"], "STANDINGS_EVIDENCE_IDS")
    if not set(standings_ids).issubset(set(capture["CAPTURE_SELECTED_EVIDENCE_IDS"])):
        raise NormalizationValidationError(
            "STANDINGS_EVIDENCE_NOT_SELECTED", "standings evidence is outside capture selection"
        )
    if not isinstance(values["EVIDENCE_ATTESTATIONS"], list) or not isinstance(
        values["FACT_BINDINGS"], list
    ):
        raise NormalizationValidationError(
            "NORMALIZATION_SCHEMA_MISMATCH",
            "evidence attestations and fact bindings must be arrays",
        )
    output_value = _exact_object(
        values["OUTPUT_STANDINGS_INPUT_BINDING"],
        OUTPUT_STANDINGS_INPUT_BINDING_FIELDS,
        "OUTPUT_STANDINGS_INPUT_BINDING",
    )
    attestations = [
        _validate_attestation(row, index)
        for index, row in enumerate(values["EVIDENCE_ATTESTATIONS"])
    ]
    attestation_ids = [row["EVIDENCE_ID"] for row in attestations]
    if (
        len(set(attestation_ids)) != len(attestation_ids)
        or canonical_code_point_sorted(attestation_ids) != standings_ids
    ):
        raise NormalizationValidationError(
            "ATTESTATION_SET_MISMATCH", "attestations must exactly cover standings evidence"
        )
    attestations = canonical_code_point_sorted(attestations, key=lambda row: row["EVIDENCE_ID"])
    state_ids = _sorted_unique_ids(output_value["FIXTURE_STATE_IDS"], "FIXTURE_STATE_IDS")
    adjustment_ids = _sorted_unique_ids(
        output_value["ADMINISTRATIVE_ADJUSTMENT_IDS"], "ADMINISTRATIVE_ADJUSTMENT_IDS"
    )
    facts = [
        _validate_fact_binding(row, index, set(standings_ids))
        for index, row in enumerate(values["FACT_BINDINGS"])
    ]
    fact_ids = [row["BINDING_ID"] for row in facts]
    if len(set(fact_ids)) != len(fact_ids):
        raise NormalizationValidationError(
            "FACT_BINDING_ORDER_MISMATCH", "fact bindings must be unique"
        )
    facts = canonical_code_point_sorted(facts, key=lambda row: row["BINDING_ID"])
    output = _validate_output_binding(
        values["OUTPUT_STANDINGS_INPUT_BINDING"], context, state_ids, adjustment_ids
    )
    _validate_status(values["STATUS"])
    expected_digest = compute_normalization_content_digest(values)
    if expected_digest != values["NORMALIZATION_CONTENT_DIGEST"]:
        raise NormalizationValidationError(
            "NORMALIZATION_CONTENT_DIGEST_MISMATCH", "normalization content digest mismatch"
        )
    return {
        "valid": True,
        "normalization_instance_id": values["NORMALIZATION_INSTANCE_ID"],
        "normalization_content_digest": expected_digest,
        "prediction_context": context,
        "runtime_capture_binding": capture,
        "standings_evidence_ids": tuple(standings_ids),
        "evidence_attestations": tuple(attestations),
        "fact_bindings": tuple(facts),
        "output_standings_input_binding": output,
        "statuses": dict(values["STATUS"]),
    }


def validate_normalization_envelope_against_runtime_capture(
    envelope: dict[str, Any], capture_manifest: dict[str, Any], payloads: Mapping[str, bytes]
) -> dict[str, Any]:
    """Validate the envelope against the actual canonical runtime capture."""
    envelope_result = validate_normalization_envelope_structure(envelope)
    from src.ml.inference.feature_contract_boundary_validator import (  # noqa: PLC0415
        validate_runtime_capture_manifest_against_canonical_registry,
    )

    try:
        capture_result = validate_runtime_capture_manifest_against_canonical_registry(
            capture_manifest, payloads
        )
    except ValueError as exc:
        raise NormalizationValidationError("CAPTURE_BINDING_INVALID", str(exc)) from exc

    capture_context = capture_manifest["PREDICTION_CONTEXT"]
    context = envelope_result["prediction_context"]
    for field in PREDICTION_CONTEXT_FIELDS:
        actual = capture_context[field]
        if field.endswith("_UTC"):
            actual = _timestamp(actual, field)
        if actual != context[field]:
            raise NormalizationValidationError(
                "CAPTURE_CONTEXT_MISMATCH", f"capture {field} differs from envelope"
            )
    binding = envelope_result["runtime_capture_binding"]
    if (
        binding["CAPTURE_INSTANCE_ID"] != capture_manifest["CAPTURE_INSTANCE_ID"]
        or binding["CAPTURE_CONTENT_DIGEST"] != capture_result["capture_content_digest"]
    ):
        raise NormalizationValidationError(
            "CAPTURE_IDENTITY_MISMATCH", "capture identity differs from envelope"
        )
    selected = tuple(capture_result["selected_evidence_ids"])
    if tuple(binding["CAPTURE_SELECTED_EVIDENCE_IDS"]) != selected:
        raise NormalizationValidationError(
            "CAPTURE_SELECTION_MISMATCH", "capture selected evidence differs from envelope"
        )
    standings_ids = envelope_result["standings_evidence_ids"]
    capture_by_id = {row["EVIDENCE_ID"]: row for row in capture_manifest["EVIDENCE"]}
    envelope_attestations_by_id = {
        row["EVIDENCE_ID"]: _canonicalize_tree(row)
        for row in envelope_result["evidence_attestations"]
    }
    actual_attestations_by_id = {
        evidence_id: _canonicalize_tree(deepcopy(capture_by_id[evidence_id]))
        for evidence_id in standings_ids
    }
    if envelope_attestations_by_id != actual_attestations_by_id:
        raise NormalizationValidationError(
            "ATTESTATION_CAPTURE_MISMATCH", "attestation is not an exact capture projection"
        )
    if any(
        row["SOURCE_PROVENANCE_STATUS"] != "UNKNOWN"
        for row in envelope_result["evidence_attestations"]
    ):
        raise NormalizationValidationError(
            "SOURCE_AUTHORITY_PROOF_UNAVAILABLE", "generic capture cannot prove source authority"
        )
    return {
        **envelope_result,
        "capture_validation": capture_result,
        "statuses": {
            **envelope_result["statuses"],
            "CAPTURE_BINDING_VALIDITY": "PROVEN",
            "SOURCE_SEMANTIC_NORMALIZATION_VALIDITY": "NOT_PROVEN",
            "SOURCE_AUTHORITY_VALIDITY": "NOT_PROVEN",
            "SOURCE_STREAM_COMPLETENESS": "NOT_PROVEN",
            "RUNTIME_NUMERIC_ELIGIBILITY": "NO",
        },
    }


__all__ = [
    "CANONICAL_SERIALIZATION",
    "FACT_BINDING_FIELDS",
    "FACT_BINDING_ROLES",
    "NORMALIZATION_CONTENT_DIGEST_ALGORITHM",
    "NORMALIZATION_CONTENT_DIGEST_SCOPE",
    "NORMALIZATION_CONTRACT_ID",
    "NORMALIZATION_CONTRACT_STATUS",
    "NORMALIZATION_CONTRACT_VERSION",
    "NORMALIZATION_ENVELOPE_FIELDS",
    "NormalizationValidationError",
    "canonical_code_point_sorted",
    "compute_fact_binding_digest",
    "compute_normalization_content_digest",
    "compute_output_input_binding_digest",
    "source_record_ref_for_evidence_ids",
    "validate_normalization_envelope_against_runtime_capture",
    "validate_normalization_envelope_structure",
]
