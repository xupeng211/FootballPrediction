"""Tests for the M2 governance growth freeze gate — core scenarios.

lifecycle: test-fixture

Uses real temporary git repos with real base/head commits.
Covers positive, negative, anti-false-positive, basename-matcher,
rename-status, same-count dependency replacement, and authorization scenarios.

Hardening boundary tests (real exit code, JS string-awareness, basename
boundary integration) live in test_governance_growth_gate_hardening.py.
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
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _init_repo(tmp_path: Path) -> Path:
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
    for path, content in files.items():
        _write_file(repo, path, content)
    return _commit_all(repo, "base commit")


def _run_gate(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    return ggg.run_governance_growth_gate(repo, base_sha, head_sha)


# ---------------------------------------------------------------------------
# Test fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_base(tmp_path: Path) -> tuple[Path, str]:
    repo = _init_repo(tmp_path)
    base_files = {
        "docs/_reports/OLD_REPORT.md": "# Old historical report\nlifecycle: permanent\n",
        "docs/_manifests/old_manifest.json": '{"key": "old"}',
        "scripts/ops/fotmob_adg60_existing.js": "// Existing ADG script\n",
        "src/services/event_bus.py": textwrap.dedent(
            """\
            from scripts.ops.hunt_league_hashes import find_hash
            """
        ),
        "src/main.py": "def main(): pass\n",
        "scripts/ci/normal_ci_check.py": "# Normal CI script\n",
        "src/services/old_dep.py": textwrap.dedent(
            """\
            from scripts.ops.old_helper import run
            """
        ),
    }
    base_sha = _make_base_commit(repo, base_files)
    return repo, base_sha


# ---------------------------------------------------------------------------
# Positive tests
# ---------------------------------------------------------------------------


class TestPositivePassThrough:
    """Changes that SHOULD produce NO errors."""

    def test_no_changes_passes(self, repo_with_base):
        repo, base = repo_with_base
        assert _run_gate(repo, base, base) == []

    def test_modify_existing_report_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/OLD_REPORT.md", "# Updated\n")
        assert _run_gate(repo, base, _commit_all(repo, "modify report")) == []

    def test_modify_existing_manifest_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_manifests/old_manifest.json", '{"k":"v"}')
        assert _run_gate(repo, base, _commit_all(repo, "modify manifest")) == []

    def test_modify_existing_adg_script_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/fotmob_adg60_existing.js", "// Modified\n")
        assert _run_gate(repo, base, _commit_all(repo, "modify ADG script")) == []

    def test_existing_reverse_dep_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/main.py", "def main(): pass\n# comment\n")
        assert _run_gate(repo, base, _commit_all(repo, "modify unrelated")) == []

    def test_normal_business_import_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/new_service.py", "from src.models import User\nimport os\n")
        assert _run_gate(repo, base, _commit_all(repo, "add normal import")) == []

    def test_new_normal_doc_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/new_feature.md", "# New feature\n")
        assert _run_gate(repo, base, _commit_all(repo, "add normal doc")) == []

    def test_new_normal_ci_script_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/deploy_check.sh", "#!/bin/bash\necho ok\n")
        assert _run_gate(repo, base, _commit_all(repo, "add CI script")) == []

    def test_delete_historical_governance_file_passes(self, repo_with_base):
        repo, base = repo_with_base
        (repo / "docs/_reports/OLD_REPORT.md").unlink()
        assert _run_gate(repo, base, _commit_all(repo, "delete old report")) == []

    def test_output_order_stable(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/Z_REPORT.md", "# Z\n")
        _write_file(repo, "docs/_reports/A_REPORT.md", "# A\n")
        head = _commit_all(repo, "add two reports")
        assert _run_gate(repo, base, head) == _run_gate(repo, base, head)

    def test_delete_old_reverse_dep_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/old_dep.py", "def no_deps(): pass\n")
        errors = _run_gate(repo, base, _commit_all(repo, "remove old dep"))
        assert errors == [], f"Unexpected: {errors}"

    def test_same_dep_different_line_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/event_bus.py",
            textwrap.dedent(
                """\
                        import os
                        from scripts.ops.hunt_league_hashes import find_hash
                        """
            ),
        )
        errors = _run_gate(repo, base, _commit_all(repo, "move dep line"))
        assert errors == [], f"Should pass: {errors}"

    def test_same_dep_reformat_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/event_bus.py",
            "from scripts.ops.hunt_league_hashes import (\n    find_hash,\n)\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "reformat"))
        assert errors == [], f"Reformat should pass: {errors}"


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


class TestNegativeBlockNewReports:
    """Block new reports/manifests."""

    def test_new_report_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/NEW_REPORT.md", "# New\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add report"))
        assert len(errors) >= 1
        assert any(ggg.ERR_REPORT in e for e in errors)

    def test_new_manifest_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_manifests/new_manifest.json", "{}")
        errors = _run_gate(repo, base, _commit_all(repo, "add manifest"))
        assert len(errors) >= 1
        assert any(ggg.ERR_MANIFEST in e for e in errors)

    def test_rename_into_reports_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/normal.md", "# Normal\n")
        _commit_all(repo, "add normal doc")
        _git(repo, "mv", "docs/normal.md", "docs/_reports/renamed_in.md")
        errors = _run_gate(repo, base, _commit_all(repo, "rename into reports"))
        assert len(errors) >= 1
        assert any(ggg.ERR_REPORT in e for e in errors)


class TestNegativeBlockNumberedScripts:
    """Block new Phase/ADG numbered governance scripts."""

    def test_new_phase_99_underscore_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/phase_99_example.py", "# Phase 99\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add phase_99"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_phase_99_dash_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/Phase-12-review.js", "// Phase 12\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add Phase-12"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_phase99a_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/Phase99A_review.py", "# Phase 99A\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add Phase99A"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_adg999_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/adg999_new_step.py", "# ADG 999\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add adg999"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_new_adg_100a_dash_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/ADG-100A_plan.js", "// ADG-100A\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add ADG-100A"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_separator_prefixed_phase_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/something-phase2-plan.py", "# plan\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add something-phase2"))
        assert any(ggg.ERR_PHASE in e for e in errors)


class TestNegativeBlockReverseDeps:
    """Block new src -> scripts/ops reverse dependencies."""

    def test_new_python_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/new_service.py", "from scripts.ops.helpers.something import helper\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add reverse dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_dynamic_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/dynamic_import.py",
            "import importlib\n" + 'mod = importlib.import_module("scripts.ops.helper")\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add dynamic dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_python_subprocess_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/runner.py",
            textwrap.dedent(
                """\
                        import subprocess
                        subprocess.run(["python3", "scripts/ops/some_script.py"])
                        """
            ),
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add subprocess dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_require_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/newService.js", 'const helper = require("../../scripts/ops/helper.js");\n')
        errors = _run_gate(repo, base, _commit_all(repo, "add JS require"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/newModule.mjs", 'import helper from "../scripts/ops/helper.js";\n')
        errors = _run_gate(repo, base, _commit_all(repo, "add JS import"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_new_js_spawn_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/execService.js",
            textwrap.dedent(
                """\
                        const { spawn } = require("child_process");
                        spawn("node", ["scripts/ops/run_production.js"]);
                        """
            ),
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add JS spawn"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)

    def test_same_count_python_dep_replacement_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/old_dep.py", "from scripts.ops.new_helper import run\n")
        errors = _run_gate(repo, base, _commit_all(repo, "replace dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)
        assert any("new_helper" in e for e in errors)

    def test_same_count_js_dep_replacement_blocked(self, repo_with_base):
        repo, _base = repo_with_base
        _write_file(repo, "src/services/baseJsDep.js", 'const x = require("../../scripts/ops/old_tool.js");\n')
        base2 = _commit_all(repo, "add base JS dep")
        _write_file(repo, "src/services/baseJsDep.js", 'const x = require("../../scripts/ops/new_tool.js");\n')
        errors = _run_gate(repo, base2, _commit_all(repo, "replace JS dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)
        assert any("new_tool" in e for e in errors)

    def test_delete_two_add_two_blocked(self, repo_with_base):
        repo, _base = repo_with_base
        _write_file(
            repo,
            "src/services/old_dep.py",
            textwrap.dedent(
                """\
                        from scripts.ops.helper_a import func_a
                        from scripts.ops.helper_b import func_b
                        """
            ),
        )
        base2 = _commit_all(repo, "base with two deps")
        _write_file(
            repo,
            "src/services/old_dep.py",
            textwrap.dedent(
                """\
                        from scripts.ops.helper_c import func_c
                        from scripts.ops.helper_d import func_d
                        """
            ),
        )
        errors = _run_gate(repo, base2, _commit_all(repo, "replace two deps"))
        _min_expected_reverse_deps = 2
        assert sum(1 for e in errors if ggg.ERR_REVERSE_DEP in e) >= _min_expected_reverse_deps

    def test_new_file_with_dep_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/brand_new.py", "from scripts.ops.brand_new_helper import do_stuff\n")
        errors = _run_gate(repo, base, _commit_all(repo, "new file with dep"))
        assert any(ggg.ERR_REVERSE_DEP in e for e in errors)


class TestNegativeMultiViolation:
    """Multiple violations all reported."""

    def test_all_violations_reported(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/NEW_VIOLATION.md", "# V\n")
        _write_file(repo, "docs/_manifests/new_violation.json", "{}")
        _write_file(repo, "scripts/ops/phase_99_violation.py", "# Phase 99\n")
        _write_file(repo, "src/services/violation.py", "from scripts.ops.violation import bad\n")
        errors = _run_gate(repo, base, _commit_all(repo, "all violations"))
        _min_expected_violations = 4
        assert len(errors) >= _min_expected_violations
        for code in [ggg.ERR_REPORT, ggg.ERR_MANIFEST, ggg.ERR_PHASE, ggg.ERR_REVERSE_DEP]:
            assert any(code in e for e in errors), f"Missing {code}"

    def test_non_zero_exit_on_violation(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/FAIL_ME.md", "# Will fail\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add violation"))
        assert len(errors) > 0


class TestNegativeFailClosed:
    """Fail-closed on bad refs."""

    def test_bad_base_ref_fails_closed(self, repo_with_base):
        repo, base = repo_with_base
        assert len(_run_gate(repo, "nonexistent-ref-99999", base)) > 0

    def test_bad_head_ref_fails_closed(self, repo_with_base):
        repo, base = repo_with_base
        assert len(_run_gate(repo, base, "nonexistent-ref-99999")) > 0


# ---------------------------------------------------------------------------
# Rename status (Fix 1)
# ---------------------------------------------------------------------------


class TestRenameStatus:
    """Rename detection handles R100/R095, not just bare 'R'."""

    def test_rename_into_phase_r100_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py", "scripts/ops/phase_99_new_gate.py")
        errors = _run_gate(repo, base, _commit_all(repo, "rename R100"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_rename_into_adg_r100_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/normal_check.js", "// normal\n")
        _commit_all(repo, "add normal JS file")
        _git(repo, "mv", "scripts/ci/normal_check.js", "scripts/ops/ADG-100A-plan.js")
        errors = _run_gate(repo, base, _commit_all(repo, "rename JS R100"))
        assert any(ggg.ERR_PHASE in e for e in errors)

    def test_rename_normal_to_normal_passes(self, repo_with_base):
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py", "scripts/ci/renamed_ci_check.py")
        errors = _run_gate(repo, base, _commit_all(repo, "rename normal"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []


# ---------------------------------------------------------------------------
# Anti-false-positive tests
# ---------------------------------------------------------------------------


class TestAntiFalsePositive:
    """Gate must NOT produce false positives."""

    def test_comment_scripts_ops_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/commented.py", "# old: from scripts.ops.helper import x\ndef foo(): pass\n")
        assert _run_gate(repo, base, _commit_all(repo, "comment")) == []

    def test_logger_message_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/logger_example.py",
            textwrap.dedent(
                """\
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info("Use scripts/ops/run_production.js")
                        """
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "logger")) == []

    def test_docstring_scripts_ops_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/docstring_example.py",
            textwrap.dedent(
                '''\
                        """Module docs. Used scripts.ops.helper before. Now internal."""
                        def process(): pass
                        '''
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "docstring")) == []

    def test_python_subprocess_cross_function_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/cross_func.py",
            textwrap.dedent(
                """\
                        import subprocess
                        def first():
                            subprocess.run(["echo", "ok"])
                        def second():
                            help_text = "scripts/ops/old_tool.py is deprecated"
                        """
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "cross-func")) == []

    def test_python_multiline_docstring_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/multiline_doc.py",
            textwrap.dedent(
                '''\
                        """
                        Example:
                            from scripts.ops.helper import old_helper
                        This module replaces that.
                        """
                        def new_approach(): pass
                        '''
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "multiline doc")) == []

    def test_python_string_literal_subprocess_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/string_example.py",
            'example = \'subprocess.run(["python", "scripts/ops/demo.py"])\'\n' + "def real_func():\n    return 42\n",
        )
        assert _run_gate(repo, base, _commit_all(repo, "string literal")) == []

    def test_js_spawn_cross_function_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/crossFunc.js",
            textwrap.dedent(
                """\
                        const { spawn } = require("child_process");
                        function first() {
                          spawn("echo", ["ok"]);
                        }
                        function second() {
                          const example = 'spawn("node", ["scripts/ops/demo.js"])';
                        }
                        """
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "JS cross-func")) == []

    def test_js_plain_string_variable_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/helpText.js",
            textwrap.dedent(
                """\
                        const helpText = "See scripts/ops/run_production.js";
                        console.log(helpText);
                        """
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "JS help")) == []

    def test_js_require_in_comment_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/commented.js", '// require("../../scripts/ops/helper.js")\nconst x = 1;\n')
        assert _run_gate(repo, base, _commit_all(repo, "JS comment")) == []

    def test_js_require_in_plain_string_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/docString.js", "const example = 'require(\"../../scripts/ops/helper.js\")';\n")
        assert _run_gate(repo, base, _commit_all(repo, "JS string req")) == []

    def test_js_spawn_echo_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/echoService.js",
            textwrap.dedent(
                """\
                        const { spawn } = require("child_process");
                        spawn("echo", ["ok"]);
                        """
            ),
        )
        assert _run_gate(repo, base, _commit_all(repo, "JS echo")) == []

    def test_plain_phase_variable_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/training.py",
            "class Trainer:\n"
            "    def __init__(self):\n"
            '        self.phase = "warmup"\n'
            "        self.current_phase_number = 1\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "phase variable"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_adg_in_doc_not_in_scripts_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/adg_review_notes.md", "# ADG Review\n")
        errors = _run_gate(repo, base, _commit_all(repo, "ADG docs"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_outside_src_reverse_dep_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "tests/unit/test_helper.py", "from scripts.ops.helpers.something import helper\n")
        errors = _run_gate(repo, base, _commit_all(repo, "test import"))
        assert [e for e in errors if ggg.ERR_REVERSE_DEP in e] == []

    def test_existing_historical_debt_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/innocent.py", "def foo(): pass\n")
        assert _run_gate(repo, base, _commit_all(repo, "innocent")) == []

    def test_phase_without_digits_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ci/phase_transition_check.py", "# Phase transition\n")
        errors = _run_gate(repo, base, _commit_all(repo, "phase_transition"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_scripts_ops_reference_in_test_fixture_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "tests/fixtures/sample.py", "# fixture: import scripts.ops.helper\n")
        errors = _run_gate(repo, base, _commit_all(repo, "test fixture"))
        assert [e for e in errors if ggg.ERR_REVERSE_DEP in e] == []


# ---------------------------------------------------------------------------
# Basename matcher boundary tests (Fix 5)
# ---------------------------------------------------------------------------


class TestBasenameMatcher:
    """Unit tests for _is_numbered_governance_basename with boundary rules."""

    @pytest.mark.parametrize(
        ("basename", "expected"),
        [
            # Must match (starts at position 0)
            ("phase_99_example.py", True),
            ("Phase-12-review.js", True),
            ("Phase99A_review.py", True),
            ("adg999_new_step.py", True),
            ("ADG-100A_plan.js", True),
            ("adg_60_final.js", True),
            ("phase1_test.js", True),
            ("ADG1_initial.md", True),
            # Must match (after separator)
            ("something-phase2-plan.py", True),
            ("fotmob_adg60_existing.js", True),
            # Must NOT match (no separator before governance word)
            ("biophase9_data.csv", False),
            ("metadg10_result.py", False),
            ("prephase2_transform.js", False),
            # Must NOT match (no digit)
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
        assert ggg._is_numbered_governance_basename(basename) == expected, f"basename={basename!r} expected={expected}"


# ---------------------------------------------------------------------------
# Basename boundary integration (Fix 5)
# ---------------------------------------------------------------------------


class TestBasenameBoundaryIntegration:
    """Boundary filenames in real git repos under scripts/."""

    def test_biophase9_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/biophase9_data.csv", "a,b,c\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add biophase9"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_metadg10_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/metadg10_result.py", "x = 1\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add metadg10"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_prephase2_not_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/data/prephase2_transform.js", "// xform\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add prephase2"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_photographer_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/photographer.py", "# photos\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add photographer"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []

    def test_adg_review_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "scripts/ops/adg_review.md", "# review\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add adg_review"))
        assert [e for e in errors if ggg.ERR_PHASE in e] == []


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestAuthorization:
    """AUTHORIZED_GOVERNANCE_ADDITIONS must remain empty and exact-match."""

    def test_auth_set_is_empty(self):
        assert frozenset() == ggg.AUTHORIZED_GOVERNANCE_ADDITIONS

    def test_similar_path_not_authorized(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/ALMOST_AUTHORIZED.md", "# almost\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add unauthorized"))
        assert len(errors) >= 1

    def test_glob_not_supported(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/any_name_here.md", "# any\n")
        errors = _run_gate(repo, base, _commit_all(repo, "add any"))
        assert len(errors) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
