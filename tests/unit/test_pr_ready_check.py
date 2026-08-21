"""Tests for the canonical read-only PR readiness state check.

lifecycle: test-fixture

All GitHub/Git calls are mocked. No network, merge, database, or test runner
is invoked by the implementation under test.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/devops"))
import pr_ready_check as ready  # noqa: E402

HEAD = "a" * 40
OTHER_HEAD = "b" * 40
REPO = "xupeng211/FootballPrediction"


def _fake_commands(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
    *,
    local_head: str = HEAD,
    branch: str = "feature/example",
    dirty: str = "",
    required_checks: tuple[str, ...] = (
        "Environment / Proxy / Static / Unit Gate",
        "Docker Build Validation",
    ),
    check_status: str = "completed",
    check_conclusion: str = "success",
    check_head: str = HEAD,
) -> None:
    rules = [{"context": name} for name in required_checks]

    def fake_gh(args: list[str]) -> str:
        if args[:2] == ["repo", "view"]:
            return json.dumps({"nameWithOwner": REPO, "defaultBranchRef": {"name": "main"}})
        if args[:2] == ["pr", "view"]:
            return json.dumps(
                {
                    "title": "test: workflow change",
                    "state": "OPEN",
                    "isDraft": False,
                    "baseRefName": "main",
                    "headRefName": branch,
                    "headRefOid": HEAD,
                    "mergeable": "MERGEABLE",
                    "body": "## Summary\nworkflow change",
                }
            )
        if args[0] == "api" and args[1].split("?", 1)[0].endswith("/rulesets"):
            return json.dumps([[{"id": 7939844}]])
        if args[0] == "api" and args[1].split("?", 1)[0].endswith("/rulesets/7939844"):
            return json.dumps(
                {
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                    "rules": [
                        {
                            "type": "required_status_checks",
                            "parameters": {"required_status_checks": rules},
                        }
                    ],
                }
            )
        if args[0] == "api" and "check-runs" in args[1]:
            return json.dumps(
                [
                    {
                        "check_runs": [
                            {
                                "name": name,
                                "status": check_status,
                                "conclusion": check_conclusion,
                                "head_sha": check_head,
                            }
                            for name in required_checks
                        ]
                    }
                ]
            )
        raise AssertionError(f"unexpected gh command: {args}")

    def fake_git(args: list[str]) -> str:
        if args == ["branch", "--show-current"]:
            return branch
        if args == ["rev-parse", "HEAD"]:
            return local_head
        if args[:2] == ["status", "--porcelain=v1"]:
            return dirty
        raise AssertionError(f"unexpected git command: {args}")

    monkeypatch.setattr(ready, "run_gh", fake_gh)
    monkeypatch.setattr(ready, "run_git", fake_git)


def test_current_clean_feature_head_and_required_checks_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_commands(monkeypatch)

    result = ready.evaluate(1866)

    assert result.passed
    assert result.verdict == "PASS"
    assert result.local.head_sha == HEAD
    assert all(finding.passed for finding in result.findings)


def test_local_source_change_makes_readiness_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch, dirty=" M src/example.js")

    result = ready.evaluate(1866)

    assert not result.passed
    assert any(
        finding.name == "worktree-clean" and not finding.passed for finding in result.findings
    )


def test_local_head_must_match_current_pr_head(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch, local_head=OTHER_HEAD)

    result = ready.evaluate(1866)

    assert not result.passed
    finding = next(item for item in result.findings if item.name == "local-head-matches-pr-head")
    assert not finding.passed


def test_short_sha_is_not_a_valid_authority_value() -> None:
    assert not ready._is_full_sha(HEAD[:7])
    assert ready._is_full_sha(HEAD)


def test_required_check_for_wrong_head_cannot_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch, check_head=OTHER_HEAD)

    result = ready.evaluate(1866)

    assert not result.passed
    assert any(
        name.startswith("required-check:") and not passed
        for name, passed in ((f.name, f.passed) for f in result.findings)
    )


def test_required_check_failure_cannot_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch, check_conclusion="failure")

    result = ready.evaluate(1866)

    assert not result.passed
    assert any(
        not finding.passed
        for finding in result.findings
        if finding.name.startswith("required-check:")
    )


def test_missing_ruleset_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch)

    def no_ruleset(args: list[str]) -> str:
        if args[:2] == ["repo", "view"]:
            return json.dumps({"nameWithOwner": REPO, "defaultBranchRef": {"name": "main"}})
        if args[:2] == ["pr", "view"]:
            return json.dumps({"headRefOid": HEAD})
        if args[0] == "api" and args[1].split("?", 1)[0].endswith("/rulesets"):
            return json.dumps([[]])
        raise AssertionError(args)

    monkeypatch.setattr(ready, "run_gh", no_ruleset)
    with pytest.raises(ready.PreflightError, match="required status checks"):
        ready.evaluate(1866)


def test_json_output_contains_exact_head_and_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_commands(monkeypatch)

    data = json.loads(ready.format_json(ready.evaluate(1866)))

    assert data["verdict"] == "PASS"
    assert data["pr"]["head_sha"] == HEAD
    assert data["local"]["head_sha"] == HEAD
    assert data["required_checks"]
    assert data["findings"]


def test_cli_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/devops/pr_ready_check.py"), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "read-only PR ready" in result.stdout
