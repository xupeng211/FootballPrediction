#!/usr/bin/env python3
"""Provider-neutral domain rules for ``INDEPENDENT_REVIEW_PROTOCOL_V1``.

lifecycle: permanent
owner: engineering workflow governance

This additive module does not select a backend or alter the existing Codex
approval path.  It centralises only facts every future backend must satisfy.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import re
from typing import Any

from scripts.ops.helpers.agent_workflow_contract import (
    ALL_REVIEW_SEVERITIES,
    BLOCKING_REVIEW_SEVERITIES,
    REVIEW_RESULT_FAIL,
    REVIEW_RESULT_PASS,
)

PROTOCOL_VERSION = "INDEPENDENT_REVIEW_PROTOCOL_V1"
RECEIPT_VERSION = "independent-review-receipt/v1"
INFRASTRUCTURE_FAILURES = frozenset(
    {
        "TRANSPORT_FAILURE",
        "AUTH_FAILURE",
        "MODEL_MISMATCH",
        "PROVIDER_MISMATCH",
        "TIMEOUT",
        "BACKEND_CRASH",
        "INVALID_STRUCTURED_OUTPUT",
        "REVIEW_INVALID",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
SHA1_HEX_LENGTH = 40


class IndependentReviewProtocolError(ValueError):
    """A provider-neutral review artifact failed a fail-closed invariant."""


def canonical_json(value: object) -> bytes:
    """Encode a deterministic UTF-8 JSON payload for integrity binding."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of immutable bytes."""
    return sha256(value).hexdigest()


def validate_sha(value: object, *, name: str, length: int) -> str:
    """Require a canonical hexadecimal SHA-1 or SHA-256 value."""
    pattern = SHA1_RE if length == SHA1_HEX_LENGTH else SHA256_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise IndependentReviewProtocolError(f"{name} must be a {length}-hex digest")
    return value.lower()


def validate_result(result: object) -> dict[str, Any]:  # noqa: C901, PLR0912
    """Validate the shared result vocabulary without trusting declared counts."""

    if not isinstance(result, dict) or set(result) != {
        "protocol_version",
        "review_result",
        "findings",
    }:
        raise IndependentReviewProtocolError(
            "result must contain only protocol_version, review_result and findings"
        )
    if result["protocol_version"] != PROTOCOL_VERSION:
        raise IndependentReviewProtocolError("result protocol_version is not current")
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise IndependentReviewProtocolError("result findings must be an array")
    normalized: list[dict[str, Any]] = []
    counts = Counter(dict.fromkeys(ALL_REVIEW_SEVERITIES, 0))
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict) or set(finding) - {
            "severity",
            "title",
            "evidence",
            "file",
            "line",
            "symbol",
        }:
            raise IndependentReviewProtocolError(f"finding[{index}] has unsupported fields")
        for field in ("severity", "title", "evidence"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise IndependentReviewProtocolError(f"finding[{index}] missing {field}")
        severity = finding["severity"].upper()
        if severity not in ALL_REVIEW_SEVERITIES:
            raise IndependentReviewProtocolError(f"finding[{index}] has invalid severity")
        line = finding.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            raise IndependentReviewProtocolError(f"finding[{index}] line must be positive or null")
        for field in ("file", "symbol"):
            if (
                field in finding
                and finding[field] is not None
                and not isinstance(finding[field], str)
            ):
                raise IndependentReviewProtocolError(
                    f"finding[{index}] {field} must be string or null"
                )
        counts[severity] += 1
        normalized.append({**finding, "severity": severity})
    blocking = sum(counts[item] for item in BLOCKING_REVIEW_SEVERITIES)
    verdict = result.get("review_result")
    if verdict not in {REVIEW_RESULT_PASS, REVIEW_RESULT_FAIL}:
        raise IndependentReviewProtocolError("review_result must be PASS or FAIL")
    if (verdict == REVIEW_RESULT_PASS) != (blocking == 0):
        raise IndependentReviewProtocolError("review_result conflicts with blocking findings")
    return {
        "review_result": verdict,
        "findings": normalized,
        "finding_counts_by_severity": dict(counts),
        "blocking_findings": blocking,
    }
