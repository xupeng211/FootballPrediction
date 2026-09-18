#!/usr/bin/env python3
"""Integrity and registry helpers for additive generic review receipts.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    RECEIPT_VERSION,
    IndependentReviewProtocolError,
    canonical_json,
    sha256_bytes,
    validate_result,
    validate_sha,
)
from scripts.ops.helpers.agent_workflow_scope_context import validate_mission_scope_reference_path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "agentic" / "independent_review_receipt.schema.json"
_MISSION_ID_RE = __import__("re").compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True)
class ReceiptEvidenceContext:
    """Harness-owned immutable facts required to validate a generic receipt."""

    repo_root: Path
    base_sha: str
    head_sha: str
    mission_scope_path: str
    prompt_bytes: bytes
    raw_output_bytes: bytes
    final_result_bytes: bytes


SECRET_FIELD_TOKENS = (
    "api_key",
    "token",
    "cookie",
    "authorization",
    "email",
    "credential",
    "account_id",
    "refresh",
)


def _reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(token in str(key).casefold() for token in SECRET_FIELD_TOKENS):
                raise IndependentReviewProtocolError(f"forbidden secret-bearing field: {key}")
            _reject_secret_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_secret_keys(nested)


def receipt_payload_sha256(receipt: dict[str, Any]) -> str:
    """Hash the receipt excluding its self-referential integrity object."""
    payload = dict(receipt)
    payload.pop("integrity", None)
    return sha256_bytes(canonical_json(payload))


def _schema_validator() -> Draft202012Validator:
    """Load the tracked generic receipt schema for runtime fail-closed validation."""
    try:
        schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError(f"cannot load receipt schema: {exc}") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(receipt: object) -> None:
    errors = sorted(_schema_validator().iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise IndependentReviewProtocolError(f"generic receipt schema invalid: {errors[0].message}")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise IndependentReviewProtocolError(f"{field} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndependentReviewProtocolError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise IndependentReviewProtocolError(f"{field} must include timezone")
    return parsed


def _actual_diff_sha256(context: ReceiptEvidenceContext) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--binary",
                "--no-ext-diff",
                f"{context.base_sha}...{context.head_sha}",
            ],
            cwd=context.repo_root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise IndependentReviewProtocolError(f"cannot calculate reviewed diff: {exc}") from exc
    if result.returncode != 0:
        raise IndependentReviewProtocolError("cannot calculate reviewed diff")
    return sha256_bytes(result.stdout)


def _validate_external_bindings(receipt: dict[str, Any], context: ReceiptEvidenceContext) -> None:
    """Bind receipt declarations to harness-owned bytes and exact Git facts."""
    base = validate_sha(context.base_sha, name="evidence base_sha", length=40)
    head = validate_sha(context.head_sha, name="evidence head_sha", length=40)
    if receipt["base_sha"].lower() != base or receipt["head_sha"].lower() != head:
        raise IndependentReviewProtocolError("receipt base/head do not match trusted evidence")
    scope_path = validate_mission_scope_reference_path(context.mission_scope_path)
    if receipt["mission_scope_path"] != scope_path:
        raise IndependentReviewProtocolError("receipt scope path does not match trusted evidence")
    scope_file = context.repo_root / scope_path
    try:
        scope_bytes = scope_file.read_bytes()
    except OSError as exc:
        raise IndependentReviewProtocolError(f"cannot read trusted mission scope: {exc}") from exc
    if (
        scope_file.is_symlink()
        or sha256_bytes(scope_bytes) != receipt["mission_scope_sha256"].lower()
    ):
        raise IndependentReviewProtocolError(
            "receipt mission scope hash does not match trusted bytes"
        )
    if _actual_diff_sha256(context) != receipt["diff_sha256"].lower():
        raise IndependentReviewProtocolError("receipt diff hash does not match reviewed diff")
    for field, evidence in (
        ("review_prompt_sha256", context.prompt_bytes),
        ("raw_output_sha256", context.raw_output_bytes),
        ("final_result_sha256", context.final_result_bytes),
    ):
        if sha256_bytes(evidence) != receipt[field].lower():
            raise IndependentReviewProtocolError(f"receipt {field} does not match trusted evidence")
    try:
        final_result = json.loads(context.final_result_bytes)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError("trusted final result is not JSON") from exc
    expected_final = {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": receipt["review_result"],
        "findings": receipt["findings"],
    }
    if (
        context.final_result_bytes != canonical_json(expected_final)
        or final_result != expected_final
    ):
        raise IndependentReviewProtocolError("trusted final result is not canonical receipt result")


def validate_backend_registry(registry: object) -> dict[str, dict[str, Any]]:
    """Validate and index the repository-controlled approved-backend registry."""
    if (
        not isinstance(registry, dict)
        or registry.get("registry_version") != "independent-review-backends/v1"
    ):
        raise IndependentReviewProtocolError("invalid backend registry version")
    entries = registry.get("backends")
    if not isinstance(entries, list) or not entries:
        raise IndependentReviewProtocolError("backend registry must contain backends")
    indexed: dict[str, dict[str, Any]] = {}
    required = {
        "backend_id",
        "harness_id",
        "provider_id",
        "status",
        "allowed_requested_models",
        "minimum_harness_version",
        "required_provenance_fields",
        "isolation_requirements",
        "transport_policy",
        "task_eligibility",
        "no_silent_fallback",
    }
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != required:
            raise IndependentReviewProtocolError("backend registry entry fields are invalid")
        backend = entry["backend_id"]
        if (
            not isinstance(backend, str)
            or backend in indexed
            or entry["status"] not in {"active", "reserved", "disabled"}
        ):
            raise IndependentReviewProtocolError("backend registry entry is invalid")
        if (
            not isinstance(entry["allowed_requested_models"], list)
            or not entry["allowed_requested_models"]
        ):
            raise IndependentReviewProtocolError("backend allowed models are required")
        if entry["no_silent_fallback"] is not True or not isinstance(
            entry["required_provenance_fields"], list
        ):
            raise IndependentReviewProtocolError("backend provenance/fallback policy is invalid")
        indexed[backend] = entry
    return indexed


def load_backend_registry(path: Path) -> dict[str, dict[str, Any]]:
    """Read a non-secret backend registry and validate its protocol shape."""
    try:
        return validate_backend_registry(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError(f"cannot load backend registry: {exc}") from exc


def validate_receipt(  # noqa: C901, PLR0912
    receipt: object,
    *,
    registry: dict[str, dict[str, Any]],
    evidence_context: ReceiptEvidenceContext,
) -> dict[str, Any]:
    """Validate a newly-issued generic receipt; legacy receipts use an adapter."""

    if not isinstance(receipt, dict):
        raise IndependentReviewProtocolError("receipt must be an object")
    _validate_schema(receipt)
    _reject_secret_keys(receipt)
    required = {
        "protocol_version",
        "receipt_version",
        "review_run_id",
        "review_backend",
        "review_harness",
        "provider",
        "requested_model",
        "base_sha",
        "head_sha",
        "diff_sha256",
        "mission_id",
        "mission_scope_path",
        "mission_scope_sha256",
        "review_prompt_sha256",
        "review_started_at",
        "review_completed_at",
        "review_result",
        "finding_counts_by_severity",
        "findings",
        "raw_output_sha256",
        "final_result_sha256",
        "isolation",
        "provenance",
        "integrity",
    }
    if set(receipt) - (required | {"resolved_model"}) or not required.issubset(receipt):
        raise IndependentReviewProtocolError("receipt fields are invalid")
    if (
        receipt["protocol_version"] != PROTOCOL_VERSION
        or receipt["receipt_version"] != RECEIPT_VERSION
    ):
        raise IndependentReviewProtocolError("receipt protocol/version mismatch")
    if not _MISSION_ID_RE.fullmatch(receipt["mission_id"]):
        raise IndependentReviewProtocolError("receipt mission_id is invalid")
    started = _parse_timestamp(receipt["review_started_at"], "review_started_at")
    completed = _parse_timestamp(receipt["review_completed_at"], "review_completed_at")
    if completed < started:
        raise IndependentReviewProtocolError("receipt completed timestamp precedes start")
    backend = registry.get(receipt["review_backend"])
    if backend is None or backend["status"] != "active":
        raise IndependentReviewProtocolError("receipt backend is not active")
    if (
        receipt["provider"] != backend["provider_id"]
        or receipt["review_harness"] != backend["harness_id"]
    ):
        raise IndependentReviewProtocolError("receipt backend provenance mismatch")
    if receipt["requested_model"] not in backend["allowed_requested_models"]:
        raise IndependentReviewProtocolError("receipt requested model is not approved")
    for field, length in (
        ("base_sha", 40),
        ("head_sha", 40),
        ("diff_sha256", 64),
        ("mission_scope_sha256", 64),
        ("review_prompt_sha256", 64),
        ("raw_output_sha256", 64),
        ("final_result_sha256", 64),
    ):
        validate_sha(receipt.get(field), name=field, length=length)
    result = validate_result(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": receipt["review_result"],
            "findings": receipt["findings"],
        }
    )
    if receipt["finding_counts_by_severity"] != result["finding_counts_by_severity"]:
        raise IndependentReviewProtocolError("receipt finding counts do not match findings")
    isolation = receipt["isolation"]
    if not isinstance(isolation, dict) or any(
        isolation.get(field) is not True
        for field in (
            "fresh_process",
            "fresh_context",
            "detached_worktree",
            "read_only",
            "worktree_clean_before",
            "worktree_clean_after",
        )
    ):
        raise IndependentReviewProtocolError("receipt isolation facts are incomplete")
    if isolation.get("worktree_head_sha", "").lower() != receipt["head_sha"].lower():
        raise IndependentReviewProtocolError("receipt worktree head does not match reviewed head")
    if not isinstance(receipt["provenance"], dict) or not set(
        backend["required_provenance_fields"]
    ).issubset(receipt["provenance"]):
        raise IndependentReviewProtocolError("receipt required backend provenance is missing")
    _validate_external_bindings(receipt, evidence_context)
    integrity = receipt["integrity"]
    if not isinstance(integrity, dict) or integrity.get(
        "receipt_payload_sha256"
    ) != receipt_payload_sha256(receipt):
        raise IndependentReviewProtocolError("receipt payload hash mismatch")
    return result
