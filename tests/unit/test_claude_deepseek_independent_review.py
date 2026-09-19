"""Regression tests for the explicit DeepSeek exact-head runner."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_receipt_evidence as consumer


def test_runner_rejects_non_current_head_before_creating_external_evidence(tmp_path: Path):
    args = Namespace(
        repo_root=Path(__file__).resolve().parents[2],
        base_sha="HEAD^",
        head_sha="HEAD^",
        mission_id="CLAUDE_CODE_DEEPSEEK_INDEPENDENT_REVIEW_BACKEND",
        mission_scope_file=Path(__file__).resolve().parents[2]
        / "docs/agentic/missions/CLAUDE_CODE_DEEPSEEK_INDEPENDENT_REVIEW_BACKEND.json",
        evidence_dir=tmp_path / "evidence",
    )
    with pytest.raises(runner.DeepSeekReviewError, match="current exact HEAD"):
        runner.run_review(args)
    assert not args.evidence_dir.exists()


def _args(tmp_path: Path) -> Namespace:
    return Namespace(repo_root=tmp_path, evidence_dir=tmp_path / "evidence")


def test_runner_removes_only_new_worktree_after_success(monkeypatch, tmp_path: Path):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()
    unrelated = args.evidence_dir / "claude-deepseek-worktree-unrelated"
    unrelated.mkdir()

    def fake_run_review(_args):
        created = _args.evidence_dir / "claude-deepseek-worktree-current"
        created.mkdir()
        receipt = _args.evidence_dir / "claude-deepseek-receipt-current.json"
        receipt.write_text("{}", encoding="utf-8")
        return receipt

    calls: list[list[str]] = []

    def fake_subprocess(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).rmdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess)
    receipt = runner.run_review(args)
    assert receipt.exists()
    assert unrelated.exists()
    assert calls == [
        [
            "git",
            "worktree",
            "remove",
            "--force",
            str(args.evidence_dir / "claude-deepseek-worktree-current"),
        ]
    ]


@pytest.mark.parametrize(
    "failure",
    [
        runner.backend.BackendInfrastructureError("timeout"),
        runner.DeepSeekReviewError("validation"),
    ],
)
def test_runner_removes_new_worktree_and_partial_evidence_on_failure(
    monkeypatch, tmp_path: Path, failure
):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()
    retained = args.evidence_dir / "claude-deepseek-raw-prior.json"
    retained.write_text("prior", encoding="utf-8")

    def fake_run_review(_args):
        (_args.evidence_dir / "claude-deepseek-worktree-current").mkdir()
        (_args.evidence_dir / "claude-deepseek-raw-current.json").write_text(
            "partial", encoding="utf-8"
        )
        raise failure

    def fake_subprocess(command, **_kwargs):
        Path(command[-1]).rmdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess)
    with pytest.raises(type(failure)):
        runner.run_review(args)
    assert retained.exists()
    assert not (args.evidence_dir / "claude-deepseek-worktree-current").exists()
    assert not (args.evidence_dir / "claude-deepseek-raw-current.json").exists()


def test_runner_cleanup_failure_removes_receipt_and_returns_controlled_error(
    monkeypatch, tmp_path: Path
):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()

    def fake_run_review(_args):
        (_args.evidence_dir / "claude-deepseek-worktree-current").mkdir()
        receipt = _args.evidence_dir / "claude-deepseek-receipt-current.json"
        receipt.write_text("{}", encoding="utf-8")
        return receipt

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(
        runner.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1)
    )
    with pytest.raises(runner.DeepSeekReviewError, match="worktree cleanup failed"):
        runner.run_review(args)
    assert not (args.evidence_dir / "claude-deepseek-receipt-current.json").exists()


def test_backend_failure_exposes_only_allowlisted_classification():
    assert (
        runner._safe_backend_failure_code(
            runner.backend.BackendInfrastructureError("AUTH_FAILURE: private detail")
        )
        == "AUTH_FAILURE"
    )


def test_chunked_receipt_prompt_bytes_hash_without_double_encoding():
    """The chunk aggregate prompt is already canonical bytes at receipt construction."""

    prompt = b'{"manifest":"chunked"}'
    assert runner._canonical_prompt_bytes(prompt) is prompt
    assert runner.sha256_bytes(runner._canonical_prompt_bytes(prompt)) == runner.sha256_bytes(
        prompt
    )


def test_canonical_prompt_bytes_encodes_text_once():
    assert runner._canonical_prompt_bytes("chunked") == b"chunked"
    assert (
        runner._safe_backend_failure_code(
            runner.backend.BackendInfrastructureError("unexpected sensitive detail")
        )
        == "CLI_RUNTIME_FAILURE"
    )


def test_chunked_consumer_accepts_command_with_canonical_empty_tools_argument(
    monkeypatch, tmp_path: Path
):
    """Chunked receipts retain the required empty value after ``--tools``."""

    receipt = {
        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
        "review_backend": "claude-code-deepseek",
        "requested_model": "deepseek-flash",
        "resolved_model": "deepseek-flash",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "diff_sha256": "d" * 64,
        "mission_id": "MISSION",
        "mission_scope_sha256": "c" * 64,
        "review_run_id": "a",
        "review_result": "PASS",
        "findings": [],
        "finding_counts_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "integrity": {"receipt_payload_sha256": "ok"},
        "provenance": {
            "chunked_review": True,
            "reviewer_command": ["claude", "--tools", ""],
            "command_sha256": "d" * 64,
            "claude_cli_version": "2.1.276",
            "claude_binary_sha256": "e" * 64,
            "settings_sha256": "f" * 64,
            "provider_endpoint": "https://api.deepseek.com/anthropic",
            "session_id": "session",
        },
    }
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    path = evidence_dir / "claude-deepseek-receipt-bbbbbbbbbbbb-a.json"
    path.write_text(__import__("json").dumps(receipt), encoding="utf-8")
    registry = {
        "claude-code-deepseek": {
            "status": "active",
            "allowed_requested_models": ["deepseek-flash"],
            "required_provenance_fields": list(receipt["provenance"].keys())[1:],
        }
    }
    monkeypatch.setattr(consumer, "load_backend_registry", lambda _path: registry)
    monkeypatch.setattr(consumer, "receipt_payload_sha256", lambda _value: "ok")
    monkeypatch.setattr(
        consumer,
        "validate_result",
        lambda _value: {
            "review_result": "PASS",
            "findings": [],
            "finding_counts_by_severity": receipt["finding_counts_by_severity"],
        },
    )
    monkeypatch.setattr(consumer, "sha256_bytes", lambda _value: "d" * 64)
    monkeypatch.setattr(consumer, "validate_receipt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        consumer.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout=b"diff")
    )
    top = {"chunks": [], "manifest": {"chunks": []}}
    raw = evidence_dir / "claude-deepseek-raw-bbbbbbbbbbbb-a.json"
    final = evidence_dir / "claude-deepseek-final-bbbbbbbbbbbb-a.json"
    raw.write_text(__import__("json").dumps(top), encoding="utf-8")
    final.write_bytes(
        consumer.canonical_json(
            {
                "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                "review_result": "PASS",
                "findings": [],
            }
        )
    )
    raw.chmod(0o600)
    final.chmod(0o600)
    receipt["raw_output_sha256"] = receipt["final_result_sha256"] = "d" * 64
    path.write_text(__import__("json").dumps(receipt), encoding="utf-8")
    path.chmod(0o600)
    result = consumer._deepseek_receipt_evidence(
        path,
        repo_root=repo_root,
        expected_base="a" * 40,
        expected_head="b" * 40,
        expected_mission_id="MISSION",
        expected_scope_hash="c" * 64,
    )
    assert result.trusted is True


def test_chunked_consumer_rejects_incomplete_or_repo_local_artifacts(tmp_path: Path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    artifact = evidence_dir / "chunk.json"
    artifact.write_text("{}", encoding="utf-8")
    artifact.chmod(0o644)
    with pytest.raises(ValueError, match="invalid chunk artifact metadata"):
        consumer._assert_external_artifact(
            artifact, repo_root=tmp_path / "repo", kind="chunk artifact"
        )

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local = repo_root / "receipt.json"
    local.write_text("{}", encoding="utf-8")
    local.chmod(0o600)
    with pytest.raises(ValueError, match="outside repository"):
        consumer._assert_external_artifact(local, repo_root=repo_root, kind="receipt")
