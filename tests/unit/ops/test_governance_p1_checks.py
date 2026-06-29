"""Tests for TECHDEBT-G2 P1 governance checks.

lifecycle: test-fixture

Covers:
- P1-1: check_no_archive_runtime_import
- P1-2: check_dangerous_auth_path_cross_validation
- P1-3: check_script_lifecycle_requirement
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import scripts.ops.helpers.governance_p1_checks as _p1_mod  # noqa: E402
from scripts.ops.helpers.governance_p1_checks import (  # noqa: E402
    check_dangerous_auth_path_cross_validation,
    check_no_archive_runtime_import,
    check_script_lifecycle_requirement,
)

# ============================================================================
# Helpers
# ============================================================================


@contextmanager
def _temp_root(tmpdir: str):
    """Temporarily override _p1_mod.ROOT to point to *tmpdir*."""
    old_root = _p1_mod.ROOT
    try:
        _p1_mod.ROOT = Path(tmpdir)
        yield
    finally:
        _p1_mod.ROOT = old_root


def _mkfile(tmpdir: str, relpath: str, content: str) -> None:
    """Create a file under *tmpdir* with *relpath* and *content*."""
    full = Path(tmpdir) / relpath
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


# ============================================================================
# P1-1: check_no_archive_runtime_import
# ============================================================================


class TestNoArchiveRuntimeImport:
    """P1-1: Prevent active runtime code from importing archive code."""

    def test_docs_file_with_archive_reference_passes(self):
        """docs/ file mentioning archive_vault_2026 is exempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "docs/guide.md", "See archive_vault_2026 for old code.")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import({"docs/guide.md"})
                assert len(errors) == 0, f"docs/ should be exempt, got: {errors}"

    def test_tests_file_with_archive_reference_report_only(self):
        """tests/ file referencing archive code is report-only, not blocking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "tests/unit/test_thing.py",
                    "from archive_vault_2026 import old_func")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import(
                    {"tests/unit/test_thing.py"}
                )
                assert len(errors) == 0, f"tests should be report-only, got: {errors}"

    def test_archive_vault_path_exempt(self):
        """archive_vault_2026/ files are never scanned."""
        errors = check_no_archive_runtime_import({"archive_vault_2026/old_code.py"})
        assert len(errors) == 0

    def test_github_path_exempt(self):
        """.github/ files are never scanned."""
        errors = check_no_archive_runtime_import({".github/workflows/ci.yml"})
        assert len(errors) == 0

    def test_src_file_with_no_archive_reference_passes(self):
        """src/ file without any archive reference passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "src/clean.py",
                    "import os\nimport sys\n\ndef foo():\n    pass\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import({"src/clean.py"})
                assert len(errors) == 0

    def test_unchanged_file_not_scanned(self):
        """Only changed files are scanned; empty set produces no errors."""
        errors = check_no_archive_runtime_import(set())
        assert len(errors) == 0

    def test_nonexistent_file_skipped(self):
        """Changed file that doesn't exist on disk is silently skipped."""
        errors = check_no_archive_runtime_import({"src/does_not_exist.py"})
        assert len(errors) == 0

    def test_scripts_ops_nonexistent_file_skipped(self):
        """Non-existent scripts/ops file is silently skipped."""
        errors = check_no_archive_runtime_import({"scripts/ops/nonexistent.py"})
        assert len(errors) == 0

    def test_real_src_file_with_archive_vault_string_fails(self):
        """A real src/ file containing 'archive_vault_2026' in any form fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "src/bad.py",
                    "import sys\nfrom archive_vault_2026.utils import helper\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import({"src/bad.py"})
                assert len(errors) >= 1, "Expected errors for archive import"
                assert any("src/bad.py" in e for e in errors)
                assert any("archive_vault_2026" in e for e in errors)

    def test_real_src_file_with_import_archive_fails(self):
        """A real src/ file with 'import archive' fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "src/bad2.py", "import archive\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import({"src/bad2.py"})
                assert len(errors) >= 1, "Expected errors for 'import archive'"
                assert any("src/bad2.py" in e for e in errors)

    def test_real_scripts_ops_file_with_archive_import_fails(self):
        """A real scripts/ops/ file with archive reference fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/bad.py",
                    "from archive_vault import old\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import(
                    {"scripts/ops/bad.py"}
                )
                assert len(errors) >= 1
                assert any("scripts/ops/bad.py" in e for e in errors)

    def test_multiple_changed_files_one_bad(self):
        """Only the bad file should be reported among multiple changed files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "src/clean.py", "import os\n")
            _mkfile(tmpdir, "src/bad.py", "from archive_vault import old\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_no_archive_runtime_import(
                    {"src/clean.py", "src/bad.py"}
                )
                assert len(errors) >= 1
                assert any("src/bad.py" in e for e in errors)
                assert not any("src/clean.py" in e for e in errors)


