"""Reviewer model provenance and three-state receipt classification tests.

lifecycle: test-fixture

These tests bootstrap the v1.1 reviewer policy on itself: the pinned model and
reasoning effort must be visible in the canonical invocation, a v2 receipt must
record them from the executed argv rather than from a Builder declaration, and
a legitimate tooling upgrade must stay distinguishable from tampered evidence.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.devops import agent_workflow, codex_independent_review
from scripts.devops.codex_review_classification import (
    CLASSIFICATION_INVALID,
    CLASSIFICATION_STALE_TOOLING,
    CLASSIFICATION_VALID_CURRENT,
    INTEGRITY_INTACT,
    INTEGRITY_TAMPERED,
    classify_receipt,
    validate_receipt,
)
from scripts.devops.codex_review_contract import (
    REVIEW_MODEL_PINNED,
    REVIEW_REASONING_EFFORT_PINNED,
    build_reviewer_command,
)
from scripts.devops.codex_review_provenance import ReviewReceiptError
from scripts.devops.codex_review_receipt import REVIEW_OUTPUT_SCHEMA
from tests.helpers.agentic_workflow_fixtures import BASE_SHA, MISSION_ID, MISSION_SCOPE_PATH
from tests.helpers.agentic_workflow_fixtures import body as _body
from tests.helpers.agentic_workflow_fixtures import make_repo as _make_repo
from tests.helpers.agentic_workflow_fixtures import write_valid_receipt as _write_valid_receipt


def _scope_file(repo: Path) -> Path:
    return repo / MISSION_SCOPE_PATH


@pytest.fixture(autouse=True)
def _synthetic_codex_provenance_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give classification fixtures an explicit non-production Codex binary."""

    codex_root = tmp_path / "codex-home"
    codex_root.mkdir(mode=0o700)
    bin_root = tmp_path / "bin"
    bin_root.mkdir(mode=0o700)
    codex_binary = bin_root / "codex"
    codex_binary.write_text(
        '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "codex-cli 0.153.4"; exit 0; fi\nexit 0\n',
        encoding="utf-8",
    )
    codex_binary.chmod(0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_root))
    monkeypatch.setenv("PATH", f"{bin_root}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(codex_independent_review, "resolve_codex_binary", lambda _: codex_binary)


def _pinned_command() -> list[str]:
    return build_reviewer_command(
        codex_binary="codex",
        base_sha=BASE_SHA,
        output_schema=REVIEW_OUTPUT_SCHEMA,
        final_message_path=Path("/tmp/final.json"),
    )


def _classification(
    receipt: Path,
    repo: Path,
    *,
    current_head: str | None,
    expected_base: str | None = None,
    historical_audit: bool = False,
):
    return classify_receipt(
        receipt,
        repo_root=repo,
        current_head=current_head,
        expected_base=expected_base,
        expected_mission_id=MISSION_ID,
        historical_audit=historical_audit,
    )


def _merge_ready(
    repo: Path,
    base: str,
    head: str,
    receipt: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Run the real merge-ready gate and return its structured output."""

    local = repo.parent / "local-preflight.json"
    preflight = {
        "schema_version": "agentic-engineering-workflow/v1",
        "workflow": "agentic_engineering_workflow_v1",
        "verdict": "PASS",
        "base_sha": base,
        "head_sha": head,
        "current_head_sha": head,
        "changed_paths": ["Makefile"],
    }
    local.write_text(json.dumps(preflight), encoding="utf-8")
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--mission-scope-file",
            str(_scope_file(repo)),
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--pr",
            "1",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--json",
        ]
    )
    monkeypatch.setattr(
        agent_workflow,
        "_remote_pr_check",
        lambda pr_number, *, expected_head, **_kwargs: (
            agent_workflow.GateCheck("remote-required-ci", "PASS", "mock exact-head CI"),
            {"pr": pr_number, "verdict": "PASS", "head_sha": expected_head},
            _body(review_result="PASS", reviewed_sha=expected_head, provider="codex"),
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.agent_workflow_preflight.run_preflight",
        lambda *_args, **_kwargs: preflight,
    )
    stream = io.StringIO()
    with redirect_stdout(stream):
        exit_code = agent_workflow.merge_ready_command(args)
    output = json.loads(stream.getvalue())
    output["exit_code"] = exit_code
    return output


def test_model_pin_present_in_reviewer_command():
    command = _pinned_command()
    assert "-m" in command
    assert command[command.index("-m") + 1] == REVIEW_MODEL_PINNED == "gpt-6-astra"


def test_reasoning_effort_pin_present_in_reviewer_command():
    command = _pinned_command()
    assert 'model_reasoning_effort="medium"' in command
    assert REVIEW_REASONING_EFFORT_PINNED == "medium"
    assert "--ignore-user-config" in command


def test_new_receipt_records_review_model(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    recorded = document["provenance"]["reviewer_command"]
    assert document["schema_version"] == "codex-independent-review-receipt/v2"
    assert document["model_provenance"]["review_model"] == REVIEW_MODEL_PINNED
    assert recorded[recorded.index("-m") + 1] == document["model_provenance"]["review_model"]
    assert document["model_provenance"]["derived_from_recorded_command"] is True


def test_new_receipt_records_reasoning_effort(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    recorded = document["provenance"]["reviewer_command"]
    assert document["model_provenance"]["review_reasoning_effort"] == (
        REVIEW_REASONING_EFFORT_PINNED
    )
    assert 'model_reasoning_effort="medium"' in recorded


def test_new_receipt_records_observed_codex_cli_version(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    observed = codex_independent_review.observe_codex_cli_version(
        Path(document["provenance"]["codex_binary"])
    )
    assert document["model_provenance"]["codex_cli_version"] == observed
    assert document["model_provenance"]["cli_version_source"] == ("observed_codex_version_stdout")


def test_current_receipt_matching_policy_is_valid_current(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    result = _classification(receipt, repo, current_head=head, expected_base=base)
    assert result.classification == CLASSIFICATION_VALID_CURRENT
    assert result.integrity == INTEGRITY_INTACT
    assert result.reason_codes == ()
    assert result.current_approval_eligible is True
    assert result.review_model == REVIEW_MODEL_PINNED
    assert result.review_reasoning_effort == REVIEW_REASONING_EFFORT_PINNED


def test_model_field_command_mismatch_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"model_provenance": {"review_model": "gpt-6-impostor"}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "MODEL_FIELD_COMMAND_MISMATCH" in result.reason_codes
    with pytest.raises(ReviewReceiptError, match="MODEL_FIELD_COMMAND_MISMATCH"):
        validate_receipt(receipt, repo_root=repo, current_head=head)


def test_reasoning_field_command_mismatch_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"model_provenance": {"review_reasoning_effort": "high"}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "REASONING_FIELD_COMMAND_MISMATCH" in result.reason_codes


def test_cli_version_invocation_mismatch_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"model_provenance": {"codex_cli_version": "0.0.0-fabricated"}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert result.integrity == INTEGRITY_TAMPERED
    assert "CLI_VERSION_INVOCATION_MISMATCH" in result.reason_codes


def test_legitimate_tooling_upgrade_is_stale_tooling(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path, wrapper_content="# legacy reviewer wrapper\n")
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        legacy_schema=True,
        overrides={"provenance": {"codex_binary_sha256": "c" * 64}},
    )
    result = _classification(receipt, repo, current_head=head, expected_base=base)
    assert result.classification == CLASSIFICATION_STALE_TOOLING
    assert result.integrity == INTEGRITY_INTACT
    assert result.current_approval_eligible is False
    assert "WRAPPER_TOOLING_DRIFT" in result.reason_codes
    assert "CODEX_BINARY_DRIFT" in result.reason_codes
    assert "RECEIPT_LEGACY_SCHEMA_V1" in result.reason_codes
    assert not any("TAMPER" in code for code in result.reason_codes)
    assert not any("WRONG_" in code for code in result.reason_codes)


def test_legitimate_v2_tooling_upgrade_is_stale_not_tampered(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path, wrapper_content="# older wrapper\n")
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"codex_binary_sha256": "d" * 64}},
    )
    result = _classification(receipt, repo, current_head=head, expected_base=base)
    assert result.classification == CLASSIFICATION_STALE_TOOLING
    assert result.integrity == INTEGRITY_INTACT
    assert "WRAPPER_TOOLING_DRIFT" in result.reason_codes
    assert "CODEX_BINARY_DRIFT" in result.reason_codes
    assert result.reason_codes.count("RECEIPT_LEGACY_SCHEMA_V1") == 0
    assert result.review_model == REVIEW_MODEL_PINNED


def test_stale_tooling_cannot_satisfy_merge_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, base, head = _make_repo(tmp_path, wrapper_content="# older wrapper\n")
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"codex_binary_sha256": "e" * 64}},
    )
    assert _classification(receipt, repo, current_head=head).classification == (
        CLASSIFICATION_STALE_TOOLING
    )
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["merge_ready"] == "NO"
    assert output["ready_for_execution_controller_merge_review"] == "NO"
    assert output["model_provenance_valid"] == "NO"
    assert output["receipt_classification"] == CLASSIFICATION_STALE_TOOLING
    assert output["exit_code"] == 1
    review_check = next(
        check for check in output["checks"] if check["name"] == "independent-review"
    )
    assert review_check["status"] == "FAIL"


def test_wrapper_evidence_tamper_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"wrapper_sha256": "b" * 64}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert result.integrity == INTEGRITY_TAMPERED
    assert "WRAPPER_EVIDENCE_TAMPER" in result.reason_codes


def test_unresolvable_binary_evidence_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"codex_binary": str(tmp_path / "absent-codex")}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "BINARY_EVIDENCE_UNRESOLVABLE" in result.reason_codes


def test_command_evidence_tamper_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"command_sha256": "f" * 64}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "COMMAND_EVIDENCE_TAMPER" in result.reason_codes


def test_wrong_head_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    result = _classification(receipt, repo, current_head="3" * 40)
    assert result.classification == CLASSIFICATION_INVALID
    assert "WRONG_HEAD" in result.reason_codes
    assert result.integrity == INTEGRITY_INTACT


def test_wrong_base_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    result = _classification(receipt, repo, current_head=head, expected_base="2" * 40)
    assert result.classification == CLASSIFICATION_INVALID
    assert "WRONG_BASE" in result.reason_codes


def test_wrong_diff_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head, overrides={"diff_sha256": "0" * 64})
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "WRONG_DIFF" in result.reason_codes


def test_wrong_scope_is_invalid(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path, repo, base, head, overrides={"mission_scope_sha256": "0" * 64}
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert "WRONG_SCOPE" in result.reason_codes


def test_old_v1_receipt_is_legacy_not_current_approval(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head, legacy_schema=True)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert document["schema_version"] == "codex-independent-review-receipt/v1"
    assert "model_provenance" not in document
    assert "reviewer_command" not in document["provenance"]
    historical = _classification(
        receipt, repo, current_head=head, expected_base=base, historical_audit=True
    )
    assert historical.classification == CLASSIFICATION_STALE_TOOLING
    assert historical.integrity == INTEGRITY_INTACT
    assert "RECEIPT_LEGACY_SCHEMA_V1" in historical.reason_codes
    assert historical.current_approval_eligible is False
    assert historical.review_model is None
    with pytest.raises(ReviewReceiptError, match="RECEIPT_LEGACY_SCHEMA_V1"):
        validate_receipt(receipt, repo_root=repo, current_head=head, expected_base=base)


def test_v1_command_hash_tamper_is_invalid(tmp_path: Path):
    """A v1 receipt must still prove its command hash, not just its shape."""

    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        legacy_schema=True,
        overrides={"provenance": {"command_sha256": "a" * 64}},
    )
    assert (
        json.loads(receipt.read_text(encoding="utf-8"))["provenance"]["command_sha256"] == "a" * 64
    )
    result = _classification(receipt, repo, current_head=head, historical_audit=True)
    assert result.classification == CLASSIFICATION_INVALID
    assert result.integrity == INTEGRITY_TAMPERED
    assert "COMMAND_EVIDENCE_TAMPER" in result.reason_codes
    assert result.current_approval_eligible is False


def test_removed_review_worktree_keeps_receipt_historical_evidence(tmp_path: Path):
    """The runner puts --output-schema in a worktree that is later cleaned up."""

    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    worktree = Path(json.loads(receipt.read_text(encoding="utf-8"))["isolation"]["worktree_path"])
    assert (worktree / "schemas" / "agentic" / "codex_review_result.schema.json").is_file()
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
        check=True,
        capture_output=True,
    )
    assert not worktree.exists()
    result = _classification(receipt, repo, current_head=head, historical_audit=True)
    assert result.classification == CLASSIFICATION_STALE_TOOLING
    assert result.integrity == INTEGRITY_INTACT
    assert "REVIEW_WORKTREE_UNAVAILABLE" in result.reason_codes
    assert "REVIEW_OUTPUT_SCHEMA_UNAVAILABLE" in result.reason_codes
    assert result.current_approval_eligible is False
    assert not any("TAMPER" in code for code in result.reason_codes)


def test_removed_worktree_schema_hash_mismatch_is_still_invalid(tmp_path: Path):
    """A vanished schema file must not excuse a schema that contradicts HEAD."""

    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        overrides={"provenance": {"output_schema_sha256": "b" * 64}},
    )
    worktree = Path(json.loads(receipt.read_text(encoding="utf-8"))["isolation"]["worktree_path"])
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
        check=True,
        capture_output=True,
    )
    result = _classification(receipt, repo, current_head=head, historical_audit=True)
    assert result.classification == CLASSIFICATION_INVALID
    assert result.integrity == INTEGRITY_TAMPERED
    assert "OUTPUT_SCHEMA_INVALID" in result.reason_codes


def test_old_v1_receipt_cannot_satisfy_merge_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head, legacy_schema=True)
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["merge_ready"] == "NO"
    assert output["model_provenance_valid"] == "NO"
    assert output["exit_code"] == 1


def test_current_receipt_can_satisfy_merge_ready_with_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["exit_code"] == 0
    assert output["merge_ready"] == "YES"
    assert output["receipt_classification"] == CLASSIFICATION_VALID_CURRENT
    assert output["model_provenance_valid"] == "YES"
    assert output["review_model"] == REVIEW_MODEL_PINNED
    assert output["review_reasoning_effort"] == REVIEW_REASONING_EFFORT_PINNED
    provenance_check = next(
        check for check in output["checks"] if check["name"] == "review-model-provenance"
    )
    assert provenance_check["status"] == "PASS"
