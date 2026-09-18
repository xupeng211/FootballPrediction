"""Focused additive tests for the generic review protocol foundation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
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
BASE_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD^"], cwd=ROOT, check=True, capture_output=True, text=True
).stdout.strip()
HEAD_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
).stdout.strip()
SCOPE_PATH = (
    "docs/agentic/missions/GENERIC_INDEPENDENT_REVIEW_FOUNDATION_BOOTSTRAP_ACCEPTANCE_REPAIR.json"
)
PROMPT_BYTES = b"generic protocol review prompt\n"
SHA64 = "b" * 64
THREAD_ID = "trusted-codex-thread"
REVIEWER_COMMAND = (
    "/trusted/codex",
    "exec",
    "--sandbox",
    "read-only",
    "--ignore-user-config",
    "--ephemeral",
    "-m",
    "gpt-5.6-terra",
    "-c",
    'model_reasoning_effort="medium"',
    "--json",
    "--output-schema",
    "/trusted/review-result-schema.json",
    "--output-last-message",
    "/trusted/final-result.json",
)
CODEX_BINARY_SHA = "c" * 64


def _result(verdict: str = "PASS", findings: list[dict] | None = None) -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": verdict,
        "findings": findings or [],
    }


def _raw_output(final_result_bytes: bytes, thread_id: str = THREAD_ID) -> bytes:
    final_text = final_result_bytes.decode("utf-8")[:-1]
    events = (
        {"type": "thread.started", "thread_id": thread_id},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": final_text},
        },
        {"type": "turn.completed"},
    )
    return b"".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n" for event in events
    )


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
        "resolved_model": "gpt-5.6-terra",
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "diff_sha256": "b" * 64,
        "mission_id": "GENERIC_INDEPENDENT_REVIEW_FOUNDATION_BOOTSTRAP_ACCEPTANCE_REPAIR",
        "mission_scope_path": SCOPE_PATH,
        "mission_scope_sha256": "b" * 64,
        "review_prompt_sha256": "b" * 64,
        "review_started_at": "2026-01-01T00:00:00+00:00",
        "review_completed_at": "2026-01-01T00:00:01+00:00",
        "review_result": "PASS",
        "finding_counts_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "findings": [],
        "raw_output_sha256": "b" * 64,
        "final_result_sha256": "b" * 64,
        "isolation": {
            "fresh_process": True,
            "fresh_context": True,
            "detached_worktree": True,
            "read_only": True,
            "worktree_head_sha": HEAD_SHA,
            "worktree_clean_before": True,
            "worktree_clean_after": True,
        },
        "provenance": {
            "reviewer_command": list(REVIEWER_COMMAND),
            "command_sha256": receipts.sha256_bytes(
                receipts.canonical_json(list(REVIEWER_COMMAND))
            ),
            "codex_cli_version": "0.1.0",
            "codex_binary_sha256": CODEX_BINARY_SHA,
        },
    }
    context = _context(value)
    value["diff_sha256"] = receipts._actual_diff_sha256(context)
    value["mission_scope_sha256"] = receipts.sha256_bytes(
        subprocess.run(
            ["git", "show", f"{HEAD_SHA}:{SCOPE_PATH}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
    )
    value["review_prompt_sha256"] = receipts.sha256_bytes(PROMPT_BYTES)
    value["raw_output_sha256"] = receipts.sha256_bytes(context.raw_output_bytes)
    value["final_result_sha256"] = receipts.sha256_bytes(context.final_result_bytes)
    value["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(value)}
    return value


def _context(receipt: dict) -> receipts.ReceiptEvidenceContext:
    final = receipts.canonical_json(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": receipt["review_result"],
            "findings": receipt["findings"],
        }
    )
    return receipts.ReceiptEvidenceContext(
        repo_root=ROOT,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        mission_scope_path=SCOPE_PATH,
        prompt_bytes=PROMPT_BYTES,
        raw_output_bytes=_raw_output(final),
        final_result_bytes=final,
        codex_execution=receipts.CodexExecutionEvidence(
            reviewer_command=REVIEWER_COMMAND,
            resolved_model="gpt-5.6-terra",
            codex_cli_version="0.1.0",
            codex_binary_sha256=CODEX_BINARY_SHA,
            thread_id=THREAD_ID,
        ),
    )


def _validate(receipt: dict) -> dict:
    return receipts.validate_receipt(
        receipt, registry=_registry(), evidence_context=_context(receipt)
    )


def _rehash(receipt: dict) -> None:
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}


def _historical_self_hash_only_validator(receipt: dict) -> str:
    """Hermetic model of the original receipt-self-integrity-only defect."""
    if receipt.get("integrity", {}).get(
        "receipt_payload_sha256"
    ) != receipts.receipt_payload_sha256(receipt):
        raise IndependentReviewProtocolError("historical payload hash mismatch")
    return receipt["review_result"]


def _historical_worktree_scope_validator(
    receipt: dict, context: receipts.ReceiptEvidenceContext
) -> str:
    """Hermetic model of the old mutable-worktree scope lookup defect."""
    scope_bytes = (context.repo_root / receipt["mission_scope_path"]).read_bytes()
    if receipt["mission_scope_sha256"] != receipts.sha256_bytes(scope_bytes):
        raise IndependentReviewProtocolError("historical scope hash mismatch")
    return receipt["review_result"]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _temporary_scope_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """Create base and reviewed commits whose scope bytes are immutable Git evidence."""
    repo = tmp_path / "scope-evidence-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "base",
    )
    base = _git(repo, "rev-parse", "HEAD")
    scope = repo / SCOPE_PATH
    scope.parent.mkdir(parents=True)
    scope.write_bytes((ROOT / SCOPE_PATH).read_bytes())
    _git(repo, "add", SCOPE_PATH)
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "scope A",
    )
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _temporary_receipt_context(
    repo: Path, base: str, head: str, scope_bytes: bytes
) -> tuple[dict, receipts.ReceiptEvidenceContext]:
    receipt = _receipt()
    final_bytes = receipts.canonical_json(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": receipt["review_result"],
            "findings": receipt["findings"],
        }
    )
    context = receipts.ReceiptEvidenceContext(
        repo_root=repo,
        base_sha=base,
        head_sha=head,
        mission_scope_path=SCOPE_PATH,
        prompt_bytes=PROMPT_BYTES,
        raw_output_bytes=_raw_output(final_bytes),
        final_result_bytes=final_bytes,
        codex_execution=receipts.CodexExecutionEvidence(
            reviewer_command=REVIEWER_COMMAND,
            resolved_model="gpt-5.6-terra",
            codex_cli_version="0.1.0",
            codex_binary_sha256=CODEX_BINARY_SHA,
            thread_id=THREAD_ID,
        ),
    )
    receipt.update(
        {
            "base_sha": base,
            "head_sha": head,
            "diff_sha256": receipts._actual_diff_sha256(context),
            "mission_scope_sha256": receipts.sha256_bytes(scope_bytes),
            "review_prompt_sha256": receipts.sha256_bytes(PROMPT_BYTES),
            "raw_output_sha256": receipts.sha256_bytes(context.raw_output_bytes),
            "final_result_sha256": receipts.sha256_bytes(final_bytes),
            "isolation": {**receipt["isolation"], "worktree_head_sha": head},
        }
    )
    _rehash(receipt)
    return receipt, context


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
    assert _validate(receipt)["review_result"] == "PASS"


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
        _validate(receipt)


def test_tampered_payload_hash_is_rejected():
    receipt = _receipt()
    receipt["integrity"]["receipt_payload_sha256"] = SHA64
    with pytest.raises(IndependentReviewProtocolError):
        _validate(receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mission_scope_path", "/tmp/evil.json"),
        ("mission_scope_path", "docs/agentic/missions/../evil.json"),
        ("mission_id", "GENERIC\x00TEST"),
        ("review_started_at", "not-a-timestamp"),
        ("review_completed_at", "2025-01-01T00:00:00+00:00"),
        ("diff_sha256", "a" * 64),
        ("mission_scope_sha256", "a" * 64),
        ("review_prompt_sha256", "a" * 64),
        ("raw_output_sha256", "a" * 64),
        ("final_result_sha256", "a" * 64),
    ],
)
def test_bootstrap_p2_self_consistent_fake_binding_is_rejected(field, value):
    """Regression: the reviewed P2 payload must fail even after self-rehashing."""
    receipt = _receipt()
    receipt[field] = value
    _rehash(receipt)
    with pytest.raises(IndependentReviewProtocolError):
        _validate(receipt)


def test_tampered_external_evidence_is_rejected_after_self_rehash():
    receipt = _receipt()
    _rehash(receipt)
    bad_context = receipts.ReceiptEvidenceContext(
        **{**_context(receipt).__dict__, "raw_output_bytes": b"tampered"}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry(), evidence_context=bad_context)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"resolved_model": "unapproved-provider-fallback"}),
        lambda value: value["provenance"].update({"command_sha256": "a" * 64}),
        lambda value: value["provenance"].update({"codex_binary_sha256": "a" * 64}),
        lambda value: value["provenance"].update({"codex_cli_version": None}),
        lambda value: value["provenance"].update(
            {"reviewer_command": ["/trusted/codex", "exec", "-m", "other-model"]}
        ),
    ],
)
def test_codex_provenance_claims_cannot_self_authorize(mutate):
    receipt = _receipt()
    mutate(receipt)
    _rehash(receipt)
    with pytest.raises(IndependentReviewProtocolError):
        _validate(receipt)


def test_missing_trusted_codex_execution_evidence_fails_closed():
    receipt = _receipt()
    context = _context(receipt)
    context_without_execution = receipts.ReceiptEvidenceContext(
        **{**context.__dict__, "codex_execution": None}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            receipt, registry=_registry(), evidence_context=context_without_execution
        )


def test_trusted_resolved_model_mismatch_is_rejected_even_when_receipt_rehashed():
    receipt = _receipt()
    context = _context(receipt)
    mismatched_execution = receipts.CodexExecutionEvidence(
        **{**context.codex_execution.__dict__, "resolved_model": "provider-fallback"}
    )
    mismatched_context = receipts.ReceiptEvidenceContext(
        **{**context.__dict__, "codex_execution": mismatched_execution}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            receipt, registry=_registry(), evidence_context=mismatched_context
        )


def test_raw_output_must_bind_one_successful_completed_final_message():
    receipt = _receipt()
    context = _context(receipt)
    forged_raw = b'{"type":"thread.started","thread_id":"trusted-codex-thread"}\n'
    forged_receipt = dict(receipt)
    forged_receipt["raw_output_sha256"] = receipts.sha256_bytes(forged_raw)
    _rehash(forged_receipt)
    forged_context = receipts.ReceiptEvidenceContext(
        **{**context.__dict__, "raw_output_bytes": forged_raw}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            forged_receipt, registry=_registry(), evidence_context=forged_context
        )


def test_raw_output_thread_must_match_trusted_execution_evidence():
    receipt = _receipt()
    context = _context(receipt)
    forged_raw = _raw_output(context.final_result_bytes, thread_id="wrong-codex-thread")
    forged_receipt = dict(receipt)
    forged_receipt["raw_output_sha256"] = receipts.sha256_bytes(forged_raw)
    _rehash(forged_receipt)
    forged_context = receipts.ReceiptEvidenceContext(
        **{**context.__dict__, "raw_output_bytes": forged_raw}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            forged_receipt, registry=_registry(), evidence_context=forged_context
        )


@pytest.mark.parametrize("duplicate_index", [0, 2])
def test_raw_output_rejects_mixed_or_duplicate_codex_events(duplicate_index):
    receipt = _receipt()
    context = _context(receipt)
    raw_lines = _raw_output(context.final_result_bytes).splitlines()
    forged_raw = b"\n".join((*raw_lines[:3], raw_lines[duplicate_index], *raw_lines[3:])) + b"\n"
    forged_receipt = dict(receipt)
    forged_receipt["raw_output_sha256"] = receipts.sha256_bytes(forged_raw)
    _rehash(forged_receipt)
    forged_context = receipts.ReceiptEvidenceContext(
        **{**context.__dict__, "raw_output_bytes": forged_raw}
    )
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(
            forged_receipt, registry=_registry(), evidence_context=forged_context
        )


def test_scope_evidence_uses_reviewed_git_blob_not_dirty_worktree(tmp_path):
    """Regression for bootstrap P1: a checkout cannot substitute scope evidence."""
    repo, base, head = _temporary_scope_repo(tmp_path)
    scope_path = repo / SCOPE_PATH
    scope_a = scope_path.read_bytes()
    scope_path.write_bytes(scope_a + b"\n")
    receipt, context = _temporary_receipt_context(repo, base, head, scope_a)
    assert receipts.validate_receipt(receipt, registry=_registry(), evidence_context=context)

    receipt_b, context_b = _temporary_receipt_context(repo, base, head, scope_path.read_bytes())
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt_b, registry=_registry(), evidence_context=context_b)


def test_negative_control_old_validator_accepted_dirty_worktree_scope(tmp_path):
    """The pre-bootstrap-P1 validator used checkout bytes instead of the head blob."""
    repo, base, head = _temporary_scope_repo(tmp_path)
    scope_path = repo / SCOPE_PATH
    scope_path.write_bytes(scope_path.read_bytes() + b"\n")
    forged_receipt, context = _temporary_receipt_context(repo, base, head, scope_path.read_bytes())
    assert _historical_worktree_scope_validator(forged_receipt, context) == "PASS"
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(forged_receipt, registry=_registry(), evidence_context=context)


def test_negative_controls_are_hermetic_without_historical_git_objects(tmp_path):
    """Negative controls use generated commits and synthetic old behavior only."""
    repo, base, head = _temporary_scope_repo(tmp_path)
    assert _git(repo, "rev-list", "--all").splitlines() == [head, base]


def test_scope_absent_at_reviewed_head_cannot_come_from_worktree(tmp_path):
    repo, base, _head_with_scope = _temporary_scope_repo(tmp_path)
    scope_path = repo / SCOPE_PATH
    _git(repo, "checkout", "-q", base)
    scope_path.parent.mkdir(parents=True, exist_ok=True)
    scope_path.write_bytes((ROOT / SCOPE_PATH).read_bytes())
    receipt, context = _temporary_receipt_context(repo, base, base, scope_path.read_bytes())
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry(), evidence_context=context)


def test_scope_blob_from_different_commit_is_rejected(tmp_path):
    repo, base, head_a = _temporary_scope_repo(tmp_path)
    scope_path = repo / SCOPE_PATH
    scope_path.write_bytes(scope_path.read_bytes() + b"\n")
    _git(repo, "add", SCOPE_PATH)
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "scope B",
    )
    scope_b = scope_path.read_bytes()
    receipt, context = _temporary_receipt_context(repo, base, head_a, scope_b)
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry(), evidence_context=context)


def test_receipt_mission_id_must_match_reviewed_scope_contract():
    receipt = _receipt()
    receipt["mission_id"] = "DIFFERENT_VALID_MISSION"
    _rehash(receipt)
    with pytest.raises(IndependentReviewProtocolError):
        _validate(receipt)


@pytest.mark.parametrize(
    ("context_field", "value"),
    [
        ("head_sha", "a" * 40),
        ("base_sha", "b" * 40),
        ("head_sha", "HEAD:docs/agentic/missions/evil.json"),
        ("mission_scope_path", "docs/agentic/missions/good.json:evil"),
    ],
)
def test_untrusted_git_revision_or_scope_reference_is_rejected(context_field, value):
    receipt = _receipt()
    context_values = _context(receipt).__dict__.copy()
    context_values[context_field] = value
    bad_context = receipts.ReceiptEvidenceContext(**context_values)
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_receipt(receipt, registry=_registry(), evidence_context=bad_context)


def test_bootstrap_p2_negative_control_old_validator_accepts_self_rehashed_fake_receipt():
    """Prove the reviewed base implementation accepted the bootstrap P2 exploit."""
    receipt = _receipt()
    receipt.update(
        {
            "mission_scope_path": "/tmp/forged.json",
            "mission_id": "GENERIC\x00FORGED",
            "review_started_at": "not-a-timestamp",
            "diff_sha256": "a" * 64,
            "review_prompt_sha256": "a" * 64,
            "raw_output_sha256": "a" * 64,
            "final_result_sha256": "a" * 64,
        }
    )
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    assert _historical_self_hash_only_validator(receipt) == "PASS"
    with pytest.raises(IndependentReviewProtocolError):
        _validate(receipt)


def test_registry_rejects_duplicate_and_malformed_entries():
    raw = json.loads((ROOT / "docs/agentic/independent_review_backends.json").read_text())
    raw["backends"].append(dict(raw["backends"][0]))
    with pytest.raises(IndependentReviewProtocolError):
        receipts.validate_backend_registry(raw)


def test_legacy_adapter_delegates_current_and_stale_classification(monkeypatch, tmp_path):
    observed = {}

    def fake_classify(*_args, **kwargs):
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
        lambda *_args, **_kwargs: SimpleNamespace(
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
