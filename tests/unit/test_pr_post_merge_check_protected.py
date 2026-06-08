"""Tests for post-merge check protected branch safety gate.

lifecycle: test-fixture

All tests use mocked gh/git subprocess output — no real GitHub access,
no real git mutations.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/devops/pr_post_merge_check.py"
_PR_NUM = 1475
_MERGE_COMMIT = "49b4341cf46f7710a082e2701a4b75d1f47e6e99"
_BRANCH = "feature/test-branch"

sys.path.insert(0, str(ROOT / "scripts/devops"))
import pr_post_merge_check as pp  # noqa: E402

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

MERGED_PR_JSON = {
    "state": "MERGED",
    "mergedAt": "2026-06-08T13:52:08Z",
    "mergeCommit": {"oid": _MERGE_COMMIT},
}

VALID_CI_RUN = [
    {
        "name": "Production Gate",
        "databaseId": 9876543210,
        "status": "completed",
        "conclusion": "success",
    }
]


# ---------------------------------------------------------------------------
# Helpers (minimal duplication — shared across protected-branch tests only)
# ---------------------------------------------------------------------------


def _make_git_mock(  # noqa: C901
    merge_contains_main: bool = True,
    main_is_ancestor: bool = True,
    origin_is_ancestor: bool = True,
    behind_count: str = "0",
    status_clean: bool = True,
) -> mock.MagicMock:
    """Return a mock for git commands."""

    def _run(args, **_kwargs):  # noqa: C901 PLR0912
        result = mock.MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        if args[0] != "git":
            raise RuntimeError(f"Unexpected command: {args}")

        if args[1] == "fetch":
            result.returncode = 0
        elif args[1] == "branch" and "--contains" in args:
            if merge_contains_main:
                result.stdout = "  origin/main\n  origin/HEAD"
            else:
                result.stdout = ""
                result.returncode = 1
        elif args[1] == "merge-base" and "--is-ancestor" in args:
            if "main" in args[2] and "origin/main" in args[3]:
                result.returncode = 0 if main_is_ancestor else 1
            elif "origin/main" in args[2] and "main" in args[3]:
                result.returncode = 0 if origin_is_ancestor else 1
        elif args[1] == "rev-list":
            result.stdout = behind_count
        elif args[1] == "status" and "--short" in args:
            if not status_clean:
                result.stdout = " M dirty_file.py\n?? new_file.py"
        elif args[1] in ("push", "branch") and ("--delete" in args or "-d" in args):
            result.returncode = 0
        else:
            result.returncode = 0

        return result

    return mock.MagicMock(side_effect=_run)


def _assert_fail(result: pp.PostMergeResult, reason_contains: str = "") -> None:
    assert not result.passed, f"Expected FAIL but got PASS. Failures: {result.failures}"
    assert result.verdict() == "FAIL"
    if reason_contains:
        assert any(reason_contains in f for f in result.failures), (
            f"Expected failure containing '{reason_contains}', got: {result.failures}"
        )


def _assert_pass(result: pp.PostMergeResult) -> None:
    assert result.passed, f"Expected PASS but got FAIL. Failures: {result.failures}"
    assert result.verdict() == "PASS"


def _make_all_pass_mocks():
    """Return (pr_mock, ci_mock, git_mock) for tests where checks would pass."""
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_mock = _make_git_mock()

    return pr_mock, ci_mock, git_mock


def _make_combined_run(pr_mock, ci_mock, git_mock):
    """Return a combined subprocess.run mock."""

    def _run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_mock(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    return _run


# ---------------------------------------------------------------------------
# Protected branch checks — evaluate() rejects protected branches
# ---------------------------------------------------------------------------


def test_protected_branch_main_fails():
    """CONFIRM_CLEANUP=1 + BRANCH=main → FAIL, no deletion."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()
    combined = _make_combined_run(pr_mock, ci_mock, git_mock)

    with mock.patch("subprocess.run", side_effect=combined):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, "main")
    _assert_fail(result, reason_contains="protected")
    assert any("main" in f for f in result.failures)


def test_protected_branch_master_fails():
    """CONFIRM_CLEANUP=1 + BRANCH=master → FAIL, no deletion."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()
    combined = _make_combined_run(pr_mock, ci_mock, git_mock)

    with mock.patch("subprocess.run", side_effect=combined):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, "master")
    _assert_fail(result, reason_contains="protected")


def test_protected_branch_origin_main_fails():
    """CONFIRM_CLEANUP=1 + BRANCH=origin/main → FAIL, no deletion."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()
    combined = _make_combined_run(pr_mock, ci_mock, git_mock)

    with mock.patch("subprocess.run", side_effect=combined):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, "origin/main")
    _assert_fail(result, reason_contains="protected")


def test_protected_branch_origin_master_fails():
    """CONFIRM_CLEANUP=1 + BRANCH=origin/master → FAIL, no deletion."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()
    combined = _make_combined_run(pr_mock, ci_mock, git_mock)

    with mock.patch("subprocess.run", side_effect=combined):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, "origin/master")
    _assert_fail(result, reason_contains="protected")


def test_current_branch_fails():
    """CONFIRM_CLEANUP=1 + BRANCH=current branch → FAIL, no deletion."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()

    # Make git rev-parse --abbrev-ref HEAD return the branch name
    def _git_with_current(args, **kwargs):
        if args[1] == "rev-parse" and "--abbrev-ref" in args:
            result = mock.MagicMock()
            result.returncode = 0
            result.stdout = _BRANCH
            result.stderr = ""
            return result
        return git_mock(args, **kwargs)

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return _git_with_current(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="currently checked-out")


def test_cleanup_branch_refuses_protected():
    """cleanup_branch() refuses main even if called directly."""
    logs = pp.cleanup_branch("main")
    assert any("REFUSED" in line for line in logs)


def test_cleanup_branch_refuses_master():
    """cleanup_branch() refuses master even if called directly."""
    logs = pp.cleanup_branch("master")
    assert any("REFUSED" in line for line in logs)


def test_cleanup_branch_refuses_origin_main():
    """cleanup_branch() refuses origin/main even if called directly."""
    logs = pp.cleanup_branch("origin/main")
    assert any("REFUSED" in line for line in logs)


def test_cleanup_branch_refuses_origin_master():
    """cleanup_branch() refuses origin/master even if called directly."""
    logs = pp.cleanup_branch("origin/master")
    assert any("REFUSED" in line for line in logs)


def test_check_branch_not_protected_ok():
    """Normal feature branch passes protection check."""
    result = pp._check_branch_not_protected(_BRANCH)
    assert len(result) == 0


def test_check_branch_not_protected_main():
    """main is detected as protected."""
    result = pp._check_branch_not_protected("main")
    assert len(result) >= 1
    assert any("protected" in r.lower() for r in result)


def test_check_branch_not_protected_master():
    """master is detected as protected."""
    result = pp._check_branch_not_protected("master")
    assert len(result) >= 1
    assert any("protected" in r.lower() for r in result)


def test_non_protected_branch_cleanup_allowed():
    """Normal branch with CONFIRM_CLEANUP can proceed through evaluate."""
    pr_mock, ci_mock, git_mock = _make_all_pass_mocks()
    combined = _make_combined_run(pr_mock, ci_mock, git_mock)

    # _BRANCH is "feature/test-branch" — not in PROTECTED_BRANCHES
    with mock.patch("subprocess.run", side_effect=combined):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_pass(result)
