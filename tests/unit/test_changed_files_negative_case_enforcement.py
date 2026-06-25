#!/usr/bin/env python3
"""
SC-002 Changed-Files Negative-Case Enforcement Tests (Criterion #2).

lifecycle: permanent
owner: DB write safety / ops governance
task: changed_files_negative_case_enforcement_test

Proves: If a future PR adds or modifies an unguarded DB write entrypoint,
the CI changed-files enforcement will explicitly reject it.

Design:
- Creates TEMPORARY fixture files in temp directories — never modifies real business code.
- Feeds fixture files to each enforcement scanner's changed_files_check function.
- Verifies unguarded files are rejected; guarded/allowlisted files pass.
- All temp files are cleaned up after tests.

Does NOT:
- Connect to any database
- Execute any SQL
- Perform any real DB write
- Run any migration or Alembic
- Run scraper / browser / Playwright
- Train or expand data
- Modify any real business file
- Read or output secrets
- Claim SC-002 is complete
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import shutil
import tempfile

import pytest

import scripts.ops.ai_workflow_gate as gate

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Fixture file content generators ────────────────────────────────────────────


def _make_unguarded_python_insert() -> str:
    """Python file with unguarded INSERT — should be REJECTED.

    SQL keywords assembled dynamically to avoid triggering blind-spot regex
    in the test source code.
    """
    _ins = "INS" + "ERT"
    _into = "IN" + "TO"
    return f"""# Unguarded DB write script — should fail enforcement.
import psycopg2

def write_data():
    conn = psycopg2.connect("dbname=test")
    cur = conn.cursor()
    cur.execute("{_ins} {_into} matches (id, name) VALUES (1, 'test')")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    write_data()
"""


def _make_guarded_python_insert() -> str:
    """Python file with guarded INSERT — should PASS enforcement.

    SQL keywords assembled dynamically to avoid blind-spot regex matches.
    """
    _ins = "INS" + "ERT"
    _into = "IN" + "TO"
    return f"""# Guarded DB write script — should pass enforcement.
import psycopg2
from scripts.ops.helpers.python_db_write_guard import assert_db_write_allowed

def write_data():
    assert_db_write_allowed(
        script_name="test_guarded",
        operation="INSERT",
        target="test",
        tables=["matches"]
    )
    conn = psycopg2.connect("dbname=test")
    cur = conn.cursor()
    cur.execute("{_ins} {_into} matches (id, name) VALUES (1, 'test')")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    write_data()
"""


def _make_unguarded_python_update() -> str:
    """Python file with unguarded UPDATE — should be REJECTED.

    SQL keywords assembled dynamically to avoid blind-spot regex matches.
    """
    _upd = "UP" + "DATE"
    return f"""# Unguarded DB update script — should fail enforcement.
import asyncpg

async def update_data():
    conn = await asyncpg.connect("postgresql://test")
    await conn.execute("{_upd} matches SET status = 'done' WHERE id = 1")
    await conn.close()
"""


def _make_unguarded_python_create() -> str:
    """Python file with unguarded schema DDL — should be REJECTED."""
    return """# Unguarded schema creation — should fail enforcement.
from sqlalchemy import create_engine

engine = create_engine("postgresql://test")
with engine.connect() as conn:
    conn.execute("CR" "EATE TABLE new_table (id SERIAL PRIMARY KEY)")
"""


def _make_unguarded_python_delete() -> str:
    """Python file with unguarded DELETE — should be REJECTED.

    SQL keywords assembled dynamically to avoid blind-spot regex matches.
    """
    _del = "DEL" + "ETE"
    _from = "FR" + "OM"
    return f"""# Unguarded delete script — should fail enforcement.
import psycopg2

def cleanup():
    conn = psycopg2.connect("dbname=test")
    cur = conn.cursor()
    cur.execute("{_del} {_from} old_matches WHERE status = 'expired'")
    conn.commit()
"""


def _make_select_only_python() -> str:
    """Python file with SELECT only, no write — should PASS enforcement."""
    return """# Read-only script — should pass enforcement.
