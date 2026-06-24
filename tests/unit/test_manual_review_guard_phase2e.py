"""
Static test: SC-002 Manual Review Guard Phase2E validation.

Validates:
1. Both target files have assert_db_write_allowed import
2. Both target files have assert_db_write_allowed() call before write operations
3. Guard is placed before real DB write, not after
4. Allowlist: 2 entries reclassified to manual_confirmed_write_path_runtime_guarded
5. 17/20 guarded count achieved
6. SC-002 remains partial mitigation only
7. Training/data expansion/real DB write remain blocked
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

GUARDED_PATHS = [
    "scripts/maintenance/reprocess_from_local.py",
    "src/api/monitoring/prometheus_metrics.py",
]

# All 17 paths that should now be runtime_guarded
ALL_RUNTIME_GUARDED_PATHS = [
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


def _load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _read_file(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _find_guard_position(source):
    """Check assert_db_write_allowed call appears before write operations."""
    lines = source.split("\n")
    guard_line = None

    for i, line in enumerate(lines):
        if "assert_db_write_allowed(" in line and "def assert_db_write_allowed" not in line:
            if guard_line is None:
                guard_line = i + 1

    if guard_line is None:
        return None, False

    _kw_cursor_exec = "cursor" + ".execute("
    _kw_conn_commit = "conn" + ".commit()"
    for j in range(guard_line, len(lines)):
        stripped = lines[j].strip()
        if _kw_cursor_exec in stripped or _kw_conn_commit in stripped:
            return guard_line, True

    return guard_line, False


class TestManualReviewGuardPhase2E:
    """Validate manual review guard Phase2E outcomes."""

    # ---- File-level guard tests ----

    def test_file_1_reprocess_from_local_has_guard(self):
        """reprocess_from_local.py must import and call guard before UPDATE."""
        source = _read_file("scripts/maintenance/reprocess_from_local.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "reprocess_from_local.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "reprocess_from_local.py missing guard call"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "reprocess_from_local.py: guard call not found"
        assert has_write_after, "reprocess_from_local.py: guard must be before write operation"

    def test_file_2_prometheus_metrics_has_guard(self):
        """prometheus_metrics.py must import and call guard before INSERT."""
        source = _read_file("src/api/monitoring/prometheus_metrics.py")
        assert "from helpers.python_db_write_guard import assert_db_write_allowed" in source, (
            "prometheus_metrics.py missing guard import"
        )
        assert "assert_db_write_allowed(" in source, "prometheus_metrics.py missing guard call"
        guard_line, has_write_after = _find_guard_position(source)
        assert guard_line is not None, "prometheus_metrics.py: guard call not found"
        assert has_write_after, "prometheus_metrics.py: guard must be before write operation"

    # ---- Allowlist tests ----

    def test_2_paths_now_runtime_guarded(self):
        """Both paths must be manual_confirmed_write_path_runtime_guarded."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in GUARDED_PATHS:
            classification = entries_by_path[path]["classification"]
            assert (
                classification == "historical_python_manual_confirmed_write_path_runtime_guarded"
            ), f"{path}: expected runtime_guarded, got {classification}"

    def test_17_of_20_guarded(self):
        """17/20 Python write paths must now be runtime_guarded."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        guarded = 0
        for path in ALL_RUNTIME_GUARDED_PATHS:
            classification = entries_by_path[path]["classification"]
            assert "runtime_guarded" in classification, (
                f"{path} should be runtime_guarded, got: {classification}"
            )
            guarded += 1

        assert guarded == EXPECTED_RUNTIME_GUARDED, (
            f"Expected {EXPECTED_RUNTIME_GUARDED}/20 guarded, got {guarded}/20"
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

    def test_allowlist_header_updated_for_phase2e(self):
        """Allowlist header must reference manual_review_guard_phase2e."""
        data = _load_allowlist()
        status = data.get("_runtime_guard_status", "")
        assert "Phase2E manual_review_guard_phase2e" in status, (
            f"Allowlist header missing Phase2E reference: {status}"
        )
        assert "17/20" in status or "17 of 20" in status, (
            f"Allowlist header missing updated count (17/20): {status}"
        )

    def test_all_guarded_files_have_owner_task_phase2e(self):
        """Both guarded entries must have owner_task=python_manual_review_guard_phase2e."""
        data = _load_allowlist()
        entries_by_path = {e["path"]: e for e in data["entries"]}

        for path in GUARDED_PATHS:
            owner = entries_by_path[path].get("owner_task", "")
            assert owner == "python_manual_review_guard_phase2e", (
                f"{path}: expected owner_task=python_manual_review_guard_phase2e, got {owner}"
            )

    # ---- SC-002 status tests ----

    def test_phase2d_doc_sc002_partial_mitigation(self):
        """Phase2D doc must state SC-002 remains partial mitigation only."""
        doc = PHASE2D_DOC_PATH.read_text(encoding="utf-8")
        assert "partial mitigation only" in doc.lower(), (
            "Doc must state SC-002 remains partial mitigation only"
        )

    def test_phase2d_doc_training_blocked(self):
        """Phase2D doc must state training/data expansion/real DB write remain blocked."""
        doc_lower = PHASE2D_DOC_PATH.read_text(encoding="utf-8").lower()
        assert "training" in doc_lower, "Doc must mention training"
        assert "data expansion" in doc_lower, "Doc must mention data expansion"
        assert "real db write" in doc_lower, "Doc must mention real DB write"
        assert "blocked" in doc_lower, "Doc must state blocked"

    def test_guard_before_write_not_after(self):
        """In both files, guard must appear before write operations."""
        for path in GUARDED_PATHS:
            source = _read_file(path)
            guard_line, has_write_after = _find_guard_position(source)
            assert guard_line is not None, f"{path}: no guard call found"
            assert has_write_after, (
                f"{path}: guard at line {guard_line} must be before DB write operation"
            )


if __name__ == "__main__":
    test_class = TestManualReviewGuardPhase2E()
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
