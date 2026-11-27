"""Regression tests for post-merge completion/cleanup separation.

lifecycle: test-fixture

The completion helper is read-only.  Branch names are evidence fields only;
branch/worktree cleanup is not a completion authority or a callable side
effect of this module.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/devops/pr_post_merge_check.py"
PR_NUMBER = 1475
MERGE_COMMIT = "49b4341cf46f7710a082e2701a4b75d1f47e6e99"

sys.path.insert(0, str(ROOT / "scripts/devops"))
import pr_post_merge_check as pp  # noqa: E402

MERGED_PR_JSON = {
    "state": "MERGED",
    "mergedAt": "2026-06-08T13:52:08Z",
    "mergeCommit": {"oid": MERGE_COMMIT},
}
VALID_CI_RUN = [
    {
        "name": "Production Gate",
        "databaseId": 9876543210,
        "status": "completed",
        "conclusion": "success",
        "headSha": MERGE_COMMIT,
        "event": "push",
        "headBranch": "main",
    }
]


def _make_git_mock():
    """Return a read-only subprocess mock with all completion checks green."""

    def run(args, **_kwargs):
        result = mock.MagicMock(returncode=0, stdout="", stderr="")
        if args[1] == "branch" and "--contains" in args:
            result.stdout = "  origin/main\n"
        elif args[1] == "status" and "--short" in args:
            result.stdout = ""
        elif args[1] == "rev-list":
            result.stdout = "0 0"
        return result

    return mock.MagicMock(side_effect=run)


def test_protected_branch_name_is_report_only():
    """A main branch label does not add a cleanup gate to completion evidence."""
    pr_mock = mock.MagicMock()
    pr_mock.stdout = json.dumps(MERGED_PR_JSON)
    pr_mock.returncode = 0
    ci_mock = mock.MagicMock()
    ci_mock.stdout = json.dumps(VALID_CI_RUN)
    ci_mock.returncode = 0
    git_mock = _make_git_mock()

    def combined_run(args, **kwargs):
        if args[0] == "gh":
            return pr_mock if "pr" in args else ci_mock
        if args[0] == "git":
            return git_mock(args, **kwargs)
        raise RuntimeError(f"Unexpected command: {args}")

    with mock.patch("subprocess.run", side_effect=combined_run):
        result = pp.evaluate(PR_NUMBER, MERGE_COMMIT, "main")

    assert result.passed
    git_commands = [call.args[0] for call in git_mock.call_args_list]
    assert not any("--delete" in command or "-d" in command for command in git_commands)


def test_evaluate_reuses_one_snapshot_for_verdict_and_evidence():
    """A later mutable-state change cannot contradict the verdict evidence."""
    ci_data = {
        "found": True,
        "workflow": "Production Gate",
        "run_id": "9876543210",
        "status": "completed",
        "conclusion": "success",
        "head_sha": MERGE_COMMIT,
        "event": "push",
        "head_branch": "main",
    }
    main_ff_mock = mock.Mock(
        side_effect=[
            (True, "STATE=UP_TO_DATE"),
            (False, "STATE=GIT_COMMAND_FAILED: transient second read"),
        ]
    )
    status_mock = mock.Mock(
        side_effect=[
            (True, "Working tree is clean"),
            (False, "Working tree is dirty: transient second read"),
        ]
    )

    with (
        mock.patch.object(pp, "fetch_pr", return_value=MERGED_PR_JSON),
        mock.patch.object(pp, "fetch_ci", return_value=ci_data),
        mock.patch.object(pp, "merge_commit_in_origin_main", return_value=True),
        mock.patch.object(pp, "main_can_ff_sync", main_ff_mock),
        mock.patch.object(pp, "git_status_clean", status_mock),
    ):
        result = pp.evaluate(PR_NUMBER, MERGE_COMMIT, "main")

    assert main_ff_mock.call_count == 1
    assert status_mock.call_count == 1
    assert result.passed
    assert result.main_ff_ok
    assert result.status_clean
    assert result.failures == []


def test_cleanup_flag_is_not_a_supported_completion_option():
    """The completion CLI no longer exposes a branch deletion switch."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--confirm-cleanup" not in result.stdout


@pytest.mark.parametrize(
    "remote_oid",
    [MERGE_COMMIT[:7] + "0" * 33, MERGE_COMMIT[:7], None],
)
def test_ci_is_not_queried_until_github_binds_the_supplied_merge_sha(remote_oid):
    pr = {**MERGED_PR_JSON, "mergeCommit": {"oid": remote_oid}}
    green_ci = {
        "found": True,
        "status": "completed",
        "conclusion": "success",
        "head_sha": MERGE_COMMIT,
        "event": "push",
        "head_branch": "main",
    }
    with (
        mock.patch.object(pp, "fetch_pr", return_value=pr),
        mock.patch.object(pp, "fetch_ci", return_value=green_ci) as fetch_ci,
        mock.patch.object(pp, "merge_commit_in_origin_main", return_value=True) as reachable,
        mock.patch.object(pp, "main_can_ff_sync", return_value=(True, "")),
        mock.patch.object(pp, "git_status_clean", return_value=(True, "")),
    ):
        result = pp.evaluate(PR_NUMBER, MERGE_COMMIT, "feature/test-branch")

    assert result.verdict() == "FAIL"
    assert any("PR merge SHA" in failure for failure in result.failures)
    fetch_ci.assert_not_called()
    reachable.assert_not_called()


@pytest.mark.parametrize(
    ("event", "head_branch"),
    [("workflow_dispatch", "main"), ("push", "feature/test"), (None, "main"), ("push", None)],
)
def test_successful_ci_requires_a_main_push(event, head_branch):
    ci = {
        "found": True,
        "status": "completed",
        "conclusion": "success",
        "head_sha": MERGE_COMMIT,
        "event": event,
        "head_branch": head_branch,
    }

    failures = pp._check_ci(ci, MERGE_COMMIT)

    assert failures
