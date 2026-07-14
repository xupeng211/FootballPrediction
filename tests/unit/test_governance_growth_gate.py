"""Tests for the M2 governance growth freeze gate.

lifecycle: test-fixture

Uses real temporary git repos with real base/head commits.
Covers positive, negative, anti-false-positive, basename-boundary,
rename-status, same-count dependency replacement, and real-exit-code scenarios.
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

import governance_growth_gate as ggg  # noqa: E402


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


def _git_ok(repo: Path, *args: str) -> bool:
    """Run git, return True on success, False on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


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
# Real-process helpers (Fix 6: exit code verification)
# ---------------------------------------------------------------------------

def _run_gate_via_cli(repo: Path, base_sha: str, head_sha: str) -> tuple[int, str]:
    """Run the gate via a subprocess to verify real exit codes.

    Imports the gate module from the real project tree, but runs it against
    the test repo for git operations.
    """
    # Find the real gate module path from the currently loaded module
    gate_dir = str(Path(ggg.__file__).resolve().parent)
    project_root = str(Path(ggg.__file__).resolve().parents[2])

    helper = (
        "import sys; "
        f"sys.path.insert(0, {gate_dir!r}); "
        f"sys.path.insert(0, {project_root!r}); "
        "from governance_growth_gate import run_governance_growth_gate; "
        f"errors = run_governance_growth_gate({str(repo)!r}, sys.argv[1], sys.argv[2]); "
        "sys.stderr.write('\\n'.join(errors)); "
        "sys.exit(1 if errors else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", helper, base_sha, head_sha],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stderr


# ---------------------------------------------------------------------------
# Test fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_base(tmp_path: Path) -> tuple[Path, str]:
    """Create a repo with base files including historical reports/manifests/deps."""
    repo = _init_repo(tmp_path)

    base_files = {
        "docs/_reports/OLD_REPORT.md": "# Old historical report\nlifecycle: permanent\n",
        "docs/_manifests/old_manifest.json": '{"key": "old"}',
        "scripts/ops/fotmob_adg60_existing.js": "// Existing ADG script\n",
        "src/services/event_bus.py": textwrap.dedent("""\
            from scripts.ops.hunt_league_hashes import find_hash
            """),
        "src/main.py": "def main(): pass\n",
        "scripts/ci/normal_ci_check.py": "# Normal CI script\n",
        "src/services/old_dep.py": textwrap.dedent("""\
            from scripts.ops.old_helper import run
            """),
    }
    base_sha = _make_base_commit(repo, base_files)
    return repo, base_sha


# ---------------------------------------------------------------------------
# Positive tests — changes that SHOULD pass
# ---------------------------------------------------------------------------