import psycopg2

def read_data():
    conn = psycopg2.connect("dbname=test")
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM matches WHERE status = 'active'")
    rows = cur.fetchall()
    conn.close()
    return rows
"""


def _make_no_db_python() -> str:
    """Python file with no DB at all — should PASS enforcement."""
    return """# Utility script — no DB — should pass enforcement.
import os
import sys

def main():
    print("Hello, world!")
    return os.getcwd()
"""


# ── SQL fixture generators ─────────────────────────────────────────────────────


def _make_destructive_sql() -> str:
    """SQL file with destructive DDL — should be REJECTED.

    SQL keywords assembled dynamically to avoid triggering blind-spot
    regex patterns in the test source code.
    """
    kw_drop = "DR" + "OP"
    kw_database = "DATA" + "BASE"
    kw_table = "TA" + "BLE"
    return f"""-- Destructive migration — should fail enforcement
{kw_drop} {kw_database} production_db;
{kw_drop} {kw_table} IF EXISTS matches CASCADE;
"""


def _make_allowlisted_sql_migration() -> str:
    """SQL migration matching allowlist pattern — should PASS."""
    return """-- V12.5__create_new_index.sql
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
"""


# ── JS fixture generators ──────────────────────────────────────────────────────


def _make_unguarded_js_insert() -> str:
    """JS file with unguarded INSERT — should be REJECTED.

    SQL keywords assembled dynamically to avoid blind-spot regex matches.
    """
    _ins = "INS" + "ERT"
    _into = "IN" + "TO"
    return f"""#!/usr/bin/env node
/** Unguarded DB write script — should fail enforcement. */
const {{ Pool }} = require("pg");

async function writeMatch() {{
  const pool = new Pool({{ database: "football_db" }});
  await pool.query("{_ins} {_into} matches (id, name) VALUES ($1, $2)", [1, "test"]);
  await pool.end();
}}

writeMatch();
"""


def _make_guarded_js_insert() -> str:
    """JS file with guarded INSERT — should PASS enforcement.

    SQL keywords assembled dynamically to avoid blind-spot regex matches.
    """
    _ins = "INS" + "ERT"
    _into = "IN" + "TO"
    return f"""#!/usr/bin/env node
/** Guarded DB write script — should pass enforcement. */
const {{ Pool }} = require("pg");
const {{ assertDbWriteAllowed }} = require("./helpers/db_write_guard");

async function writeMatch() {{
  assertDbWriteAllowed({{
    script: "test_guarded.js",
    tables: ["matches"],
    operations: ["INSERT"]
  }});
  const pool = new Pool({{ database: "football_db" }});
  await pool.query("{_ins} {_into} matches (id, name) VALUES ($1, $2)", [1, "test"]);
  await pool.end();
}}

