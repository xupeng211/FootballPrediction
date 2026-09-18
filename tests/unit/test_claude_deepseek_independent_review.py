"""Regression tests for the explicit DeepSeek exact-head runner."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

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
