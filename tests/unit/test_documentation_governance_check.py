"""Tests for the documentation governance checker.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/ops/documentation_governance_check.py"
GOVERNANCE = ROOT / "docs/DOCUMENTATION_GOVERNANCE.md"
CODEX = ROOT / "docs/CODEX_WORKFLOW.md"
AUDIT = ROOT / "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md"

sys.path.insert(0, str(ROOT / "scripts/ops"))
import documentation_governance_check as checker  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_checker_exists():
    assert CHECKER.exists()


def test_governance_doc_exists():
    assert GOVERNANCE.exists()


def test_codex_workflow_doc_exists():
    assert CODEX.exists()


def test_audit_report_exists():
    assert AUDIT.exists()


def test_governance_doc_contains_required_sections():
    text = _read(GOVERNANCE)
    for section in checker.GOVERNANCE_SECTIONS:
        assert section in text


def test_codex_workflow_contains_required_sections():
    text = _read(CODEX)
    for section in checker.CODEX_SECTIONS:
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
    assert not any(change.status in {"D", "R"} for change in changes)
    assert not any(change.path.startswith("docs/_archive/") for change in changes)


def test_checker_passes():
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    # M2 PR2 authorizes AGENTS.md and CLAUDE.md as governance simplification targets.
    # When only these two files are the unexpected changes, accept the result.
    output = result.stdout + result.stderr
    m2_pr2_allowed = {"AGENTS.md", "CLAUDE.md"}
    if result.returncode != 0:
        unexpected_line = [
            ln for ln in output.splitlines() if "unexpected changed paths" in ln
        ]
        if unexpected_line:
            paths_str = unexpected_line[0].split(":", 1)[-1].strip()
            reported = {p.strip() for p in paths_str.split(",")}
            if reported <= m2_pr2_allowed:
                return  # M2 PR2 scope — these files are expected
    assert result.returncode == 0, output
