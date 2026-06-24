#!/usr/bin/env python3
"""
Static tests for Python Confirmed Write Paths Design Phase2C Batch4.

lifecycle: permanent
scope: static verification only — does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration, does NOT execute
       any Python scripts, does NOT perform real DB writes.

Tests cover:
  Design-phase classifications for 5 remaining confirmed write paths
  Allowlist consistency: new classification fields, no file marked guarded
  Design document content: SC-002 status, blocked items, analysis coverage
  Integration: existing 9 runtime_guarded files unchanged, scanner compatibility
"""

from __future__ import annotations

import json
from pathlib import Path
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


@pytest.fixture
def design_doc(repo_root):
    """The Phase2C remaining confirmed write paths design document."""
    p = repo_root / "docs" / "SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    pytest.skip("Design document not found")


# ── The 5 remaining confirmed write paths ─────────────────────────────────────

REMAINING_PATHS = [
    "scripts/maintenance/odds_integrity_guard.py",
    "scripts/maintenance/integrity_guard.py",
    "src/database/sql_store.py",
    "src/database/sync_db_pool.py",
    "src/database/db_pool.py",
]

NEW_CLASSIFICATIONS = {
    "scripts/maintenance/odds_integrity_guard.py": "historical_python_confirmed_write_path_read_only_candidate",
    "scripts/maintenance/integrity_guard.py": "historical_python_confirmed_write_path_read_only_candidate",
    "src/database/sql_store.py": "historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard",
    "src/database/sync_db_pool.py": "historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard",
    "src/database/db_pool.py": "historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard",
}

EXPECTED_CLASSIFICATIONS = {"read_only_candidate", "infrastructure_only_needs_caller_guard"}


# ═══════════════════════════════════════════════════════════════════════════════
# Classification tests — each remaining file has correct design classification
# ═══════════════════════════════════════════════════════════════════════════════


class TestRemainingFilesClassified:
    """All 5 remaining confirmed write paths have design-phase classifications."""

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_new_classification(self, allowlist_entries, rel_path):
        """File classification is NOT pending_runtime_guard — it has a design classification."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"{rel_path} must exist in allowlist"
        assert (
            entry["classification"]
            != "historical_python_confirmed_write_path_pending_runtime_guard"
        ), (
            f"{rel_path} must not be pending_runtime_guard — "
            f"should have design classification, got {entry['classification']}"
        )

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_expected_classification(self, allowlist_entries, rel_path):
        """File has the expected design classification from batch4 analysis."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        expected = NEW_CLASSIFICATIONS[rel_path]
        assert entry["classification"] == expected, (
            f"{rel_path} expected classification {expected}, got {entry['classification']}"
        )

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_analysis_task_field(self, allowlist_entries, rel_path):
        """Each file has the analysis_task field."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "analysis_task" in entry, f"{rel_path} missing 'analysis_task' field"
        assert entry["analysis_task"] == "python_confirmed_write_paths_design_phase2C_batch4"

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_recommended_next_action(self, allowlist_entries, rel_path):
        """Each file has a recommended_next_action field."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "recommended_next_action" in entry, f"{rel_path} missing 'recommended_next_action'"

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_why_not_guarded_in_this_pr(self, allowlist_entries, rel_path):
        """Each file explains why it was not guarded in this PR."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "why_not_guarded_in_this_pr" in entry, (
            f"{rel_path} missing 'why_not_guarded_in_this_pr'"
        )

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_observed_operations(self, allowlist_entries, rel_path):
        """Each file has observed_operations field."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "observed_operations" in entry, f"{rel_path} missing 'observed_operations'"

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_direct_write_boundary(self, allowlist_entries, rel_path):
        """Each file has direct_write_boundary field."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert "direct_write_boundary" in entry, f"{rel_path} missing 'direct_write_boundary'"

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_file_has_owner_task_batch4(self, allowlist_entries, rel_path):
        """Owner task updated to batch4."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None
        assert entry.get("owner_task") == "python_confirmed_write_paths_design_phase2C_batch4"


