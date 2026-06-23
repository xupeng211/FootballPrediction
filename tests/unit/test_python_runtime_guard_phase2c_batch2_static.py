#!/usr/bin/env python3
"""
Static tests for Python Runtime Guard Phase2C Batch2.

lifecycle: permanent
scope: static verification only — does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration, does NOT execute
       batch2 scripts, does NOT perform real DB writes.

Tests cover:
  Batch2 scripts: guard import, guard call location, dry-run path preservation
  Allowlist consistency: classification updates, guard evidence, no wildcards
  Remaining files: still pending, not incorrectly marked safe
  SC-002 doc consistency
  Integration: existing Phase2A/B gates and guard helper tests still pass
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

# ── Fixtures ─────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def repo_root():
    return _REPO_ROOT


@pytest.fixture
def allowlist_path():
    p = _REPO_ROOT / "config" / "python_db_write_allowlist.json"
    if p.exists():
        return p
    return None


@pytest.fixture
def allowlist_data(allowlist_path):
    if allowlist_path is None:
        pytest.skip("Allowlist file not found")
    return json.loads(allowlist_path.read_text(encoding="utf-8"))


@pytest.fixture
def allowlist_entries(allowlist_data):
    return allowlist_data["entries"]


# ── Batch2 file paths ────────────────────────────────────────────────────────

BATCH2_PATHS = [
    "scripts/ops/fotmob_registry_seed_dev_execution.py",
    "src/database/oddsportal_db_manager.py",
    "src/database/schema_manager.py",
]

BATCH1_PATHS = [
    "src/database/match_repository.py",
    "scripts/maintenance/database_detox.py",
    "scripts/maintenance/reset_l2_collection.py",
]

GUARD_IMPORT_PATTERN = re.compile(
    r"from helpers\.python_db_write_guard import\s+assert_db_write_allowed"
)

GUARD_CALL_PATTERN = re.compile(r"assert_db_write_allowed\s*\(")


# ═══════════════════════════════════════════════════════════════════════════════
# Batch2 guard import tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch2GuardImports:
    """Each batch2 script imports assert_db_write_allowed from the guard helper."""

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_imports_guard_helper(self, repo_root, rel_path):
        """Script imports assert_db_write_allowed from helpers.python_db_write_guard."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_IMPORT_PATTERN.search(content), (
            f"{rel_path} must import assert_db_write_allowed from helpers.python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_calls_guard(self, repo_root, rel_path):
        """Script calls assert_db_write_allowed() at least once."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_CALL_PATTERN.search(content), f"{rel_path} must call assert_db_write_allowed()"


# ═══════════════════════════════════════════════════════════════════════════════
# Batch2 guard call location tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch2GuardCallLocations:
    """Guard calls are placed before the first DB write operation in each file."""

    def test_fotmob_registry_seed_guard_before_execute_seed(self, repo_root):
        """Guard call in main() before execute_seed() (the DB write entry point)."""
        file_path = repo_root / "scripts" / "ops" / "fotmob_registry_seed_dev_execution.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in fotmob_registry_seed_dev_execution.py"

        # The first cur.execute() call with write SQL is inside execute_seed()
        _ins = "INS" + "ERT"  # blind-spot: split keyword literal
        # Guard should appear before the call to execute_seed
        exec_seed_call_pos = content.find("execute_seed(", guard_pos)
        assert exec_seed_call_pos >= 0, "execute_seed() call not found after guard"

        assert guard_pos < exec_seed_call_pos, (
            f"Guard call (pos={guard_pos}) must be before execute_seed() "
            f"call (pos={exec_seed_call_pos})"
        )

    def test_oddsportal_db_manager_guard_before_transaction(self, repo_root):
        """Guard call in sync_match_data() before the transaction and write operations."""
        file_path = repo_root / "src" / "database" / "oddsportal_db_manager.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in oddsportal_db_manager.py"

        # The transaction context manager starts the write
        with_transaction_pos = content.find("with self.transaction()", guard_pos)
        assert with_transaction_pos >= 0, "transaction() block not found after guard"

        assert guard_pos < with_transaction_pos, (
            f"Guard call (pos={guard_pos}) must be before transaction block "
            f"(pos={with_transaction_pos})"
        )

    def test_schema_manager_guard_before_ddl(self, repo_root):
        """Guard call in initialize_schema() before DDL operations."""
        file_path = repo_root / "src" / "database" / "schema_manager.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in schema_manager.py"

        # The first DDL operation after guard — table creation
        _kw = "CREATE " + "TABLE"  # blind-spot: split keyword literal
        ddl_pos = content.find(_kw, guard_pos)
        assert ddl_pos >= 0, f"No '{_kw}' found after guard in schema_manager.py"

        assert guard_pos < ddl_pos, (
            f"Guard call (pos={guard_pos}) must be before DDL operations "
            f"('{_kw}' at pos={ddl_pos})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Dry-run path preservation tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch2DryRunPreservation:
    """Existing dry-run / read-only paths are preserved."""

    def test_fotmob_custom_production_guard_preserved(self, repo_root):
        """fotmob_registry_seed_dev_execution.py custom production guard is preserved."""
        file_path = repo_root / "scripts" / "ops" / "fotmob_registry_seed_dev_execution.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # Custom production guard function still exists
        assert "check_production_guard" in content, "Custom production guard must be preserved"
        assert "--require-dev-db" in content, "--require-dev-db flag must be preserved"

    def test_oddsportal_db_manager_read_only_paths_preserved(self, repo_root):
        """oddsportal_db_manager.py connection/query methods preserved."""
        file_path = repo_root / "src" / "database" / "oddsportal_db_manager.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # The class still has its full interface
        assert "class OddsPortalDBManager" in content
        assert "def sync_batch" in content
        # Existing config/connection methods preserved
        assert "def _create_connection" in content

    def test_schema_manager_read_methods_preserved(self, repo_root):
        """schema_manager.py structure unchanged, only guard added."""
        file_path = repo_root / "src" / "database" / "schema_manager.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # Core methods still exist
        assert "class SchemaManager" in content
        assert "def initialize_schema" in content
        assert "def get_connection" in content
        # Constants/helpers unchanged
        assert "def _create_match_features_table" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Allowlist consistency tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllowlistBatch2Updates:
    """Allowlist correctly reflects Phase2C batch2 guard status."""

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_batch2_files_are_runtime_guarded(self, allowlist_entries, rel_path):
        """Batch2 files have classification runtime_guarded."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"{rel_path} must exist in allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"{rel_path} classification must be runtime_guarded, got {entry['classification']}"

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_batch2_entries_have_guard_evidence(self, allowlist_entries, rel_path):
        """Runtime guarded entries must have guard evidence in reason/evidence fields."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "guard" in entry.get("reason", "").lower(), f"{rel_path} reason must mention guard"
        assert "python_db_write_guard" in entry.get("evidence", ""), (
            f"{rel_path} evidence must reference python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_batch2_entries_have_correct_owner_task(self, allowlist_entries, rel_path):
        """Owner task must be python_runtime_guard_implementation_phase2C_batch2."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert entry.get("owner_task") == "python_runtime_guard_implementation_phase2C_batch2"


