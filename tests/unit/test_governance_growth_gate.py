"""Tests for the M2 governance growth freeze gate.

lifecycle: test-fixture

Uses real temporary git repos with real base/head commits.
Covers positive, negative, and anti-false-positive scenarios.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ci"))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

import governance_growth_gate as ggg  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    """Initialize a temporary git repo and return its path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.email", "gate-test@example.invalid")
    _git(repo, "config", "user.name", "Gov Growth Gate Tests")
    return repo


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _write_file(repo: Path, path: str, content: str) -> None:
    file_path = repo / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def _make_base_commit(repo: Path, files: dict[str, str]) -> str:
    """Create files and commit them as the base revision."""
    for path, content in files.items():
        _write_file(repo, path, content)
    return _commit_all(repo, "base commit")


def _run_gate(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    return ggg.run_governance_growth_gate(repo, base_sha, head_sha)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_base(tmp_path: Path) -> tuple[Path, str]:
    """Create a repo with base files including historical reports/manifests/deps."""
    repo = _init_repo(tmp_path)

    base_files = {
        # Historical report and manifest (should be allowed)
        "docs/_reports/OLD_REPORT.md": "# Old historical report\nlifecycle: permanent\n",
        "docs/_manifests/old_manifest.json": '{"key": "old"}',
        # Historical ADG scripts (should be allowed)
        "scripts/ops/fotmob_adg60_existing.js": "// Existing ADG script\n",
        # Historical src -> scripts/ops dependency (should be allowed)
        "src/services/event_bus.py": textwrap.dedent("""\
            from scripts.ops.hunt_league_hashes import find_hash
            """),
        # Normal business files
        "src/main.py": "def main(): pass\n",
        "scripts/ci/normal_ci_check.py": "# Normal CI script\n",
    }
    base_sha = _make_base_commit(repo, base_files)
    return repo, base_sha


# ---------------------------------------------------------------------------
# Positive tests — changes that SHOULD pass
# ---------------------------------------------------------------------------


class TestPositivePassThrough:
    """Tests where the gate should produce NO errors."""

    def test_no_changes_passes(self, repo_with_base):
        """Base == head (no changes): passes."""
        repo, base = repo_with_base
        errors = _run_gate(repo, base, base)
        assert errors == []

    def test_modify_existing_report_passes(self, repo_with_base):
        """Modifying an existing report: passes."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/OLD_REPORT.md", "# Updated content\n")
        head = _commit_all(repo, "modify existing report")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_modify_existing_manifest_passes(self, repo_with_base):
        """Modifying an existing manifest: passes."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_manifests/old_manifest.json", '{"key": "updated"}')
        head = _commit_all(repo, "modify existing manifest")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_modify_existing_adg_script_passes(self, repo_with_base):
        """Modifying an existing ADG script: passes."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/fotmob_adg60_existing.js", "// Modified\n")
        head = _commit_all(repo, "modify existing ADG script")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_existing_reverse_dep_passes(self, repo_with_base):
        """Base has src → scripts/ops dep, head doesn't add new ones: passes."""
        repo, base = repo_with_base
        _write_file(repo, "src/main.py", "def main(): pass\n# just a comment\n")
        head = _commit_all(repo, "modify unrelated src file")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_normal_business_import_passes(self, repo_with_base):
        """Normal src business imports: passes."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/new_service.py",
            "from src.models import User\nimport os\n",
        )
        head = _commit_all(repo, "add normal business import")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_new_normal_doc_passes(self, repo_with_base):
        """New documentation outside _reports/_manifests: passes."""
        repo, base = repo_with_base
        _write_file(repo, "docs/new_feature.md", "# New feature docs\n")
        head = _commit_all(repo, "add normal doc")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_new_normal_ci_script_passes(self, repo_with_base):
        """New CI script without Phase/ADG numbering: passes."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/deploy_check.sh", "#!/bin/bash\necho ok\n")
        head = _commit_all(repo, "add normal CI script")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_delete_historical_governance_file_passes(self, repo_with_base):
        """Deleting a historical governance file: passes."""
        repo, base = repo_with_base
        (repo / "docs/_reports/OLD_REPORT.md").unlink()
        head = _commit_all(repo, "delete old report")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_output_order_stable(self, repo_with_base):
        """Error output order is stable across runs."""
        repo, base = repo_with_base
        # Add two new reports
        _write_file(repo, "docs/_reports/Z_REPORT.md", "# Z\n")
        _write_file(repo, "docs/_reports/A_REPORT.md", "# A\n")
        head = _commit_all(repo, "add two reports")
        errors1 = _run_gate(repo, base, head)
        errors2 = _run_gate(repo, base, head)
        assert errors1 == errors2


# ---------------------------------------------------------------------------
# Negative tests — changes that MUST fail
# ---------------------------------------------------------------------------