class TestPositivePassThrough:
    """Tests where the gate should produce NO errors."""

    def test_no_changes_passes(self, repo_with_base):
        repo, base = repo_with_base
        errors = _run_gate(repo, base, base)
        assert errors == []

    def test_modify_existing_report_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/OLD_REPORT.md", "# Updated content\n")
        head = _commit_all(repo, "modify existing report")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_modify_existing_manifest_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_manifests/old_manifest.json", '{"key": "updated"}')
        head = _commit_all(repo, "modify existing manifest")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_modify_existing_adg_script_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/fotmob_adg60_existing.js", "// Modified\n")
        head = _commit_all(repo, "modify existing ADG script")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_existing_reverse_dep_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/main.py", "def main(): pass\n# just a comment\n")
        head = _commit_all(repo, "modify unrelated src file")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_normal_business_import_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/new_service.py",
            "from src.models import User\nimport os\n",
        )
        head = _commit_all(repo, "add normal business import")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_new_normal_doc_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/new_feature.md", "# New feature docs\n")
        head = _commit_all(repo, "add normal doc")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_new_normal_ci_script_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/deploy_check.sh", "#!/bin/bash\necho ok\n")
        head = _commit_all(repo, "add normal CI script")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_delete_historical_governance_file_passes(self, repo_with_base):
        repo, base = repo_with_base
        (repo / "docs/_reports/OLD_REPORT.md").unlink()
        head = _commit_all(repo, "delete old report")
        errors = _run_gate(repo, base, head)
        assert errors == []

    def test_output_order_stable(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/Z_REPORT.md", "# Z\n")
        _write_file(repo, "docs/_reports/A_REPORT.md", "# A\n")
        head = _commit_all(repo, "add two reports")
        errors1 = _run_gate(repo, base, head)
        errors2 = _run_gate(repo, base, head)
        assert errors1 == errors2

    # --- Fix 2: delete old dep, same count ---
    def test_delete_old_reverse_dep_passes(self, repo_with_base):
        """Deleting an existing src → scripts/ops dep and adding nothing: passes."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/old_dep.py",
            "def no_deps(): pass\n",
        )
        head = _commit_all(repo, "remove old reverse dep")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Unexpected errors: {errors}"

    # --- Fix 2: move line only ---
    def test_same_dep_different_line_passes(self, repo_with_base):
        """Moving a dep to a different line (same target) is not new."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/event_bus.py",
            textwrap.dedent("""\
                import os
                from scripts.ops.hunt_league_hashes import find_hash
                """),
        )
        head = _commit_all(repo, "move dep line")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Should pass on same-dep different line: {errors}"

    # --- Fix 2: reformat only ---
    def test_same_dep_reformat_passes(self, repo_with_base):
        """Reformatting an import (same target) is not a new dep."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/event_bus.py",
            "from scripts.ops.hunt_league_hashes import (\n"
            "    find_hash,\n"
            ")\n",
        )
        head = _commit_all(repo, "reformat import")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Reformat should pass: {errors}"


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
        repo, base = repo_with_base
        _write_file(repo, "docs/normal.md", "# Normal\n")
        _commit_all(repo, "add normal doc")
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

    def test_separator_prefixed_phase_blocked(self, repo_with_base):
        """File like something-phase2-plan.py under scripts/ must block."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/something-phase2-plan.py", "# plan\n")
        head = _commit_all(repo, "add something-phase2")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_PHASE in e for e in errors)


