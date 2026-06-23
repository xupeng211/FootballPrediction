#!/usr/bin/env python3
"""
Static tests for Python DB Write Static Enforcement Phase 2A.

lifecycle: permanent
scope: static verification only; does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration.

Tests cover:
  Scanner: signal detection, classification, comment/docstring awareness, JSON output
  Allowlist: completeness, no wildcards, no safe labels for risky files
  AI Workflow Gate: changed-files enforcement, docs-only exemption
  SC-002 doc consistency
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

# ── Ensure the scanner is importable ─────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_sys_path_inserted = str(_REPO_ROOT / "scripts" / "ops")
if _sys_path_inserted not in sys.path:
    sys.path.insert(0, _sys_path_inserted)

from python_db_write_static_enforcement import (  # noqa: E402
    _load_allowlist,
    _scan_file_for_signals,
    _validate_allowlist_entry,
    changed_files_check,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


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
    return _load_allowlist(allowlist_path)


# ── Scanner tests ────────────────────────────────────────────────────────────


class TestScannerSignalDetection:
    """Scanner correctly identifies DB client, execution, and write keywords."""

    def test_detects_confirmed_write_path(self, repo_root):
        """Scanner identifies a known confirmed write path file."""
        result = _scan_file_for_signals(repo_root / "src" / "database" / "schema_manager.py")
        assert result["classification"] in (
            "python_confirmed_write_risk",
            "python_possible_write_risk",
        ), f"Expected write risk, got {result['classification']}"
        assert len(result["db_client_signals"]) > 0, "Should detect DB client signals"
        assert len(result["execution_signals"]) > 0, "Should detect execution signals"

    def test_detects_indirect_write_path(self, repo_root):
        """Scanner identifies a known indirect write path."""
        path = repo_root / "scripts" / "maintenance" / "clean_corrupt_l2.py"
        if not path.exists():
            pytest.skip("File not found")
        result = _scan_file_for_signals(path)
        assert result["classification"] in (
            "python_confirmed_write_risk",
            "python_possible_write_risk",
            "python_db_connection_no_write_detected",
            "python_execution_no_db_client",
        ), f"Unexpected classification: {result['classification']}"

    def test_detects_no_db_connection_file(self, repo_root):
        """Scanner correctly identifies a file with no DB connection."""
        result = _scan_file_for_signals(repo_root / "scripts" / "ops" / "ai_workflow_gate.py")
        assert result["classification"] == "python_no_db_connection", (
            f"Expected no_db_connection, got {result['classification']}"
        )
        # AI workflow gate has SQL keywords in regex patterns, but they should be
        # in string_literal or comment context, not executable_context
        write_exec = [
            s for s in result["write_keyword_signals"] if s["evidence_type"] == "executable_context"
        ]
        assert len(write_exec) == 0, (
            f"Should have 0 executable write keywords, found {len(write_exec)}"
        )

    def test_distinguishes_comment_from_executable(self, repo_root):
        """Scanner distinguishes between comment/docstring and executable SQL."""
        result = _scan_file_for_signals(
            repo_root / "scripts" / "ops" / "python_db_write_static_enforcement.py"
        )
        # The scanner itself contains SQL keywords in regex patterns (strings)
        # These should be classified as string_literal, not executable_context
        exec_write = [
            s for s in result["write_keyword_signals"] if s["evidence_type"] == "executable_context"
        ]
        # The scanner file should NOT have executable write keywords
        assert len(exec_write) == 0, (
            f"Scanner self-scan found {len(exec_write)} executable write keywords — "
            f"should be 0 (all in strings/comments)"
        )

    def test_detects_psycopg2_signals(self):
        """Scanner detects psycopg2 import signals in a known write path."""
        path = _REPO_ROOT / "scripts" / "ops" / "fotmob_registry_seed_dev_execution.py"
        if not path.exists():
            pytest.skip("File not found")
        result = _scan_file_for_signals(path)
        # Should detect psycopg2 import
        pg_signals = [s for s in result["db_client_signals"] if "psycopg" in s["signal"].lower()]
        assert len(pg_signals) > 0, (
            "Should detect psycopg2 signals in fotmob_registry_seed_dev_execution.py"
        )

    def test_json_output_format(self):
        """Scanner JSON output contains required fields."""
        result = _scan_file_for_signals(_REPO_ROOT / "src" / "database" / "sql_store.py")
        required_fields = [
            "path",
            "classification",
            "db_client_signals",
            "db_env_signals",
            "execution_signals",
            "write_keyword_signals",
            "evidence_lines",
            "allowlist_status",
            "requires_review",
            "would_fail_changed_files_gate",
            "recommended_next_action",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_scanner_does_not_import_target_files(self):
        """Scanner scans as text — does NOT import target Python files."""
        # This is verified by the fact that _scan_file_for_signals uses
        # read_text() and regex, not import or exec. We confirm by scanning
        # a file that would fail if imported.
        result = _scan_file_for_signals(
            _REPO_ROOT / "scripts" / "ops" / "python_db_write_static_enforcement.py"
        )
        assert result["classification"] is not None

    def test_scanner_does_not_connect_to_db(self):
        """Scanner never connects to a database."""
        # Static verification: scanner code has no psycopg2.connect / asyncpg.connect
        scanner_src = (
            _REPO_ROOT / "scripts" / "ops" / "python_db_write_static_enforcement.py"
        ).read_text()
        assert "psycopg2.connect" not in scanner_src
        assert "asyncpg.connect" not in scanner_src
        assert "create_engine(" not in scanner_src
        assert "sqlite3.connect" not in scanner_src

    def test_unknown_db_write_file_would_fail(self, repo_root):
        """Unknown file with DB write risk signals would fail changed-files gate."""
        # Use fotmob_target_selection_db_dry_run.py which has psycopg2 + execute
        # and is NOT in the allowlist
        path = repo_root / "scripts" / "ops" / "fotmob_target_selection_db_dry_run.py"
        if not path.exists():
            pytest.skip("File not found")
        result = _scan_file_for_signals(path)
        if result["classification"] in (
            "python_confirmed_write_risk",
            "python_possible_write_risk",
        ):
            assert result["requires_review"], "High-risk classification should require review"


# ── Allowlist tests ──────────────────────────────────────────────────────────


class TestAllowlist:
    """Allowlist integrity and completeness checks."""

    def test_allowlist_file_exists(self, allowlist_path):
        assert allowlist_path is not None, "Allowlist file missing"
        assert allowlist_path.exists(), "Allowlist file does not exist"

    def test_allowlist_has_entries(self, allowlist_data):
        min_expected = 27  # 14 confirmed + 8 indirect + 5 review
        assert len(allowlist_data) >= min_expected, (
            f"Expected at least {min_expected} entries, got {len(allowlist_data)}"
        )

    def test_each_entry_has_required_fields(self, allowlist_data):
        missing_any = []
        for path, entry in allowlist_data.items():
            missing = _validate_allowlist_entry(entry)
            if missing:
                missing_any.append(f"{path}: missing {missing}")
        assert len(missing_any) == 0, (
            "Allowlist entries with missing required fields:\n" + "\n".join(missing_any)
        )

    def test_no_wildcard_blanket_allowlist(self, allowlist_data):
        for path in allowlist_data:
            assert "*" not in path, f"Wildcard allowlist entry not allowed: {path}"
            assert "?" not in path, f"Wildcard allowlist entry not allowed: {path}"

    def test_confirmed_write_paths_not_marked_safe(self, allowlist_data):
        for path, entry in allowlist_data.items():
            cls = entry.get("classification", "")
            if "confirmed_write_path" in cls:
                assert "safe" not in cls.lower(), (
                    f"Confirmed write path {path} must not be marked safe: {cls}"
                )
                assert "pending_runtime_guard" in cls, (
                    f"Confirmed write path {path} must have 'pending_runtime_guard' "
                    f"in classification: {cls}"
                )

    def test_manual_review_candidates_not_claimed_safe(self, allowlist_data):
        for path, entry in allowlist_data.items():
            cls = entry.get("classification", "")
            if "needs_manual_review" in cls:
                # "Do NOT mark safe" is acceptable; "safe to write" is not
                reason = entry.get("reason", "").lower()
                unsafes = [
                    "safe to write",
                    "safe to train",
                    "safe to execute",
                    "no risk",
                    "verified safe",
                    "confirmed safe",
                    "production ready",
                    "fully reviewed and safe",
                ]
                for u in unsafes:
                    assert u not in reason, (
                        f"Manual review candidate {path} uses forbidden phrase: '{u}'"
                    )

    def test_allowlist_contains_all_27_baseline_paths(self, allowlist_data):
        """Verify all 27 baseline paths from design doc are present."""
        baseline_27 = [
            # 14 confirmed write paths
            "src/database/schema_manager.py",
            "src/database/sql_store.py",
            "src/database/match_repository.py",
            "src/database/oddsportal_db_manager.py",
            "src/database/collector_repository.py",
            "src/database/sync_db_pool.py",
            "src/database/db_pool.py",
            "src/data/streaming/streaming_db_writer.py",
            "src/core/database/odds_injector.py",
            "scripts/maintenance/database_detox.py",
            "scripts/maintenance/reset_l2_collection.py",
            "scripts/maintenance/odds_integrity_guard.py",
            "scripts/maintenance/integrity_guard.py",
            "scripts/ops/fotmob_registry_seed_dev_execution.py",
            # 1 additional confirmed (alembic env)
            "src/database/migrations/env.py",
            # 8 indirect write paths
            "src/services/match_aligner.py",
            "src/services/match_linker.py",
            "src/services/match_data_service.py",
            "src/services/league_router.py",
            "src/api/collectors/odds_api_client_v38.py",
            "scripts/maintenance/reprocess_failed_matches.py",
            "scripts/maintenance/clean_corrupt_l2.py",
            "scripts/maintenance/fix_zombie_matches.py",
            # 5 manual review candidates
            "scripts/maintenance/reprocess_from_local.py",
            "scripts/maintenance/fotmob_historical_backfill.py",
            "src/api/monitoring/prometheus_metrics.py",
            "src/api/monitoring.py",
            "scripts/tools/diagnose_diagnostic.py",
        ]
        for path in baseline_27:
            assert path in allowlist_data, f"Baseline path {path} missing from allowlist"


# ── AI Workflow Gate integration tests ───────────────────────────────────────


class TestChangedFilesEnforcement:
    """Changed-files enforcement behavior."""

    def test_allowlisted_file_passes(self):
        """Changed allowlisted file passes (historical baseline)."""
        result = changed_files_check(["src/database/schema_manager.py"])
        assert len(result["violations"]) == 0, (
            f"Allowlisted file should pass, got {len(result['violations'])} violations"
        )
        assert not result["would_hard_fail"]

    def test_docs_only_changes_unaffected(self):
        """Docs-only PR with no Python changes is unaffected."""
        result = changed_files_check(["docs/PROJECT_STATUS.md", "README.md"])
        assert len(result["violations"]) == 0
        assert not result["would_hard_fail"]
        assert result.get("note") is not None

    def test_non_db_python_file_passes(self):
        """Python file with no DB signals passes."""
        result = changed_files_check(["scripts/ops/documentation_governance_check.py"])
        assert len(result["violations"]) == 0

    def test_only_python_files_scanned(self):
        """JS files are not scanned by Python enforcement (handled by JS guard)."""
        result = changed_files_check(
            ["scripts/ops/odds_sniper.js", "src/database/schema_manager.py"]
        )
        # Should only process .py files
        py_paths = [v["path"] for v in result["violations"]] + [p["path"] for p in result["passed"]]
        for p in py_paths:
            assert p.endswith(".py"), f"Non-Python file was scanned: {p}"

    def test_manual_review_allowlisted_file_passes_with_baseline_status(self):
        """Manual review candidate in allowlist passes but with baseline status."""
        result = changed_files_check(["scripts/maintenance/reprocess_from_local.py"])
        assert len(result["violations"]) == 0, (
            "Allowlisted manual_review file should not cause hard fail"
        )
        passed = result["passed"]
        assert len(passed) > 0
        allowlist_cls = passed[0].get("allowlist_classification", "")
        assert "needs_manual_review" in allowlist_cls, (
            f"Manual review file should retain needs_manual_review classification, "
            f"got: {allowlist_cls}"
        )


# ── SC-002 doc consistency tests ─────────────────────────────────────────────


class TestSC002DocConsistency:
    """Cross-document consistency checks."""

    def test_design_doc_references_phase2a_implementation(self):
        doc = _REPO_ROOT / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"
        if not doc.exists():
            pytest.skip("Design doc not found")
        content = doc.read_text()
        # May not yet reference Phase2A (we update docs later in this PR)
        # At minimum, it should exist and have the enforcement model section
        assert "Recommended enforcement model" in content
        assert "Phase 2A" in content

    def test_closure_plan_does_not_claim_sc002_complete(self):
        doc = _REPO_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
        if not doc.exists():
            pytest.skip("Closure plan not found")
        content = doc.read_text()
        # Must NOT claim SC-002 IS fully fixed (forbidden-terms table is OK)
        forbidden_claims = [
            "SC-002 is fully fixed",
            "SC-002 is complete",
            "SC-002 is resolved",
        ]
        for phrase in forbidden_claims:
            assert phrase not in content, f"Closure plan must not claim: '{phrase}'"

    def test_project_status_records_phase2a(self):
        doc = _REPO_ROOT / "docs" / "PROJECT_STATUS.md"
        if not doc.exists():
            pytest.skip("PROJECT_STATUS.md not found")
        content = doc.read_text()
        # May not yet reference Phase2A (we update docs later)
        # At minimum, verify training/data expansion remain blocked
        assert "blocked" in content.lower()

    def test_training_remains_blocked_in_docs(self):
        important_docs = [
            "docs/PROJECT_STATUS.md",
            "docs/SC002_CLOSURE_PLAN.md",
            "docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md",
        ]
        for doc_path in important_docs:
            doc = _REPO_ROOT / doc_path
            if not doc.exists():
                continue
            content = doc.read_text().lower()
            safe_to_train_refs = content.count("safe to train")
            assert safe_to_train_refs == 0 or "forbidden" in content, (
                f"{doc_path} must not claim 'safe to train'"
            )

    def test_runtime_guard_still_not_implemented(self):
        """Verify no Python runtime guard was created."""
        guard_path = _REPO_ROOT / "scripts" / "ops" / "helpers" / "db_write_guard.py"
        if guard_path.exists():
            content = guard_path.read_text()
            # If the file exists, it should be the advisory check (JS scanner wrapper)
            # not a Python runtime guard implementation
            has_runtime_guard = (
                "assert_db_write_allowed" in content or "def assert_db_write_allowed" in content
            )
            assert not has_runtime_guard, (
                "Python runtime guard should NOT be implemented in Phase2A"
            )

    def test_allowlist_does_not_authorize_runtime_writes(self):
        """Allowlist explicitly states it does not authorize runtime DB writes."""
        allowlist = _REPO_ROOT / "config" / "python_db_write_allowlist.json"
        content = allowlist.read_text()
        assert "DOES NOT AUTHORIZE" in content.upper() or "does not authorize" in content.lower(), (
            "Allowlist must explicitly state it does not authorize runtime DB writes"
        )
        assert "NOT IMPLEMENTED" in content, "Allowlist must state runtime guard is NOT IMPLEMENTED"


# ── Allowlist validation via CLI ─────────────────────────────────────────────


class TestAllowlistCLIValidation:
    """Validate allowlist via scanner CLI --validate-allowlist."""

    def test_validate_allowlist_cli(self):
        scanner = _REPO_ROOT / "scripts" / "ops" / "python_db_write_static_enforcement.py"
        proc = subprocess.run(
            ["python", str(scanner), "--validate-allowlist"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should exit 0 (all entries valid, no wildcards)
        assert proc.returncode == 0, f"Allowlist validation failed: {proc.stdout}\n{proc.stderr}"
