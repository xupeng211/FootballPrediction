#!/usr/bin/env python3
"""Integrity and registry helpers for additive generic review receipts.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    RECEIPT_VERSION,
    IndependentReviewProtocolError,
    canonical_json,
    sha256_bytes,
    validate_result,
    validate_sha,
)

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


def validate_receipt(  # noqa: C901
    receipt: object, *, registry: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Validate a newly-issued generic receipt; legacy receipts use an adapter."""

    if not isinstance(receipt, dict):
        raise IndependentReviewProtocolError("receipt must be an object")
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
    integrity = receipt["integrity"]
    if not isinstance(integrity, dict) or integrity.get(
        "receipt_payload_sha256"
    ) != receipt_payload_sha256(receipt):
        raise IndependentReviewProtocolError("receipt payload hash mismatch")
    return result
