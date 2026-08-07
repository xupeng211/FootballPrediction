"""Tests for event-to-base/head ref selection used by the Production Gate.

lifecycle: test-fixture
task: fix_production_gate_workflow_dispatch_base_head_resolution

Covers the three Production Gate triggers (pull_request / push /
workflow_dispatch) plus fail-closed behavior for missing or invalid dispatch
baselines.  production-gate.yml executes this exact module through
scripts/ops/helpers/ai_gate_event_refs.py, so the code under test here is the
code running in CI — no string matching on the workflow file.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# pull_request path
# ---------------------------------------------------------------------------


def test_pull_request_uses_pr_base_and_head():
    base, head = refs.resolve_event_refs("pull_request", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


def test_pull_request_missing_base_fails_closed():
    with pytest.raises(RuntimeError, match="pull_request event missing"):
        refs.resolve_event_refs("pull_request", None, HEAD)


def test_pull_request_empty_base_fails_closed():
    """The workflow passes empty strings when the payload field is absent."""
    with pytest.raises(RuntimeError, match="pull_request event missing"):
        refs.resolve_event_refs("pull_request", "", HEAD)


def test_pull_request_missing_head_fails_closed():
    with pytest.raises(RuntimeError, match="pull_request event missing"):
        refs.resolve_event_refs("pull_request", BASE, None)


# ---------------------------------------------------------------------------
# push path
# ---------------------------------------------------------------------------


def test_push_uses_before_and_after():
    base, head = refs.resolve_event_refs("push", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


def test_push_missing_before_fails_closed():
    """push without before (e.g. first push to a branch) must fail closed."""
    with pytest.raises(RuntimeError, match="push event missing"):
        refs.resolve_event_refs("push", "", HEAD)


def test_push_missing_after_fails_closed():
    with pytest.raises(RuntimeError, match="push event missing"):
        refs.resolve_event_refs("push", BASE, "")


# ---------------------------------------------------------------------------
# workflow_dispatch path
# ---------------------------------------------------------------------------


def test_workflow_dispatch_uses_explicit_pair():
    base, head = refs.resolve_event_refs("workflow_dispatch", BASE, HEAD)
    assert base == BASE
    assert head == HEAD


def test_workflow_dispatch_missing_base_fails_closed():
    """Dispatch without base_sha must abort — never guess a baseline."""
    with pytest.raises(RuntimeError, match="requires an explicit base_sha"):
        refs.resolve_event_refs("workflow_dispatch", None, HEAD)


def test_workflow_dispatch_empty_base_fails_closed():
    """The empty-string form is what the workflow passes when input is absent."""
    with pytest.raises(RuntimeError, match="requires an explicit base_sha"):
        refs.resolve_event_refs("workflow_dispatch", "", HEAD)


def test_workflow_dispatch_head_defaults_to_github_sha(monkeypatch):
    monkeypatch.setenv(refs.GITHUB_SHA_ENV, HEAD)
    base, head = refs.resolve_event_refs("workflow_dispatch", BASE, "")
    assert base == BASE
    assert head == HEAD


def test_workflow_dispatch_head_defaults_to_head_when_env_unset(monkeypatch):
    monkeypatch.delenv(refs.GITHUB_SHA_ENV, raising=False)
    base, head = refs.resolve_event_refs("workflow_dispatch", BASE, None)
    assert base == BASE
    assert head == "HEAD"


# ---------------------------------------------------------------------------
# unsupported events and CLI
# ---------------------------------------------------------------------------


def test_unsupported_event_fails_closed():
    with pytest.raises(RuntimeError, match="unsupported event"):
        refs.resolve_event_refs("schedule", BASE, HEAD)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_prints_resolved_pair():
    result = _run_cli("workflow_dispatch", BASE, HEAD)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{BASE} {HEAD}"


def test_cli_dispatch_missing_base_exits_nonzero():
    result = _run_cli("workflow_dispatch", "", "")
    assert result.returncode == 1
    assert "base_sha" in result.stderr


def test_cli_wrong_arg_count_exits_2():
    result = _run_cli("pull_request", BASE)
    assert result.returncode == refs.EXIT_USAGE
    assert "usage:" in result.stderr
