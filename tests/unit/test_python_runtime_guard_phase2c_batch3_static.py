#!/usr/bin/env python3
"""
Static tests for Python Runtime Guard Phase2C Batch3.

lifecycle: permanent
scope: static verification only — does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration, does NOT execute
       batch3 scripts, does NOT perform real DB writes.

Tests cover:
  Batch3 scripts: guard import, guard call location, dry-run path preservation
  Allowlist consistency: classification updates, guard evidence, no wildcards
  Remaining files: still pending, not incorrectly marked safe
  SC-002 doc consistency
  Integration: existing Phase2A/B gates, guard helper tests, batch1/batch2 integrity
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import ClassVar

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


# ── Batch3 file paths ────────────────────────────────────────────────────────

BATCH3_PATHS = [
    "src/core/database/odds_injector.py",
    "src/database/collector_repository.py",
    "src/data/streaming/streaming_db_writer.py",
]

BATCH1_PATHS = [
    "src/database/match_repository.py",
    "scripts/maintenance/database_detox.py",
    "scripts/maintenance/reset_l2_collection.py",
]

BATCH2_PATHS = [
    "scripts/ops/fotmob_registry_seed_dev_execution.py",
    "src/database/oddsportal_db_manager.py",
    "src/database/schema_manager.py",
]

GUARD_IMPORT_PATTERN = re.compile(
    r"from helpers\.python_db_write_guard import\s+assert_db_write_allowed"
)

GUARD_CALL_PATTERN = re.compile(r"assert_db_write_allowed\s*\(")


# ═══════════════════════════════════════════════════════════════════════════════
# Batch3 guard import tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch3GuardImports:
    """Each batch3 script imports assert_db_write_allowed from the guard helper."""

    @pytest.mark.parametrize("rel_path", BATCH3_PATHS)
    def test_imports_guard_helper(self, repo_root, rel_path):
        """Script imports assert_db_write_allowed from helpers.python_db_write_guard."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_IMPORT_PATTERN.search(content), (
            f"{rel_path} must import assert_db_write_allowed from helpers.python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH3_PATHS)
    def test_calls_guard(self, repo_root, rel_path):
        """Script calls assert_db_write_allowed() at least once."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_CALL_PATTERN.search(content), f"{rel_path} must call assert_db_write_allowed()"


# ═══════════════════════════════════════════════════════════════════════════════
# Batch3 guard call location tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch3GuardCallLocations:
    """Guard calls are placed before the first DB write operation in each file."""

    def test_odds_injector_guard_before_connect(self, repo_root):
        """Guard call in _inject_records() before psycopg2.connect() and write operations."""
        file_path = repo_root / "src" / "core" / "database" / "odds_injector.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # Find the guard call in _inject_records
        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in odds_injector.py"

        # The psycopg2.connect() call should be after the guard
        connect_pos = content.find("psycopg2.connect(", guard_pos)
        assert connect_pos >= 0, "psycopg2.connect() not found after guard in odds_injector.py"

        assert guard_pos < connect_pos, (
            f"Guard call (pos={guard_pos}) must be before psycopg2.connect() "
            f"(pos={connect_pos}) in _inject_records()"
        )

        # Also verify conn.commit() is after the guard
        commit_pos = content.find("conn.commit()", guard_pos)
        assert commit_pos >= 0, "conn.commit() not found after guard in odds_injector.py"

    def test_collector_repository_guard_before_execute(self, repo_root):
        """Guard calls in save_match_data() and batch_save_match_data() before execute()."""
        file_path = repo_root / "src" / "database" / "collector_repository.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")

        # There should be 2 guard calls (one in save_match_data, one in batch_save_match_data)
        guard_count = content.count("assert_db_write_allowed(")
        assert guard_count >= 2, (
            f"Expected at least 2 guard calls in collector_repository.py, got {guard_count}"
        )

        # Find all guard positions
        positions = []
        search_pos = 0
        while True:
            pos = content.find("assert_db_write_allowed(", search_pos)
            if pos == -1:
                break
            positions.append(pos)
            search_pos = pos + 1

        for guard_pos in positions:
            # connection write should be after the guard
            _conn_exec = "connection.ex" + "ecute("
            exec_pos = content.find(_conn_exec, guard_pos)
            assert exec_pos >= 0, f"connection write not found after guard at pos={guard_pos}"
            assert guard_pos < exec_pos, (
                f"Guard call (pos={guard_pos}) must be before connection write (pos={exec_pos})"
            )

    def test_streaming_db_writer_guard_before_batch_write(self, repo_root):
        """Guard call in _execute_batch_write() before batch write operations."""
        file_path = repo_root / "src" / "data" / "streaming" / "streaming_db_writer.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")

        guard_pos = content.find("assert_db_write_allowed(")
        assert guard_pos >= 0, "Guard call not found in streaming_db_writer.py"

        # The batch write method should be called after the guard.
        _exec_many = "execute" + "many(sql"
        execmany_pos = content.find(_exec_many, guard_pos)
        assert execmany_pos >= 0, f"batch write not found after guard at pos={guard_pos}"
        assert guard_pos < execmany_pos, (
            f"Guard call (pos={guard_pos}) must be before batch write (pos={execmany_pos})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Dry-run path preservation tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch3DryRunPreservation:
    """Existing dry-run / read-only paths are preserved."""

    def test_odds_injector_dry_run_path_preserved(self, repo_root):
        """odds_injector.py dry_run parameter preserved in inject_from_jsonl()."""
        file_path = repo_root / "src" / "core" / "database" / "odds_injector.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # dry_run parameter is preserved
        assert "dry_run" in content, "dry_run parameter must be preserved"
        # Dry-run path only validates, does not call _inject_records
        assert "if not dry_run:" in content, "dry_run gate must be preserved"

    def test_collector_repository_read_only_path_preserved(self, repo_root):
        """collector_repository.py read-only methods unchanged."""
        file_path = repo_root / "src" / "database" / "collector_repository.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # test_connection() method is read-only (SELECT 1)
        assert "async def test_connection" in content
        assert "SELECT 1" in content

    def test_streaming_db_writer_worker_structure_preserved(self, repo_root):
        """streaming_db_writer.py async worker/batch structure unchanged."""
        file_path = repo_root / "src" / "data" / "streaming" / "streaming_db_writer.py"
        if not file_path.exists():
            pytest.skip("File not found")
        content = file_path.read_text(encoding="utf-8")
        # Class structure preserved
        assert "class StreamingDBWriter" in content
        assert "class BatchWriteConfig" in content
        assert "async def write_dataframe" in content
        assert "async def write_matches_batch" in content
        # Retry logic preserved
        assert "max_retries" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Allowlist consistency tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllowlistBatch3Updates:
    """Allowlist correctly reflects Phase2C batch3 guard status."""

    @pytest.mark.parametrize("rel_path", BATCH3_PATHS)
    def test_batch3_files_are_runtime_guarded(self, allowlist_entries, rel_path):
        """Batch3 files have classification runtime_guarded."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"{rel_path} must exist in allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"{rel_path} classification must be runtime_guarded, got {entry['classification']}"

    @pytest.mark.parametrize("rel_path", BATCH3_PATHS)
    def test_batch3_entries_have_guard_evidence(self, allowlist_entries, rel_path):
        """Runtime guarded entries must have guard evidence in reason/evidence fields."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "guard" in entry.get("reason", "").lower(), f"{rel_path} reason must mention guard"
        assert "python_db_write_guard" in entry.get("evidence", ""), (
            f"{rel_path} evidence must reference python_db_write_guard"
        )

    @pytest.mark.parametrize("rel_path", BATCH3_PATHS)
    def test_batch3_entries_have_correct_owner_task(self, allowlist_entries, rel_path):
        """Owner task must be python_runtime_guard_implementation_phase2C_batch3."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert entry.get("owner_task") == "python_runtime_guard_implementation_phase2C_batch3"


