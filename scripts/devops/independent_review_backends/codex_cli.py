"""Compatibility adapter for existing Codex receipts.

lifecycle: permanent
owner: engineering workflow governance

It delegates all historical/current validity decisions to the existing Codex
classifier.  It never upgrades legacy evidence into a generic current approval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from scripts.devops.codex_review_classification import classify_receipt

BACKEND_ID = "codex-cli"


def classify_legacy_receipt(
    receipt_path: Path,
    *,
    repo_root: Path,
    current_head: str | None = None,
    expected_base: str | None = None,
    expected_mission_id: str | None = None,
    expected_mission_scope_file: Path | None = None,
) -> dict[str, Any]:
    """Expose legacy Codex classification without changing its semantics."""

    classification = classify_receipt(
        receipt_path,
        repo_root=repo_root,
        current_head=current_head,
        expected_base=expected_base,
        expected_mission_id=expected_mission_id,
        expected_mission_scope_file=expected_mission_scope_file,
    )
    receipt = classification.receipt or {}
    model = (
        receipt.get("model_provenance", {}).get("review_model")
        if isinstance(receipt.get("model_provenance"), dict)
        else None
    )
    return {
        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
        "review_backend": BACKEND_ID,
        "legacy_receipt_schema_version": classification.receipt_schema_version,
        "legacy_classification": classification.classification,
        "current_approval_eligible": classification.current_approval_eligible,
        "review_result": receipt.get("review_result"),
        "requested_model": model,
        "reason_codes": list(classification.reason_codes),
    }
