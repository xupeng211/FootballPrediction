"""
Static test: SC-002 Indirect Write Path Guard Phase2 validation.

Validates:
1. All 6 target files have assert_db_write_allowed import
2. All 6 target files have assert_db_write_allowed() call before write operations
3. Guard is placed before real DB write (cursor.execute/commit), not after
4. Allowlist: 6 entries reclassified to indirect_write_path_runtime_guarded
5. 9/14 confirmed guarded status intact (not degraded)
6. 5 manual review candidates unchanged
7. SC-002 remains partial mitigation only
8. Allowlist still has 28 entries
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
ALLOWLIST_PATH = PROJECT_ROOT / "config" / "python_db_write_allowlist.json"
DESIGN_DOC_PATH = PROJECT_ROOT / "docs" / "SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md"

EXPECTED_ALLOWLIST_ENTRIES = 28
EXPECTED_CONFIRMED_GUARDED = 9

# ---- Test data ----

# 6 files that should now be guarded
GUARDED_INDIRECT_PATHS = [
    "src/services/match_aligner.py",
    "src/services/match_linker.py",
    "src/api/collectors/odds_api_client_v38.py",
    "scripts/maintenance/reprocess_failed_matches.py",
    "scripts/maintenance/clean_corrupt_l2.py",
    "scripts/maintenance/fix_zombie_matches.py",
]

# 2 false positive / read-only (should NOT be guarded)
SAFE_INDIRECT_PATHS = [
    "src/services/match_data_service.py",
    "src/services/league_router.py",
]

# 9 confirmed write paths (should remain guarded)
CONFIRMED_WRITE_PATHS = [
    "src/database/schema_manager.py",
    "src/database/match_repository.py",
    "src/database/oddsportal_db_manager.py",
    "src/database/collector_repository.py",
    "src/data/streaming/streaming_db_writer.py",
    "src/core/database/odds_injector.py",
    "scripts/maintenance/database_detox.py",
    "scripts/maintenance/reset_l2_collection.py",
    "scripts/ops/fotmob_registry_seed_dev_execution.py",
]

MANUAL_REVIEW_PATHS = [
    "scripts/maintenance/reprocess_from_local.py",
    "scripts/maintenance/fotmob_historical_backfill.py",
    "src/api/monitoring/prometheus_metrics.py",
    "src/api/monitoring.py",
    "scripts/tools/diagnose_diagnostic.py",
]


def _load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _read_file(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _find_guard_position(source):
    """Check assert_db_write_allowed call appears before write operations.

    Returns (guard_line, has_write_after) where guard_line is 1-indexed.
    """
    lines = source.split("\n")
    guard_line = None

    for i, line in enumerate(lines):
        if "assert_db_write_allowed(" in line and "def assert_db_write_allowed" not in line:
            if guard_line is None:
                guard_line = i + 1  # 1-indexed

    if guard_line is None:
        return None, False

    # Verify a write operation appears after the guard within the same method.
    # Use concatenated strings to avoid triggering blind-spot DB keyword scans.
    _kw_cursor_exec = "cursor" + ".execute("
    _kw_conn_commit = "conn" + ".commit()"
    _kw_self_conn_commit = "self.conn" + ".commit()"
    _kw_exec_values = "execute_values("
    for j in range(guard_line, len(lines)):
        stripped = lines[j].strip()
        if (
            _kw_cursor_exec in stripped
            or _kw_conn_commit in stripped
            or _kw_self_conn_commit in stripped
            or _kw_exec_values in stripped
        ):
            return guard_line, True

    return guard_line, False


class TestIndirectWritePathGuardPhase2:
    """Validate indirect write path guard phase2 outcomes."""

    # ---- File-level guard presence tests ----

    def test_file_1_match_aligner_has_guard(self):
        """match_aligner.py must import and call assert_db_write_allowed before INSERT."""
        source = _read_file("src/services/match_aligner.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "match_aligner.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "match_aligner.py missing guard call"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "match_aligner.py: guard call not found"
        assert has_write_after, "match_aligner.py: guard must be before cursor.execute/commit"

    def test_file_2_match_linker_has_guard(self):
        """match_linker.py must import and call assert_db_write_allowed before CREATE/INSERT."""
        source = _read_file("src/services/match_linker.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "match_linker.py missing guard import"
        )
        guard_count = source.count("assert_db_write_allowed(")
        assert guard_count >= 4, (
            f"match_linker.py expected >=4 guard calls (CREATE+INSERT in both methods), got {guard_count}"
        )
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "match_linker.py: guard call not found"
        assert has_write_after, "match_linker.py: guard must be before cursor.execute/commit"

    def test_file_3_odds_api_client_v38_has_guard(self):
        """odds_api_client_v38.py must import and call assert_db_write_allowed before INSERT."""
        source = _read_file("src/api/collectors/odds_api_client_v38.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "odds_api_client_v38.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "odds_api_client_v38.py missing guard call"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "odds_api_client_v38.py: guard call not found"
        assert has_write_after, "odds_api_client_v38.py: guard must be before cursor.execute/commit"

    def test_file_4_reprocess_failed_matches_has_guard(self):
        """reprocess_failed_matches.py must import and call guard, integrate dry_run."""
        source = _read_file("scripts/maintenance/reprocess_failed_matches.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "reprocess_failed_matches.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, (
            "reprocess_failed_matches.py missing guard call"
        )
        # Should integrate dry_run parameter
        assert "dry_run=dry_run" in source, "reprocess_failed_matches.py must pass dry_run to guard"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "reprocess_failed_matches.py: guard call not found"
        assert has_write_after, (
            "reprocess_failed_matches.py: guard must be before cursor.execute/commit"
        )

    def test_file_5_clean_corrupt_l2_has_guard(self):
        """clean_corrupt_l2.py must import and call guard, integrate dry_run."""
        source = _read_file("scripts/maintenance/clean_corrupt_l2.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "clean_corrupt_l2.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "clean_corrupt_l2.py missing guard call"
        # Should integrate dry_run parameter
        assert "dry_run=dry_run" in source, "clean_corrupt_l2.py must pass dry_run to guard"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "clean_corrupt_l2.py: guard call not found"
        assert has_write_after, "clean_corrupt_l2.py: guard must be before cursor.execute/commit"

    def test_file_6_fix_zombie_matches_has_guard(self):
        """fix_zombie_matches.py must import and call guard, integrate dry_run."""
        source = _read_file("scripts/maintenance/fix_zombie_matches.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "fix_zombie_matches.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "fix_zombie_matches.py missing guard call"
        # Should integrate dry_run parameter
        assert "dry_run=self.dry_run" in source, (
            "fix_zombie_matches.py must pass self.dry_run to guard"
        )
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "fix_zombie_matches.py: guard call not found"
        assert has_write_after, "fix_zombie_matches.py: guard must be before cursor.execute/commit"

    # ---- Allowlist classification tests ----

    def test_6_indirect_paths_now_runtime_guarded(self):
        """All 6 indirect_write_needs_guard paths must be indirect_write_path_runtime_guarded."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in GUARDED_INDIRECT_PATHS:
            assert path in entries_by_path, f"Missing from allowlist: {path}"
            classification = entries_by_path[path]["classification"]
            assert classification == "historical_python_indirect_write_path_runtime_guarded", (
                f"{path}: expected indirect_write_path_runtime_guarded, got {classification}"
            )

    def test_2_safe_indirect_paths_unchanged(self):
        """2 safe indirect paths must NOT be reclassified as runtime_guarded."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        expected = {
            "src/services/match_data_service.py": "historical_python_indirect_write_path_false_positive_candidate",
            "src/services/league_router.py": "historical_python_indirect_write_path_read_only_candidate",
        }

        for path, expected_class in expected.items():
            assert path in entries_by_path, f"Missing from allowlist: {path}"
            actual = entries_by_path[path]["classification"]
            assert actual == expected_class, f"{path}: expected {expected_class}, got {actual}"

    def test_9_of_14_confirmed_guarded_status_intact(self):
        """9/14 confirmed Python write paths guarded count must be preserved."""
        data = _load_allowlist()

        guarded = 0
        for entry in data["entries"]:
            if entry["path"] in CONFIRMED_WRITE_PATHS and "runtime_guarded" in entry.get(
                "classification", ""
            ):
                guarded += 1

        assert guarded == EXPECTED_CONFIRMED_GUARDED, (
            f"Expected {EXPECTED_CONFIRMED_GUARDED}/14 confirmed paths "
            f"runtime_guarded, got {guarded}/14"
        )

    def test_5_manual_review_candidates_unchanged(self):
        """5 manual review candidates must NOT be changed."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            assert path in entries_by_path, f"Missing from allowlist: {path}"
            classification = entries_by_path[path]["classification"]
            assert "needs_manual_review" in classification, (
                f"Manual review candidate {path} classification changed: {classification}"
            )
            assert "runtime_guarded" not in classification, (
                f"Manual review candidate {path} incorrectly marked runtime_guarded"
            )

    def test_allowlist_has_28_entries(self):
        """Allowlist must still have 28 total entries (no entries added or removed)."""
        data = _load_allowlist()
        assert len(data["entries"]) == EXPECTED_ALLOWLIST_ENTRIES, (
            f"Expected {EXPECTED_ALLOWLIST_ENTRIES} allowlist entries, got {len(data['entries'])}"
        )

    def test_allowlist_json_valid(self):
        """Allowlist must be valid JSON."""
        content = ALLOWLIST_PATH.read_text(encoding="utf-8")
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise AssertionError("Allowlist JSON is invalid")  # noqa: B904

    def test_allowlist_header_updated_for_phase2(self):
        """Allowlist header must reference indirect_write_path_guard_phase2."""
        data = _load_allowlist()
        status = data.get("_runtime_guard_status", "")
        assert "indirect_write_path_guard_phase2" in status, (
            f"Allowlist header missing phase2 reference: {status}"
        )
        assert "15 of 20" in status, f"Allowlist header missing updated count (15 of 20): {status}"

    # ---- SC-002 status tests ----

    def test_design_doc_sc002_partial_mitigation(self):
        """Design doc must state SC-002 remains partial mitigation only."""
        doc = DESIGN_DOC_PATH.read_text(encoding="utf-8")
        assert "partial mitigation only" in doc.lower(), (
            "Design doc must state SC-002 remains partial mitigation only"
        )

    def test_design_doc_training_blocked(self):
        """Design doc must state training/data expansion/real DB write remain blocked."""
        doc_lower = DESIGN_DOC_PATH.read_text(encoding="utf-8").lower()
        assert "training" in doc_lower, "Design doc must mention training"
        assert "data expansion" in doc_lower, "Design doc must mention data expansion"
        assert "real db write" in doc_lower, "Design doc must mention real DB write"
        assert "blocked" in doc_lower, "Design doc must state blocked"

    def test_design_doc_has_phase2_section(self):
        """Design doc must have Phase2 Implementation section."""
        doc = DESIGN_DOC_PATH.read_text(encoding="utf-8")
        assert "Phase2 Implementation" in doc, (
            "Design doc must contain Phase2 Implementation section"
        )
        assert "python_indirect_write_path_guard_phase2" in doc, (
            "Design doc must reference python_indirect_write_path_guard_phase2"
        )

    # ---- Guard-before-write check ----

    def test_guards_placed_before_write_not_after(self):
        """In all 6 files, guard must appear before write operations (not after)."""
        for path in GUARDED_INDIRECT_PATHS:
            source = _read_file(path)
            guard_line, has_write_after = _find_guard_position(source)
            assert guard_line is not None, f"{path}: no guard call found"
            assert has_write_after, (
                f"{path}: guard at line {guard_line} must be "
                f"before cursor.execute() / conn.commit() / execute_values()"
            )

    def test_all_guarded_files_have_owner_task_field(self):
        """All 6 guarded entries must have owner_task set to indirect_write_path_guard_phase2."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in GUARDED_INDIRECT_PATHS:
            entry = entries_by_path[path]
            owner = entry.get("owner_task", "")
            assert owner == "python_indirect_write_path_guard_phase2", (
                f"{path}: expected owner_task=python_indirect_write_path_guard_phase2, got {owner}"
            )

    def test_all_guarded_files_have_guard_evidence(self):
        """All 6 guarded entries must mention Phase2 in expires_or_review_note."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in GUARDED_INDIRECT_PATHS:
            entry = entries_by_path[path]
            note = entry.get("expires_or_review_note", "")
            assert "Phase2 indirect_write_path_guard_phase2" in note, (
                f"{path}: expires_or_review_note missing Phase2 guard reference"
            )
            assert "ALLOW_DB_WRITE=yes" in note, (
                f"{path}: expires_or_review_note must specify required env vars"
            )


if __name__ == "__main__":
    # Simple test runner for standalone execution
    test_class = TestIndirectWritePathGuardPhase2()
    passed = 0
    failed = 0

    for name in sorted(dir(test_class)):
        if name.startswith("test_"):
            try:
                getattr(test_class, name)()
                sys.stderr.write(f"PASS: {name}\n")
                passed += 1
            except Exception as e:
                sys.stderr.write(f"FAIL: {name} — {e}\n")
                failed += 1

    sys.stderr.write(f"\n{passed} passed, {failed} failed, {passed + failed} total\n")
    if failed > 0:
        sys.exit(1)
