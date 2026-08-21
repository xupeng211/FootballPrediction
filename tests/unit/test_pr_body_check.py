"""Compatibility contract for the retired PR body checker.

lifecycle: test-fixture
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_body_checker_delegates_to_canonical_ready_check() -> None:
    source = (ROOT / "scripts/devops/pr_body_check.py").read_text(encoding="utf-8")
    assert "from scripts.devops.pr_ready_check import main" in source
    assert "workflow state" in source
