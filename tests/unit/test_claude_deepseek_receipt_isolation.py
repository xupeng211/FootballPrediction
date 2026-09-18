"""Isolation command controls for Claude/DeepSeek generic receipts."""

from __future__ import annotations

import pytest

from scripts.devops import independent_review_receipt as receipts
from scripts.devops.independent_review_protocol import IndependentReviewProtocolError
from tests.unit.test_independent_review_protocol import _claude_receipt_and_context, _registry


@pytest.mark.parametrize(
    ("command_part", "replacement"),
    [
        ("--strict-mcp-config", None),
        ("--disallowed-tools", None),
        ("Bash,Edit,Write,WebFetch,WebSearch", "Bash,Edit,Write"),
    ],
)
def test_receipt_rejects_missing_isolation_command_controls(command_part, replacement):
    receipt, context = _claude_receipt_and_context()
    command = list(context.claude_deepseek_execution.reviewer_command)
    index = command.index(command_part)
    if replacement is None:
        command.pop(index)
    else:
        command[index] = replacement
    execution = context.claude_deepseek_execution
    values = context.__dict__.copy()
    values["claude_deepseek_execution"] = receipts.ClaudeDeepSeekExecutionEvidence(
        reviewer_command=tuple(command),
        resolved_model=execution.resolved_model,
        claude_cli_version=execution.claude_cli_version,
        claude_binary_sha256=execution.claude_binary_sha256,
        settings_sha256=execution.settings_sha256,
        provider_endpoint=execution.provider_endpoint,
        session_id=execution.session_id,
    )
    receipt["provenance"]["reviewer_command"] = command
    receipt["provenance"]["command_sha256"] = receipts.sha256_bytes(
        receipts.canonical_json(command)
    )
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            receipt,
            registry=_registry(),
            evidence_context=receipts.ReceiptEvidenceContext(**values),
        )


def test_receipt_rejects_unsupported_cli_baseline():
    receipt, context = _claude_receipt_and_context()
    execution = context.claude_deepseek_execution
    values = context.__dict__.copy()
    values["claude_deepseek_execution"] = receipts.ClaudeDeepSeekExecutionEvidence(
        reviewer_command=execution.reviewer_command,
        resolved_model=execution.resolved_model,
        claude_cli_version="2.1.275 (Claude Code)",
        claude_binary_sha256=execution.claude_binary_sha256,
        settings_sha256=execution.settings_sha256,
        provider_endpoint=execution.provider_endpoint,
        session_id=execution.session_id,
    )
    receipt["provenance"]["claude_cli_version"] = "2.1.275 (Claude Code)"
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            receipt,
            registry=_registry(),
            evidence_context=receipts.ReceiptEvidenceContext(**values),
        )