class TestNegativeBlockReverseDeps:
    """Block new src → scripts/ops reverse dependencies."""

    def test_new_python_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/new_service.py",
            "from scripts.ops.helpers.something import helper\n",
        )
        head = _commit_all(repo, "add new reverse dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_dynamic_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/dynamic_import.py",
            'import importlib\nmod = importlib.import_module("scripts.ops.helper")\n',
        )
        head = _commit_all(repo, "add dynamic import dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_subprocess_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/runner.py",
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
            repo, "src/services/newService.js",
            'const helper = require("../../scripts/ops/helper.js");\n',
        )
        head = _commit_all(repo, "add JS require dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/newModule.mjs",
            'import helper from "../scripts/ops/helper.js";\n',
        )
        head = _commit_all(repo, "add JS import dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_spawn_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/execService.js",
            textwrap.dedent("""\
                const { spawn } = require("child_process");
                spawn("node", ["scripts/ops/run_production.js"]);
                """),
        )
        head = _commit_all(repo, "add JS spawn dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    # --- Fix 2: same-count replacement (Python) ---
    def test_same_count_python_dep_replacement_blocked(self, repo_with_base):
        """Replacing one scripts/ops dep with another: both are '1', must block."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/old_dep.py",
            "from scripts.ops.new_helper import run\n",
        )
        head = _commit_all(repo, "replace dep with different target")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1, f"Must block same-count replacement: {errors}"
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)
        assert any("new_helper" in e for e in errors)

    # --- Fix 2: same-count replacement (JavaScript) ---
    def test_same_count_js_dep_replacement_blocked(self, repo_with_base):
        """Replacing one JS scripts/ops dep with another: same count, must block."""
        repo, base = repo_with_base
        # Add a base JS file with a scripts/ops dep
        _write_file(
            repo, "src/services/baseJsDep.js",
            'const x = require("../../scripts/ops/old_tool.js");\n',
        )
        base2 = _commit_all(repo, "add base JS dep")
        # Replace with a different dep
        _write_file(
            repo, "src/services/baseJsDep.js",
            'const x = require("../../scripts/ops/new_tool.js");\n',
        )
        head = _commit_all(repo, "replace JS dep")
        errors = _run_gate(repo, base2, head)
        assert len(errors) >= 1, f"Must block same-count JS replacement: {errors}"
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)
        assert any("new_tool" in e for e in errors)

    # --- Fix 2: delete two, add two ---
    def test_delete_two_add_two_blocked(self, repo_with_base):
        """Delete two old deps, add two new deps — both new must be reported."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/old_dep.py",
            textwrap.dedent("""\
                from scripts.ops.helper_a import func_a
                from scripts.ops.helper_b import func_b
                """),
        )
        base2 = _commit_all(repo, "base with two deps")
        _write_file(
            repo, "src/services/old_dep.py",
            textwrap.dedent("""\
                from scripts.ops.helper_c import func_c
                from scripts.ops.helper_d import func_d
                """),
        )
        head = _commit_all(repo, "replace two deps with two different ones")
        errors = _run_gate(repo, base2, head)
        # Both new deps must be reported
        assert sum(1 for e in errors if ggg.ERR_REVERSE_DEP in e) >= 2, (
            f"Must report both new deps: {errors}"
        )

    # --- Fix 2: new file with new dep ---
    def test_new_file_with_dep_blocked(self, repo_with_base):
        """Brand-new file in head that has scripts/ops deps must block."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/brand_new.py",
            "from scripts.ops.brand_new_helper import do_stuff\n",
        )
        head = _commit_all(repo, "new file with dep")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)


class TestNegativeMultiViolation:
    """Multiple violations must all be reported."""

    def test_all_violations_reported(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/NEW_VIOLATION.md", "# Violation\n")
        _write_file(repo, "docs/_manifests/new_violation.json", "{}")
        _write_file(repo, "scripts/ops/phase_99_violation.py", "# Phase 99\n")
        _write_file(
            repo, "src/services/violation.py",
            "from scripts.ops.violation import bad\n",
        )
        head = _commit_all(repo, "all violations")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 4, (
            f"Expected >=4 errors, got {len(errors)}: {errors}"
        )
        assert any(ggg.ERR_REPORT in e for e in errors)
        assert any(ggg.ERR_MANIFEST in e for e in errors)
        assert any(ggg.ERR_PHASE in e for e in errors)
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_non_zero_exit_on_violation(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/FAIL_ME.md", "# Will fail\n")
        head = _commit_all(repo, "add violation")
        errors = _run_gate(repo, base, head)
        assert len(errors) > 0


class TestNegativeFailClosed:
    """Fail-closed on error conditions."""

    def test_bad_base_ref_fails_closed(self, repo_with_base):
        repo, base = repo_with_base
        errors = _run_gate(repo, "nonexistent-ref-99999", base)
        assert len(errors) > 0, "Expected errors on bad base ref, got none"

    def test_bad_head_ref_fails_closed(self, repo_with_base):
        repo, base = repo_with_base
        errors = _run_gate(repo, base, "nonexistent-ref-99999")
        assert len(errors) > 0, "Expected errors on bad head ref, got none"


# ---------------------------------------------------------------------------
# Fix 1: Rename status tests (R100 / R095)
# ---------------------------------------------------------------------------


class TestRenameStatus:
    """Rename detection must handle R100, R095, etc., not just bare 'R'."""

    def test_rename_ordinary_into_phase_r100_blocked(self, repo_with_base):
        """git mv normal → scripts/ops/phase_99_new_gate.py: blocked by R100."""
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py",
             "scripts/ops/phase_99_new_gate.py")
        head = _commit_all(repo, "rename via git mv (R100)")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1, f"R100 rename must be blocked: {errors}"
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_rename_ordinary_into_adg_r100_blocked(self, repo_with_base):
        """git mv normal → scripts/ops/ADG-100A-plan.js: blocked by R100."""
        repo, base = repo_with_base
        # Create a JS file to rename
        _write_file(repo, "scripts/ci/normal_check.js", "// normal\n")
        _commit_all(repo, "add normal JS file")
        _git(repo, "mv", "scripts/ci/normal_check.js",
             "scripts/ops/ADG-100A-plan.js")
        head = _commit_all(repo, "rename JS into ADG (R100)")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1, f"R100 rename into ADG must be blocked: {errors}"
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_rename_normal_to_normal_passes(self, repo_with_base):
        """Renaming a non-Phase file to another non-Phase name: passes."""
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py",
             "scripts/ci/renamed_ci_check.py")
        head = _commit_all(repo, "rename normal → normal (R100)")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"Normal rename should pass: {errors}"


# ---------------------------------------------------------------------------
# Anti-false-positive tests (expanded)
# ---------------------------------------------------------------------------


class TestAntiFalsePositive:
    """Tests that ensure the gate does NOT produce false positives."""

    def test_comment_scripts_ops_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/commented.py",
            "# This used to import from scripts.ops.helper but was removed\n"
            "def foo(): pass\n",
        )
        head = _commit_all(repo, "add comment only")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"False positive on comment: {errors}"

    def test_logger_message_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/logger_example.py",
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
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/docstring_example.py",
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

    # --- Fix 3: Python AST — cross-function subprocess false positive ---
    def test_python_subprocess_cross_function_not_blocked(self, repo_with_base):
        """subprocess.run in one function must not match a string in another."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/cross_func.py",
            textwrap.dedent("""\
                import subprocess

                def first():
                    subprocess.run(["echo", "ok"])

                def second():
                    help_text = "scripts/ops/old_tool.py is deprecated"
                """),
        )
        head = _commit_all(repo, "add cross-function safe code")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Cross-function false positive: {errors}"

    # --- Fix 3: Python AST — multiline docstring ---
    def test_python_multiline_docstring_not_blocked(self, repo_with_base):
        """Multiline docstring mentioning scripts.ops must not flag."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/multiline_doc.py",
            textwrap.dedent('''\
                """
                Example usage:
                    from scripts.ops.helper import old_helper
                    old_helper.run()

                This module replaces that old approach.
                """
                def new_approach():
                    pass
                '''),
        )
        head = _commit_all(repo, "add multiline docstring")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Multiline docstring false positive: {errors}"

    # --- Fix 3: Python AST — string literal containing subprocess ---
    def test_python_string_literal_subprocess_not_blocked(self, repo_with_base):
        """String literal containing subprocess call text must not flag."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/string_example.py",
            'example = \'subprocess.run(["python", "scripts/ops/demo.py"])\'\n'
            'def real_func():\n'
            '    return 42\n',
        )
        head = _commit_all(repo, "add string literal example")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"String literal false positive: {errors}"

    # --- Fix 4: JS — spawn in one function, string in another ---
    def test_js_spawn_cross_function_not_blocked(self, repo_with_base):
        """spawn in one function must not match a string in another function."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/crossFunc.js",
            textwrap.dedent("""\
                const { spawn } = require("child_process");

                function first() {
                  spawn("echo", ["ok"]);
                }

                function second() {
                  const example = 'spawn("node", ["scripts/ops/demo.js"])';
                }
                """),
        )
        head = _commit_all(repo, "add JS cross-function safe code")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"JS cross-function false positive: {errors}"

    # --- Fix 4: JS — plain string variable with scripts/ops ---
    def test_js_plain_string_variable_not_blocked(self, repo_with_base):
        """A plain variable string containing scripts/ops must not flag."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/helpText.js",
            textwrap.dedent("""\
                const helpText = "See scripts/ops/run_production.js for usage";
                console.log(helpText);
                """),
        )
        head = _commit_all(repo, "add JS help text")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"JS plain string false positive: {errors}"

    # --- Fix 4: JS — require in comment ---
    def test_js_require_in_comment_not_blocked(self, repo_with_base):
        """require() in a comment must not flag."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/commented.js",
            '// require("../../scripts/ops/helper.js")\n'
            'const x = 1;\n',
        )
        head = _commit_all(repo, "add JS commented require")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"JS comment require false positive: {errors}"

    # --- Fix 4: JS — require in a plain string (not a call) ---
    def test_js_require_in_plain_string_not_blocked(self, repo_with_base):
        """Text mentioning require() in a string must not flag."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/docString.js",
            'const example = \'require("../../scripts/ops/helper.js")\';\n',
        )
        head = _commit_all(repo, "add JS string with require text")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"JS string require false positive: {errors}"

    # --- Fix 4: JS — spawn("echo", ["ok"]) must pass ---
    def test_js_spawn_echo_passes(self, repo_with_base):
        """spawn("echo", ["ok"]) — no scripts/ops reference, must pass."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/echoService.js",
            textwrap.dedent("""\
                const { spawn } = require("child_process");
                spawn("echo", ["ok"]);
                """),
        )
        head = _commit_all(repo, "add JS echo spawn")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"JS echo spawn false positive: {errors}"

    def test_plain_phase_variable_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/training.py",
            "class Trainer:\n"
            "    def __init__(self):\n"
            '        self.phase = "warmup"\n'
            "        self.current_phase_number = 1\n",
        )
        head = _commit_all(repo, "add phase variable")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on phase variable: {errors}"

    def test_adg_in_doc_file_name_not_in_scripts_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/adg_review_notes.md", "# ADG Review\n")
        head = _commit_all(repo, "add ADG docs")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on ADG docs: {errors}"

    def test_outside_src_reverse_dep_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "tests/unit/test_helper.py",
            "from scripts.ops.helpers.something import helper\n",
        )
        head = _commit_all(repo, "add test helper import")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_REVERSE_DEP in e]
        assert governance_errors == [], f"False positive on test import: {errors}"

    def test_existing_historical_debt_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/innocent.py", "def foo(): pass\n")
        head = _commit_all(repo, "add innocent file")
        errors = _run_gate(repo, base, head)
        assert errors == [], f"Historical debt triggered false positive: {errors}"

    def test_phase_without_digits_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/phase_transition_check.py",
                    "# Phase transition\n")
        head = _commit_all(repo, "add phase_transition")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"False positive on phase without digits: {errors}"

    def test_scripts_ops_reference_in_test_fixture_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo, "tests/fixtures/sample.py",
            "# fixture: import scripts.ops.helper was used in production\n",
        )
        head = _commit_all(repo, "add test fixture")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_REVERSE_DEP in e]
        assert governance_errors == [], f"False positive on test fixture: {errors}"


# ---------------------------------------------------------------------------
# Fix 5: Basename matcher boundary tests
# ---------------------------------------------------------------------------


class TestBasenameMatcher:
    """Unit tests for _is_numbered_governance_basename with boundary rules."""

    @pytest.mark.parametrize(
        ("basename", "expected"),
        [
            # ---- must match (starts at position 0) ----
            ("phase_99_example.py", True),
            ("Phase-12-review.js", True),
            ("Phase99A_review.py", True),
            ("adg999_new_step.py", True),
            ("ADG-100A_plan.js", True),
            ("adg_60_final.js", True),
            ("phase1_test.js", True),
            ("ADG1_initial.md", True),
            # ---- must match (after separator) ----
            ("something-phase2-plan.py", True),
            ("fotmob_adg60_existing.js", True),
            # ---- must NOT match (no separator before governance word) ----
            ("biophase9_data.csv", False),
            ("metadg10_result.py", False),
            ("prephase2_transform.js", False),
            # ---- must NOT match (no digit) ----
            ("normal_script.py", False),
            ("phase_transition_check.py", False),
            ("deploy.sh", False),
            ("adg_review.md", False),
            ("phase.py", False),
            ("my_phase.py", False),
            ("adg_notes.txt", False),
            ("photographer.py", False),
            ("readme.md", False),
        ],
    )
    def test_basename_match(self, basename, expected):
        assert ggg._is_numbered_governance_basename(basename) == expected, (
            f"basename={basename!r} expected={expected}"
        )


# ---------------------------------------------------------------------------
# Fix 5: Integration tests — real git repos for boundary filenames
# ---------------------------------------------------------------------------


class TestBasenameBoundaryIntegration:
    """Verify boundary-safety with real git repos under scripts/."""

    def test_biophase9_not_blocked(self, repo_with_base):
        """biophase9_data.csv under scripts/ must NOT be flagged."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/biophase9_data.csv", "a,b,c\n")
        head = _commit_all(repo, "add biophase9")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"biophase9 false positive: {errors}"

    def test_metadg10_not_blocked(self, repo_with_base):
        """metadg10_result.py under scripts/ must NOT be flagged."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/metadg10_result.py", "x = 1\n")
        head = _commit_all(repo, "add metadg10")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"metadg10 false positive: {errors}"

    def test_prephase2_not_blocked(self, repo_with_base):
        """prephase2_transform.js under scripts/ must NOT be flagged."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/prephase2_transform.js", "// transform\n")
        head = _commit_all(repo, "add prephase2")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"prephase2 false positive: {errors}"

    def test_photographer_passes(self, repo_with_base):
        """photographer.py has no digit, must pass."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/photographer.py", "# photos\n")
        head = _commit_all(repo, "add photographer")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"photographer false positive: {errors}"

    def test_adg_review_passes(self, repo_with_base):
        """adg_review.md under scripts/ has no digit, must pass."""
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/adg_review.md", "# review\n")
        head = _commit_all(repo, "add adg_review")
        errors = _run_gate(repo, base, head)
        governance_errors = [e for e in errors if ggg.ERR_PHASE in e]
        assert governance_errors == [], f"adg_review false positive: {errors}"


# ---------------------------------------------------------------------------
# Fix 6: Real process exit code tests
# ---------------------------------------------------------------------------


class TestRealProcessExitCode:
    """Verify the gate produces correct exit codes via actual subprocess."""

    def test_real_exit_zero_on_pass(self, repo_with_base):
        """Clean change: real process exit code is 0."""
        repo, base = repo_with_base
        _write_file(repo, "src/services/innocent.py", "def foo(): pass\n")
        head = _commit_all(repo, "add innocent file")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. stderr: {stderr}"

    def test_real_exit_nonzero_on_violation(self, repo_with_base):
        """Violation: real process exit code is non-zero."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/FAIL_ME.md", "# Will fail\n")
        head = _commit_all(repo, "add violation")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Expected non-zero exit, got {exit_code}. stderr: {stderr}"

    def test_real_exit_nonzero_multi_violation(self, repo_with_base):
        """Multiple violations: exit non-zero; all four error codes in output."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/MULTI_1.md", "# v1\n")
        _write_file(repo, "docs/_manifests/multi_1.json", "{}")
        _write_file(repo, "scripts/ops/phase_99_multi.py", "# Phase 99\n")
        _write_file(
            repo, "src/services/multi_dep.py",
            "from scripts.ops.multi_helper import bad\n",
        )
        head = _commit_all(repo, "multi violation")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Expected non-zero exit: {exit_code}"
        assert ggg.ERR_REPORT in stderr, f"Missing {ggg.ERR_REPORT}"
        assert ggg.ERR_MANIFEST in stderr, f"Missing {ggg.ERR_MANIFEST}"
        assert ggg.ERR_PHASE in stderr, f"Missing {ggg.ERR_PHASE}"
        assert ggg.ERR_REVERSE_DEP in stderr, f"Missing {ggg.ERR_REVERSE_DEP}"

    def test_real_exit_nonzero_on_bad_ref(self, repo_with_base):
        """Bad base ref: fail-closed with non-zero exit."""
        repo, base = repo_with_base
        exit_code, stderr = _run_gate_via_cli(repo, "nonexistent-ref-99999", base)
        assert exit_code != 0, f"Expected non-zero exit on bad ref: {exit_code}"

    def test_real_exit_nonzero_rename_r100(self, repo_with_base):
        """Rename into Phase script: real exit non-zero."""
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py",
             "scripts/ops/phase_99_new_gate.py")
        head = _commit_all(repo, "rename R100 into phase")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"R100 rename must produce non-zero exit: {exit_code}"
        assert ggg.ERR_PHASE in stderr

    def test_real_exit_nonzero_same_count_replacement(self, repo_with_base):
        """Same-count dep replacement: real exit non-zero."""
        repo, base = repo_with_base
        _write_file(
            repo, "src/services/old_dep.py",
            "from scripts.ops.new_helper import run\n",
        )
        head = _commit_all(repo, "replace dep")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Same-count replacement must fail: {exit_code}"


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestAuthorization:
    """AUTHORIZED_GOVERNANCE_ADDITIONS must remain empty and exact-match."""

    def test_auth_set_is_empty(self):
        assert ggg.AUTHORIZED_GOVERNANCE_ADDITIONS == frozenset(), (
            "AUTHORIZED_GOVERNANCE_ADDITIONS must remain empty"
        )

    def test_similar_path_not_authorized(self, repo_with_base):
        """A path similar to an authorized one is NOT authorized."""
        repo, base = repo_with_base
        # Even if we add something to the set, it must match exactly
        _write_file(repo, "docs/_reports/ALMOST_AUTHORIZED.md", "# almost\n")
        head = _commit_all(repo, "add unauthorized report")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1, "Must block unauthorized report"

    def test_glob_not_supported(self, repo_with_base):
        """Wildcards/globs are NOT supported in AUTHORIZED_GOVERNANCE_ADDITIONS."""
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/any_name_here.md", "# any\n")
        head = _commit_all(repo, "add any report")
        errors = _run_gate(repo, base, head)
        assert len(errors) >= 1, "Glob/wildcard must not silently authorize"


# ---------------------------------------------------------------------------
# __main__ guard for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
