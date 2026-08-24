"""Tests for the documentation governance checker.

lifecycle: test-fixture
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/ops/documentation_governance_check.py"
GOVERNANCE = ROOT / "docs/DOCUMENTATION_GOVERNANCE.md"
AGENTS = ROOT / "AGENTS.md"
WORKFLOW = ROOT / "docs/AGENT_WORKFLOW.md"
AUDIT = ROOT / "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md"
AGENT_CONFIG_FILES = (
    ROOT / ".claude/settings.json",
    ROOT / ".claude/settings.local.json",
    ROOT / ".claude/mcp-config.json",
)
sys.path.insert(0, str(ROOT / "scripts/ops"))
import documentation_governance_check as checker  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_checker_exists():
    assert CHECKER.exists()


def test_governance_doc_exists():
    assert GOVERNANCE.exists()


def test_agents_workflow_docs_exist():
    assert AGENTS.exists()
    assert WORKFLOW.exists()


def test_audit_report_exists():
    assert AUDIT.exists()


def test_governance_doc_contains_required_sections():
    text = _read(GOVERNANCE)
    for section in checker.GOVERNANCE_SECTIONS:
        assert section in text


def test_canonical_workflow_docs_contain_required_sections():
    for path, sections in checker.WORKFLOW_SECTIONS.items():
        text = _read(ROOT / path)
        for section in sections:
            assert section in text


def test_audit_report_contains_required_sections():
    text = _read(AUDIT)
    for section in checker.AUDIT_SECTIONS:
        assert section in text


def test_no_manifest_created():
    added = checker.added_paths(checker.collect_changes())
    assert not any(path.startswith("docs/_manifests/") for path in added)


def test_no_next_plan_created():
    added = checker.added_paths(checker.collect_changes())
    assert not any("next_plan" in path.lower() or "next-plan" in path.lower() for path in added)


def test_no_review_report_created():
    added = checker.added_paths(checker.collect_changes())
    assert not any(path.startswith("docs/_reports/") and "review" in path.lower() for path in added)


def test_no_decision_report_created():
    added = checker.added_paths(checker.collect_changes())
    assert not any(
        path.startswith("docs/_reports/") and "decision" in path.lower() for path in added
    )


def test_file_budget_at_most_five():
    added = checker.added_paths(checker.collect_changes())
    assert len(added) <= checker.MAX_ADDED_FILES


def test_allowlists_use_exact_paths_without_wildcards():
    assert not any(
        any(char in path for char in checker.WILDCARD_CHARS)
        for path in checker.iter_allowlist_paths()
    )


def test_allowlists_do_not_allow_broad_reports_or_archive_paths():
    added = checker.ALLOWED_ADDED
    assert not any(path.startswith("docs/_archive/") for path in checker.iter_allowlist_paths())
    assert not any(path.startswith("docs/_manifests/") for path in added)
    assert not any("next_plan" in path.lower() or "next-plan" in path.lower() for path in added)
    assert not any(path.startswith("docs/_reports/") and "review" in path.lower() for path in added)
    assert not any(
        path.startswith("docs/_reports/") and "decision" in path.lower() for path in added
    )


def test_pull_request_template_is_allowed_when_present():
    template = ROOT / ".github/pull_request_template.md"
    if template.exists():
        assert ".github/pull_request_template.md" in checker.ALLOWED_CHANGED


def test_test_debt_audit_report_is_exact_path_allowed():
    expected = "docs/_reports/TEST_DEBT_AUDIT_NO_RUNTIME_CHANGE.md"
    assert frozenset({expected}) == checker.TEST_DEBT_AUDIT_ALLOWED_ADDED
    assert expected in checker.ALLOWED_ADDED


def test_destructive_actions_forbidden():
    changes = checker.collect_changes()
    assert not any(
        change.status == "D" and change.path not in checker.ALLOWED_DELETED for change in changes
    )
    assert not any(change.status == "R" for change in changes)
    assert not any(change.path.startswith("docs/_archive/") for change in changes)


def test_checker_passes():
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_agents_and_claude_md_in_source_of_truth_allowlist():
    """AGENTS.md and CLAUDE.md are permanent source-of-truth instruction files."""
    assert "AGENTS.md" in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED
    assert "CLAUDE.md" in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED


def test_retired_agent_skill_paths_are_exact_delete_allowlist_entries():
    expected = {
        ".claude/skills/api-testing/SKILL.md",
        ".claude/skills/data-collection/SKILL.md",
        ".claude/skills/data-engineering/SKILL.md",
        ".claude/skills/data-engineering/README.md",
        ".claude/skills/database-operations/SKILL.md",
        ".claude/skills/deployment-management/SKILL.md",
        ".claude/skills/deployment-operations/SKILL.md",
        ".claude/skills/docker-devops/SKILL.md",
        ".claude/skills/football-prediction/SKILL.md",
        ".claude/skills/feature-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/README.md",
        ".claude/skills/fastapi-development/SKILL.md",
        ".claude/skills/fastapi-development/README.md",
        ".claude/skills/performance-monitoring/SKILL.md",
        ".claude/skills/report-generation/SKILL.md",
        ".claude/skills/v26-harvest/SKILL.md",
    }

    assert expected <= checker.ALLOWED_DELETED
    assert not expected & checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED
    assert ".claude/skills/**" not in checker.ALLOWED_DELETED


def test_project_vision_is_a_source_of_truth_allowlist_entry():
    """The permanent North Star document may be updated as source-of-truth."""
    assert "docs/PROJECT_VISION.md" in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED


def test_no_wildcard_paths_in_source_of_truth_allowlist():
    """The source-of-truth allowlist uses exact paths, not wildcards."""
    assert "*.md" not in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED
    assert "package.json" in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED
    assert "package-lock.json" in checker.SOURCE_OF_TRUTH_ALLOWED_CHANGED


def test_agent_config_allowlist_uses_exact_paths():
    expected = {".claude/settings.json", ".claude/mcp-config.json"}
    assert expected == set(checker.AGENT_CONFIG_ALLOWED_CHANGED)
    assert not any("*" in path for path in checker.AGENT_CONFIG_ALLOWED_CHANGED)


def test_tracked_claude_configs_have_no_inline_userinfo_credentials():
    offenders = checker.scan_tracked_claude_config_credentials(ROOT)
    assert not offenders, "inline credential-like URI fields: " + ", ".join(offenders)


def test_claude_settings_retains_only_host_configuration_sections():
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["skills"]["enabled"] is False
    assert set(settings) <= {"skills", "mcpServers", "permissions"}
    assert not {"project", "environment", "tools"} & set(settings)


def test_claude_readme_fences_host_config_from_project_authority():
    text = _read(ROOT / ".claude/README.md")
    assert "不是项目授权" in text
    assert "不证明" in text
    assert "inline credential" in text
    assert "没有对应的 MCP loader" in text


def test_unexpected_paths_still_rejected():
    """Unknown governance file paths are still rejected."""
    errors: list[str] = []
    checker.validate_change_budget(
        [checker.Change("M", "UNEXPECTED_GOVERNANCE_FILE.md", None)],
        errors,
    )
    assert any("unexpected changed paths" in error for error in errors)
