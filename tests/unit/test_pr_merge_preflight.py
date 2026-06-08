"""Tests for the PR merge preflight evidence check.

lifecycle: test-fixture

All tests use mocked gh/subprocess output — no real GitHub access.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/devops/pr_merge_preflight.py"
_PR_NUM = 1474

sys.path.insert(0, str(ROOT / "scripts/devops"))
import pr_merge_preflight as pp  # noqa: E402

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

VALID_PR_JSON = {
    "title": "test(foo): add bar",
    "state": "OPEN",
    "isDraft": False,
    "baseRefName": "main",
    "headRefName": "feature/bar",
    "headRefOid": "abc1234567890def",
    "mergeable": "MERGEABLE",
    "changedFiles": 3,
    "additions": 42,
    "deletions": 7,
}

VALID_CI_RUN = [
    {
        "name": "Production Gate",
        "databaseId": 9876543210,
        "status": "completed",
        "conclusion": "success",
    }
]

# -- Edge-case data ----------------------------------------------------------

DRAFT_PR_JSON = {**VALID_PR_JSON, "isDraft": True}

CLOSED_PR_JSON = {**VALID_PR_JSON, "state": "CLOSED"}

NOT_MAIN_PR_JSON = {**VALID_PR_JSON, "baseRefName": "develop"}

CONFLICTING_PR_JSON = {**VALID_PR_JSON, "mergeable": "CONFLICTING"}

EMPTY_SHA_PR_JSON = {**VALID_PR_JSON, "headRefOid": ""}

CI_PENDING = [{**VALID_CI_RUN[0], "status": "in_progress", "conclusion": ""}]

CI_FAILED = [{**VALID_CI_RUN[0], "conclusion": "failure"}]

CI_CANCELLED = [{**VALID_CI_RUN[0], "conclusion": "cancelled"}]

CI_EMPTY: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_gh_output(*stdouts: str) -> mock.MagicMock:
    """Return a mock for subprocess.run that returns *stdouts* in order."""

    def _run_factory():
        call_count = 0

        def _run(args, **_kwargs):
            nonlocal call_count
            if call_count < len(stdouts):
                result = mock.MagicMock()
                result.stdout = stdouts[call_count]
                result.returncode = 0
                call_count += 1
                return result
            raise RuntimeError(f"Unexpected gh call: {args}")

        return _run

    return mock.MagicMock(side_effect=_run_factory())


def _assert_fail(result: pp.PreflightResult, reason_contains: str = "") -> None:
    assert not result.passed, f"Expected FAIL but got PASS. Failures: {result.failures}"
    assert result.verdict() == "FAIL"
    if reason_contains:
        assert any(reason_contains in f for f in result.failures), (
            f"Expected failure containing '{reason_contains}', got: {result.failures}"
        )


def _assert_pass(result: pp.PreflightResult) -> None:
    assert result.passed, f"Expected PASS but got FAIL. Failures: {result.failures}"
    assert result.verdict() == "PASS"


# ---------------------------------------------------------------------------
# PrInfo.from_gh_json
# ---------------------------------------------------------------------------


def test_parses_valid_pr_json():
    info = pp.PrInfo.from_gh_json(_PR_NUM, VALID_PR_JSON)
    assert info.number == _PR_NUM
    assert info.title == "test(foo): add bar"
    assert info.state == "OPEN"
    assert not info.is_draft
    assert info.base_ref_name == "main"
    assert info.head_ref_oid == "abc1234567890def"
    assert info.mergeable == "MERGEABLE"


# ---------------------------------------------------------------------------
# Happy path: open PR + CI success => PASS
# ---------------------------------------------------------------------------


def test_open_pr_ci_success_passes():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_pass(result)


# ---------------------------------------------------------------------------
# Closed PR => FAIL
# ---------------------------------------------------------------------------


def test_closed_pr_fails():
    stdout1 = json.dumps(CLOSED_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="CLOSED")


# ---------------------------------------------------------------------------
# Draft PR => FAIL
# ---------------------------------------------------------------------------


def test_draft_pr_fails():
    stdout1 = json.dumps(DRAFT_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="draft")


# ---------------------------------------------------------------------------
# CI pending => FAIL
# ---------------------------------------------------------------------------


def test_ci_pending_fails():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(CI_PENDING)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="in_progress")


# ---------------------------------------------------------------------------
# CI failed => FAIL
# ---------------------------------------------------------------------------


def test_ci_failed_fails():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(CI_FAILED)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="failure")


# ---------------------------------------------------------------------------
# CI missing => FAIL
# ---------------------------------------------------------------------------


def test_ci_missing_fails():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(CI_EMPTY)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="not found")


def test_ci_gh_error_is_handled_as_missing():
    stdout1 = json.dumps(VALID_PR_JSON)
    with mock.patch(
        "subprocess.run",
        side_effect=[
            # First call (gh pr view) succeeds
            mock.MagicMock(stdout=stdout1, returncode=0),
            # Second call (gh run list) raises CalledProcessError
            subprocess.CalledProcessError(1, "gh"),
        ],
    ):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="not found")


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_wrong_base_branch_fails():
    stdout1 = json.dumps(NOT_MAIN_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="develop")


def test_conflicting_mergeable_fails():
    stdout1 = json.dumps(CONFLICTING_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="CONFLICTING")


def test_empty_head_sha_fails():
    stdout1 = json.dumps(EMPTY_SHA_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="SHA")


def test_ci_cancelled_fails():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(CI_CANCELLED)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        result = pp.evaluate(_PR_NUM)
    _assert_fail(result, reason_contains="cancelled")


# ---------------------------------------------------------------------------
# format_evidence
# ---------------------------------------------------------------------------


def test_format_text_pass():
    pr = pp.PrInfo.from_gh_json(_PR_NUM, VALID_PR_JSON)
    ci = pp.CiInfo(
        workflow_name="Production Gate",
        run_id="9876543210",
        status="completed",
        conclusion="success",
    )
    result = pp.PreflightResult(pr=pr, ci=ci, passed=True, failures=[])
    text = pp.format_evidence(result, as_json=False)
    assert "PASS" in text
    assert str(_PR_NUM) in text
    assert "test(foo)" in text
    assert "Production Gate" in text


def test_format_text_fail():
    pr = pp.PrInfo.from_gh_json(_PR_NUM, DRAFT_PR_JSON)
    ci = pp.CiInfo.empty()
    result = pp.PreflightResult(pr=pr, ci=ci, passed=False, failures=["PR is a draft"])
    text = pp.format_evidence(result, as_json=False)
    assert "FAIL" in text
    assert "draft" in text


def test_format_json_pass():
    pr = pp.PrInfo.from_gh_json(_PR_NUM, VALID_PR_JSON)
    ci = pp.CiInfo(
        workflow_name="Production Gate",
        run_id="9876543210",
        status="completed",
        conclusion="success",
    )
    result = pp.PreflightResult(pr=pr, ci=ci, passed=True, failures=[])
    data = json.loads(pp.format_evidence(result, as_json=True))
    assert data["verdict"] == "PASS"
    assert data["pr_number"] == _PR_NUM


def test_format_json_fail():
    pr = pp.PrInfo.from_gh_json(_PR_NUM, CLOSED_PR_JSON)
    ci = pp.CiInfo.empty()
    result = pp.PreflightResult(pr=pr, ci=ci, passed=False, failures=["PR state is 'CLOSED'"])
    data = json.loads(pp.format_evidence(result, as_json=True))
    assert data["verdict"] == "FAIL"
    assert len(data["failures"]) >= 1


# ---------------------------------------------------------------------------
# CLI subprocess test (script runs with --help in real process)
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
    assert "preflight" in result.stdout.lower()


def test_script_requires_pr_arg():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
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
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        exit_code = pp.main(["--pr", str(_PR_NUM)])
    assert exit_code == 0


def test_main_fail():
    stdout1 = json.dumps(CLOSED_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        exit_code = pp.main(["--pr", str(_PR_NUM)])
    assert exit_code == 1


def test_main_json_output():
    stdout1 = json.dumps(VALID_PR_JSON)
    stdout2 = json.dumps(VALID_CI_RUN)
    with mock.patch("subprocess.run", _mock_gh_output(stdout1, stdout2)):
        exit_code = pp.main(["--pr", str(_PR_NUM), "--json"])
    assert exit_code == 0