class TestNegativeBlockNewReports:
    """Block new reports under docs/_reports/."""

    def test_new_report_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/NEW_REPORT.md", "# New\n")
        head = _commit_all(repo, "add new report")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REPORT in e for e in errors)
        assert any("NEW_REPORT.md" in e for e in errors)

    def test_new_manifest_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_manifests/new_manifest.json", "{}")
        head = _commit_all(repo, "add new manifest")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_MANIFEST in e for e in errors)

    def test_rename_into_reports_blocked(self, repo_with_base):
        """Renaming a normal file into docs/_reports/: blocked."""
        repo, base = repo_with_base
        # Create a normal file first
        _write_file(repo, "docs/normal.md", "# Normal\n")
        _commit_all(repo, "add normal doc")
        # Rename it into _reports
        _git(repo, "mv", "docs/normal.md", "docs/_reports/renamed_in.md")
        head = _commit_all(repo, "rename into reports")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REPORT in e for e in errors)


class TestNegativeBlockNumberedScripts:
    """Block new Phase/ADG numbered governance scripts."""

    def test_new_phase_99_underscore_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/phase_99_example.py", "# Phase 99\n")
        head = _commit_all(repo, "add phase_99")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_phase_99_dash_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/Phase-12-review.js", "// Phase 12\n")
        head = _commit_all(repo, "add Phase-12")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_phase99a_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/Phase99A_review.py", "# Phase 99A\n")
        head = _commit_all(repo, "add Phase99A")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_adg999_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/adg999_new_step.py", "# ADG 999\n")
        head = _commit_all(repo, "add adg999")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_adg_100a_dash_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/ADG-100A_plan.js", "// ADG-100A\n")
        head = _commit_all(repo, "add ADG-100A")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)


