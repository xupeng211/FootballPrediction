"""Focused additive tests for the generic review protocol foundation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops import independent_review_receipt as receipts
from scripts.devops.independent_review_backends import codex_cli
from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    IndependentReviewProtocolError,
    validate_result,
)

ROOT = Path(__file__).resolve().parents[2]
SHA40 = "a" * 40
SHA64 = "b" * 64


def _result(verdict: str = "PASS", findings: list[dict] | None = None) -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": verdict,
        "findings": findings or [],
    }


def _registry() -> dict:
    return receipts.load_backend_registry(ROOT / "docs/agentic/independent_review_backends.json")


def _receipt() -> dict:
    value = {
        "protocol_version": PROTOCOL_VERSION,
        "receipt_version": "independent-review-receipt/v1",
        "review_run_id": "review-run-0001",
        "review_backend": "codex-cli",
        "review_harness": "codex-cli",
        "provider": "openai",
        "requested_model": "gpt-5.6-terra",
        "base_sha": SHA40,
        "head_sha": "c" * 40,
        "diff_sha256": SHA64,
        "mission_id": "GENERIC_TEST",
        "mission_scope_path": "docs/agentic/missions/GENERIC_TEST.json",
        "mission_scope_sha256": SHA64,
        "review_prompt_sha256": SHA64,
        "review_started_at": "2026-01-01T00:00:00+00:00",
        "review_completed_at": "2026-01-01T00:00:01+00:00",
        "review_result": "PASS",
        "finding_counts_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "findings": [],
        "raw_output_sha256": SHA64,
        "final_result_sha256": SHA64,
        "isolation": {
            "fresh_process": True,
            "fresh_context": True,
            "detached_worktree": True,
            "read_only": True,
            "worktree_head_sha": "c" * 40,
            "worktree_clean_before": True,
            "worktree_clean_after": True,
        },
        "provenance": {
            "reviewer_command": ["codex", "exec"],
            "command_sha256": SHA64,
            "codex_cli_version": "0.1.0",
            "codex_binary_sha256": SHA64,
        },
    }
    value["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(value)}
    return value


def test_valid_generic_pass_result():
    result = validate_result(_result())
    assert result["review_result"] == "PASS"
    assert result["blocking_findings"] == 0


def test_p1_fail_and_p3_only_pass_semantics():
    finding = {"severity": "P1", "title": "bug", "evidence": "proof"}
    assert validate_result(_result("FAIL", [finding]))["blocking_findings"] == 1
    p3 = {"severity": "P3", "title": "note", "evidence": "proof"}
    assert validate_result(_result("PASS", [p3]))["blocking_findings"] == 0


@pytest.mark.parametrize(
    "result",
    [
        _result("PASS", [{"severity": "P0", "title": "bad", "evidence": "proof"}]),
        _result("FAIL", []),
        _result("PASS", [{"severity": "P9", "title": "bad", "evidence": "proof"}]),
        _result("PASS", [{"severity": "P3", "title": "", "evidence": "proof"}]),
    ],
)
def test_invalid_result_semantics_rejected(result):
    with pytest.raises(IndependentReviewProtocolError):
        validate_result(result)


def test_receipt_validates_integrity_and_required_backend_facts():
    receipt = _receipt()
    assert receipts.validate_receipt(receipt, registry=_registry())["review_result"] == "PASS"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"head_sha": "broken"}),
        lambda value: value.update({"raw_output_sha256": "broken"}),
        lambda value: value.update({"review_backend": "invented-backend"}),
        lambda value: value.update({"requested_model": "unapproved"}),
        lambda value: value["provenance"].pop("command_sha256"),
        lambda value: value.update({"provider": "fabricated"}),
        lambda value: value.update(
            {"findings": [{"severity": "P1", "title": "bad", "evidence": "proof"}]}
        ),
        lambda value: value.update({"api_key": "forbidden"}),
    ],
)
def test_adversarial_receipts_rejected(mutate):
    receipt = _receipt()
    mutate(receipt)
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry())


def test_tampered_payload_hash_is_rejected():
    receipt = _receipt()
    receipt["integrity"]["receipt_payload_sha256"] = SHA64
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry())


def test_registry_rejects_duplicate_and_malformed_entries():
    raw = json.loads((ROOT / "docs/agentic/independent_review_backends.json").read_text())
    raw["backends"].append(dict(raw["backends"][0]))
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_backend_registry(raw)


def test_legacy_adapter_delegates_current_and_stale_classification(monkeypatch, tmp_path):
    observed = {}

    def fake_classify(*args, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            receipt_schema_version="codex-independent-review-receipt/v2",
            classification="VALID_CURRENT",
            current_approval_eligible=True,
            receipt={
                "review_result": "PASS",
                "model_provenance": {"review_model": "gpt-5.6-terra"},
            },
            reason_codes=(),
        )

    monkeypatch.setattr(codex_cli, "classify_receipt", fake_classify)
    adapted = codex_cli.classify_legacy_receipt(
        tmp_path / "receipt.json", repo_root=tmp_path, current_head="d" * 40
    )
    assert adapted["current_approval_eligible"] is True
    assert adapted["review_result"] == "PASS"
    assert observed["current_head"] == "d" * 40

    monkeypatch.setattr(
        codex_cli,
        "classify_receipt",
        lambda *a, **k: SimpleNamespace(
            receipt_schema_version="codex-independent-review-receipt/v1",
            classification="STALE_TOOLING",
            current_approval_eligible=False,
            receipt={"review_result": "PASS"},
            reason_codes=("RECEIPT_LEGACY_SCHEMA_V1",),
        ),
    )
    stale = codex_cli.classify_legacy_receipt(tmp_path / "receipt.json", repo_root=tmp_path)
    assert stale["legacy_classification"] == "STALE_TOOLING"
    assert stale["current_approval_eligible"] is False