# ============================================================================
# P1-2: check_dangerous_auth_path_cross_validation
# ============================================================================


_DANGEROUS_AUTH_PR_BODY_HEADER = textwrap.dedent("""\
    ## Dangerous File Authorization

    User authorized changes to gatekeeper and governance scripts.
    Rollback: revert this PR.

    ## PR Authorization Matrix

    | Item | Value |
    |---|---|
    | Task type | workflow-governance |
""")


class TestDangerousAuthPathCrossValidation:
    """P1-2: Cross-validate dangerous changed paths against authorized paths."""

    def test_gatekeeper_sh_changed_without_authorization_fails(self):
        """Changing scripts/devops/gatekeeper.sh without auth should fail."""
        changed = {"scripts/devops/gatekeeper.sh"}
        body = "## Summary\nNo authorization section."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any("scripts/devops/gatekeeper.sh" in e for e in errors)

    def test_gatekeeper_sh_changed_with_exact_path_auth_passes(self):
        """Changing gatekeeper.sh with exact path in Authorized paths passes."""
        changed = {"scripts/devops/gatekeeper.sh"}
        body = _DANGEROUS_AUTH_PR_BODY_HEADER + (
            "| Authorized paths | scripts/devops/gatekeeper.sh |\n"
        )
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_helper_file_covered_by_prefix_wildcard_passes(self):
        """Changing helpers/foo.py with scripts/ops/helpers/** auth passes."""
        changed = {"scripts/ops/helpers/governance_p1_checks.py"}
        body = _DANGEROUS_AUTH_PR_BODY_HEADER + (
            "| Authorized paths | scripts/ops/helpers/** |\n"
        )
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_workflow_file_without_authorization_fails(self):
        """Changing .github/workflows/x.yml without authorization should fail."""
        changed = {".github/workflows/test.yml"}
        body = "## Summary\nNo auth."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any(".github/workflows/test.yml" in e for e in errors)

    def test_workflow_file_with_authorization_passes(self):
        """Changing .github/workflows/x.yml with .github/workflows/** auth passes."""
        changed = {".github/workflows/test.yml"}
        body = _DANGEROUS_AUTH_PR_BODY_HEADER + (
            "| Authorized paths | .github/workflows/** |\n"
        )
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_non_dangerous_file_passes(self):
        """A regular file that is not in dangerous paths passes."""
        changed = {"docs/readme.md"}
        body = "## Summary\nSafe docs change."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) == 0

    def test_dockerfile_without_authorization_fails(self):
        """Changing Dockerfile without authorization should fail."""
        changed = {"Dockerfile"}
        body = "## Summary\nNo auth."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any("Dockerfile" in e for e in errors)

    def test_alembic_directory_without_authorization_fails(self):
        """Changing alembic/ files without authorization should fail."""
        changed = {"alembic/versions/001.py"}
        body = "## Summary\nNo auth."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any("alembic/versions/001.py" in e for e in errors)

    def test_check_devops_prefix_covered_by_wildcard_passes(self):
        """Changing check_*.py with scripts/devops/** auth passes."""
        changed = {"scripts/devops/check_python_ast_utf8.py"}
        body = _DANGEROUS_AUTH_PR_BODY_HEADER + (
            "| Authorized paths | scripts/devops/** |\n"
        )
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_multiple_dangerous_paths_one_uncovered(self):
        """When one dangerous path is uncovered among many, it is flagged."""
        changed = {
            "scripts/devops/gatekeeper.sh",
            "scripts/ops/helpers/governance_p1_checks.py",
        }
        body = _DANGEROUS_AUTH_PR_BODY_HEADER + (
            "| Authorized paths | scripts/ops/helpers/** |\n"
        )
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any("gatekeeper.sh" in e for e in errors)
        assert not any("governance_p1_checks" in e for e in errors)

    def test_empty_changed_set_passes(self):
        """Empty changed set produces no errors."""
        errors = check_dangerous_auth_path_cross_validation(set(), "any body")
        assert len(errors) == 0

    def test_empty_pr_body_with_dangerous_paths_skips(self):
        """Empty PR body with dangerous paths returns no errors (skipped)."""
        changed = {"scripts/devops/gatekeeper.sh"}
        errors = check_dangerous_auth_path_cross_validation(changed, "")
        assert len(errors) == 0

    def test_docker_compose_without_authorization_fails(self):
        """Changing docker-compose files without authorization fails."""
        changed = {"docker-compose.prod.yml"}
        body = "## Summary\nNo auth."
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1

    def test_no_authorized_paths_entry_fails(self):
        """Having auth sections but no Authorized paths entry fails."""
        changed = {"scripts/devops/gatekeeper.sh"}
        body = textwrap.dedent("""\
            ## Dangerous File Authorization

            User authorized changes to gatekeeper.

            ## PR Authorization Matrix

            | Item | Value |
            |---|---|
            | Task type | workflow-governance |
        """)
        errors = check_dangerous_auth_path_cross_validation(changed, body)
        assert len(errors) >= 1
        assert any("Authorized paths" in e for e in errors)


