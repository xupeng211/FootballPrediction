#!/usr/bin/env python3
"""Three-state classification for engineering-independent review receipts.

lifecycle: permanent
owner: engineering workflow governance

A receipt is never a boolean.  ``VALID_CURRENT`` is the only state that may
satisfy a current exact-head review requirement.  ``STALE_TOOLING`` preserves
the historical meaning of genuine older evidence — a legitimate later wrapper,
Codex CLI or approved-policy upgrade, or a v1 receipt that predates model
pinning — and must never be converted into a current approval, and it never
satisfies merge readiness.  ``INVALID`` means the evidence does not hold for the
target it names.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scripts.devops.codex_review_contract import (
    REVIEW_MODEL_PINNED,
    REVIEW_REASONING_EFFORT_PINNED,
    build_reviewer_command,
)
from scripts.devops.codex_review_provenance import (
    ReviewReceiptError,
    observe_codex_cli_version,
    resolve_codex_binary,
)
from scripts.devops.codex_review_receipt import (
    ROOT,
    TARGET_BINDING_CODES,
    WRAPPER_NAME,
    _declared_model_provenance,
    _EvidenceError,
    _load_receipt_document,
    _verify_receipt_internals,
    sha256_file,
)
from scripts.devops.exact_head import ExactHeadError
from scripts.ops.helpers.agent_workflow_contract import MissionScopeError

# Three-state classification.  ``VALID_CURRENT`` is the only state that may
# satisfy a current exact-head review requirement; ``STALE_TOOLING`` preserves
# the historical meaning of genuine older evidence and must never be converted
# into a current approval; ``INVALID`` means the evidence itself does not hold.
CLASSIFICATION_VALID_CURRENT = "VALID_CURRENT"
CLASSIFICATION_STALE_TOOLING = "STALE_TOOLING"
CLASSIFICATION_INVALID = "INVALID"
INTEGRITY_INTACT = "INTACT"
INTEGRITY_TAMPERED = "TAMPERED"


@dataclass(frozen=True)
class ReceiptClassification:
    """Machine-readable provenance verdict for one review receipt."""

    classification: str
    integrity: str
    reason_codes: tuple[str, ...]
    detail: str
    receipt_schema_version: str | None
    review_model: str | None
    review_reasoning_effort: str | None
    codex_cli_version: str | None
    observed_codex_cli_version: str | None
    approved_review_model: str
    approved_review_reasoning_effort: str
    current_approval_eligible: bool
    head_error: bool = False
    receipt: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-facing classification without the raw receipt body."""

        payload = asdict(self)
        payload.pop("receipt", None)
        return payload


def _observed_cli_version(codex_binary: Path) -> str | None:
    """Observe the Codex CLI version, or ``None`` when it cannot be observed."""

    try:
        return observe_codex_cli_version(codex_binary)
    except (ReviewReceiptError, OSError, ValueError):
        return None


def _current_codex_binary() -> tuple[Path | None, str | None]:
    """Resolve the Codex CLI installed right now, independently of the receipt.

    Reading the "current" toolchain back from the path a receipt recorded would
    let a legitimate upgrade that switches PATH, ``CODEX_CLI_PATH`` or a symlink
    to a new CLI keep matching the retired executable, and old evidence would
    stay ``VALID_CURRENT``.  Resolution failure yields ``(None, None)``, which
    forces ``STALE_TOOLING``: the recorded toolchain then cannot be shown to
    still be the installed one.
    """

    try:
        binary = resolve_codex_binary("codex")
        return binary, sha256_file(binary)
    except (ReviewReceiptError, OSError, ValueError):
        return None, None


def _cli_version_fault(
    facts: dict[str, Any], observed_cli_version: str | None
) -> tuple[str, str] | None:
    """Return an INVALID fault when a receipt contradicts its own executable.

    Identical binary bytes must reproduce the recorded invocation evidence.  A
    same-binary version mismatch is not toolchain drift: it is a receipt that
    disagrees with the executable it claims to have used.  This only applies to
    v2 receipts, which record a CLI version at all — a v1 receipt that predates
    version recording is handled as legitimate historical evidence.
    """

    if facts["legacy_schema"] or facts["recorded_binary_sha256"] != facts["current_binary_sha256"]:
        return None
    if observed_cli_version is None:
        return (
            "CLI_VERSION_INVOCATION_MISMATCH",
            "Codex binary 未变化但无法复现 --version invocation evidence",
        )
    if facts["recorded_cli_version"] != observed_cli_version:
        return (
            "CLI_VERSION_INVOCATION_MISMATCH",
            "receipt codex_cli_version 与同一 Codex binary 的实际 invocation evidence 不一致",
        )
    return None


