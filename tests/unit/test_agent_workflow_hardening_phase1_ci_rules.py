"""Tests for the WF01 workflow-authority convergence contract.

lifecycle: test-fixture

These tests intentionally validate the current authority layout rather than
the retired multi-document hardening checklist.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))
import ai_workflow_gate as gate  # noqa: E402


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _canonical_body() -> str:
    return """## Summary

Converge the workflow authority without changing business behavior.

## Scope

| Task type | workflow-governance |
| Changed paths | AGENTS.md, docs/AGENT_WORKFLOW.md |
| Runtime behavior changed | no |

## Tests

The governance unit suite passed with 167 tests and exit code 0.

## Risk

No live fetch, DB write, raw write, training, model activation, or migration apply.

## Rollback

Revert this commit; no runtime or schema state was changed.

Do not start automatically.
Recommended next task only after user confirmation.
"""


def test_canonical_pr_body_contract_passes():
    body = _canonical_body()
    assert gate.check_required_sections(body) == []
    assert gate.check_next_task_stop_phrase(body) == []


def test_canonical_pr_body_missing_tests_and_risk_fails():
    body = _canonical_body().replace("## Tests", "## Removed").replace("## Risk", "## Removed")
    missing = gate.check_required_sections(body)
    assert "## Tests" in missing
    assert "## Risk" in missing


def test_agents_is_operational_authority():
    body = _read("AGENTS.md")
    for phrase in (
        "唯一的 operational workflow authority",
        "NORMAL",
        "STRICT",
        "make verify-targeted",
        "make verify-pr",
        "make verify-strict",
        "exact-head",
        "main Production Gate",
        "DONE",
    ):
        assert phrase in body, f"AGENTS.md missing canonical workflow phrase: {phrase}"


def test_detailed_workflow_points_back_to_agents():
    body = _read("docs/AGENT_WORKFLOW.md")
    assert "AGENTS.md" in body
    assert "唯一 operational authority" in body
    for authority in ("TEST", "CI", "REVIEW", "OWNER"):
        assert authority in body


def test_claude_is_a_pointer_not_a_parallel_workflow():
    body = _read("CLAUDE.md")
    assert "AGENTS.md" in body
    assert "docs/AGENT_WORKFLOW.md" in body
    assert "Claude-specific" in body
    assert "required CI" in body


def test_pr_template_has_only_canonical_default_sections():
    body = _read(".github/pull_request_template.md")
    for heading in ("## Summary", "## Scope", "## Tests", "## Risk", "## Rollback"):
        assert heading in body
    for retired in (
        "## Documentation Impact",
        "## Safety Impact",
        "## Next Recommended Task",
        "Agent Workflow Hardening Checklist",
    ):
        assert retired not in body


def test_duplicate_pr_template_is_removed():
    assert not (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").exists()


def test_legacy_workflow_docs_are_explicitly_non_authoritative():
    for path in (
        "docs/CODEX_WORKFLOW.md",
        "docs/AI_AGENT_WORKFLOW_HARDENING.md",
        "docs/engineering/AI_AGENT_WORKFLOW.md",
        "docs/WORKFLOW_TOOLCHAIN_INVENTORY.md",
    ):
        body = _read(path)
        assert "not" in body.lower(), path
        assert "authority" in body.lower(), path
        assert "AGENTS.md" in body, path


def test_contributing_states_observed_merge_policy_boundary():
    body = _read("CONTRIBUTING.md")
    assert "Squash Merge" in body
    assert "ruleset" in body
    assert "main Production Gate" in body


def test_makefile_keeps_safe_github_check_observer():
    body = _read("Makefile")
    assert "watch-pr:" in body
    assert "gh pr checks" in body