class TestNegativeBlockReverseDeps:
    """Block new src → scripts/ops reverse dependencies."""

    def test_new_python_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/new_service.py",
            "from scripts.ops.helpers.something import helper\n",
        )
        head = _commit_all(repo, "add new reverse dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_dynamic_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/dynamic_import.py",
            'import importlib\nmod = importlib.import_module("scripts.ops.helper")\n',
        )
        head = _commit_all(repo, "add dynamic import dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_subprocess_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/runner.py",
            textwrap.dedent("""\
                import subprocess
                subprocess.run(["python3", "scripts/ops/some_script.py"])
                """),
        )
        head = _commit_all(repo, "add subprocess dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_require_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/newService.js",
            'const helper = require("../../scripts/ops/helper.js");\n',
        )
        head = _commit_all(repo, "add JS require dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/newModule.mjs",
            'import helper from "../scripts/ops/helper.js";\n',
        )
        head = _commit_all(repo, "add JS import dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_spawn_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/execService.js",
            textwrap.dedent("""\
                const { spawn } = require("child_process");
                spawn("node", ["scripts/ops/run_production.js"]);
                """),
        )
        head = _commit_all(repo, "add JS spawn dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)


class TestNegativeMultiViolation:
    """Multiple violations must all be reported."""

    def test_all_violations_reported(self, repo_with_base):
        repo, base = repo_with_base
        # Report
        _write_file(repo, "docs/_reports/NEW_VIOLATION.md", "# Violation\n")
        # Manifest
        _write_file(repo, "docs/_manifests/new_violation.json", "{}")
        # Phase script
        _write_file(repo, "scripts/ops/phase_99_violation.py", "# Phase 99\n")
        # Reverse dep
        _write_file(
            repo,
            "src/services/violation.py",
            "from scripts.ops.violation import bad\n",
        )
        head = _commit_all(repo, "all violations")
        errors = _run_gate(repo, base, head)
        _min_expected_violations = 4
        assert len(errors) >= _min_expected_violations, (
            f"Expected >={_min_expected_violations} errors, got {len(errors)}: {errors}"
        )
        assert any(ggg.ERR_REPORT in e for e in errors)
        assert any(ggg.ERR_MANIFEST in e for e in errors)
        assert any(ggg.ERR_PHASE in e for e in errors)
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_non_zero_exit_on_violation(self, repo_with_base):
        """Gate with violations must produce non-empty errors list."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/FAIL_ME.md", "# Will fail\n")
        head = _commit_all(repo, "add violation")
        errors = _run_gate(repo, base, head)
        assert len(errors) > 0


class TestNegativeFailClosed:
    """Fail-closed on error conditions — gate returns errors, not exceptions."""

    def test_bad_base_ref_fails_closed(self, repo_with_base):
        """Invalid base ref should produce errors (fail-closed)."""
        repo, base = repo_with_base
        errors = _run_gate(repo, "nonexistent-ref-99999", base)
        assert len(errors) > 0, "Expected errors on bad base ref, got none"

    def test_bad_head_ref_fails_closed(self, repo_with_base):
        """Invalid head ref should produce errors (fail-closed)."""
        repo, base = repo_with_base
        errors = _run_gate(repo, base, "nonexistent-ref-99999")
        assert len(errors) > 0, "Expected errors on bad head ref, got none"


# ---------------------------------------------------------------------------
# Anti-false-positive tests
# ---------------------------------------------------------------------------


class TestAntiFalsePositive:
    """Tests that ensure the gate does NOT produce false positives."""

    def test_comment_scripts_ops_not_blocked(self, repo_with_base):
        """Comment mentioning scripts/ops is not a dependency."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/commented.py",
            "# This used to import from scripts.ops.helper but was removed\ndef foo(): pass\n",
        )
        head = _commit_all(repo, "add comment only")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"False positive on comment: {errors}"

    def test_logger_message_not_blocked(self, repo_with_base):
        """Logger message mentioning scripts/ops is not a dependency."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/logger_example.py",
            textwrap.dedent("""\
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Please use scripts/ops/run_production.js for this task")
                """),
        )
        head = _commit_all(repo, "add logger message")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"False positive on logger: {errors}"

    def test_docstring_scripts_ops_not_blocked(self, repo_with_base):
        """Docstring mentioning scripts/ops is not a dependency."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/docstring_example.py",
            textwrap.dedent('''\
                """Module for handling data.

                Previously used scripts.ops.helper for processing.
                Now uses internal implementation.
                """
                def process(): pass
                '''),
        )
        head = _commit_all(repo, "add docstring")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"False positive on docstring: {errors}"

    def test_plain_phase_variable_not_blocked(self, repo_with_base):
        """Variable named 'phase' in business code is not a governance script."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/training.py",
            "class Trainer:\n"
            "    def __init__(self):\n"
            '        self.phase = "warmup"\n'
            "        self.current_phase_number = 1\n",
        )
        head = _commit_all(repo, "add phase variable")
        errors = _run_gate(repo, base, head)
        # No errors from governance gate — this doesn't create a new file
        # with phase in the basename under scripts/
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on phase variable: {errors}"

    def test_adg_in_doc_file_name_not_in_scripts_not_blocked(self, repo_with_base):
        """ADG in docs/ filename is not a scripts/ governance script."""
        repo, base = repo_with_base
        _write_file(repo, "docs/adg_review_notes.md", "# ADG Review\n")
        head = _commit_all(repo, "add ADG docs")
        errors = _run_gate(repo, base, head)
        # The file is not under scripts/, so it should not trigger
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on ADG docs: {errors}"

    def test_outside_src_reverse_dep_not_blocked(self, repo_with_base):
        """scripts/ops import from outside src/ is not a business reverse dep."""
        repo, base = repo_with_base
        # This file is in tests/, not src/
        _write_file(
            repo,
            "tests/unit/test_helper.py",
            "from scripts.ops.helpers.something import helper\n",
        )
        head = _commit_all(repo, "add test helper import")
        errors = _run_gate(repo, base, head)
        # No REVERSE_DEP errors — the check only scans src/
        governance_errors = [e for e in errors if ggg.ERR_REVERSE_DEP in e]
        assert governance_errors == [], f"False positive on test import: {errors}"

    def test_existing_historical_debt_not_blocked(self, repo_with_base):
        """Historical reports/manifests/deps in base are not blocked."""
        repo, base = repo_with_base
        # Add a new normal file — should not trigger any governance errors
        _write_file(repo, "src/services/innocent.py", "def foo(): pass\n")
        head = _commit_all(repo, "add innocent file")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Historical debt triggered false positive: {errors}"

    def test_phase_without_digits_not_blocked(self, repo_with_base):
        """File named 'phase' without digits is not a numbered governance script."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/phase_transition_check.py", "# Phase transition\n")
        head = _commit_all(repo, "add phase_transition")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on phase without digits: {errors}"

    def test_scripts_ops_reference_in_test_fixture_not_blocked(self, repo_with_base):
        """Reference to scripts/ops in a test file outside src/ is not blocked."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "tests/fixtures/sample.py",
            "# fixture: import scripts.ops.helper was used in production\n",
        )
        head = _commit_all(repo, "add test fixture")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_REVERSE_DEP in e]
        assert governance_errors == [], f"False positive on test fixture: {errors}"


# ---------------------------------------------------------------------------
# Unit tests for the basename matcher
# ---------------------------------------------------------------------------


class TestBasenameMatcher:
    """Unit tests for _is_numbered_governance_basename."""

    @pytest.mark.parametrize(
        ("basename", "expected"),
        [
            ("phase_99_example.py", True),
            ("Phase-12-review.js", True),
            ("Phase99A_review.py", True),
            ("adg999_new_step.py", True),
            ("ADG-100A_plan.js", True),
            ("adg_60_final.js", True),
            ("phase1_test.js", True),
            ("ADG1_initial.md", True),
            # Should NOT match
            ("normal_script.py", False),
            ("phase_transition_check.py", False),  # no digit adjacent
            ("deploy.sh", False),
            ("adg_review.md", False),  # no digit
            ("phase.py", False),  # no digit
            ("my_phase.py", False),  # no digit
            ("adg_notes.txt", False),  # no digit
            ("photographer.py", False),
            ("readme.md", False),
        ],
    )
    def test_basename_match(self, basename, expected):
        assert ggg._is_numbered_governance_basename(basename) == expected
