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
    assert result.returncode == 0, result.stdout + result.stderr
