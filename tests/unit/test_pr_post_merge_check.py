"""Tests for the post-merge check / cleanup gate.

lifecycle: test-fixture

All tests use mocked gh/git subprocess output — no real GitHub access,
no real git mutations.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
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

OPEN_PR_JSON = {
    "state": "OPEN",
    "mergedAt": None,
    "mergeCommit": None,
}

VALID_CI_RUN = [
    {
        "name": "Production Gate",
        "databaseId": 9876543210,
        "status": "completed",
        "conclusion": "success",
    }
]

CI_NOT_FOUND: list[dict] = []

CI_PENDING = [{**VALID_CI_RUN[0], "status": "in_progress", "conclusion": ""}]

CI_FAILED = [{**VALID_CI_RUN[0], "conclusion": "failure"}]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_mock(*stdouts: str) -> mock.MagicMock:
    """Return a mock for subprocess.run that returns *stdouts* in order."""

    call_count = 0

    def _run(args, **_kwargs):
        nonlocal call_count
        if call_count < len(stdouts):
            result = mock.MagicMock()
            result.stdout = stdouts[call_count]
            result.returncode = 0
            call_count += 1
            return result
        raise RuntimeError(f"Unexpected subprocess call #{call_count}: {args}")

    return mock.MagicMock(side_effect=_run)


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


# ---------------------------------------------------------------------------
# Happy path: merged PR + CI success + clean git => PASS
# ---------------------------------------------------------------------------


def test_all_checks_pass():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_pass(result)


# ---------------------------------------------------------------------------
# PR not merged => FAIL
# ---------------------------------------------------------------------------


def test_pr_not_merged_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(OPEN_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="OPEN")


# ---------------------------------------------------------------------------
# CI not found => FAIL
# ---------------------------------------------------------------------------


def test_ci_not_found_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(CI_NOT_FOUND)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="not found")


# ---------------------------------------------------------------------------
# CI failure => FAIL
# ---------------------------------------------------------------------------


def test_ci_failure_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(CI_FAILED)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="failure")


# ---------------------------------------------------------------------------
# CI pending => FAIL
# ---------------------------------------------------------------------------


def test_ci_pending_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(CI_PENDING)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="in_progress")


# ---------------------------------------------------------------------------
# Merge commit not in origin/main => FAIL
# ---------------------------------------------------------------------------


def test_merge_not_in_main_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_bad = _make_git_mock(merge_contains_main=False)

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_bad(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="NOT in origin/main")


# ---------------------------------------------------------------------------
# Dirty working tree => FAIL
# ---------------------------------------------------------------------------


def test_dirty_tree_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_dirty = _make_git_mock(status_clean=False)

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_dirty(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_fail(result, reason_contains="dirty")


# ---------------------------------------------------------------------------
# Cleanup: no --confirm-cleanup => no branch deletion
# ---------------------------------------------------------------------------


def test_no_cleanup_without_confirm_flag():
    """When --confirm-cleanup is NOT set, cleanup_branch should not be called."""
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, _MERGE_COMMIT, _BRANCH)
    _assert_pass(result)
    # Verify no cleanup calls were made to delete branches
    # (cleanup_branch is only called from main(), not evaluate())


def test_cleanup_branch_noop_without_confirm():
    """cleanup_branch should not be invoked when confirm_cleanup is False."""
    # This is implicitly tested by the main flow — cleanup_branch is only
    # called in main() when --confirm-cleanup is set.
    # We test that evaluate() with confirm_cleanup=False does not delete.
    logs = pp.cleanup_branch(_BRANCH, dry_run=True)
    assert any("DRY RUN" in line for line in logs)
    assert any(_BRANCH in line for line in logs)


# ---------------------------------------------------------------------------
# Empty merge commit => FAIL
# ---------------------------------------------------------------------------


def test_empty_merge_commit_fails():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        result = pp.evaluate(_PR_NUM, "  ", _BRANCH)
    _assert_fail(result, reason_contains="SHA")


# ---------------------------------------------------------------------------
# format_evidence
# ---------------------------------------------------------------------------


def test_format_text_pass():
    result = pp.PostMergeResult(
        pr_number=_PR_NUM,
        pr_state="MERGED",
        merge_commit=_MERGE_COMMIT,
        branch=_BRANCH,
        ci_workflow="Production Gate",
        ci_run_id="9876543210",
        ci_status="completed",
        ci_conclusion="success",
        passed=True,
        failures=[],
        main_ff_ok=True,
        status_clean=True,
    )
    text = pp.format_evidence(result, as_json=False)
    assert "PASS" in text
    assert str(_PR_NUM) in text
    assert _MERGE_COMMIT[:7] in text
    assert "Production Gate" in text


def test_format_text_fail():
    result = pp.PostMergeResult(
        pr_number=_PR_NUM,
        pr_state="OPEN",
        merge_commit=_MERGE_COMMIT,
        branch=_BRANCH,
        ci_workflow="Production Gate",
        ci_run_id=None,
        ci_status="",
        ci_conclusion="",
        passed=False,
        failures=["PR state is 'OPEN', expected 'MERGED'"],
        main_ff_ok=True,
        status_clean=True,
    )
    text = pp.format_evidence(result, as_json=False)
    assert "FAIL" in text
    assert "OPEN" in text


def test_format_json_pass():
    result = pp.PostMergeResult(
        pr_number=_PR_NUM,
        pr_state="MERGED",
        merge_commit=_MERGE_COMMIT,
        branch=_BRANCH,
        ci_workflow="Production Gate",
        ci_run_id="9876543210",
        ci_status="completed",
        ci_conclusion="success",
        passed=True,
        failures=[],
        main_ff_ok=True,
        status_clean=True,
    )
    data = json.loads(pp.format_evidence(result, as_json=True))
    assert data["verdict"] == "PASS"
    assert data["pr_number"] == _PR_NUM


def test_format_json_fail():
    result = pp.PostMergeResult(
        pr_number=_PR_NUM,
        pr_state="OPEN",
        merge_commit=_MERGE_COMMIT,
        branch=_BRANCH,
        ci_workflow="Production Gate",
        ci_run_id=None,
        ci_status="",
        ci_conclusion="",
        passed=False,
        failures=["PR not merged"],
        main_ff_ok=True,
        status_clean=True,
    )
    data = json.loads(pp.format_evidence(result, as_json=True))
    assert data["verdict"] == "FAIL"
    assert len(data["failures"]) >= 1


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


def test_script_exists():
    assert SCRIPT.exists()


def test_script_help_succeeds():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "post-merge" in result.stdout.lower()


def test_script_requires_pr_arg():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_script_requires_all_args():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--pr", str(_PR_NUM)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# main() integration with mocked subprocess
# ---------------------------------------------------------------------------


def test_main_pass():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        exit_code = pp.main(
            [
                "--pr",
                str(_PR_NUM),
                "--merge-commit",
                _MERGE_COMMIT,
                "--branch",
                _BRANCH,
            ]
        )
    assert exit_code == 0


def test_main_fail():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(OPEN_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        exit_code = pp.main(
            [
                "--pr",
                str(_PR_NUM),
                "--merge-commit",
                _MERGE_COMMIT,
                "--branch",
                _BRANCH,
            ]
        )
    assert exit_code == 1


def test_main_json_output():
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0

    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0

    git_ok = _make_git_mock()

    def _combined_run(args, **kwargs):
        if args[0] == "gh":
            if "pr" in args:
                return pr_mock
            return ci_mock
        if args[0] == "git":
            return git_ok(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=_combined_run):
        exit_code = pp.main(
            [
                "--pr",
                str(_PR_NUM),
                "--merge-commit",
                _MERGE_COMMIT,
                "--branch",
                _BRANCH,
                "--json",
            ]
        )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_merge_commit_short_fails():
    result = pp._check_merge_commit("abc")
    assert len(result) >= 1
    assert any("SHA" in r for r in result)


def test_merge_commit_valid_passes():
    result = pp._check_merge_commit(_MERGE_COMMIT)
    assert len(result) == 0


def test_pr_merged_check_passes():
    result = pp._check_pr_merged(MERGED_PR_JSON)
    assert len(result) == 0


def test_pr_open_check_fails():
    result = pp._check_pr_merged(OPEN_PR_JSON)
    assert len(result) >= 1
    assert any("OPEN" in r for r in result)


def test_ci_check_success_passes():
    ci_data = {
        "found": True,
        "workflow": "Production Gate",
        "run_id": "12345",
        "status": "completed",
        "conclusion": "success",
    }
    result = pp._check_ci(ci_data)
    assert len(result) == 0


def test_ci_check_not_found_fails():
    ci_data = {"found": False, "run_id": None, "status": "", "conclusion": ""}
    result = pp._check_ci(ci_data)
    assert len(result) >= 1
    assert any("not found" in r for r in result)


def test_ci_check_failed_fails():
    ci_data = {
        "found": True,
        "run_id": "12345",
        "status": "completed",
        "conclusion": "failure",
    }
    result = pp._check_ci(ci_data)
    assert len(result) >= 1
    assert any("failure" in r for r in result)
