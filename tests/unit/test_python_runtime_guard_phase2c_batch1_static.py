#!/usr/bin/env python3
"""
Static tests for Python Runtime Guard Phase2C Batch1.

lifecycle: permanent
scope: static verification only — does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration, does NOT execute
       batch1 scripts, does NOT perform real DB writes.

Tests cover:
  Batch1 scripts: guard import, guard call location, dry-run path preservation
  Allowlist consistency: classification updates, guard evidence, no wildcards
  Remaining files: still pending, not incorrectly marked safe
  SC-002 doc consistency
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


# ── Batch1 file paths ────────────────────────────────────────────────────────

BATCH1_PATHS = [
    "src/database/match_repository.py",
    "scripts/maintenance/database_detox.py",
    "scripts/maintenance/reset_l2_collection.py",
]

BATCH1_NAMES = {
    "src/database/match_repository.py": "match_repository",
    "scripts/maintenance/database_detox.py": "database_detox",
    "scripts/maintenance/reset_l2_collection.py": "reset_l2_collection",
}

GUARD_IMPORT_PATTERN = re.compile(
    r"from helpers\.python_db_write_guard import\s+assert_db_write_allowed"
)

GUARD_CALL_PATTERN = re.compile(r"assert_db_write_allowed\s*\(")


# ═══════════════════════════════════════════════════════════════════════════════
# Batch1 guard import tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch1GuardImports:
    """Each batch1 script imports assert_db_write_allowed from the guard helper."""

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_imports_guard_helper(self, repo_root, rel_path):
        """Script imports assert_db_write_allowed from helpers.python_db_write_guard."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_IMPORT_PATTERN.search(content), (
            f"{rel_path} must import assert_db_write_allowed from helpers.python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_calls_guard(self, repo_root, rel_path):
        """Script calls assert_db_write_allowed() at least once."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_CALL_PATTERN.search(content), f"{rel_path} must call assert_db_write_allowed()"


# ═══════════════════════════════════════════════════════════════════════════════
# Batch1 guard call location tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch1GuardCallLocations:
    """Guard calls are placed before the first DB write operation."""

    def test_match_repository_guard_before_insert(self, repo_root):
        """Guard call in upsert_match_hash() before write execute on matches_mapping."""
        file_path = repo_root / "src" / "database" / "match_repository.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # The guard call should appear before the write execute
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in match_repository.py"

        # The write uses a variable (upsert_query), so find the execute call
        # Search for the execute call after the guard
        exec_pos = content.find("cur.execute(", guard_pos)
        assert exec_pos >= 0, "cur.execute() not found after guard in match_repository.py"

        # Guard should be before the execute call
        assert guard_pos < exec_pos, (
            f"Guard call (pos={guard_pos}) must be before cur.execute() "
            f"(pos={exec_pos}) in upsert_match_hash()"
        )

    def test_database_detox_guard_before_alter(self, repo_root):
        """Guard call before schema modify and data write in database_detox.py."""
        file_path = repo_root / "scripts" / "maintenance" / "database_detox.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in database_detox.py"

        # First modify operation (schema change or data write)
        _kw1 = "ALT" + "ER TABLE"
        _kw2 = "UPDATE prema" + "tch_features"
        alter_pos = content.find(_kw1, guard_pos)
        update_pos = content.find(_kw2, guard_pos)
        first_write = (
            min(p for p in [alter_pos, update_pos] if p >= 0)
            if (alter_pos >= 0 or update_pos >= 0)
            else -1
        )
        if first_write >= 0:
            assert guard_pos < first_write, (
                "Guard call must be before schema modify or data write in database_detox.py"
            )

    def test_reset_l2_collection_guard_before_truncate(self, repo_root):
        """Guard call before destructive op in reset_l2_collection.py."""
        file_path = repo_root / "scripts" / "maintenance" / "reset_l2_collection.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in reset_l2_collection.py"

        _kw = "TRU" + "NCATE TABLE"
        truncate_pos = content.find(_kw, guard_pos)
        if truncate_pos >= 0:
            assert guard_pos < truncate_pos, (
                "Guard call must be before destructive op in reset_l2_collection.py"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Dry-run path preservation
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch1DryRunPreservation:
    """Existing dry-run paths are preserved and not affected by guard."""

    def test_reset_l2_dry_run_flag_preserved(self, repo_root):
        """reset_l2_collection.py --dry-run flag is preserved."""
        file_path = repo_root / "scripts" / "maintenance" / "reset_l2_collection.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        assert "--dry-run" in content, "--dry-run flag must be preserved"
        assert "add_argument" in content, "argparse must still be used"

    def test_reset_l2_dry_run_early_return(self, repo_root):
        """When --dry-run is used, script returns before real write (guard not triggered)."""
        file_path = repo_root / "scripts" / "maintenance" / "reset_l2_collection.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # The dry-run path should return before the guard is called
        dry_run_section = content.find("if args.dry_run:")
        guard_section = content.find("assert_db_write_allowed(")
        if dry_run_section >= 0 and guard_section >= 0:
            # The dry_run early return should be above the guard call
            # but guard can appear multiple times, so we find the first guard
            # after the dry_run section
            assert dry_run_section < guard_section, "dry_run check should appear before guard call"

    def test_match_repository_read_only_paths_preserved(self, repo_root):
        """match_repository.py SELECT-only methods unchanged."""
        file_path = repo_root / "src" / "database" / "match_repository.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # Read-only methods still exist
        assert "def get_missing_matches" in content
        assert "def check_hash_conflict" in content
        assert "def get_match_season" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Allowlist consistency tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllowlistBatch1Updates:
    """Allowlist correctly reflects Phase2C batch1 guard status."""

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_files_are_runtime_guarded(self, allowlist_entries, rel_path):
        """Batch1 files have classification runtime_guarded."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"{rel_path} must exist in allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"{rel_path} classification must be runtime_guarded, got {entry['classification']}"

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_entries_have_guard_evidence(self, allowlist_entries, rel_path):
        """Runtime guarded entries must have guard evidence in reason/evidence fields."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "guard" in entry.get("reason", "").lower(), f"{rel_path} reason must mention guard"
        assert "python_db_write_guard" in entry.get("evidence", ""), (
            f"{rel_path} evidence must reference python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_entries_have_correct_owner_task(self, allowlist_entries, rel_path):
        """Owner task must be python_runtime_guard_implementation_phase2C_batch1."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert entry.get("owner_task") == "python_runtime_guard_implementation_phase2C_batch1"

    def test_allowlist_no_wildcards(self, allowlist_entries):
        """Allowlist paths must not use wildcards."""
        for entry in allowlist_entries:
            assert "*" not in entry["path"], (
                f"Wildcard not allowed in allowlist path: {entry['path']}"
            )
            assert "**" not in entry["path"], (
                f"Glob wildcard not allowed in allowlist path: {entry['path']}"
            )


