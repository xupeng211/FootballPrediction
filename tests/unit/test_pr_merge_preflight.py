"""Compatibility contract for the retired merge preflight.

lifecycle: test-fixture
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_merge_preflight_delegates_to_canonical_ready_check() -> None:
    source = (ROOT / "scripts/devops/pr_merge_preflight.py").read_text(encoding="utf-8")
    assert "from scripts.devops.pr_ready_check import main" in source
    assert "second authority" in source
