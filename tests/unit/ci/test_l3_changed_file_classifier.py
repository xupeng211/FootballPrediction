#!/usr/bin/env python3
"""
Unit tests for TECHDEBT-L3G warning-only changed-file classifier.

Tests cover:
  1. docs/techdebt/** → l3-docs
  2. scripts/ops/fotmob_probe.py → restricted-legacy
  3. scripts/ops/sentinel_watch.js → restricted-legacy + high-risk
  4. scripts/test/run_test_suite.js → test-only
  5. src/main.py → active-runtime
  6. .github/workflows/production-gate.yml → github-workflow-sensitive
  7. CODEOWNERS → codeowners-sensitive
  8. archive_vault_2026/foo.py → archive-read-only
  9. D old.py → deletion detected
  10. R100 old.py new.py → rename detected
  11. completely/unknown/path.xyz → unclassified-path
  12. CLI with --changed-files-file exits 0 and prints warning-only header

Lifecycle: L3G test artifact.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure we can import the classifier
_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "ci"
sys.path.insert(0, str(_SCRIPT_DIR))

from l3_changed_file_classifier import (  # type: ignore[import-not-found]
    LABEL_ACTIVE_API_ROUTER,
    LABEL_ACTIVE_GOVERNANCE,
    LABEL_ACTIVE_RUNTIME,
    LABEL_ARCHIVE_READ_ONLY,
    LABEL_CODEOWNERS_SENSITIVE,
    LABEL_DB_MIGRATION_SENSITIVE,
    LABEL_DOCKER_SENSITIVE,
    LABEL_DOCUMENTATION,
    LABEL_GATE_SENSITIVE,
    LABEL_GITHUB_WORKFLOW_SENSITIVE,
    LABEL_HIGH_RISK,
    LABEL_L3_DOCS,
    LABEL_RESTRICTED_LEGACY,
    LABEL_SCRAPER_TRAINING_SENSITIVE,
    LABEL_TEST_ONLY,
    LABEL_UNCLASSIFIED,
    _is_deletion,
    _is_rename,
    attention_notes,
    classify_path,
    main,
    parse_changed_files_file,
    render_output,
)


class TestPathClassification(unittest.TestCase):
    """Test classify_path() against expected L3 labels."""

    def test_l3_docs(self):
        """docs/techdebt/** → l3-docs"""
        labels = classify_path("docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md")
        self.assertIn(LABEL_L3_DOCS, labels)
        self.assertEqual(len(labels), 1, f"L3 docs should have single label, got {labels}")

    def test_l3_report_docs(self):
        """docs/_reports/L3* → l3-docs"""
        labels = classify_path("docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md")
        self.assertIn(LABEL_L3_DOCS, labels)

    def test_general_documentation(self):
        """docs/non-l3-doc.md → documentation"""
        labels = classify_path("docs/architecture/overview.md")
        self.assertIn(LABEL_DOCUMENTATION, labels)

    def test_fotmob_probe_restricted_legacy(self):
        """scripts/ops/fotmob_probe.py → restricted-legacy"""
        labels = classify_path("scripts/ops/fotmob_probe.py")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)
        self.assertNotIn(LABEL_HIGH_RISK, labels)

    def test_fotmob_wildcard_restricted_legacy(self):
        """scripts/ops/fotmob_endpoint_runtime_candidate_probe.py → restricted-legacy"""
        labels = classify_path("scripts/ops/fotmob_endpoint_runtime_candidate_probe.py")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_sentinel_watch_restricted_legacy_high_risk(self):
        """scripts/ops/sentinel_watch.js → restricted-legacy + high-risk"""
        labels = classify_path("scripts/ops/sentinel_watch.js")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)
        self.assertIn(LABEL_HIGH_RISK, labels)

    def test_check_health_restricted_legacy(self):
        """scripts/ops/check_health.js → restricted-legacy"""
        labels = classify_path("scripts/ops/check_health.js")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_audit_dataset_restricted_legacy(self):
        """scripts/ops/audit_dataset.js → restricted-legacy"""
        labels = classify_path("scripts/ops/audit_dataset.js")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_integrity_guard_restricted_legacy(self):
        """scripts/maintenance/integrity_guard.sh → restricted-legacy"""
        labels = classify_path("scripts/maintenance/integrity_guard.sh")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_run_test_suite_test_only(self):
        """scripts/test/run_test_suite.js → test-only"""
        labels = classify_path("scripts/test/run_test_suite.js")
        self.assertIn(LABEL_TEST_ONLY, labels)

    def test_tests_directory_test_only(self):
        """tests/unit/test_foo.py → test-only"""
        labels = classify_path("tests/unit/test_foo.py")
        self.assertIn(LABEL_TEST_ONLY, labels)

    def test_src_main_active_runtime(self):
        """src/main.py → active-runtime"""
        labels = classify_path("src/main.py")
        self.assertIn(LABEL_ACTIVE_RUNTIME, labels)

    def test_src_core_active_runtime(self):
        """src/core/config.py → active-runtime"""
        labels = classify_path("src/core/config.py")
        self.assertIn(LABEL_ACTIVE_RUNTIME, labels)

    def test_src_api_health_active_api_router(self):
        """src/api/health.py → active-api-router"""
        labels = classify_path("src/api/health.py")
        self.assertIn(LABEL_ACTIVE_API_ROUTER, labels)

    def test_github_workflow_sensitive(self):
        """.github/workflows/production-gate.yml → github-workflow-sensitive"""
        labels = classify_path(".github/workflows/production-gate.yml")
        self.assertIn(LABEL_GITHUB_WORKFLOW_SENSITIVE, labels)

    def test_github_dir_sensitive(self):
        """.github/dependabot.yml → github-workflow-sensitive"""
        labels = classify_path(".github/dependabot.yml")
        self.assertIn(LABEL_GITHUB_WORKFLOW_SENSITIVE, labels)

    def test_codeowners_sensitive(self):
        """CODEOWNERS → codeowners-sensitive"""
        labels = classify_path("CODEOWNERS")
        self.assertIn(LABEL_CODEOWNERS_SENSITIVE, labels)
        self.assertIn(LABEL_GITHUB_WORKFLOW_SENSITIVE, labels)

    def test_archive_read_only(self):
        """archive_vault_2026/foo.py → archive-read-only"""
        labels = classify_path("archive_vault_2026/foo.py")
        self.assertIn(LABEL_ARCHIVE_READ_ONLY, labels)

    def test_legacy_archive_read_only(self):
        """tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/run_benchmarks.py → archive-read-only"""
        labels = classify_path("tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/run_benchmarks.py")
        self.assertIn(LABEL_ARCHIVE_READ_ONLY, labels)

    def test_gatekeeper_active_governance_gate_sensitive(self):
        """scripts/devops/gatekeeper.sh → active-governance + gate-sensitive"""
        labels = classify_path("scripts/devops/gatekeeper.sh")
        self.assertIn(LABEL_ACTIVE_GOVERNANCE, labels)
        self.assertIn(LABEL_GATE_SENSITIVE, labels)

    def test_ai_workflow_gate_active_governance_gate_sensitive(self):
        """scripts/ops/ai_workflow_gate.py → active-governance + gate-sensitive"""
        labels = classify_path("scripts/ops/ai_workflow_gate.py")
        self.assertIn(LABEL_ACTIVE_GOVERNANCE, labels)
        self.assertIn(LABEL_GATE_SENSITIVE, labels)

    def test_unclassified_path(self):
        """completely/unknown/path.xyz → unclassified-path"""
        labels = classify_path("completely/unknown/path.xyz")
        self.assertIn(LABEL_UNCLASSIFIED, labels)

    def test_dockerfile_sensitive(self):
        """Dockerfile → docker-sensitive"""
        labels = classify_path("Dockerfile")
        self.assertIn(LABEL_DOCKER_SENSITIVE, labels)

    def test_docker_compose_sensitive(self):
        """docker-compose.dev.yml → docker-sensitive"""
        labels = classify_path("docker-compose.dev.yml")
        self.assertIn(LABEL_DOCKER_SENSITIVE, labels)

    def test_alembic_db_migration_sensitive(self):
        """alembic/versions/migration.py → db-migration-sensitive"""
        labels = classify_path("alembic/versions/001_migration.py")
        self.assertIn(LABEL_DB_MIGRATION_SENSITIVE, labels)

    def test_makefile_documentation(self):
        """Makefile → documentation (matches *.md glob for docs and general)"""
        labels = classify_path("Makefile")
        # Makefile shouldn't match *.md patterns
        self.assertNotIn(LABEL_DOCUMENTATION, labels)

    def test_run_production_restricted_legacy(self):
        """scripts/ops/run_production.js → restricted-legacy"""
        labels = classify_path("scripts/ops/run_production.js")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_maintenance_dir_restricted_legacy(self):
        """scripts/maintenance/cleanup.sh → restricted-legacy"""
        labels = classify_path("scripts/maintenance/cleanup.sh")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_predict_router_restricted_legacy(self):
        """src/api/predictions/predict_router.py → restricted-legacy"""
        labels = classify_path("src/api/predictions/predict_router.py")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)

    def test_train_model_restricted_legacy_scraper(self):
        """scripts/ops/train_model.py → restricted-legacy + scraper-training-sensitive"""
        labels = classify_path("scripts/ops/train_model.py")
        self.assertIn(LABEL_RESTRICTED_LEGACY, labels)
        self.assertIn(LABEL_SCRAPER_TRAINING_SENSITIVE, labels)

    def test_source_module_with_main(self):
        """src/core/environment_detector.py → active-runtime (module)"""
        labels = classify_path("src/core/environment_detector.py")
        self.assertIn(LABEL_ACTIVE_RUNTIME, labels)


class TestAttentionNotes(unittest.TestCase):
    """Test attention_notes() for deletion, rename, and special paths."""

    def test_deletion_detected(self):
        """D old.py → deletion detected note"""
        notes = attention_notes("old.py", "D", [LABEL_UNCLASSIFIED])
        self.assertTrue(any("DELETION DETECTED" in n for n in notes))

    def test_rename_detected(self):
        """R100 old.py new.py → rename detected note"""
        notes = attention_notes("new.py", "R100", [LABEL_ACTIVE_RUNTIME])
        self.assertTrue(any("RENAME/MOVE DETECTED" in n for n in notes))

    def test_high_risk_sentinel_note(self):
        """sentinel_watch.js → high-risk shutdown note"""
        notes = attention_notes(
            "scripts/ops/sentinel_watch.js",
            "M",
            [LABEL_RESTRICTED_LEGACY, LABEL_HIGH_RISK],
        )
        self.assertTrue(any("HIGH-RISK" in n for n in notes))
        self.assertTrue(any("sentinel_watch.js" in n for n in notes))

    def test_restricted_legacy_note(self):
        """restricted-legacy file → read-only note"""
        notes = attention_notes(
            "scripts/ops/fotmob_probe.py",
            "M",
            [LABEL_RESTRICTED_LEGACY],
        )
        self.assertTrue(any("restricted-legacy" in n for n in notes))

    def test_codeowners_note(self):
        """CODEOWNERS touched → separate authorization note"""
        notes = attention_notes(
            "CODEOWNERS",
            "M",
            [LABEL_CODEOWNERS_SENSITIVE, LABEL_GITHUB_WORKFLOW_SENSITIVE],
        )
        self.assertTrue(any("CODEOWNERS" in n for n in notes))

    def test_unclassified_note(self):
        """unclassified path → manual review note"""
        notes = attention_notes(
            "completely/unknown/path.xyz",
            "M",
            [LABEL_UNCLASSIFIED],
        )
        self.assertTrue(any("UNCLASSIFIED" in n for n in notes))

    def test_archive_note(self):
        """archive path → archive authorization note"""
        notes = attention_notes(
            "archive_vault_2026/data.json",
            "M",
            [LABEL_ARCHIVE_READ_ONLY],
        )
        self.assertTrue(any("archive-read-only" in n for n in notes))


class TestParseChangedFilesFile(unittest.TestCase):
    """Test parse_changed_files_file() with both path-only and name-status formats."""

    def test_path_only_format(self):
        """Path-only format parses correctly."""
        content = "docs/foo.md\nsrc/main.py\nscripts/bar.sh\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = parse_changed_files_file(tmp_path)
            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0], ("M", "docs/foo.md"))
            self.assertEqual(entries[1], ("M", "src/main.py"))
            self.assertEqual(entries[2], ("M", "scripts/bar.sh"))
        finally:
            os.unlink(tmp_path)

    def test_name_status_format(self):
        """git diff --name-status format parses correctly."""
        content = (
            "M\tdocs/foo.md\n"
            "A\tscripts/new_script.py\n"
            "D\told_legacy.py\n"
            "R100\told.py\tnew.py\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = parse_changed_files_file(tmp_path)
            self.assertEqual(len(entries), 4)
            self.assertEqual(entries[0], ("M", "docs/foo.md"))
            self.assertEqual(entries[1], ("A", "scripts/new_script.py"))
            self.assertEqual(entries[2], ("D", "old_legacy.py"))
            # For rename, we take the NEW path
            self.assertEqual(entries[3][0], "R100")
            self.assertEqual(entries[3][1], "new.py")
        finally:
            os.unlink(tmp_path)

    def test_whitespace_format(self):
        """Space-separated git diff format parses correctly."""
        content = "M    docs/foo.md\nD    old.py\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = parse_changed_files_file(tmp_path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0], ("M", "docs/foo.md"))
            self.assertEqual(entries[1], ("D", "old.py"))
        finally:
            os.unlink(tmp_path)

    def test_empty_lines_skipped(self):
        """Empty lines and comments are skipped."""
        content = "\n# comment line\n\ndocs/foo.md\n\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = parse_changed_files_file(tmp_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0], ("M", "docs/foo.md"))
        finally:
            os.unlink(tmp_path)


class TestRenderOutput(unittest.TestCase):
    """Test render_output() for correct header, summary, and table."""

    def test_header_present(self):
        """Output contains TECHDEBT-L3G warning-only header."""
        entries = [("M", "docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md")]
        output = render_output(entries, ".")
        self.assertIn("TECHDEBT-L3G warning-only changed-file classifier", output)
        self.assertIn("warning-only", output.lower())
        self.assertIn("This step is warning-only", output)

    def test_restricted_legacy_in_summary(self):
        """Output mentions restricted-legacy when touched."""
        entries = [("M", "scripts/ops/fotmob_probe.py")]
        output = render_output(entries, ".")
        self.assertIn("restricted-legacy", output)

    def test_high_risk_in_output(self):
        """Output mentions high-risk for sentinel_watch.js."""
        entries = [("M", "scripts/ops/sentinel_watch.js")]
        output = render_output(entries, ".")
        self.assertIn("high-risk", output)
        self.assertIn("HIGH-RISK", output)

    def test_codeowners_in_output(self):
        """Output mentions codeowners-sensitive for CODEOWNERS."""
        entries = [("M", "CODEOWNERS")]
        output = render_output(entries, ".")
        self.assertIn("codeowners-sensitive", output)

    def test_unclassified_in_output(self):
        """Output mentions unclassified-path for unknown files."""
        entries = [("M", "completely/unknown/path.xyz")]
        output = render_output(entries, ".")
        self.assertIn("unclassified-path", output)

    def test_deletion_in_output(self):
        """Output mentions deletion detected."""
        entries = [("D", "old_legacy.py")]
        output = render_output(entries, ".")
        self.assertIn("DELETION DETECTED", output)
        self.assertIn("deletion(s) detected", output)

    def test_rename_in_output(self):
        """Output mentions rename detected."""
        entries = [("R100", "new_path.py")]
        output = render_output(entries, ".")
        self.assertIn("RENAME/MOVE DETECTED", output)

    def test_markdown_table_present(self):
        """Output contains markdown table."""
        entries = [("M", "src/main.py")]
        output = render_output(entries, ".")
        self.assertIn("| Status | Path | Labels | Attention |", output)

    def test_empty_entries(self):
        """Output handles empty entries gracefully."""
        output = render_output([], ".")
        self.assertIn("No changed files detected", output)

    def test_non_blocking_footer(self):
        """Output contains non-blocking footer."""
        entries = [("M", "src/main.py")]
        output = render_output(entries, ".")
        self.assertIn("[L3-ENFORCEMENT][Layer-2][WARNING-ONLY]", output)
        self.assertIn("does not block CI", output)

    def test_summary_stats_present(self):
        """Output contains summary statistics."""
        entries = [
            ("M", "src/main.py"),
            ("M", "docs/techdebt/L3_FOO.md"),
            ("M", "scripts/ops/sentinel_watch.js"),
        ]
        output = render_output(entries, ".")
        self.assertIn("Changed file count: 3", output)
        self.assertIn("Labels touched:", output)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_is_deletion(self):
        self.assertTrue(_is_deletion("D"))
        self.assertFalse(_is_deletion("M"))
        self.assertFalse(_is_deletion("A"))
        self.assertFalse(_is_deletion("R100"))

    def test_is_rename(self):
        self.assertTrue(_is_rename("R100"))
        self.assertTrue(_is_rename("R050"))
        self.assertTrue(_is_rename("R"))
        self.assertFalse(_is_rename("M"))
        self.assertFalse(_is_rename("D"))


class TestCLI(unittest.TestCase):
    """Test CLI exits 0 and produces expected output."""

    def test_changed_files_file_exits_zero(self):
        """CLI with --changed-files-file exits 0."""
        content = "docs/techdebt/L3_FOO.md\nsrc/main.py\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            # Simulate CLI args
            old_argv = sys.argv
            sys.argv = [
                "l3_changed_file_classifier.py",
                "--changed-files-file", tmp_path,
            ]
            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
            finally:
                sys.argv = old_argv
        finally:
            os.unlink(tmp_path)

    def test_changed_files_file_prints_header(self):
        """CLI with --changed-files-file prints warning-only header."""
        content = "docs/techdebt/L3_FOO.md\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            import io

            old_argv = sys.argv
            old_stdout = sys.stdout
            sys.argv = [
                "l3_changed_file_classifier.py",
                "--changed-files-file", tmp_path,
            ]
            captured = io.StringIO()
            sys.stdout = captured

            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout

            output = captured.getvalue()
            self.assertIn("TECHDEBT-L3G warning-only changed-file classifier", output)
            self.assertIn("warning-only", output.lower())
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