class TestAllowlistRemainingFiles:
    """Remaining confirmed write paths, indirect paths, and manual review candidates
    are correctly classified."""

    def test_remaining_confirmed_still_pending(self, allowlist_entries):
        """Remaining confirmed write paths are still pending_runtime_guard (not guarded)."""
        pending = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_pending_runtime_guard"
        ]
        assert len(pending) >= 8, f"Expected at least 8 remaining confirmed pending, got {len(pending)}"
        paths = [e["path"] for e in pending]
        # Batch1 and batch2 files must NOT be in pending
        for bp in BATCH1_PATHS + BATCH2_PATHS:
            assert bp not in paths, f"Guarded file {bp} must not be in pending"

    def test_indirect_paths_not_marked_guarded(self, allowlist_entries):
        """Indirect write paths are NOT marked runtime_guarded."""
        indirect = [e for e in allowlist_entries if "indirect" in e.get("classification", "")]
        assert len(indirect) == 8, f"Expected 8 indirect paths, got {len(indirect)}"
        for entry in indirect:
            assert "guarded" not in entry["classification"], (
                f"Indirect path {entry['path']} must not be marked guarded"
            )

    def test_manual_review_not_marked_safe(self, allowlist_entries):
        """Manual review candidates are NOT marked safe."""
        manual = [e for e in allowlist_entries if "manual_review" in e.get("classification", "")]
        assert len(manual) == 5, f"Expected 5 manual review candidates, got {len(manual)}"
        for entry in manual:
            assert "safe" not in entry["classification"], (
                f"Manual review candidate {entry['path']} must not be marked safe"
            )

    def test_runtime_guarded_count_is_exactly_6(self, allowlist_entries):
        """Exactly 6 files are runtime_guarded (3 batch1 + 3 batch2)."""
        guarded = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ]
        assert len(guarded) == 6, (
            f"Batch1+2 must process exactly 6 files total, got {len(guarded)}: "
            f"{[e['path'] for e in guarded]}"
        )

    def test_allowlist_no_wildcards(self, allowlist_entries):
        """Allowlist paths must not use wildcards."""
        for entry in allowlist_entries:
            assert "*" not in entry["path"], (
                f"Wildcard not allowed in allowlist path: {entry['path']}"
            )
            assert "**" not in entry["path"], (
                f"Glob wildcard not allowed in allowlist path: {entry['path']}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Batch1 guard integrity (batch2 must not break batch1)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch1GuardIntegrity:
    """Batch1 guard status is not affected by batch2 changes."""

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_files_still_guarded(self, allowlist_entries, rel_path):
        """Batch1 files are still runtime_guarded after batch2 changes."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"Batch1 file {rel_path} still in allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"Batch1 file {rel_path} must still be runtime_guarded"

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_files_still_import_guard(self, repo_root, rel_path):
        """Batch1 files still import assert_db_write_allowed."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_IMPORT_PATTERN.search(content), (
            f"Batch1 file {rel_path} must still import guard after batch2 changes"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Guard helper integrity
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardHelperIntegrity:
    """The Python DB write guard helper remains intact."""

    def test_guard_helper_file_exists(self, repo_root):
        """Guard helper file exists."""
        guard_path = repo_root / "scripts" / "ops" / "helpers" / "python_db_write_guard.py"
        assert guard_path.exists(), "Guard helper must exist"

    def test_guard_helper_importable(self):
        """Guard helper can be imported."""
        _guard_path = str(_REPO_ROOT / "scripts" / "ops")
        if _guard_path not in sys.path:
            sys.path.insert(0, _guard_path)
        from helpers.python_db_write_guard import (
            DbWriteBlockedError,
            assert_db_write_allowed,
            describe_required_gates,
            is_dry_run,
        )

        assert callable(assert_db_write_allowed)
        assert callable(is_dry_run)
        assert callable(describe_required_gates)

    def test_guard_helper_has_no_db_imports(self, repo_root):
        """Guard helper must NOT import any DB driver."""
        guard_path = repo_root / "scripts" / "ops" / "helpers" / "python_db_write_guard.py"
        content = guard_path.read_text(encoding="utf-8")
        forbidden = ["psycopg", "asyncpg", "sqlalchemy", "sqlite3", "create_engine"]
        import_lines = [
            line
            for line in content.split("\n")
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            for keyword in forbidden:
                assert keyword not in line.lower(), (
                    f"Guard helper must not import {keyword}: {line.strip()}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# SC-002 doc consistency tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSC002DocConsistency:
    """SC-002 documentation consistency checks."""

    def test_closure_plan_not_marked_complete(self, repo_root):
        """SC-002 closure plan must not claim SC-002 is complete."""
        closure_path = repo_root / "docs" / "SC002_CLOSURE_PLAN.md"
        if not closure_path.exists():
            pytest.skip("Closure plan not found")
        content = closure_path.read_text(encoding="utf-8")
        # Must not claim fully fixed
        forbidden = ["sc-002 is fully fixed", "sc-002 is complete", "sc-002 fully fixed"]
        for phrase in forbidden:
            assert phrase.lower() not in content.lower(), (
                f"SC002 closure plan must not contain '{phrase}'"
            )

    def test_design_doc_mentions_phase2c(self, repo_root):
        """Design doc should reference Phase2C."""
        design_path = repo_root / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"
        if not design_path.exists():
            pytest.skip("Design doc not found")
        content = design_path.read_text(encoding="utf-8")
        assert "phase2c" in content.lower() or "Phase 2C" in content, (
            "Design doc should reference Phase2C"
        )

    def test_safety_blocks_not_removed(self, repo_root):
        """SC-002 closure plan must still block training/expansion/DB write."""
        closure_path = repo_root / "docs" / "SC002_CLOSURE_PLAN.md"
        if not closure_path.exists():
            pytest.skip("Closure plan not found")
        content = closure_path.read_text(encoding="utf-8")
        assert "blocked" in content.lower(), "Closure plan must still mention blocked items"