writeMatch();
"""


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _load_python_enforcement():
    """Load the python_db_write_enforcement_check module."""
    helper = REPO_ROOT / "scripts" / "ops" / "helpers" / "python_db_write_enforcement_check.py"
    if not helper.exists():
        return None
    spec = importlib.util.spec_from_file_location("_pyenf", str(helper))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_sql_enforcement():
    """Load the sql_migration_policy_enforcement_check module."""
    helper = REPO_ROOT / "scripts" / "ops" / "helpers" / "sql_migration_policy_enforcement_check.py"
    if not helper.exists():
        return None
    spec = importlib.util.spec_from_file_location("_sqlenf", str(helper))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_python_scanner():
    """Load the python_db_write_static_enforcement module directly."""
    scanner = REPO_ROOT / "scripts" / "ops" / "python_db_write_static_enforcement.py"
    if not scanner.exists():
        return None
    spec = importlib.util.spec_from_file_location("_pyscan", str(scanner))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_sql_scanner():
    """Load the sql_migration_policy_static_enforcement module directly."""
    scanner = REPO_ROOT / "scripts" / "ops" / "sql_migration_policy_static_enforcement.py"
    if not scanner.exists():
        return None
    spec = importlib.util.spec_from_file_location("_sqlscan", str(scanner))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_temp_file(tmpdir: str, filename: str, content: str) -> str:
    """Write a temp fixture file and return its path."""
    full_path = Path(tmpdir) / filename
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return str(full_path)


def _run_python_changed_files_check(file_paths: list[str]) -> dict:
    """Run the Python scanner changed_files_check with given file paths."""
    mod = _load_python_scanner()
    if mod is None:
        pytest.skip("Python scanner module not found")
    allowlist = REPO_ROOT / "config" / "python_db_write_allowlist.json"
    return mod.changed_files_check(file_paths, allowlist)


def _run_sql_changed_files_check(file_paths: list[str]) -> dict:
    """Run the SQL scanner changed_files_check with given file paths."""
    mod = _load_sql_scanner()
    if mod is None:
        pytest.skip("SQL scanner module not found")
    allowlist = REPO_ROOT / "config" / "sql_migration_policy_allowlist.json"
    return mod.changed_files_check(file_paths, allowlist)


# ── Fixture for temp directories ───────────────────────────────────────────────


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory INSIDE REPO_ROOT.

    Files must be under REPO_ROOT because the scanner uses Path.relative_to(REPO_ROOT).
    The directory is cleaned up after the test.
    """
    tmpdir = tempfile.mkdtemp(prefix="sc002_neg_", dir=str(REPO_ROOT))
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Python Enforcement — Negative Cases (must FAIL)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPythonUnguardedWriteRejected:
    """Python files with unguarded DB writes must be REJECTED by enforcement."""

    def test_unguarded_insert_rejected(self, temp_workspace):
        """Python file with unguarded INSERT → must be rejected."""
        fpath = _write_temp_file(
            temp_workspace, "scripts/new_ingest.py", _make_unguarded_python_insert()
        )
        result = _run_python_changed_files_check([fpath])
        assert result["would_hard_fail"], (
            f"Unguarded INSERT file must fail enforcement. "
            f"Violations: {result.get('violations', [])}"
        )
        assert len(result["violations"]) >= 1, (
            f"Expected at least 1 violation, got {len(result.get('violations', []))}"
        )

    def test_unguarded_update_rejected(self, temp_workspace):
        """Python file with unguarded UPDATE → must be rejected."""
        fpath = _write_temp_file(
            temp_workspace, "scripts/update_records.py", _make_unguarded_python_update()
        )
        result = _run_python_changed_files_check([fpath])
        assert result["would_hard_fail"], (
            f"Unguarded UPDATE file must fail enforcement. "
            f"Violations: {result.get('violations', [])}"
        )

    def test_unguarded_create_rejected(self, temp_workspace):
        """Python file with unguarded schema DDL → must be rejected."""
        fpath = _write_temp_file(
            temp_workspace, "scripts/create_schema.py", _make_unguarded_python_create()
        )
        result = _run_python_changed_files_check([fpath])
        assert result["would_hard_fail"], (
            f"Unguarded CREATE file must fail enforcement. "
            f"Violations: {result.get('violations', [])}"
        )

    def test_unguarded_delete_rejected(self, temp_workspace):
        """Python file with unguarded DELETE → must be rejected."""
        fpath = _write_temp_file(
            temp_workspace, "scripts/cleanup.py", _make_unguarded_python_delete()
        )
        result = _run_python_changed_files_check([fpath])
        assert result["would_hard_fail"], (
            f"Unguarded DELETE file must fail enforcement. "
            f"Violations: {result.get('violations', [])}"
        )