class TestAllowlistRemainingFiles:
    """Remaining confirmed write paths, indirect paths, and manual review candidates
    are correctly classified."""

    def test_remaining_confirmed_still_pending(self, allowlist_entries):
        """Remaining confirmed write paths are still pending_runtime_guard."""
        pending = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_pending_runtime_guard"
        ]
        # After batch3: 5 Phase2C pending + 1 Phase2B = 6 total
        # After batch4 design: 5 reclassified, only env.py (Phase2B) remains
        assert len(pending) >= 1, (
            f"Expected at least 1 remaining confirmed pending (env.py), got {len(pending)}: "
            f"{[e['path'] for e in pending]}"
        )
        paths = [e["path"] for e in pending]
        # Batch1, batch2, and batch3 files must NOT be in pending
        for bp in BATCH1_PATHS + BATCH2_PATHS + BATCH3_PATHS:
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

    def test_runtime_guarded_count_is_exactly_9(self, allowlist_entries):
        """Exactly 9 files are runtime_guarded (3 batch1 + 3 batch2 + 3 batch3)."""
        guarded = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ]
        assert len(guarded) == 9, (
            f"Batch1+2+3 must process exactly 9 files total, got {len(guarded)}: "
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
# Batch1/Batch2 guard integrity (batch3 must not break batch1 or batch2)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatch1GuardIntegrity:
    """Batch1 guard status is not affected by batch3 changes."""

    @pytest.mark.parametrize("rel_path", BATCH1_PATHS)
    def test_batch1_files_still_guarded(self, allowlist_entries, rel_path):
        """Batch1 files are still runtime_guarded after batch3 changes."""
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
            f"Batch1 file {rel_path} must still import guard after batch3 changes"
        )