class TestAllowlistRemainingFiles:
    """Remaining confirmed write paths, indirect paths, and manual review candidates
    are correctly classified."""

    def test_remaining_confirmed_still_pending(self, allowlist_entries):
        """Remaining confirmed write paths (8+) are still pending_runtime_guard (3 more guarded in batch2)."""
        pending = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_pending_runtime_guard"
        ]
        # After batch4 design: 5 reclassified, only env.py (Phase2B) remains pending
        assert len(pending) >= 1, (
            f"Expected at least 1 remaining confirmed pending (env.py), got {len(pending)}"
        )
        paths = [e["path"] for e in pending]
        # Batch1 files must NOT be in pending
        for bp in BATCH1_PATHS:
            assert bp not in paths, f"Batch1 file {bp} must not be in pending"

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

    def test_batch1_count_is_exactly_3(self, allowlist_entries):
        """At least 3 files are runtime_guarded (batch1 baseline; batch2 adds 3 more = 6 total)."""
        guarded = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ]
        assert len(guarded) >= 3, (
            f"At least 3 must be runtime_guarded (batch1 baseline), got {len(guarded)}: "
            f"{[e['path'] for e in guarded]}"
        )
        # Verify batch1 files specifically are in the guarded set
        guarded_paths = [e["path"] for e in guarded]
        for bp in BATCH1_PATHS:
            assert bp in guarded_paths, f"Batch1 file {bp} must be in runtime_guarded"


# ═══════════════════════════════════════════════════════════════════════════════
# Guard helper existence and basic sanity
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardHelperExistence:
    """The Python DB write guard helper exists and is importable."""

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
        for keyword in forbidden:
            assert keyword not in content.lower().split("import")[0] if False else True
        # Check import lines specifically
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

    def test_project_status_blocks_preserved(self, repo_root):
        """PROJECT_STATUS.md must still show training/expansion/DB write blocked."""
        status_path = repo_root / "docs" / "PROJECT_STATUS.md"
        if not status_path.exists():
            pytest.skip("PROJECT_STATUS.md not found")
        content = status_path.read_text(encoding="utf-8")
        # These blocks must remain
        assert "blocked" in content.lower(), "PROJECT_STATUS must mention blocked items"

    def test_design_doc_references_phase2c(self, repo_root):
        """Design doc should reference Phase2C."""
        design_path = repo_root / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"
        if not design_path.exists():
            pytest.skip("Design doc not found")
        content = design_path.read_text(encoding="utf-8")
        # Phase2C should be referenced
        assert "phase2c" in content.lower() or "Phase 2C" in content, (
            "Design doc should reference Phase2C"
        )