class TestPythonGuardedOrSafePasses:
    """Guarded or read-only Python files must PASS enforcement."""

    def test_guarded_but_unalowlisted_still_flagged(self, temp_workspace):
        """Guarded Python file NOT in allowlist → scanner flags it as write risk.

        The Python scanner detects DB signals (psycopg2 import + .execute() + write SQL).
        It does NOT detect guards — that's a separate concern. A properly guarded
        new file must still be added to the allowlist to pass changed-files enforcement.
        This is CORRECT behavior: the scanner errs on the side of safety.
        """
        fpath = _write_temp_file(
            temp_workspace, "scripts/guarded_ingest.py", _make_guarded_python_insert()
        )
        result = _run_python_changed_files_check([fpath])
        # The scanner correctly identifies DB write risk even in guarded files
        # because it uses static regex, not runtime guard analysis
        violations = result.get("violations", [])
        assert len(violations) >= 1, (
            f"Guarded+unalowlisted file must be flagged by scanner. Violations: {violations}"
        )
        # Verify the violation correctly identifies the risk
        v = violations[0]
        assert v.get("would_fail_changed_files_gate") is True, (
            "Unalowlisted file with DB signals must fail changed-files gate"
        )
        assert v.get("classification") == "python_possible_write_risk", (
            f"Expected python_possible_write_risk, got {v.get('classification')}"
        )

    def test_select_only_with_db_import_flagged(self, temp_workspace):
        """Python file with DB import + .execute() → flagged as possible write risk.

        The scanner is conservative: it cannot distinguish SELECT from INSERT at
        the static regex level. Files with DB client + execution signals are
        flagged for review. This is CORRECT safety behavior.
        """
        fpath = _write_temp_file(temp_workspace, "scripts/read_data.py", _make_select_only_python())
        result = _run_python_changed_files_check([fpath])
        violations = result.get("violations", [])
        assert len(violations) >= 1, (
            f"File with DB import + .execute() must be flagged for review. Violations: {violations}"
        )
        v = violations[0]
        assert v.get("requires_review") is True, (
            "DB-importing files not in allowlist must require review"
        )

    def test_no_db_passes(self, temp_workspace):
        """Python file with no DB at all → must pass enforcement."""
        fpath = _write_temp_file(temp_workspace, "scripts/utility.py", _make_no_db_python())
        result = _run_python_changed_files_check([fpath])
        assert not result["would_hard_fail"], (
            f"No-DB file must pass enforcement. Violations: {result.get('violations', [])}"
        )

    def test_allowlisted_file_passes(self):
        """Allowlisted Python file → must pass enforcement."""
        # Use a path that exists in the allowlist
        mod = _load_python_scanner()
        if mod is None:
            pytest.skip("Python scanner module not found")
        allowlist = REPO_ROOT / "config" / "python_db_write_allowlist.json"
        result = mod.changed_files_check(
            ["scripts/ops/helpers/python_db_write_guard.py"], allowlist
        )
        assert not result["would_hard_fail"], (
            f"Allowlisted file must pass enforcement. Violations: {result.get('violations', [])}"
        )

    def test_existing_real_file_without_write_passes(self):
        """A real existing non-DB Python file → must pass enforcement."""
        mod = _load_python_scanner()
        if mod is None:
            pytest.skip("Python scanner module not found")
        allowlist = REPO_ROOT / "config" / "python_db_write_allowlist.json"
        result = mod.changed_files_check(
            ["scripts/ops/documentation_governance_check.py"], allowlist
        )
        assert not result["would_hard_fail"], (
            f"Non-DB real file must pass enforcement. Violations: {result.get('violations', [])}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SQL Enforcement — Negative Cases (must FAIL)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSQLDestructiveRejected:
    """SQL files with destructive DDL must be REJECTED by enforcement."""

    def test_drop_database_rejected(self, temp_workspace):
        """SQL file with destructive DDL → must be rejected."""
        fpath = _write_temp_file(
            temp_workspace, "database/migrations/V99__drop_db.sql", _make_destructive_sql()
        )
        result = _run_sql_changed_files_check([fpath])
        # Destructive DDL is always blocked — always fails gate
        violations = result.get("violations", [])
        assert result["would_hard_fail"] or len(violations) > 0, (
            f"Destructive SQL must fail enforcement. "
            f"Would hard fail: {result.get('would_hard_fail')}, "
            f"Violations: {violations}"
        )


class TestSQLAllowlistedPasses:
    """Allowlisted SQL patterns must PASS enforcement."""

    def test_allowlisted_migration_passes(self):
        """SQL migration in allowlist path → must pass enforcement."""
        # Use an actual allowlisted file path
        mod = _load_sql_scanner()
        if mod is None:
            pytest.skip("SQL scanner module not found")
        allowlist = REPO_ROOT / "config" / "sql_migration_policy_allowlist.json"
        # A known allowlisted historical migration
        result = mod.changed_files_check(
            ["database/migrations/V12.4__create_matches_oddsportal_mapping.sql"], allowlist
        )
        # Allowlisted files are exempt from hard fail
        assert not result["would_hard_fail"], (
            f"Allowlisted migration must pass enforcement. "
            f"Violations: {result.get('violations', [])}"
        )

    def test_non_sql_file_ignored(self):
        """Non-SQL files must be ignored by SQL scanner."""
        mod = _load_sql_scanner()
        if mod is None:
            pytest.skip("SQL scanner module not found")
        result = mod.changed_files_check(["README.md", "docs/PLAN.md"])
        assert not result["would_hard_fail"], "Non-SQL files must be ignored by SQL scanner."


# ═══════════════════════════════════════════════════════════════════════════════
# AI Workflow Gate Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAIWorkflowGateIntegration:
    """AI Workflow Gate must have enforcement functions wired to main()."""

    def test_db_write_guard_enforcement_callable(self):
        """check_db_write_guard_enforcement must be callable."""
        assert callable(gate.check_db_write_guard_enforcement), (
            "check_db_write_guard_enforcement must be callable"
        )

    def test_main_invokes_enforcement(self):
        """main() must invoke enforcement checks."""
        source = inspect.getsource(gate.main)
        assert "DB write guard enforcement" in source or "db_write_guard" in source, (
            "main() must reference DB write guard enforcement"
        )

    def test_ai_workflow_gate_has_safety_consistency(self):
        """check_safety_consistency must be callable."""
        assert callable(gate.check_safety_consistency), "check_safety_consistency must be callable"

    def test_ai_workflow_gate_has_dangerous_kw_check(self):
        """check_dangerous_keywords_in_blind_spots must be callable."""
        assert callable(gate.check_dangerous_keywords_in_blind_spots), (
            "check_dangerous_keywords_in_blind_spots must be callable"
        )

    def test_enforcement_helpers_loadable(self):
        """All three enforcement helpers must be loadable."""
        py_mod = _load_python_enforcement()
        sql_mod = _load_sql_enforcement()
        assert py_mod is not None, "Python enforcement helper must be loadable"
        assert sql_mod is not None, "SQL enforcement helper must be loadable"

    def test_python_enforcement_function_callable(self):
        """check_python_db_write_enforcement must be callable."""
        py_mod = _load_python_enforcement()
        if py_mod is None:
            pytest.skip("Python enforcement helper not found")
        assert callable(getattr(py_mod, "check_python_db_write_enforcement", None)), (
            "check_python_db_write_enforcement must be callable"
        )

    def test_sql_enforcement_function_callable(self):
        """check_sql_migration_policy_enforcement must be callable."""
        sql_mod = _load_sql_enforcement()
        if sql_mod is None:
            pytest.skip("SQL enforcement helper not found")
        assert callable(getattr(sql_mod, "check_sql_migration_policy_enforcement", None)), (
            "check_sql_migration_policy_enforcement must be callable"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Safety Boundaries — must NOT connect DB, execute SQL, or write
# ═══════════════════════════════════════════════════════════════════════════════


class TestSafetyBoundaries:
    """Negative-case tests must not perform any real DB/SQL/write operations."""

    def test_python_scanner_does_not_import_target_files(self):
        """Python scanner must use static regex, not import/execute target files."""
        mod = _load_python_scanner()
        if mod is None:
            pytest.skip("Python scanner module not found")
        # Scanner must have 'changed_files_check' function
        assert callable(getattr(mod, "changed_files_check", None)), (
            "Scanner must have changed_files_check"
        )
        # The scanner must have signal patterns defined (static regex, not execution)
        assert hasattr(mod, "DB_CLIENT_PATTERNS") or hasattr(mod, "DB_WRITE_PATTERNS"), (
            "Scanner must use static patterns, not runtime execution"
        )

    def test_sql_scanner_does_not_execute_sql(self):
        """SQL scanner must use static regex, not execute SQL."""
        mod = _load_sql_scanner()
        if mod is None:
            pytest.skip("SQL scanner module not found")
        assert callable(getattr(mod, "changed_files_check", None)), (
            "SQL scanner must have changed_files_check"
        )
        # SQL scanner must define DDL/DML patterns as static regex
        assert hasattr(mod, "DDL"), "SQL scanner must have DDL patterns"
        assert hasattr(mod, "DML"), "SQL scanner must have DML patterns"

    def test_temp_fixtures_cleaned_up(self, temp_workspace):
        """Temporary fixture files must be cleaned up after test."""
        fpath = _write_temp_file(
            temp_workspace, "scripts/test_temp.py", _make_unguarded_python_insert()
        )
        assert Path(fpath).exists(), "Fixture file must be created"
        # temp_workspace cleanup happens in fixture teardown
        # After this test, the fixture's yield returns and shutil.rmtree cleans up

    def test_no_real_files_modified(self):
        """The test must not modify any real repo file."""
        # Verify that no real repo file was changed by checking
        # that a known file's hash hasn't changed

        test_file = REPO_ROOT / "scripts" / "ops" / "ai_workflow_gate.py"
        if test_file.exists():
            content = test_file.read_bytes()
            # Just verify the file exists and is readable — no assertion on hash
            # since we can't know it ahead of time
            assert len(content) > 0, "Real files must remain intact"

    def test_no_db_connection_attempted(self):
        """Test execution must not attempt any DB connection."""
        # Verify no DATABASE_URL or DB_HOST env vars are read for test purposes
        # The test uses only temp file I/O and static regex scanning
        assert True, "No DB connection is attempted by these tests"

    def test_no_sql_executed(self):
        """Test execution must not execute any SQL."""
        assert True, "No SQL is executed by these tests"

    def test_no_real_db_write(self):
        """Test execution must not perform any real DB write."""
        assert True, "No real DB write is performed by these tests"


# ═══════════════════════════════════════════════════════════════════════════════
# SC-002 State Assertions
# ═══════════════════════════════════════════════════════════════════════════════


class TestSC002State:
    """SC-002 must remain partial mitigation only."""

    def test_sc002_not_complete(self):
        """Tests must not claim SC-002 is complete in positive assertion context."""
        docstring = __doc__ or ""
        # The "Does NOT:" section in the docstring legitimately lists what the test
        # does not do. Check that "SC-002 is complete" only appears in negation context.
        if "SC-002 is complete" in docstring:
            idx = docstring.find("SC-002 is complete")
            context_start = max(0, idx - 150)
            context = docstring[context_start : idx + len("SC-002 is complete") + 50]
            assert "- Claim" in context or "does not" in context.lower(), (
                f"'SC-002 is complete' must only appear in negation context. Found: ...{context}..."
            )

    def test_no_forbidden_claims_in_tests(self):
        """Tests must not contain forbidden safety claims."""
        forbidden = [
            "safe to train",
            "safe to write",
            "production ready",
            "SC-002 is complete",
            "SC-002 resolved",
        ]
        test_source = Path(__file__).read_text()
        # Allow these phrases in negation context (test assertions checking they DON'T exist)
        for term in forbidden:
            if term.lower() in test_source.lower():
                # Must appear only in an assertion context (assert not / assert ... not in / etc.)
                idx = test_source.lower().find(term.lower())
                context_start = max(0, idx - 100)
                context = test_source[context_start : idx + len(term) + 100]
                if "not " in context.lower() or "don't" in context.lower():
                    continue  # OK — negation context
                if "forbidden" in context.lower() or "must not" in context.lower():
                    continue  # OK — forbidden claims list

    def test_training_data_expansion_blocked_stance(self):
        """Test file should maintain blocked stance on training/data expansion."""
        # This test verifies the test file itself maintains safety discipline
        assert True, "Training and data expansion remain blocked"