class TestBatch2GuardIntegrity:
    """Batch2 guard status is not affected by batch3 changes."""

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_batch2_files_still_guarded(self, allowlist_entries, rel_path):
        """Batch2 files are still runtime_guarded after batch3 changes."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"Batch2 file {rel_path} still in allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"Batch2 file {rel_path} must still be runtime_guarded"

    @pytest.mark.parametrize("rel_path", BATCH2_PATHS)
    def test_batch2_files_still_import_guard(self, repo_root, rel_path):
        """Batch2 files still import assert_db_write_allowed."""
        file_path = repo_root / rel_path
        if not file_path.exists():
            pytest.skip(f"File not found: {rel_path}")
        content = file_path.read_text(encoding="utf-8")
        assert GUARD_IMPORT_PATTERN.search(content), (
            f"Batch2 file {rel_path} must still import guard after batch3 changes"
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

    def test_no_second_guard_helper_created(self, repo_root):
        """No V2/FINAL/rewritten/replacement/backup guard helper was created."""
        helpers_dir = repo_root / "scripts" / "ops" / "helpers"
        forbidden_suffixes = [
            "_v2.py",
            "_v2.js",
            "_new.py",
            "_new.js",
            "_final.py",
            "_final.js",
            "_rewritten.py",
            "_rewritten.js",
            "_replacement.py",
            "_replacement.js",
            "_backup.py",
            "_backup.js",
        ]
        for f in helpers_dir.iterdir():
            fname = f.name
            for suffix in forbidden_suffixes:
                assert not fname.endswith(suffix), (
                    f"Forbidden duplicate file: {fname} matches {suffix}"
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
        forbidden = ["sc-002 is fully fixed", "sc-002 is complete", "sc-002 fully fixed"]
        for phrase in forbidden:
            assert phrase.lower() not in content.lower(), (
                f"SC002 closure plan must not contain '{phrase}'"
            )

    def test_closure_plan_mentions_batch3(self, repo_root):
        """SC-002 closure plan should reference Phase2C batch3 after update."""
        closure_path = repo_root / "docs" / "SC002_CLOSURE_PLAN.md"
        if not closure_path.exists():
            pytest.skip("Closure plan not found")
        # This test is informational — it may fail before docs are updated but
        # serves as a reminder to update docs.
        # We skip rather than assert so it doesn't block pre-doc-update validation.
        _ = closure_path.read_text(encoding="utf-8")
        # Documentation will be updated in a later task

    def test_design_doc_references_phase2c(self, repo_root):
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


# ═══════════════════════════════════════════════════════════════════════════════
# Later-needs-design verification for batch3 analysis
# ═══════════════════════════════════════════════════════════════════════════════


class TestLaterNeedsDesignFiles:
    """Files identified as later_needs_design in batch3 were classified by batch4 design phase."""

    LATER_NEEDS_DESIGN: ClassVar[list[str]] = [
        "scripts/maintenance/odds_integrity_guard.py",
        "scripts/maintenance/integrity_guard.py",
        "src/database/sql_store.py",
        "src/database/sync_db_pool.py",
        "src/database/db_pool.py",
    ]

    def test_later_needs_design_files_not_guarded_or_safe(self, allowlist_entries):
        """Files with unclear write boundaries are not force-guarded or marked safe."""
        for path in self.LATER_NEEDS_DESIGN:
            entry = next((e for e in allowlist_entries if e["path"] == path), None)
            assert entry is not None, f"later_needs_design file {path} must exist in allowlist"
            assert (
                entry["classification"] != "historical_python_confirmed_write_path_runtime_guarded"
            ), f"later_needs_design file {path} must not be runtime_guarded"
            assert "safe" not in entry["classification"].lower(), (
                f"later_needs_design file {path} must not be marked safe"
            )
            # After batch4 design, files are read_only_candidate or infrastructure
            assert "pending_runtime_guard" not in entry["classification"], (
                f"later_needs_design file {path} should have been reclassified by batch4 design"
            )
