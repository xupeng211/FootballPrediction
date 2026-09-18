"""Regression tests for the explicit DeepSeek exact-head runner."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner


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