def _policy_drift_codes(facts: dict[str, Any]) -> list[str]:
    """Return STALE codes for a recorded review policy that is no longer active."""

    if facts["legacy_schema"]:
        return []
    try:
        canonical_command = build_reviewer_command(
            codex_binary=facts["codex_binary_argument"],
            base_sha=facts["base_sha"],
            output_schema=Path(facts["schema_argument"]),
            final_message_path=Path(facts["final_argument"]),
        )
    except (ReviewReceiptError, ExactHeadError, ValueError):
        canonical_command = None
    codes: list[str] = []
    if canonical_command is None or facts["recorded_command"] != canonical_command:
        codes.append("REVIEW_POLICY_DRIFT")
    if facts["review_model"] != REVIEW_MODEL_PINNED:
        codes.append("REVIEW_MODEL_POLICY_DRIFT")
    if facts["review_effort"] != REVIEW_REASONING_EFFORT_PINNED:
        codes.append("REVIEW_EFFORT_POLICY_DRIFT")
    return codes


def _toolchain_reason_codes(facts: dict[str, Any]) -> tuple[list[str], str | None, str | None]:
    """Compare recorded provenance with the currently installed toolchain.

    Returns ``(stale_reason_codes, invalid_code, invalid_detail)``.  Anything
    that only reflects a newer legitimate toolchain is returned as STALE_TOOLING
    and can never satisfy a current approval.
    """

    stale: list[str] = []
    current_wrapper_sha = sha256_file(ROOT / WRAPPER_NAME)
    if facts["recorded_wrapper_sha256"] != current_wrapper_sha:
        stale.append(
            "WRAPPER_TOOLING_DRIFT"
            if facts["wrapper_anchored"]
            else "WRAPPER_TOOLING_DRIFT_UNANCHORED"
        )
    if facts["legacy_schema"]:
        stale.append("RECEIPT_LEGACY_SCHEMA_V1")
    if facts["worktree_available"] is False:
        stale.append("REVIEW_WORKTREE_UNAVAILABLE")
    if facts["schema_file_available"] is False:
        # The historical schema only survived inside the transient worktree, so
        # it is verified against the reviewed commit instead of the vanished
        # file.  That keeps the receipt auditable as history while guaranteeing
        # it can never satisfy a current approval.
        stale.append("REVIEW_OUTPUT_SCHEMA_UNAVAILABLE")

    current_binary_path = facts["current_binary_path"]
    observed_cli_version = (
        _observed_cli_version(current_binary_path) if current_binary_path is not None else None
    )
    fault = _cli_version_fault(facts, observed_cli_version)
    if fault is not None:
        return stale, fault[0], fault[1]
    if facts["current_binary_sha256"] is None:
        stale.append("CODEX_BINARY_UNRESOLVED")
    elif facts["recorded_binary_sha256"] != facts["current_binary_sha256"]:
        stale.append("CODEX_BINARY_DRIFT")
        if (
            facts["recorded_cli_version"] is not None
            and facts["recorded_cli_version"] != observed_cli_version
        ):
            stale.append("CODEX_CLI_VERSION_DRIFT")
    stale.extend(_policy_drift_codes(facts))
    return stale, None, None


