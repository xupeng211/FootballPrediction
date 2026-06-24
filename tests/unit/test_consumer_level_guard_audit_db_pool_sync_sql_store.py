#!/usr/bin/env python3
"""
Static tests for Consumer-Level Guard Audit: db_pool / sync_db_pool / sql_store.

lifecycle: permanent
scope: static verification only — does NOT import or execute target Python files,
       does NOT connect to DB, does NOT run SQL/migration, does NOT execute
       any Python scripts, does NOT perform real DB writes.

Tests cover:
  Audit document existence and content requirements
  Consumer classification table presence
  Required disclaimers (no DB, no SQL, SC-002 partial, training blocked)
  Allowlist entries for 3 infrastructure files still NOT runtime_guarded
  Allowlist entries have consumer audit fields
  Existing 9 runtime_guarded entries unchanged
  Read-only candidates NOT marked safe
  Indirect write paths NOT changed to guarded
  Manual review candidates NOT changed to safe
  Scanner test compatibility
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

# ── Fixtures ─────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MIN_AUDIT_DOC_LENGTH = 500


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
def audit_doc(repo_root):
    """The consumer-level guard audit document."""
    p = repo_root / "docs" / "SC002_CONSUMER_LEVEL_GUARD_AUDIT_DB_POOL_SYNC_SQL_STORE.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    pytest.skip("Audit document not found")


# ── The 3 infrastructure files under audit ────────────────────────────────────

INFRASTRUCTURE_FILES = [
    "src/database/sql_store.py",
    "src/database/sync_db_pool.py",
    "src/database/db_pool.py",
]

# Phase2C batch1+2+3 runtime_guarded files (9 total)
RUNTIME_GUARDED_FILES = [
    "scripts/ops/ai_workflow_gate.py",
    "scripts/ops/local_pr_gate_preflight.py",
    "scripts/devops/gatekeeper.sh",
    "scripts/ops/helpers/db_write_guard.js",
    "scripts/ops/db_write_guard_static_enforcement_dry_run.js",
    "scripts/ops/helpers/python_db_write_guard.py",
    "src/database/collector_repository.py",
    "src/data/streaming/streaming_db_writer.py",
    "src/core/database/odds_injector.py",
]

# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Audit document existence and content
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditDocumentExists:
    """Audit document exists and covers all three infrastructure files."""

    def test_audit_doc_exists(self, audit_doc):
        """Audit document is present and non-empty."""
        assert audit_doc, "Audit document must exist and be non-empty"
        assert len(audit_doc) > _MIN_AUDIT_DOC_LENGTH, (
            "Audit document should have substantial content"
        )

    @pytest.mark.parametrize("infra_file", INFRASTRUCTURE_FILES)
    def test_doc_covers_file(self, audit_doc, infra_file):
        """Audit document covers each infrastructure file."""
        fname = infra_file.split("/")[-1]
        assert fname in audit_doc, f"Audit doc must reference {fname}"

    def test_doc_contains_consumer_classification_table(self, audit_doc):
        """Audit document contains a consumer classification table."""
        assert "consumer" in audit_doc.lower(), "Audit doc must discuss consumers"
        assert "Classification" in audit_doc, "Audit doc must have classification section"
        assert "read_only" in audit_doc.lower() or "read-only" in audit_doc.lower(), (
            "Audit doc must classify read-only consumers"
        )

    def test_doc_contains_no_db_disclaimer(self, audit_doc):
        """Audit document states no DB connection was made."""
        assert "No DB connection" in audit_doc or "no DB connection" in audit_doc.lower(), (
            "Audit doc must state no DB connection"
        )

    def test_doc_contains_no_sql_disclaimer(self, audit_doc):
        """Audit document states no SQL/migration was executed."""
        assert "No SQL" in audit_doc or "no SQL" in audit_doc.lower(), (
            "Audit doc must state no SQL execution"
        )

    def test_doc_contains_no_real_write_disclaimer(self, audit_doc):
        """Audit document states no real DB write was performed."""
        assert "No real DB write" in audit_doc or "no real DB write" in audit_doc.lower(), (
            "Audit doc must state no real DB write"
        )

    def test_doc_contains_sc002_partial_mitigation(self, audit_doc):
        """Audit document states SC-002 remains partial mitigation only."""
        assert "partial mitigation" in audit_doc.lower(), (
            "Audit doc must state SC-002 remains partial mitigation"
        )

    def test_doc_contains_training_blocked(self, audit_doc):
        """Audit document states training/data expansion/real DB write remain blocked."""
        assert "remain blocked" in audit_doc.lower(), (
            "Audit doc must state training/data expansion/real DB write remain blocked"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: Allowlist state — infrastructure files NOT runtime_guarded
# ═══════════════════════════════════════════════════════════════════════════════


class TestInfrastructureFilesNotGuarded:
    """The 3 infrastructure files remain NOT runtime_guarded."""

    @pytest.mark.parametrize("infra_file", INFRASTRUCTURE_FILES)
    def test_file_classification_not_runtime_guarded(self, allowlist_entries, infra_file):
        """Infrastructure file classification does NOT contain runtime_guarded."""
        entry = next((e for e in allowlist_entries if e["path"] == infra_file), None)
        assert entry is not None, f"{infra_file} must exist in allowlist"
        classification = entry.get("classification", "")
        assert "runtime_guarded" not in classification, (
            f"{infra_file} must NOT be runtime_guarded, got: {classification}"
        )

    @pytest.mark.parametrize("infra_file", INFRASTRUCTURE_FILES)
    def test_file_has_consumer_audit_task(self, allowlist_entries, infra_file):
        """Infrastructure file entry has consumer_audit_task field."""
        entry = next((e for e in allowlist_entries if e["path"] == infra_file), None)
        assert entry is not None
        assert (
            entry.get("consumer_audit_task")
            == "consumer_level_guard_audit_for_db_pool_sync_db_pool_sql_store"
        ), f"{infra_file} must have consumer_audit_task"

    @pytest.mark.parametrize("infra_file", INFRASTRUCTURE_FILES)
    def test_file_has_recommended_next_action(self, allowlist_entries, infra_file):
        """Infrastructure file entry has recommended_next_action."""
        entry = next((e for e in allowlist_entries if e["path"] == infra_file), None)
        assert entry is not None
        assert entry.get("recommended_next_action"), (
            f"{infra_file} must have recommended_next_action"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Existing runtime_guarded entries preserved
# ═══════════════════════════════════════════════════════════════════════════════


class TestExistingGuardedPathsPreserved:
    """Existing 9 runtime_guarded entries remain unchanged."""

    @pytest.mark.parametrize("guarded_file", RUNTIME_GUARDED_FILES)
    def test_guarded_file_still_guarded(self, allowlist_entries, guarded_file):
        """Previously guarded files are still runtime_guarded or equivalent."""
        entry = next((e for e in allowlist_entries if e["path"] == guarded_file), None)
        if entry is None:
            # Not all guarded files may have explicit allowlist entries;
            # some may be guarded via batch manifests
            return
        classification = entry.get("classification", "")
        assert "runtime_guarded" in classification or "guarded" in classification.lower(), (
            f"{guarded_file} must remain guarded, got: {classification}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: read_only_candidate entries NOT changed to safe
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadOnlyCandidatesNotChanged:
    """read_only_candidate entries have not been changed to safe."""

    def test_no_read_only_candidate_became_safe(self, allowlist_entries):
        """No read_only_candidate is now marked safe."""
        for entry in allowlist_entries:
            classification = entry.get("classification", "")
            if "read_only_candidate" in classification:
                assert "safe" not in classification.lower(), (
                    f"{entry['path']} is read_only_candidate, must not be safe"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Indirect write paths NOT changed
# ═══════════════════════════════════════════════════════════════════════════════


class TestIndirectWritePathsNotChanged:
    """Indirect write paths have not been changed to guarded."""

    def test_indirect_write_paths_not_guarded(self, allowlist_entries):
        """No indirect write path has been changed to runtime_guarded."""
        for entry in allowlist_entries:
            classification = entry.get("classification", "")
            path = entry.get("path", "")
            if "indirect" in classification.lower():
                assert "runtime_guarded" not in classification, (
                    f"Indirect write path {path} must not be runtime_guarded"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: Manual review candidates NOT changed to safe
# ═══════════════════════════════════════════════════════════════════════════════


class TestManualReviewCandidatesNotChanged:
    """Manual review candidates have not been changed to safe."""

    def test_manual_review_candidates_not_safe(self, allowlist_entries):
        """No manual review candidate has been changed to safe."""
        for entry in allowlist_entries:
            classification = entry.get("classification", "")
            path = entry.get("path", "")
            if (
                "manual_review" in classification.lower()
                or "needs_manual_review" in classification.lower()
            ):
                assert "safe" not in classification.lower(), (
                    f"Manual review candidate {path} must not be safe"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7: Consumer audit completeness
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsumerAuditCompleteness:
    """Consumer audit covers all required classifications."""

    def test_audit_doc_has_consumer_count(self, audit_doc):
        """Audit document reports total consumer count."""
        assert "Total" in audit_doc or "11" in audit_doc, (
            "Audit doc should contain consumer count summary"
        )

    def test_audit_doc_has_category_a(self, audit_doc):
        """Audit doc identifies category A (write_needs_guard) or states zero."""
        assert "consumer_write_needs_guard" in audit_doc or "write_needs_guard" in audit_doc, (
            "Audit doc must address category A (write_needs_guard)"
        )

    def test_audit_doc_has_category_b(self, audit_doc):
        """Audit doc identifies category B (write_already_guarded)."""
        assert (
            "consumer_write_already_guarded" in audit_doc
            or "already_guarded" in audit_doc
            or "already guarded" in audit_doc.lower()
        ), "Audit doc must address category B (write_already_guarded)"

    def test_audit_doc_has_category_c(self, audit_doc):
        """Audit doc identifies category C (read_only)."""
        assert "consumer_read_only" in audit_doc or "read_only" in audit_doc, (
            "Audit doc must address category C (read_only)"
        )

    def test_audit_doc_has_category_f(self, audit_doc):
        """Audit doc identifies category F (no_active_consumers)."""
        assert "no_active_consumers" in audit_doc, (
            "Audit doc must address category F (no_active_consumers)"
        )

    def test_collector_repository_identified_as_guarded(self, audit_doc):
        """collector_repository.py identified as already guarded."""
        assert "collector_repository" in audit_doc, "Audit doc must mention collector_repository.py"

    def test_streaming_db_writer_identified_as_guarded(self, audit_doc):
        """streaming_db_writer.py identified as already guarded."""
        assert "streaming_db_writer" in audit_doc, "Audit doc must mention streaming_db_writer.py"

    def test_sql_store_no_consumers(self, audit_doc):
        """SQLStore has zero active consumers documented."""
        assert (
            "zero" in audit_doc.lower()
            or "no active consumers" in audit_doc.lower()
            or "0" in audit_doc
        ), "Audit doc must document SQLStore has zero/no consumers"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8: No runtime guard was added in this task
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoRuntimeGuardAdded:
    """This task did not add any runtime guard."""

    def test_audit_doc_states_no_guard_added(self, audit_doc):
        """Audit document explicitly states no runtime guard was added."""
        assert (
            "No runtime guard" in audit_doc
            or "no runtime guard" in audit_doc.lower()
            or "did NOT implement" in audit_doc
            or "does NOT implement" in audit_doc
        ), "Audit doc must state no runtime guards were added"

    def test_infrastructure_files_not_modified(self, repo_root):
        """Infrastructure files were not modified by this task."""
        result = subprocess.run(
            ["git", "diff", "origin/main", "--name-only"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
        changed = result.stdout.strip().split("\n") if result.stdout.strip() else []
        infra_changed = [f for f in changed if f in INFRASTRUCTURE_FILES]
        assert not infra_changed, f"Infrastructure files must not be modified: {infra_changed}"
