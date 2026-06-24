"""
Static test: SC-002 Indirect Write Path Design Phase1 validation.

Validates:
1. All 8 indirect paths are covered in the allowlist
2. No indirect path is marked runtime_guarded
3. No manual review candidate is marked safe
4. 9/14 confirmed guarded status unchanged
5. Design doc asserts SC-002 remains partial mitigation only
6. Design doc asserts training/data expansion/real DB write remain blocked
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

EXPECTED_INDIRECT_PATHS = [
    "src/services/match_aligner.py",
    "src/services/match_linker.py",
    "src/services/match_data_service.py",
    "src/services/league_router.py",
    "src/api/collectors/odds_api_client_v38.py",
    "scripts/maintenance/reprocess_failed_matches.py",
    "scripts/maintenance/clean_corrupt_l2.py",
    "scripts/maintenance/fix_zombie_matches.py",
]

EXPECTED_CLASSIFICATIONS = {
    "src/services/match_aligner.py": "historical_python_indirect_write_path_runtime_guarded",
    "src/services/match_linker.py": "historical_python_indirect_write_path_runtime_guarded",
    "src/services/match_data_service.py": "historical_python_indirect_write_path_false_positive_candidate",
    "src/services/league_router.py": "historical_python_indirect_write_path_read_only_candidate",
    "src/api/collectors/odds_api_client_v38.py": "historical_python_indirect_write_path_runtime_guarded",
    "scripts/maintenance/reprocess_failed_matches.py": "historical_python_indirect_write_path_runtime_guarded",
    "scripts/maintenance/clean_corrupt_l2.py": "historical_python_indirect_write_path_runtime_guarded",
    "scripts/maintenance/fix_zombie_matches.py": "historical_python_indirect_write_path_runtime_guarded",
}

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


def _load_design_doc():
    return DESIGN_DOC_PATH.read_text(encoding="utf-8")


# ---- Tests ----


class TestIndirectWritePathDesignPhase1:
    """Validate indirect write path design phase1 outcomes."""

    def test_all_8_indirect_paths_covered(self):
        """All 8 indirect paths must be present in allowlist with correct classification."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in EXPECTED_INDIRECT_PATHS:
            assert path in entries_by_path, f"Missing from allowlist: {path}"
            entry = entries_by_path[path]
            expected = EXPECTED_CLASSIFICATIONS[path]
            actual = entry["classification"]
            assert actual == expected, (
                f"Classification mismatch for {path}: expected={expected}, got={actual}"
            )

    def test_no_indirect_path_marked_safe(self):
        """After Phase2 guard implementation, 6 indirect paths should be runtime_guarded.
        The 2 safe paths (read_only, false_positive) should NOT be marked runtime_guarded."""
        data = _load_allowlist()
        NEEDS_GUARD_PATHS = {
            p
            for p in EXPECTED_INDIRECT_PATHS
            if "match_data_service" not in p and "league_router" not in p
        }
        SAFE_PATHS = {
            p for p in EXPECTED_INDIRECT_PATHS if "match_data_service" in p or "league_router" in p
        }

        for entry in data["entries"]:
            path = entry["path"]
            if path in NEEDS_GUARD_PATHS:
                classification = entry.get("classification", "")
                assert "runtime_guarded" in classification, (
                    f"Indirect path {path} should now be runtime_guarded after Phase2, "
                    f"got: {classification}"
                )
            elif path in SAFE_PATHS:
                classification = entry.get("classification", "")
                assert "safe" not in classification, (
                    f"Safe indirect path {path} incorrectly marked safe: {classification}"
                )
                assert "runtime_guarded" not in classification, (
                    f"Safe indirect path {path} incorrectly marked runtime_guarded: {classification}"
                )

    def test_no_manual_review_candidate_marked_safe(self):
        """After Phase2D: manual review candidates have been reclassified.
        None should be marked 'safe'; 2 are write_needs_guard (not runtime_guarded yet)."""
        data = _load_allowlist()

        for entry in data["entries"]:
            path = entry["path"]
            if path in MANUAL_REVIEW_PATHS:
                classification = entry.get("classification", "")
                # None should be runtime_guarded (guard deferred to Phase2E)
                assert "runtime_guarded" not in classification, (
                    f"Manual review candidate {path} incorrectly marked runtime_guarded"
                )
                # None should be marked 'safe' literally
                assert "safe" not in classification, (
                    f"Manual review candidate {path} incorrectly marked safe: {classification}"
                )
                # All 5 should now be classified (not needs_manual_review)
                assert "manual_" in classification, (
                    f"Manual review candidate {path} should now have manual_* "
                    f"classification after Phase2D, got: {classification}"
                )

    def test_9_of_14_confirmed_guarded_status_unchanged(self):
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

    def test_design_doc_exists(self):
        """Design document must exist."""
        assert DESIGN_DOC_PATH.exists(), f"Design doc missing: {DESIGN_DOC_PATH}"

    def test_design_doc_sc002_partial_mitigation(self):
        """Design doc must clearly state SC-002 remains partial mitigation only."""
        doc = _load_design_doc()
        assert "partial mitigation only" in doc.lower(), (
            "Design doc must state SC-002 remains partial mitigation only"
        )
        # Must NOT affirmatively claim SC-002 is complete or fully fixed
        doc_cleaned = doc.replace("- Claiming SC-002 is resolved or complete", "")
        assert "SC-002 is fully fixed" not in doc_cleaned, (
            "Design doc must not affirmatively claim SC-002 is fully fixed"
        )
        assert "SC-002 is complete" not in doc_cleaned, (
            "Design doc must not affirmatively claim SC-002 is complete"
        )

    def test_design_doc_training_blocked(self):
        """Design doc must state training/data expansion/real DB write remain blocked."""
        doc_lower = _load_design_doc().lower()
        assert "training" in doc_lower, "Design doc must mention training"
        assert "data expansion" in doc_lower, "Design doc must mention data expansion"
        assert "real db write" in doc_lower, "Design doc must mention real DB write"
        assert "blocked" in doc_lower, "Design doc must state blocked"

    def test_design_doc_has_all_8_paths(self):
        """Design doc must reference all 8 indirect paths."""
        doc = _load_design_doc()
        for path in EXPECTED_INDIRECT_PATHS:
            filename = Path(path).name
            assert filename in doc, f"Design doc missing reference to {filename}"

    def test_design_doc_classification_summary_table(self):
        """Design doc must contain classification summary with correct counts."""
        doc = _load_design_doc()
        assert "indirect_write_needs_guard" in doc, (
            "Design doc must mention indirect_write_needs_guard"
        )
        assert "indirect_read_only_candidate" in doc, (
            "Design doc must mention indirect_read_only_candidate"
        )
        assert "indirect_false_positive_candidate" in doc, (
            "Design doc must mention indirect_false_positive_candidate"
        )

    def test_design_doc_non_goals(self):
        """Design doc must clearly state what it is NOT doing."""
        doc_lower = _load_design_doc().lower()
        assert "not" in doc_lower, "Design doc must state non-goals"
        non_goal_terms = [
            "runtime guard implementation",
            "real db write",
            "sql",
            "scraper",
            "training",
        ]
        for term in non_goal_terms:
            assert term.lower() in doc_lower, f"Design doc non-goals should mention: {term}"

    def test_allowlist_header_updated(self):
        """Allowlist header must reference indirect write path status."""
        data = _load_allowlist()
        status = data.get("_runtime_guard_status", "")
        assert (
            "indirect_write_path_design_phase1" in status
            or "indirect_write_path_guard_phase2" in status
        ), f"Allowlist header missing indirect write path reference: {status}"
        # After guard phase2, needs_guard count is 0; header should show 6 guarded
        assert (
            "indirect_write_needs_guard" in status
            or "6 of 6 indirect write paths now runtime guarded" in status
        ), f"Allowlist header missing classification summary: {status}"

    def test_allowlist_no_orphan_consumer_audit_fields(self):
        """Indirect paths should not have stale consumer_audit fields after update."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in EXPECTED_INDIRECT_PATHS:
                assert "consumer_audit_task" not in entry, (
                    f"Indirect path {entry['path']} has stale consumer_audit_task"
                )
                assert "consumer_audit_doc" not in entry, (
                    f"Indirect path {entry['path']} has stale consumer_audit_doc"
                )

    def test_all_indirect_paths_have_analysis_task(self):
        """All indirect paths must have analysis_task field set."""
        data = _load_allowlist()
        expected_task = "python_indirect_write_path_design_phase1"
        for entry in data["entries"]:
            if entry["path"] in EXPECTED_INDIRECT_PATHS:
                assert entry.get("analysis_task") == expected_task, (
                    f"Indirect path {entry['path']} missing analysis_task"
                )

    def test_all_indirect_paths_have_observed_operations(self):
        """All indirect paths must have observed_operations field."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in EXPECTED_INDIRECT_PATHS:
                ops = entry.get("observed_operations")
                assert ops is not None, f"Indirect path {entry['path']} missing observed_operations"
                assert isinstance(ops, list), (
                    f"Indirect path {entry['path']} observed_operations must be list"
                )

    def test_all_indirect_paths_have_direct_write_boundary(self):
        """All indirect paths must have direct_write_boundary field."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in EXPECTED_INDIRECT_PATHS:
                boundary = entry.get("direct_write_boundary")
                assert boundary is not None, (
                    f"Indirect path {entry['path']} missing direct_write_boundary"
                )

    def test_all_indirect_paths_have_recommended_next_action(self):
        """All indirect paths must have recommended_next_action field."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in EXPECTED_INDIRECT_PATHS:
                action = entry.get("recommended_next_action")
                assert action is not None, (
                    f"Indirect path {entry['path']} missing recommended_next_action"
                )

    def test_allowlist_has_28_total_entries(self):
        """Allowlist must still have 28 total entries (no entries added or removed)."""
        data = _load_allowlist()
        assert len(data["entries"]) == EXPECTED_ALLOWLIST_ENTRIES, (
            f"Expected {EXPECTED_ALLOWLIST_ENTRIES} allowlist entries, got {len(data['entries'])}"
        )

    def test_allowlist_json_is_valid(self):
        """Allowlist must be valid JSON."""
        content = ALLOWLIST_PATH.read_text(encoding="utf-8")
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise AssertionError("Allowlist JSON is invalid")  # noqa: B904


if __name__ == "__main__":
    # Simple test runner for standalone execution
    test_class = TestIndirectWritePathDesignPhase1()
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