def classify_receipt(
    receipt_path: Path,
    *,
    repo_root: Path,
    current_head: str | None = None,
    expected_base: str | None = None,
    expected_mission_id: str | None = None,
    expected_mission_scope_file: Path | None = None,
    historical_audit: bool = False,
) -> ReceiptClassification:
    """Classify one receipt as VALID_CURRENT, STALE_TOOLING or INVALID.

    ``VALID_CURRENT`` requires that the evidence holds, that it covers the exact
    evaluated HEAD, and that the model, reasoning effort, wrapper and Codex CLI
    it recorded are the ones currently installed.  ``STALE_TOOLING`` preserves
    the historical meaning of genuine older evidence (including v1 receipts)
    without ever satisfying a current approval.  ``INVALID`` means the evidence
    does not hold for the target it names.
    """

    try:
        receipt, permission_faults = _load_receipt_document(receipt_path, repo_root)
    except _EvidenceError as exc:
        raise ReviewReceiptError(f"INVALID[{exc.code}]: {exc.detail}") from exc
    declared = _declared_model_provenance(receipt)

    def _result(
        classification: str,
        integrity: str,
        codes: list[str],
        detail: str,
        *,
        model: str | None = None,
        effort: str | None = None,
        cli_version: str | None = None,
        observed: str | None = None,
        head_error: bool = False,
    ) -> ReceiptClassification:
        return ReceiptClassification(
            classification=classification,
            integrity=integrity,
            reason_codes=tuple(dict.fromkeys(codes)),
            detail=detail,
            receipt_schema_version=receipt.get("schema_version")
            if isinstance(receipt.get("schema_version"), str)
            else None,
            review_model=model,
            review_reasoning_effort=effort,
            codex_cli_version=cli_version,
            observed_codex_cli_version=observed,
            approved_review_model=REVIEW_MODEL_PINNED,
            approved_review_reasoning_effort=REVIEW_REASONING_EFFORT_PINNED,
            current_approval_eligible=classification == CLASSIFICATION_VALID_CURRENT,
            head_error=head_error,
            receipt=receipt,
        )

    try:
        facts = _verify_receipt_internals(
            receipt,
            repo_root=repo_root,
            current_head=current_head,
            expected_base=expected_base,
            expected_mission_id=expected_mission_id,
            expected_mission_scope_file=expected_mission_scope_file,
            historical_audit=historical_audit,
        )
    except _EvidenceError as failure:
        integrity = INTEGRITY_INTACT if failure.code in TARGET_BINDING_CODES else INTEGRITY_TAMPERED
        return _result(
            CLASSIFICATION_INVALID,
            integrity,
            [*permission_faults, failure.code],
            failure.detail,
            model=declared.get("review_model"),
            effort=declared.get("review_reasoning_effort"),
            cli_version=declared.get("codex_cli_version"),
            head_error=failure.head_error,
        )
    except (ReviewReceiptError, ExactHeadError, MissionScopeError, OSError, ValueError) as exc:
        return _result(
            CLASSIFICATION_INVALID,
            INTEGRITY_TAMPERED,
            [*permission_faults, "UNCLASSIFIED_EVIDENCE_FAILURE"],
            str(exc),
            model=declared.get("review_model"),
            effort=declared.get("review_reasoning_effort"),
            cli_version=declared.get("codex_cli_version"),
        )
    if isinstance(receipt.get("model_provenance"), dict):
        facts["recorded_cli_version"] = receipt["model_provenance"].get("codex_cli_version")
    else:
        facts["recorded_cli_version"] = None
    # The currently installed Codex CLI is resolved here rather than read back
    # from the path the receipt recorded, so a swap of the installed executable
    # cannot leave retired evidence looking current.
    facts["current_binary_path"], facts["current_binary_sha256"] = _current_codex_binary()

    stale_codes, invalid_code, invalid_detail = _toolchain_reason_codes(facts)
    if invalid_code is not None:
        return _result(
            CLASSIFICATION_INVALID,
            INTEGRITY_TAMPERED,
            [*permission_faults, *stale_codes, invalid_code],
            invalid_detail or invalid_code,
            model=facts["review_model"] or declared.get("review_model"),
            effort=facts["review_effort"] or declared.get("review_reasoning_effort"),
            cli_version=facts["recorded_cli_version"] or declared.get("codex_cli_version"),
        )
    if permission_faults:
        return _result(
            CLASSIFICATION_INVALID,
            INTEGRITY_TAMPERED,
            [*permission_faults, *stale_codes],
            "receipt evidence 不是 owner-only 文件",
            model=facts["review_model"],
            effort=facts["review_effort"],
            cli_version=facts["recorded_cli_version"],
        )
    if historical_audit:
        # A historical query deliberately skipped the current-HEAD freshness
        # comparison, so it can never produce a current approval: the receipt is
        # reported as genuine history and ``current_approval_eligible`` stays
        # false even when every recorded fact still matches the installed
        # toolchain.  VALID_CURRENT is only reachable after a real exact-head
        # comparison has been performed.
        stale_codes.append("HISTORICAL_AUDIT_NO_CURRENT_APPROVAL")
    if stale_codes:
        return _result(
            CLASSIFICATION_STALE_TOOLING,
            INTEGRITY_INTACT,
            stale_codes,
            "receipt 是内部一致的合法历史证据，但其 toolchain/policy 与当前不同，不能作为当前 approval",
            model=facts["review_model"] or declared.get("review_model"),
            effort=facts["review_effort"] or declared.get("review_reasoning_effort"),
            cli_version=facts["recorded_cli_version"] or declared.get("codex_cli_version"),
        )
    return _result(
        CLASSIFICATION_VALID_CURRENT,
        INTEGRITY_INTACT,
        [],
        "receipt 与当前 exact HEAD、mission scope、pinned model/effort 和已安装 Codex CLI 完全一致",
        model=facts["review_model"],
        effort=facts["review_effort"],
        cli_version=facts["recorded_cli_version"],
    )


def validate_receipt(
    receipt_path: Path,
    *,
    repo_root: Path,
    current_head: str | None = None,
    expected_base: str | None = None,
    expected_mission_id: str | None = None,
    expected_mission_scope_file: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed validation for one external, exact-head receipt.

    Only ``VALID_CURRENT`` passes.  ``STALE_TOOLING`` — genuine older evidence
    whose model, effort, wrapper or Codex CLI has since moved — fails exactly
    like ``INVALID`` for the purpose of a current approval, while keeping its
    distinct machine-readable reason codes so historical audits never mislabel
    it as tampering.
    """

    result = classify_receipt(
        receipt_path,
        repo_root=repo_root,
        current_head=current_head,
        expected_base=expected_base,
        expected_mission_id=expected_mission_id,
        expected_mission_scope_file=expected_mission_scope_file,
    )
    if result.classification != CLASSIFICATION_VALID_CURRENT:
        message = (
            f"{result.classification}"
            f"[{'/'.join(result.reason_codes) or 'UNSPECIFIED'}]: {result.detail}"
        )
        if result.head_error:
            raise ExactHeadError(message)
        raise ReviewReceiptError(message)
    if result.receipt is None:  # pragma: no cover - defensive fail-closed guard
        raise ReviewReceiptError("VALID_CURRENT classification 缺少 receipt payload")
    return result.receipt
