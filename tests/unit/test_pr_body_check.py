"""Tests for the PR body and CI evidence check.

lifecycle: test-fixture

All tests use mocked GitHub/AI gate data unless they only exercise CLI argument parsing.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/devops/pr_body_check.py"
_PR_NUM = 1476
_HEAD_SHA = "abc1234567890defabc1234567890defabc12345"
_RUN_ID = "9876543210"

sys.path.insert(0, str(ROOT / "scripts/devops"))
import pr_body_check as pc  # noqa: E402


def _valid_body() -> str:
    return f"""## Summary
- governance-only
- no runtime code changed
- Head SHA: {_HEAD_SHA[:7]}
- Changed Files: 4
- Production Gate run id: {_RUN_ID}

## Scope
- PR body and CI evidence check tooling only.

## Documentation Impact
- docs/AGENT_WORKFLOW.md updated.

## Safety Impact
- no FotMob touched
- no DB touched
- no scraper touched

## Validation
- pytest: tests/unit/test_pr_body_check.py passed

## CI Gate Scope
- Production Gate run id: {_RUN_ID}

## No deletion / no move / no rename confirmation
- No deletion, move, or rename.

## Rollback Plan
- Revert this PR.

## Next Recommended Task
Do not start automatically.
Recommended next task only after user confirmation.
"""


def _pr(body: str | None = None) -> pc.PrInfo:
    return pc.PrInfo(
        number=_PR_NUM,
        title="chore: add PR body check",
        state="OPEN",
        head_sha=_HEAD_SHA,
        changed_files=4,
        body=_valid_body() if body is None else body,
    )


def _ci(
    *,
    run_id: str | None = _RUN_ID,
    status: str = "completed",
    conclusion: str = "success",
    head_sha: str = _HEAD_SHA,
) -> pc.CiInfo:
    return pc.CiInfo(
        workflow_name="Production Gate",
        run_id=run_id,
        status=status,
        conclusion=conclusion,
        head_sha=head_sha,
    )


AI_PASS = pc.AIWorkflowGateResult(
    passed=True,
    exit_code=0,
    summary="PASS: AI workflow gate checks passed",
)

AI_FAIL_REQUIRED_SECTION = pc.AIWorkflowGateResult(
    passed=False,
    exit_code=1,
    summary="FAIL: Missing required PR body sections: ## Scope",
)


def _run_with(
    pr: pc.PrInfo, ci: pc.CiInfo, ai_gate: pc.AIWorkflowGateResult = AI_PASS
) -> pc.PrBodyCheckResult:
    with (
        mock.patch.object(pc, "fetch_pr", return_value=pr),
        mock.patch.object(pc, "fetch_ci", return_value=ci),
        mock.patch.object(pc, "run_ai_workflow_gate", return_value=ai_gate),
    ):
        return pc.evaluate(_PR_NUM)


def _assert_pass(result: pc.PrBodyCheckResult) -> None:
    assert result.passed, f"Expected PASS but got FAIL. Failures: {result.failures}"
    assert result.verdict() == "PASS"


def _assert_fail(result: pc.PrBodyCheckResult, reason_contains: str) -> None:
    assert not result.passed, "Expected FAIL but got PASS"
    assert result.verdict() == "FAIL"
    assert any(reason_contains in failure for failure in result.failures), result.failures


def test_pr_body_passes() -> None:
    result = _run_with(_pr(), _ci())
    _assert_pass(result)


def test_pr_body_missing_required_section_fails() -> None:
    result = _run_with(_pr(), _ci(), ai_gate=AI_FAIL_REQUIRED_SECTION)
    _assert_fail(result, "Missing required PR body sections")


def test_pr_body_pending_evidence_fails() -> None:
    body = _valid_body() + "\nGitHub Production Gate | pending\n"
    result = _run_with(_pr(body), _ci())
    _assert_fail(result, "pending")


def test_pr_body_missing_current_head_sha_fails() -> None:
    body = _valid_body().replace(_HEAD_SHA[:7], "fffffff")
    result = _run_with(_pr(body), _ci())
    _assert_fail(result, _HEAD_SHA[:7])


def test_ci_run_not_found_fails() -> None:
    result = _run_with(_pr(), _ci(run_id=None, status="", conclusion="", head_sha=""))
    _assert_fail(result, "not found")


def test_ci_run_not_current_head_sha_fails() -> None:
    result = _run_with(_pr(), _ci(head_sha="deadbeef"))
    _assert_fail(result, "expected")


def test_ci_run_failure_fails() -> None:
    result = _run_with(_pr(), _ci(conclusion="failure"))
    _assert_fail(result, "failure")


def test_script_requires_pr_arg() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_script_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PR body" in result.stdout


def test_format_evidence_contains_required_output_fields() -> None:
    result = pc.PrBodyCheckResult(
        pr=_pr(),
        ci=_ci(),
        ai_gate=AI_PASS,
        passed=True,
        failures=[],
    )
    text = pc.format_evidence(result)
    assert f"PR Number:                    {_PR_NUM}" in text
    assert "PR Title:" in text
    assert _HEAD_SHA in text
    assert "Changed Files:                4" in text
    assert f"Production Gate Run ID:       {_RUN_ID}" in text
    assert "Production Gate Status:       completed" in text
    assert "Production Gate Conclusion:   success" in text
    assert "AI Workflow Gate Result:" in text
    assert "Final Verdict:                PASS" in text
