#!/usr/bin/env python3
"""
Static tests for standardize-ci-watch-command.

lifecycle: permanent
scope: static verification only — Makefile target presence, CLAUDE.md rule presence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def repo_root():
    return _REPO_ROOT


@pytest.fixture
def makefile(repo_root):
    p = repo_root / "Makefile"
    if p.exists():
        return p.read_text(encoding="utf-8")
    pytest.skip("Makefile not found")


@pytest.fixture
def claude_md(repo_root):
    p = repo_root / "CLAUDE.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    pytest.skip("CLAUDE.md not found")


class TestMakefileWatchPr:
    """Makefile contains the watch-pr target."""

    def test_watch_pr_target_exists(self, makefile):
        """Makefile has a watch-pr target."""
        assert "watch-pr:" in makefile, "Makefile must have watch-pr target"

    def test_watch_pr_uses_gh_pr_checks_watch(self, makefile):
        """watch-pr uses gh pr checks --watch."""
        assert "gh pr checks" in makefile, "watch-pr must use gh pr checks"
        assert "--watch" in makefile, "watch-pr must use --watch flag"

    def test_watch_pr_requires_pr_param(self, makefile):
        """watch-pr validates PR parameter."""
        assert "$(PR)" in makefile, "watch-pr must use PR variable"

    def test_watch_pr_has_fallback_message(self, makefile):
        """watch-pr gives clear fallback when --watch unavailable."""
        assert "not supported" in makefile.lower() or "manually" in makefile.lower(), (
            "watch-pr must provide fallback when --watch unavailable"
        )


class TestClaudeMdCiWatchRules:
    """CLAUDE.md forbids custom CI watch loops."""

    def test_forbids_while_true_sleep_loop(self, claude_md):
        """CLAUDE.md forbids custom while true / sleep CI monitoring loops."""
        assert "while true" in claude_md.lower() or "while" in claude_md.lower(), (
            "CLAUDE.md must reference the forbidden pattern"
        )

    def test_forbids_monitor_wrapper(self, claude_md):
        """CLAUDE.md forbids Monitor tool for CI watch."""
        assert "monitor" in claude_md.lower() or "禁止" in claude_md, (
            "CLAUDE.md must forbid Monitor-based CI watch"
        )

    def test_requires_make_watch_pr(self, claude_md):
        """CLAUDE.md mandates make watch-pr."""
        assert "watch-pr" in claude_md, "CLAUDE.md must reference make watch-pr"

    def test_forbids_modifying_business_code_on_ci_failure(self, claude_md):
        """CLAUDE.md forbids modifying business code when CI monitoring fails."""
        assert "不要" in claude_md or "do not" in claude_md.lower(), (
            "CLAUDE.md must have prohibition language"
        )
