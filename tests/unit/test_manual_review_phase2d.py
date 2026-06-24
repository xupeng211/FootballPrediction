"""
Static test: SC-002 Manual Review Phase2D validation.

Validates:
1. All 5 manual review candidates are covered in allowlist with correct classification
2. 15 runtime_guarded status not degraded
3. No file is incorrectly marked "safe"
4. Documents assert SC-002 partial mitigation only
5. Documents assert training/data expansion/real DB write blocked
6. Next guard candidates correctly identified
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
ALLOWLIST_PATH = PROJECT_ROOT / "config" / "python_db_write_allowlist.json"
PHASE2D_DOC_PATH = PROJECT_ROOT / "docs" / "SC002_MANUAL_REVIEW_PHASE2D.md"

EXPECTED_ALLOWLIST_ENTRIES = 28
EXPECTED_RUNTIME_GUARDED = 17

# ---- Test data ----

# 5 manual review candidates with expected new classifications
EXPECTED_CLASSIFICATIONS = {
    "scripts/maintenance/reprocess_from_local.py": "historical_python_manual_confirmed_write_path_runtime_guarded",
    "scripts/maintenance/fotmob_historical_backfill.py": "historical_python_manual_false_positive_candidate",
    "src/api/monitoring/prometheus_metrics.py": "historical_python_manual_confirmed_write_path_runtime_guarded",
    "src/api/monitoring.py": "historical_python_manual_read_only_candidate",
    "scripts/tools/diagnose_diagnostic.py": "historical_python_manual_false_positive_candidate",
}

MANUAL_REVIEW_PATHS = list(EXPECTED_CLASSIFICATIONS.keys())

# 17 paths that must remain runtime_guarded
RUNTIME_GUARDED_PATHS = [
    "src/database/schema_manager.py",
    "src/database/match_repository.py",
    "src/database/oddsportal_db_manager.py",
    "src/database/collector_repository.py",
    "src/data/streaming/streaming_db_writer.py",
    "src/core/database/odds_injector.py",
    "scripts/maintenance/database_detox.py",
    "scripts/maintenance/reset_l2_collection.py",
    "scripts/ops/fotmob_registry_seed_dev_execution.py",
    "src/services/match_aligner.py",
    "src/services/match_linker.py",
    "src/api/collectors/odds_api_client_v38.py",
    "scripts/maintenance/reprocess_failed_matches.py",
    "scripts/maintenance/clean_corrupt_l2.py",
    "scripts/maintenance/fix_zombie_matches.py",
    "scripts/maintenance/reprocess_from_local.py",
    "src/api/monitoring/prometheus_metrics.py",
]

# 2 next guard candidates
NEXT_GUARD_CANDIDATES = [
    "scripts/maintenance/reprocess_from_local.py",
    "src/api/monitoring/prometheus_metrics.py",
]


def _load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _read_doc(path):
    return path.read_text(encoding="utf-8")


class TestManualReviewPhase2D:
    """Validate manual review Phase2D outcomes."""

    # ---- Allowlist classification tests ----

    def test_all_5_manual_review_candidates_covered(self):
        """All 5 manual review candidates must be in allowlist with correct new classification."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path, expected_class in EXPECTED_CLASSIFICATIONS.items():
            assert path in entries_by_path, f"Missing from allowlist: {path}"
            actual = entries_by_path[path]["classification"]
            assert actual == expected_class, (
                f"Classification mismatch for {path}: expected={expected_class}, got={actual}"
            )

    def test_15_runtime_guarded_status_intact(self):
        """15 runtime_guarded paths must remain runtime_guarded (not degraded)."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        count = 0
        for path in RUNTIME_GUARDED_PATHS:
            assert path in entries_by_path, f"Guarded path missing: {path}"
            classification = entries_by_path[path]["classification"]
            assert "runtime_guarded" in classification, (
                f"{path} should remain runtime_guarded, got: {classification}"
            )
            count += 1

        assert count == EXPECTED_RUNTIME_GUARDED, (
            f"Expected {EXPECTED_RUNTIME_GUARDED} guarded paths, got {count}"
        )

    def test_no_manual_review_candidate_marked_safe(self):
        """No manual review candidate should be marked 'safe'."""
        data = _load_allowlist()
        for entry in data["entries"]:
            classification = entry.get("classification", "")
            if "safe" in classification.lower():
                raise AssertionError(
                    f"{entry['path']} incorrectly marked as safe: {classification}"
                )

    def test_no_manual_review_candidate_unclassified(self):
        """After Phase2E: all manual review candidates now classified.
        2 write paths are now runtime_guarded, 3 safe reclassified."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in MANUAL_REVIEW_PATHS:
                classification = entry.get("classification", "")
                assert "manual_" in classification, (
                    f"{entry['path']} should have manual_* classification, got: {classification}"
                )

    def test_allowlist_has_28_entries(self):
        """Allowlist must still have 28 total entries."""
        data = _load_allowlist()
        assert len(data["entries"]) == EXPECTED_ALLOWLIST_ENTRIES, (
            f"Expected {EXPECTED_ALLOWLIST_ENTRIES} entries, got {len(data['entries'])}"
        )

    def test_allowlist_json_valid(self):
        """Allowlist must be valid JSON."""
        content = ALLOWLIST_PATH.read_text(encoding="utf-8")
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise AssertionError("Allowlist JSON is invalid")  # noqa: B904

    def test_allowlist_header_updated_for_phase2d(self):
        """Allowlist header must reference manual_review_phase2d."""
        data = _load_allowlist()
        status = data.get("_runtime_guard_status", "")
        assert "Phase2D manual review" in status, (
            f"Allowlist header missing Phase2D reference: {status}"
        )
        assert "2/2" in status or "2 of 2" in status or "17/20" in status, (
            f"Allowlist header must show Phase2E guard completion: {status}"
        )
        assert "0 unreviewed" in status or "No remaining" in status, (
            f"Allowlist header must state 0 unreviewed: {status}"
        )

    def test_all_5_entries_have_analysis_task(self):
        """All 5 entries must have analysis_task field set."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            entry = entries_by_path[path]
            assert entry.get("analysis_task") == "python_manual_review_phase2d", (
                f"{path}: missing or wrong analysis_task: {entry.get('analysis_task')}"
            )

    def test_all_5_entries_have_observed_operations(self):
        """All 5 entries must have observed_operations field."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            ops = entries_by_path[path].get("observed_operations")
            assert ops is not None, f"{path}: missing observed_operations"
            assert isinstance(ops, list), f"{path}: observed_operations must be list"

    def test_all_5_entries_have_direct_write_boundary(self):
        """All 5 entries must have direct_write_boundary field."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            boundary = entries_by_path[path].get("direct_write_boundary")
            assert boundary is not None, f"{path}: missing direct_write_boundary"

    def test_all_5_entries_have_recommended_next_action(self):
        """All 5 entries must have recommended_next_action field."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            action = entries_by_path[path].get("recommended_next_action")
            assert action is not None, f"{path}: missing recommended_next_action"

    def test_all_5_entries_have_source_doc_phase2d(self):
        """All 5 entries must reference the Phase2D source doc."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            source = entries_by_path[path].get("source_doc", "")
            assert source == "docs/SC002_MANUAL_REVIEW_PHASE2D.md", (
                f"{path}: expected source_doc=docs/SC002_MANUAL_REVIEW_PHASE2D.md, got {source}"
            )

    def test_no_stale_consumer_audit_fields(self):
        """Manual review entries should not have stale consumer_audit fields."""
        data = _load_allowlist()
        for entry in data["entries"]:
            if entry["path"] in MANUAL_REVIEW_PATHS:
                assert "consumer_audit_task" not in entry, (
                    f"{entry['path']} has stale consumer_audit_task"
                )
                assert "consumer_audit_doc" not in entry, (
                    f"{entry['path']} has stale consumer_audit_doc"
                )

    def test_owner_task_set_to_phase2d_or_phase2e(self):
        """Entries must have owner_task reflecting the phase that last touched them."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in MANUAL_REVIEW_PATHS:
            owner = entries_by_path[path].get("owner_task", "")
            assert owner in (
                "python_manual_review_phase2d",
                "python_manual_review_guard_phase2e",
            ), f"{path}: unexpected owner_task: {owner}"

    # ---- Next guard candidate tests ----

    def test_2_next_guard_candidates_now_guarded(self):
        """After Phase2E: 2 paths that were next guard candidates are now runtime_guarded."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in NEXT_GUARD_CANDIDATES:
            classification = entries_by_path[path]["classification"]
            assert "runtime_guarded" in classification, (
                f"{path} should now be runtime_guarded after Phase2E, got: {classification}"
            )

    def test_next_guard_candidates_marked_done(self):
        """After Phase2E: the 2 paths should have 'Done' in recommended_next_action."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in NEXT_GUARD_CANDIDATES:
            action = entries_by_path[path].get("recommended_next_action", "")
            assert "Done" in action, (
                f"{path}: recommended_next_action should say Done, got: {action}"
            )

    # ---- Document tests ----

    def test_phase2d_doc_exists(self):
        """Phase2D document must exist."""
        assert PHASE2D_DOC_PATH.exists(), f"Phase2D doc missing: {PHASE2D_DOC_PATH}"

    def test_phase2d_doc_sc002_partial_mitigation(self):
        """Phase2D doc must state SC-002 remains partial mitigation only."""
        doc = _read_doc(PHASE2D_DOC_PATH)
        assert "partial mitigation only" in doc.lower(), (
            "Phase2D doc must state SC-002 remains partial mitigation only"
        )

    def test_phase2d_doc_training_blocked(self):
        """Phase2D doc must state training/data expansion/real DB write remain blocked."""
        doc_lower = _read_doc(PHASE2D_DOC_PATH).lower()
        assert "training" in doc_lower, "Phase2D doc must mention training"
        assert "data expansion" in doc_lower, "Phase2D doc must mention data expansion"
        assert "real db write" in doc_lower, "Phase2D doc must mention real DB write"
        assert "blocked" in doc_lower, "Phase2D doc must state blocked"

    def test_phase2d_doc_has_all_5_paths(self):
        """Phase2D doc must reference all 5 manual review paths."""
        doc = _read_doc(PHASE2D_DOC_PATH)
        for path in MANUAL_REVIEW_PATHS:
            filename = Path(path).name
            assert filename in doc, f"Phase2D doc missing reference to {filename}"

    def test_phase2d_doc_classification_summary(self):
        """Phase2D doc must contain classification summary table."""
        doc = _read_doc(PHASE2D_DOC_PATH)
        assert "manual_confirmed_write_needs_guard" in doc, (
            "Phase2D doc must mention manual_confirmed_write_needs_guard"
        )
        assert "manual_read_only_candidate" in doc, (
            "Phase2D doc must mention manual_read_only_candidate"
        )
        assert "manual_false_positive_candidate" in doc, (
            "Phase2D doc must mention manual_false_positive_candidate"
        )

    def test_phase2d_doc_next_guard_candidates_section(self):
        """Phase2D doc must have Next Guard Candidates section."""
        doc = _read_doc(PHASE2D_DOC_PATH)
        assert "Next Guard Candidates" in doc, "Phase2D doc must have Next Guard Candidates section"
        assert "python_manual_review_guard_phase2e" in doc, (
            "Phase2D doc must reference next task python_manual_review_guard_phase2e"
        )

    def test_phase2d_doc_non_goals(self):
        """Phase2D doc must state non-goals clearly."""
        doc_lower = _read_doc(PHASE2D_DOC_PATH).lower()
        non_goal_terms = [
            "runtime guard implementation",
            "real db write",
            "scraper",
            "training",
        ]
        for term in non_goal_terms:
            assert term.lower() in doc_lower, f"Phase2D doc non-goals should mention: {term}"


if __name__ == "__main__":
    test_class = TestManualReviewPhase2D()
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