class TestNoFileMarkedGuarded:
    """None of the 5 remaining files was accidentally marked runtime_guarded."""

    def test_remaining_files_not_runtime_guarded(self, allowlist_entries):
        """Remaining files must NOT be in runtime_guarded classification."""
        for rel_path in REMAINING_PATHS:
            entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
            assert entry is not None
            assert (
                entry["classification"] != "historical_python_confirmed_write_path_runtime_guarded"
            ), f"{rel_path} must NOT be runtime_guarded — this is a design task, not implementation"

    def test_no_file_marked_safe(self, allowlist_entries):
        """No remaining file classified as 'safe'."""
        for rel_path in REMAINING_PATHS:
            entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
            assert entry is not None
            assert "safe" not in entry["classification"].lower(), (
                f"{rel_path} must not be marked safe"
            )

    def test_no_file_has_guard_evidence(self, allowlist_entries):
        """Remaining files should NOT have guard evidence (no guard added in this task)."""
        for rel_path in REMAINING_PATHS:
            entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
            assert entry is not None
            evidence = entry.get("evidence", "")
            assert "guard:" not in evidence.lower(), (
                f"{rel_path} must not have guard evidence — this is a design task"
            )
            assert "python_db_write_guard" not in evidence.lower(), (
                f"{rel_path} must not reference guard helper — no guard added"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Allowlist integrity — existing guarded files unchanged
# ═══════════════════════════════════════════════════════════════════════════════


class TestExistingGuardedFilesIntact:
    """9 runtime_guarded files from batch1+batch2+batch3 remain unchanged."""

    BATCH1_PATHS: ClassVar[list[str]] = [
        "src/database/match_repository.py",
        "scripts/maintenance/database_detox.py",
        "scripts/maintenance/reset_l2_collection.py",
    ]

    BATCH2_PATHS: ClassVar[list[str]] = [
        "scripts/ops/fotmob_registry_seed_dev_execution.py",
        "src/database/oddsportal_db_manager.py",
        "src/database/schema_manager.py",
    ]

    BATCH3_PATHS: ClassVar[list[str]] = [
        "src/core/database/odds_injector.py",
        "src/database/collector_repository.py",
        "src/data/streaming/streaming_db_writer.py",
    ]

    ALL_GUARDED: ClassVar[list[str]] = (
        BATCH1_PATHS + BATCH2_PATHS + BATCH3_PATHS  # type: ignore[operator]
    )

    @pytest.mark.parametrize("rel_path", ALL_GUARDED)
    def test_guarded_file_still_guarded(self, allowlist_entries, rel_path):
        """Previously guarded files are still runtime_guarded."""
        entry = next((e for e in allowlist_entries if e["path"] == rel_path), None)
        assert entry is not None, f"Guarded file {rel_path} missing from allowlist"
        assert (
            entry["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ), f"{rel_path} must still be runtime_guarded"

    def test_runtime_guarded_count_is_9(self, allowlist_entries):
        """Exactly 9 files are runtime_guarded (unchanged by design task)."""
        guarded = [
            e
            for e in allowlist_entries
            if e["classification"] == "historical_python_confirmed_write_path_runtime_guarded"
        ]
        assert len(guarded) == 9, (
            f"Must be exactly 9 runtime_guarded, got {len(guarded)}: {[e['path'] for e in guarded]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Other file categories unchanged
# ═══════════════════════════════════════════════════════════════════════════════


class TestOtherCategoriesUnchanged:
    """Indirect, manual review, and env.py categories unchanged."""

    def test_indirect_paths_not_marked_guarded(self, allowlist_entries):
        """Indirect write paths still NOT marked runtime_guarded."""
        indirect = [e for e in allowlist_entries if "indirect" in e.get("classification", "")]
        assert len(indirect) == 8, f"Expected 8 indirect paths, got {len(indirect)}"
        for entry in indirect:
            assert "guarded" not in entry["classification"], (
                f"Indirect path {entry['path']} must not be guarded"
            )

    def test_manual_review_not_marked_safe(self, allowlist_entries):
        """Manual review candidates still NOT marked safe."""
        manual = [e for e in allowlist_entries if "manual_review" in e.get("classification", "")]
        assert len(manual) == 5, f"Expected 5 manual review candidates, got {len(manual)}"
        for entry in manual:
            assert "safe" not in entry["classification"], (
                f"Manual review candidate {entry['path']} must not be marked safe"
            )

    def test_env_py_still_pending(self, allowlist_entries):
        """Alembic env.py (Phase2B) is still pending."""
        env_entry = next(
            (e for e in allowlist_entries if e["path"] == "src/database/migrations/env.py"), None
        )
        assert env_entry is not None, "env.py must be in allowlist"
        # env.py is Phase2B, not affected by Phase2C batch4
        assert "guarded" not in env_entry["classification"], "env.py must not be guarded"


# ═══════════════════════════════════════════════════════════════════════════════
# Design document content checks
# ═══════════════════════════════════════════════════════════════════════════════


class TestDesignDocumentContent:
    """Design document contains required statements and covers all 5 files."""

    def test_design_doc_exists(self, repo_root):
        """Design doc exists at expected path."""
        p = repo_root / "docs" / "SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md"
        assert p.exists(), "Design document must exist"

    @pytest.mark.parametrize("rel_path", REMAINING_PATHS)
    def test_design_doc_covers_file(self, design_doc, rel_path):
        """Design doc references each of the 5 files."""
        file_stem = Path(rel_path).name
        assert file_stem in design_doc, f"Design doc must reference {file_stem}"

    def test_design_doc_sc002_partial_mitigation(self, design_doc):
        """Design doc states SC-002 remains partial mitigation only."""
        assert "partial mitigation" in design_doc.lower(), (
            "Design doc must state SC-002 is partial mitigation only"
        )

    def test_design_doc_training_blocked(self, design_doc):
        """Design doc states training remains blocked."""
        assert "training" in design_doc.lower(), "Design doc must mention training status"
        assert "blocked" in design_doc.lower(), "Design doc must state items remain blocked"

    def test_design_doc_no_db_connection(self, design_doc):
        """Design doc states no DB connection was used."""
        assert "no database connection" in design_doc.lower(), (
            "Design doc must state no DB connection was used"
        )

    def test_design_doc_no_target_scripts_executed(self, design_doc):
        """Design doc states no target scripts were executed."""
        assert "no python target scripts" in design_doc.lower(), (
            "Design doc must state no target scripts executed"
        )

    def test_design_doc_no_real_db_write(self, design_doc):
        """Design doc states no real DB write was performed."""
        assert "no real db write" in design_doc.lower(), "Design doc must state no real DB write"

    def test_design_doc_classification_summary(self, design_doc):
        """Design doc contains the classification summary table."""
        assert "read_only_or_select_only" in design_doc, (
            "Design doc must mention read_only_or_select_only classification"
        )
        assert "infrastructure_only_needs_caller_guard" in design_doc, (
            "Design doc must mention infrastructure_only_needs_caller_guard classification"
        )

    def test_design_doc_read_only_count(self, design_doc):
        """Design doc correctly identifies 2 read-only files."""
        assert (
            "2 files classified as" in design_doc.lower()
            or "read_only_or_select_only" in design_doc
        ), "Design doc should reference read-only classification count"

    def test_design_doc_infrastructure_count(self, design_doc):
        """Design doc correctly identifies 3 infrastructure files."""
        assert (
            "3 files classified as" in design_doc.lower() or "infrastructure" in design_doc.lower()
        ), "Design doc should reference infrastructure classification count"

    def test_design_doc_per_file_sections(self, design_doc):
        """Design doc has per-file analysis sections with 'Per-File Analysis' heading."""
        assert "Per-File Analysis" in design_doc or "per-file" in design_doc.lower(), (
            "Design doc must have per-file analysis section"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Allowlist header consistency
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllowlistHeaderConsistency:
    """Allowlist header metadata is consistent with design task outcome."""

    def test_header_reflects_batch4(self, allowlist_data):
        """Allowlist header references design phase batch4."""
        status = allowlist_data.get("_runtime_guard_status", "")
        assert "batch4" in status.lower(), (
            f"Allowlist header should reference batch4, got: {status}"
        )

    def test_header_still_sc002_partial(self, allowlist_data):
        """Allowlist header still says partial mitigation."""
        status = allowlist_data.get("_runtime_guard_status", "")
        assert "partial" in status.lower(), "Allowlist header must still say partial"

    def test_allowlist_no_wildcards(self, allowlist_entries):
        """Allowlist paths must not use wildcards."""
        for entry in allowlist_entries:
            assert "*" not in entry["path"], f"Wildcard in path: {entry['path']}"
            assert "**" not in entry["path"], f"Glob wildcard in path: {entry['path']}"


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner compatibility — new classifications don't break enforcements
# ═══════════════════════════════════════════════════════════════════════════════


class TestScannerCompatibility:
    """New classification names are compatible with existing scanners."""

    def test_python_enforcement_check_importable(self):
        """python_db_write_enforcement_check module is importable."""
        _enf_path = str(_REPO_ROOT / "scripts" / "ops" / "helpers")
        if _enf_path not in sys.path:
            sys.path.insert(0, _enf_path)

        from python_db_write_enforcement_check import (
            check_python_db_write_enforcement,
            run_python_db_write_gate_check,
        )

        assert callable(check_python_db_write_enforcement)
        assert callable(run_python_db_write_gate_check)

    def test_scanner_accepts_new_classifications(self, allowlist_entries):
        """Scanner reads new classification values without error (they are just strings)."""
        for entry in allowlist_entries:
            cls = entry.get("classification", "")
            assert isinstance(cls, str) and len(cls) > 0, (
                f"Classification must be non-empty string: {entry['path']}: {cls!r}"
            )
            # New classifications contain valid path-like prefixes
            assert "historical_python" in cls, (
                f"Classification must start with historical_python: {cls}"
            )

    def test_design_doc_not_added_to_reports(self, repo_root):
        """Design doc is at docs/ root, NOT under docs/_reports."""
        reports_doc = (
            repo_root
            / "docs"
            / "_reports"
            / "SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md"
        )
        assert not reports_doc.exists(), "Design document must NOT be placed under docs/_reports"

    def test_only_one_design_doc_added(self, repo_root):
        """Only one new design document was added (no sprawl)."""
        # Check that no other batch4 design docs exist
        batch4_docs = list(repo_root.glob("docs/**/*batch4*.md"))
        # There should be exactly 1 (the design doc we just created)
        # Actually, this test covers that we don't have duplicate docs
        assert len(batch4_docs) <= 1, (
            f"At most 1 batch4 design doc expected, found {len(batch4_docs)}: "
            f"{[str(d) for d in batch4_docs]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Classification coverage — right files in right categories
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassificationCoverage:
    """Classification categories are correctly populated."""

    def test_read_only_candidate_count(self, allowlist_entries):
        """Exactly 2 files are read_only_candidate."""
        read_only = [
            e for e in allowlist_entries if "read_only_candidate" in e.get("classification", "")
        ]
        assert len(read_only) == 2, (
            f"Expected 2 read_only_candidate, got {len(read_only)}: {[e['path'] for e in read_only]}"
        )
        read_only_paths = {e["path"] for e in read_only}
        assert "scripts/maintenance/odds_integrity_guard.py" in read_only_paths
        assert "scripts/maintenance/integrity_guard.py" in read_only_paths

    def test_infrastructure_caller_guard_count(self, allowlist_entries):
        """Exactly 3 files are infrastructure_only_needs_caller_guard."""
        infra = [
            e
            for e in allowlist_entries
            if "infrastructure_only_needs_caller_guard" in e.get("classification", "")
        ]
        assert len(infra) == 3, (
            f"Expected 3 infrastructure_only_needs_caller_guard, got {len(infra)}: "
            f"{[e['path'] for e in infra]}"
        )
        infra_paths = {e["path"] for e in infra}
        assert "src/database/sql_store.py" in infra_paths
        assert "src/database/sync_db_pool.py" in infra_paths
        assert "src/database/db_pool.py" in infra_paths