# ============================================================================
# P1-3: check_script_lifecycle_requirement
# ============================================================================


class TestScriptLifecycleRequirement:
    """P1-3: Require lifecycle/ownership for newly added scripts."""

    def test_new_script_without_lifecycle_fails(self):
        """New scripts/ops/x.py without lifecycle header or PR section fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/manual_probe.py",
                    "#!/usr/bin/env python3\n\nprint('hello')\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/ops/manual_probe.py"},
                    "## Summary\nNo lifecycle section.",
                )
                assert len(errors) >= 1, f"Expected errors, got: {errors}"
                assert any("manual_probe.py" in e for e in errors)

    def test_new_script_with_lifecycle_header_passes(self):
        """New script with Lifecycle: in file header passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/valid_script.py",
                    '#!/usr/bin/env python3\n"""Valid script.\n\n'
                    'lifecycle: permanent\n"""\n\nprint("ok")\n')
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/ops/valid_script.py"}, ""
                )
                assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_new_script_with_owner_header_passes(self):
        """New script with Owner: in file header passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/devops/check_x.py",
                    '"""Check X.\n\nOwner: CI team\n"""\n\nprint("ok")\n')
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/devops/check_x.py"}, ""
                )
                assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_new_script_with_pr_body_script_lifecycle_passes(self):
        """New script without file header but PR has Script Lifecycle section passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/new_helper.py",
                    "#!/usr/bin/env python3\n\n# No lifecycle header\nprint('hello')\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/ops/new_helper.py"},
                    "## Script Lifecycle\n\nThis script is permanent governance infra.",
                )
                assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_modified_existing_script_passes(self):
        """Modified (not new) script without lifecycle passes — only new files checked."""
        errors = check_script_lifecycle_requirement(set(), "## Summary\nNo lifecycle.")
        assert len(errors) == 0

    def test_new_tests_file_passes(self):
        """New tests/ file is exempt from lifecycle requirement."""
        errors = check_script_lifecycle_requirement(
            {"tests/unit/test_foo.py"}, "## Summary\nNo lifecycle."
        )
        assert len(errors) == 0

    def test_new_non_py_file_in_scripts_ops_passes(self):
        """New .txt file under scripts/ops/ does not trigger lifecycle check."""
        errors = check_script_lifecycle_requirement(
            {"scripts/ops/notes.txt"}, "## Summary\nNo lifecycle."
        )
        assert len(errors) == 0

    def test_new_script_under_scripts_ops_requires_lifecycle(self):
        """New .py under scripts/ops/ requires lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/no_lifecycle.py", "print('no header')\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/ops/no_lifecycle.py"}, "## Summary\nNo section."
                )
                assert len(errors) >= 1
                assert any("no_lifecycle.py" in e for e in errors)

    def test_multiple_new_scripts_all_missing(self):
        """Multiple new scripts without lifecycle should each be reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/ops/a.py", "print(1)\n")
            _mkfile(tmpdir, "scripts/devops/b.py", "print(2)\n")
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/ops/a.py", "scripts/devops/b.py"},
                    "## Summary\nNo lifecycle.",
                )
                min_expected = 2
                assert len(errors) >= min_expected, (
                    f"Expected >= {min_expected} errors, got: {errors}"
                )
                assert any("a.py" in e for e in errors)
                assert any("b.py" in e for e in errors)

    def test_new_script_with_maintainer_header_passes(self):
        """New script with Maintainer: in header passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _mkfile(tmpdir, "scripts/devops/with_maintainer.py",
                    '"""Script.\n\nMaintainer: devops team\n"""\n\nprint("ok")\n')
            with _temp_root(tmpdir):
                errors = _p1_mod.check_script_lifecycle_requirement(
                    {"scripts/devops/with_maintainer.py"}, ""
                )
                assert len(errors) == 0, f"Expected 0 errors, got: {errors}"
