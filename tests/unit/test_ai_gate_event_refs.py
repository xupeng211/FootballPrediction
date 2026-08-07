"""Tests for event-to-base/head ref selection used by the Production Gate.

lifecycle: test-fixture
task: pr1820_codex_round1_remediation

Covers the three Production Gate triggers (pull_request / push /
workflow_dispatch) plus every fail-closed invariant added during Codex
Round-1 remediation:

- full 40-hex contract (^[0-9a-fA-F]{40}$) — short SHAs, HEAD, branch names,
  tags, whitespace, newlines and shell syntax are all rejected
- workflow_dispatch head is ALWAYS the dispatched commit (GITHUB_SHA), with
  defense-in-depth equality against a caller-supplied head; there is NO
  literal "HEAD" fallback
- workflow_dispatch base must resolve to a commit, must not equal head, and
  must be an ancestor of head
- unsupported events fail closed

production-gate.yml executes this exact module through
scripts/ops/helpers/ai_gate_event_refs.py, so the code under test here is the
code running in CI — no string matching on the workflow file.  Dispatch
ancestry checks run against a real throwaway git repository (git init + 3
commits), not mocks.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "ops" / "helpers" / "ai_gate_event_refs.py"

sys.path.insert(0, str(ROOT / "scripts" / "ops" / "helpers"))

import ai_gate_event_refs as refs  # noqa: E402

BASE = "a" * 40
HEAD = "b" * 40
SHORT_SHA = "0123456789abcdef"  # 16 hex chars — must be rejected
NONEXISTENT = "f" * 40  # full 40-hex, but no such commit


@dataclass
class Repo:
    """A real throwaway git repo: a -> b -> c (c is the newest commit)."""

    path: Path
    a: str
    b: str
    c: str


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repo:
    """Build a real git repo with 3 linear commits and chdir into it."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "gate-test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Gate Test"],
        cwd=tmp_path,
        check=True,
    )
    shas: list[str] = []
    for message in ("a", "b", "c"):
        (tmp_path / "f.txt").write_text(message + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", message],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        shas.append(rev.stdout.strip())
    return Repo(path=tmp_path, a=shas[0], b=shas[1], c=shas[2])


# ---------------------------------------------------------------------------
# pull_request path
# ---------------------------------------------------------------------------


def test_pull_request_uses_pr_base_and_head():
    base, head = refs.resolve_event_refs("pull_request", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


def test_pull_request_missing_base_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", None, HEAD)


def test_pull_request_empty_base_fails_closed():
    """The workflow passes empty strings when the payload field is absent."""
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", "", HEAD)


def test_pull_request_malformed_base_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", SHORT_SHA, HEAD)


def test_pull_request_missing_head_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", BASE, None)


def test_pull_request_malformed_head_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", BASE, "refs/heads/main")


def test_pull_request_imposes_no_ancestry_rule():
    """A PR base tip may legitimately not be an ancestor of the PR head.

    The 40-hex syntax check must be the ONLY constraint on the PR path —
    ancestry rules are dispatch-only.
    """
    base, head = refs.resolve_event_refs("pull_request", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


# ---------------------------------------------------------------------------
# push path
# ---------------------------------------------------------------------------


def test_push_uses_before_and_after():
    base, head = refs.resolve_event_refs("push", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


def test_push_missing_before_fails_closed():
    """push without before (e.g. first push to a branch) must fail closed."""
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("push", "", HEAD)


def test_push_missing_after_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("push", BASE, "")


def test_push_malformed_after_fails_closed():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("push", BASE, "origin/main")


# ---------------------------------------------------------------------------
# workflow_dispatch path — head binding (no user-supplied head)
# ---------------------------------------------------------------------------


def test_dispatch_missing_github_sha_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """Without GITHUB_SHA there is NO fallback — fail closed."""
    monkeypatch.delenv(refs.GITHUB_SHA_ENV, raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_SHA"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.b, git_repo.c)


def test_dispatch_malformed_github_sha_fails_closed(
    git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, "not-a-sha")
    with pytest.raises(RuntimeError, match="GITHUB_SHA"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.b, git_repo.c)


def test_dispatch_head_is_github_sha_not_literal_head(
    git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    """The resolved head must be GITHUB_SHA, never the string 'HEAD'."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    _, head = refs.resolve_event_refs("workflow_dispatch", git_repo.b, git_repo.c)
    assert head == git_repo.c
    assert head != "HEAD"
    assert head == os.environ[refs.GITHUB_SHA_ENV]


def test_dispatch_supplied_head_must_equal_github_sha(
    git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    """Defense in depth: a caller-supplied head different from GITHUB_SHA is rejected."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="must equal GITHUB_SHA"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.b, BASE)


def test_dispatch_no_head_fallback_absent_from_helper():
    """The helper source must contain no literal 'HEAD' fallback."""
    source = HELPER.read_text(encoding="utf-8")
    assert 'or "HEAD"' not in source
    assert '== "HEAD"' not in source


# ---------------------------------------------------------------------------
# workflow_dispatch path — base validation
# ---------------------------------------------------------------------------


def test_dispatch_valid_ancestor_passes(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """Explicit base that is a real ancestor of GITHUB_SHA must pass."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    base, head = refs.resolve_event_refs("workflow_dispatch", git_repo.b, git_repo.c)
    assert base == git_repo.b
    assert head == git_repo.c


def test_dispatch_older_ancestor_passes(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """An older legitimate ancestor broadens the diff and is safe."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    base, head = refs.resolve_event_refs("workflow_dispatch", git_repo.a, git_repo.c)
    assert base == git_repo.a
    assert head == git_repo.c


def test_dispatch_missing_base_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """Dispatch without base_sha must abort — never guess a baseline."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="base_sha is not a full 40-hex"):
        refs.resolve_event_refs("workflow_dispatch", None, git_repo.c)


def test_dispatch_empty_base_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """The empty-string form is what the workflow passes when input is absent."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="base_sha is not a full 40-hex"):
        refs.resolve_event_refs("workflow_dispatch", "", git_repo.c)


def test_dispatch_short_base_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="base_sha is not a full 40-hex"):
        refs.resolve_event_refs("workflow_dispatch", SHORT_SHA, git_repo.c)


def test_dispatch_branch_name_base_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="base_sha is not a full 40-hex"):
        refs.resolve_event_refs("workflow_dispatch", "main", git_repo.c)


def test_dispatch_base_equals_head_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="must not equal head"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.c, git_repo.c)


def test_dispatch_reversed_ancestry_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """head before base (descendant as base) must fail — base must be older."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.b)
    with pytest.raises(RuntimeError, match="must be an ancestor of head"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.c, git_repo.b)


def test_dispatch_unrelated_full_hex_fails_closed(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    """A 40-hex string that resolves to nothing must fail before ancestry."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="does not resolve to a commit"):
        refs.resolve_event_refs("workflow_dispatch", NONEXISTENT, git_repo.c)


def test_dispatch_nonexistent_github_sha_fails_closed(
    git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    """Even a syntactically valid GITHUB_SHA must resolve to a commit."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, NONEXISTENT)
    with pytest.raises(RuntimeError, match="does not resolve to a commit"):
        refs.resolve_event_refs("workflow_dispatch", git_repo.b, NONEXISTENT)


# ---------------------------------------------------------------------------
# Shell safety — arbitrary workflow-input strings must never reach git
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious",
    [
        "$(rm -rf /)",
        "`id`",
        "$HOME/../etc",
        "'quoted'",
        '"double"',
        "abc; rm -rf /",
        "refs/heads/main",
        "HEAD",
        "main",
        "a" * 40 + "\n",  # newline suffix
        "\n" + "b" * 40,  # newline prefix
        " " + "c" * 40,  # whitespace prefix
    ],
)
def test_dispatch_shell_meta_base_rejected(
    malicious: str, git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    """Malformed/non-40-hex inputs are rejected before any git use."""
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("workflow_dispatch", malicious, git_repo.c)


def test_pull_request_shell_meta_rejected():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("pull_request", "$(rm -rf /)", HEAD)


def test_push_shell_meta_rejected():
    with pytest.raises(RuntimeError, match="is not a full 40-hex commit SHA"):
        refs.resolve_event_refs("push", BASE, "`rm -rf /`")


# ---------------------------------------------------------------------------
# Unsupported events
# ---------------------------------------------------------------------------


def test_unsupported_event_fails_closed():
    with pytest.raises(RuntimeError, match="unsupported event"):
        refs.resolve_event_refs("schedule", BASE, HEAD)


# ---------------------------------------------------------------------------
# CLI contract (the exact interface production-gate.yml invokes)
# ---------------------------------------------------------------------------


def _run_cli(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )


def test_cli_prints_resolved_pair(git_repo: Repo):
    env = {**os.environ, refs.GITHUB_SHA_ENV: git_repo.c}
    result = _run_cli("workflow_dispatch", git_repo.b, git_repo.c, cwd=git_repo.path, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{git_repo.b} {git_repo.c}"


def test_cli_dispatch_missing_base_exits_nonzero(git_repo: Repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, git_repo.c)
    result = _run_cli("workflow_dispatch", "", "", cwd=git_repo.path)
    assert result.returncode == 1
    assert "base_sha" in result.stderr


def test_cli_dispatch_without_github_sha_exits_nonzero(
    git_repo: Repo, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(refs.GITHUB_SHA_ENV, raising=False)
    result = _run_cli("workflow_dispatch", git_repo.b, git_repo.c, cwd=git_repo.path)
    assert result.returncode == 1
    assert "GITHUB_SHA" in result.stderr


def test_cli_pull_request_prints_resolved_pair():
    result = _run_cli("pull_request", BASE, HEAD)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{BASE} {HEAD}"


def test_cli_unknown_event_exits_nonzero():
    result = _run_cli("schedule", BASE, HEAD)
    assert result.returncode == 1
    assert "unsupported event" in result.stderr


def test_cli_wrong_arg_count_exits_2():
    result = _run_cli("pull_request", BASE)
    assert result.returncode == refs.EXIT_USAGE
    assert "usage:" in result.stderr
