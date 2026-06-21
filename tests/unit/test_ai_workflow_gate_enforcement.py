"""Tests for AI workflow gate — DB write guard enforcement phase2.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/ops/ai_workflow_gate.py"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ops"))
import textwrap  # noqa: E402

import ai_workflow_gate as gate  # noqa: E402


def _valid_pr_body() -> str:
    """A minimal-valid PR body with all required sections."""
    return textwrap.dedent(
        """\
    ## Summary

    - Test PR for AI workflow gate validation.

    ## Scope

    | Item | Value |
    |---|---|
    | Task type | governance-only |
    | One task / one branch / one PR | yes |
    | Business code changed | no |

    ## Documentation Impact

    | Item | Value |
    |---|---|
    | New docs added | 0 |
    | Modified docs | AGENT_WORKFLOW.md — added section 19.5 hollow-compliance rules |
    | Reason | Updated workflow documentation to record new content-quality gate rules |

    ## Safety Impact

    | Item | Value |
    |---|---|
    | DB used | n/a |
    | Browser automation used | no |
    | Scraper run | no |

    ## Validation

    | Validation | Result |
    |---|---|
    | Unit tests (pytest) | 47 passed, 0 failed |
    | Ruff check | clean |
    | Ruff format --check | clean |
    | Gate CLI smoke | AI workflow gate passes with valid body |

    ## CI Gate Scope

    - What the validation proves: CI passes.
    - What the validation does not prove: runtime correctness.

    ## No deletion / no move / no rename confirmation

    | Item | Value |
    |---|---|
    | Deleted files | 0 |

    ## Rollback Plan

    - Revert this commit via `git revert <merge-commit-sha>`.
    - No database migrations, schema changes, or data writes are involved.
    - After revert, re-run `make ci-local` to confirm the gate still passes.

    ## Next Recommended Task

    Do not start automatically.

    Recommended next task only after user confirmation:

    - TBD
    """
    )


def test_db_write_guard_enforcement_function_exists():
    """check_db_write_guard_enforcement must be importable."""
    assert callable(gate.check_db_write_guard_enforcement)


def test_db_write_guard_enforcement_no_js_ops_changed():
    """When no scripts/ops/*.js files changed, returns empty errors/warnings."""
    errors, warnings = gate.check_db_write_guard_enforcement({"docs/README.md", "src/main.py"})
    assert errors == []
    assert warnings == []


_ENFORCEMENT_TUPLE_LEN = 2


def test_db_write_guard_enforcement_guarded_file():
    """A known guarded scripts/ops file should produce no errors."""
    errors, _warnings = gate.check_db_write_guard_enforcement({"scripts/ops/purge_orphans.js"})
    assert errors == [], f"Expected no errors for guarded file, got: {errors}"


def test_db_write_guard_enforcement_returns_tuple():
    """check_db_write_guard_enforcement must return a 2-tuple of lists."""
    result = gate.check_db_write_guard_enforcement({"scripts/ops/purge_orphans.js"})
    assert isinstance(result, tuple)
    assert len(result) == _ENFORCEMENT_TUPLE_LEN
    errors, warnings = result
    assert isinstance(errors, list)
    assert isinstance(warnings, list)


def test_enforcement_validate_integration_clean():
    """validate() should pass when DB write guard enforcement finds no violations."""
    body = _valid_pr_body()
    changes = [
        gate.Change("M", "scripts/ops/purge_orphans.js"),
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
    ]
    errors = gate.validate(body, changes)
    db_errors = [e for e in errors if "DB-WRITE-GUARD ENFORCEMENT" in e]
    assert db_errors == [], f"Should not have DB enforcement errors: {db_errors}"


def test_gate_cli_with_skip_body_checks_and_clean_files_passes():
    """Gate CLI with --skip-body-checks and clean changed files should exit 0."""
    result = subprocess.run(
        [sys.executable, str(GATE), "--pr-body-file", "/dev/null", "--skip-body-checks"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_gate_cli_with_valid_body_and_clean_files_passes():
    """Gate CLI with valid PR body and clean changed files should exit 0."""
    body = _valid_pr_body()
    result = subprocess.run(
        [sys.executable, str(GATE), "--pr-body-stdin"],
        input=body,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
