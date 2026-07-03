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

from __future__ import annotations

from collections import Counter
import io
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

# Ensure we can import the classifier script from scripts/ci/
_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "ci"
sys.path.insert(0, str(_SCRIPT_DIR))

import l3_changed_file_classifier as classifier  # noqa: E402


class TestPathClassification:
    """Test classifier.classify_path() against expected L3 labels."""

    def test_l3_docs(self):
        """docs/techdebt/** → l3-docs"""
        labels = classifier.classify_path("docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md")
        assert classifier.LABEL_L3_DOCS in labels
        assert len(labels) == 1, f"L3 docs should have single label, got {labels}"

    def test_l3_report_docs(self):
        """docs/_reports/L3* → l3-docs"""
        labels = classifier.classify_path("docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md")
        assert classifier.LABEL_L3_DOCS in labels

    def test_general_documentation(self):
        """docs/non-l3-doc.md → documentation"""
        labels = classifier.classify_path("docs/architecture/overview.md")
        assert classifier.LABEL_DOCUMENTATION in labels

    def test_fotmob_probe_restricted_legacy(self):
        """scripts/ops/fotmob_probe.py → restricted-legacy"""
        labels = classifier.classify_path("scripts/ops/fotmob_probe.py")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels
        assert classifier.LABEL_HIGH_RISK not in labels

    def test_fotmob_wildcard_restricted_legacy(self):
        """scripts/ops/fotmob_endpoint_runtime_candidate_probe.py → restricted-legacy"""
        labels = classifier.classify_path("scripts/ops/fotmob_endpoint_runtime_candidate_probe.py")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_sentinel_watch_restricted_legacy_high_risk(self):
        """scripts/ops/sentinel_watch.js → restricted-legacy + high-risk"""
        labels = classifier.classify_path("scripts/ops/sentinel_watch.js")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels
        assert classifier.LABEL_HIGH_RISK in labels

    def test_check_health_restricted_legacy(self):
        """scripts/ops/check_health.js → restricted-legacy"""
        labels = classifier.classify_path("scripts/ops/check_health.js")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_audit_dataset_restricted_legacy(self):
        """scripts/ops/audit_dataset.js → restricted-legacy"""
        labels = classifier.classify_path("scripts/ops/audit_dataset.js")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_integrity_guard_restricted_legacy(self):
        """scripts/maintenance/integrity_guard.sh → restricted-legacy"""
        labels = classifier.classify_path("scripts/maintenance/integrity_guard.sh")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_run_test_suite_test_only(self):
        """scripts/test/run_test_suite.js → test-only"""
        labels = classifier.classify_path("scripts/test/run_test_suite.js")
        assert classifier.LABEL_TEST_ONLY in labels

    def test_tests_directory_test_only(self):
        """tests/unit/test_foo.py → test-only"""
        labels = classifier.classify_path("tests/unit/test_foo.py")
        assert classifier.LABEL_TEST_ONLY in labels

    def test_src_main_active_runtime(self):
        """src/main.py → active-runtime"""
        labels = classifier.classify_path("src/main.py")
        assert classifier.LABEL_ACTIVE_RUNTIME in labels

    def test_src_core_active_runtime(self):
        """src/core/config.py → active-runtime"""
        labels = classifier.classify_path("src/core/config.py")
        assert classifier.LABEL_ACTIVE_RUNTIME in labels

    def test_src_api_health_active_api_router(self):
        """src/api/health.py → active-api-router"""
        labels = classifier.classify_path("src/api/health.py")
        assert classifier.LABEL_ACTIVE_API_ROUTER in labels

    def test_github_workflow_sensitive(self):
        """.github/workflows/production-gate.yml → github-workflow-sensitive"""
        labels = classifier.classify_path(".github/workflows/production-gate.yml")
        assert classifier.LABEL_GITHUB_WORKFLOW_SENSITIVE in labels

    def test_github_dir_sensitive(self):
        """.github/dependabot.yml → github-workflow-sensitive"""
        labels = classifier.classify_path(".github/dependabot.yml")
        assert classifier.LABEL_GITHUB_WORKFLOW_SENSITIVE in labels

    def test_codeowners_sensitive(self):
        """CODEOWNERS → codeowners-sensitive"""
        labels = classifier.classify_path("CODEOWNERS")
        assert classifier.LABEL_CODEOWNERS_SENSITIVE in labels
        assert classifier.LABEL_GITHUB_WORKFLOW_SENSITIVE in labels

    def test_archive_read_only(self):
        """archive_vault_2026/foo.py → archive-read-only"""
        labels = classifier.classify_path("archive_vault_2026/foo.py")
        assert classifier.LABEL_ARCHIVE_READ_ONLY in labels

    def test_legacy_archive_read_only(self):
        """tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/run_benchmarks.py → archive-read-only"""
        labels = classifier.classify_path("tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/run_benchmarks.py")
        assert classifier.LABEL_ARCHIVE_READ_ONLY in labels

    def test_gatekeeper_active_governance_gate_sensitive(self):
        """scripts/devops/gatekeeper.sh → active-governance + gate-sensitive"""
        labels = classifier.classify_path("scripts/devops/gatekeeper.sh")
        assert classifier.LABEL_ACTIVE_GOVERNANCE in labels
        assert classifier.LABEL_GATE_SENSITIVE in labels

    def test_ai_workflow_gate_active_governance_gate_sensitive(self):
        """scripts/ops/ai_workflow_gate.py → active-governance + gate-sensitive"""
        labels = classifier.classify_path("scripts/ops/ai_workflow_gate.py")
        assert classifier.LABEL_ACTIVE_GOVERNANCE in labels
        assert classifier.LABEL_GATE_SENSITIVE in labels

    def test_unclassified_path(self):
        """completely/unknown/path.xyz → unclassified-path"""
        labels = classifier.classify_path("completely/unknown/path.xyz")
        assert classifier.LABEL_UNCLASSIFIED in labels

    def test_dockerfile_sensitive(self):
        """Dockerfile → docker-sensitive"""
        labels = classifier.classify_path("Dockerfile")
        assert classifier.LABEL_DOCKER_SENSITIVE in labels

    def test_docker_compose_sensitive(self):
        """docker-compose.dev.yml → docker-sensitive"""
        labels = classifier.classify_path("docker-compose.dev.yml")
        assert classifier.LABEL_DOCKER_SENSITIVE in labels

    def test_alembic_db_migration_sensitive(self):
        """alembic/versions/migration.py → db-migration-sensitive"""
        labels = classifier.classify_path("alembic/versions/001_migration.py")
        assert classifier.LABEL_DB_MIGRATION_SENSITIVE in labels

    def test_makefile_documentation(self):
        """Makefile → documentation (matches *.md glob for docs and general)"""
        labels = classifier.classify_path("Makefile")
        # Makefile shouldn't match *.md patterns
        assert classifier.LABEL_DOCUMENTATION not in labels

    def test_run_production_restricted_legacy(self):
        """scripts/ops/run_production.js → restricted-legacy"""
        labels = classifier.classify_path("scripts/ops/run_production.js")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_maintenance_dir_restricted_legacy(self):
        """scripts/maintenance/cleanup.sh → restricted-legacy"""
        labels = classifier.classify_path("scripts/maintenance/cleanup.sh")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_predict_router_restricted_legacy(self):
        """src/api/predictions/predict_router.py → restricted-legacy"""
        labels = classifier.classify_path("src/api/predictions/predict_router.py")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels

    def test_train_model_restricted_legacy_scraper(self):
        """scripts/ops/train_model.py → restricted-legacy + scraper-training-sensitive"""
        labels = classifier.classify_path("scripts/ops/train_model.py")
        assert classifier.LABEL_RESTRICTED_LEGACY in labels
        assert classifier.LABEL_SCRAPER_TRAINING_SENSITIVE in labels

    def test_source_module_with_main(self):
        """src/core/environment_detector.py → active-runtime (module)"""
        labels = classifier.classify_path("src/core/environment_detector.py")
        assert classifier.LABEL_ACTIVE_RUNTIME in labels


class TestAttentionNotes:
    """Test classifier.attention_notes() for deletion, rename, and special paths."""

    def test_deletion_detected(self):
        """D old.py → deletion detected note"""
        notes = classifier.attention_notes("old.py", "D", [classifier.LABEL_UNCLASSIFIED])
        assert any("DELETION DETECTED" in n for n in notes)

    def test_rename_detected(self):
        """R100 old.py new.py → rename detected note"""
        notes = classifier.attention_notes("new.py", "R100", [classifier.LABEL_ACTIVE_RUNTIME])
        assert any("RENAME/MOVE DETECTED" in n for n in notes)

    def test_high_risk_sentinel_note(self):
        """sentinel_watch.js → high-risk shutdown note"""
        notes = classifier.attention_notes(
            "scripts/ops/sentinel_watch.js",
            "M",
            [classifier.LABEL_RESTRICTED_LEGACY, classifier.LABEL_HIGH_RISK],
        )
        assert any("HIGH-RISK" in n for n in notes)
        assert any("sentinel_watch.js" in n for n in notes)

    def test_restricted_legacy_note(self):
        """restricted-legacy file → read-only note"""
        notes = classifier.attention_notes(
            "scripts/ops/fotmob_probe.py",
            "M",
            [classifier.LABEL_RESTRICTED_LEGACY],
        )
        assert any("restricted-legacy" in n for n in notes)

    def test_codeowners_note(self):
        """CODEOWNERS touched → separate authorization note"""
        notes = classifier.attention_notes(
            "CODEOWNERS",
            "M",
            [classifier.LABEL_CODEOWNERS_SENSITIVE, classifier.LABEL_GITHUB_WORKFLOW_SENSITIVE],
        )
        assert any("CODEOWNERS" in n for n in notes)

    def test_unclassified_note(self):
        """unclassified path → manual review note"""
        notes = classifier.attention_notes(
            "completely/unknown/path.xyz",
            "M",
            [classifier.LABEL_UNCLASSIFIED],
        )
        assert any("UNCLASSIFIED" in n for n in notes)

    def test_archive_note(self):
        """archive path → archive authorization note"""
        notes = classifier.attention_notes(
            "archive_vault_2026/data.json",
            "M",
            [classifier.LABEL_ARCHIVE_READ_ONLY],
        )
        assert any("archive-read-only" in n for n in notes)


class TestParseChangedFilesFile:
    """Test classifier.parse_changed_files_file() with both path-only and name-status formats."""

    def test_path_only_format(self):
        """Path-only format parses correctly."""
        content = "docs/foo.md\nsrc/main.py\nscripts/bar.sh\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = classifier.parse_changed_files_file(tmp_path)
            assert len(entries) == 3  # noqa: PLR2004
            assert entries[0] == ("M", "docs/foo.md")
            assert entries[1] == ("M", "src/main.py")
            assert entries[2] == ("M", "scripts/bar.sh")
        finally:
            Path(tmp_path).unlink()

    def test_name_status_format(self):
        """git diff --name-status format parses correctly."""
        content = (
            "M\tdocs/foo.md\nA\tscripts/new_script.py\nD\told_legacy.py\nR100\told.py\tnew.py\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = classifier.parse_changed_files_file(tmp_path)
            assert len(entries) == 4  # noqa: PLR2004
            assert entries[0] == ("M", "docs/foo.md")
            assert entries[1] == ("A", "scripts/new_script.py")
            assert entries[2] == ("D", "old_legacy.py")
            # For rename, we take the NEW path
            assert entries[3][0] == "R100"
            assert entries[3][1] == "new.py"
        finally:
            Path(tmp_path).unlink()

    def test_whitespace_format(self):
        """Space-separated git diff format parses correctly."""
        content = "M    docs/foo.md\nD    old.py\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = classifier.parse_changed_files_file(tmp_path)
            assert len(entries) == 2  # noqa: PLR2004
            assert entries[0] == ("M", "docs/foo.md")
            assert entries[1] == ("D", "old.py")
        finally:
            Path(tmp_path).unlink()

    def test_empty_lines_skipped(self):
        """Empty lines and comments are skipped."""
        content = "\n# comment line\n\ndocs/foo.md\n\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            entries = classifier.parse_changed_files_file(tmp_path)
            assert len(entries) == 1
            assert entries[0] == ("M", "docs/foo.md")
        finally:
            Path(tmp_path).unlink()


class TestRenderOutput:
    """Test classifier.render_output() for correct header, summary, and table."""

    def test_header_present(self):
        """Output contains TECHDEBT-L3G warning-only header."""
        entries = [("M", "docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md")]
        output = classifier.render_output(entries, ".")
        assert "TECHDEBT-L3G warning-only changed-file classifier" in output
        assert "warning-only" in output.lower()
        assert "This step is warning-only" in output

    def test_restricted_legacy_in_summary(self):
        """Output mentions restricted-legacy when touched."""
        entries = [("M", "scripts/ops/fotmob_probe.py")]
        output = classifier.render_output(entries, ".")
        assert "restricted-legacy" in output

    def test_high_risk_in_output(self):
        """Output mentions high-risk for sentinel_watch.js."""
        entries = [("M", "scripts/ops/sentinel_watch.js")]
        output = classifier.render_output(entries, ".")
        assert "high-risk" in output
        assert "HIGH-RISK" in output

    def test_codeowners_in_output(self):
        """Output mentions codeowners-sensitive for CODEOWNERS."""
        entries = [("M", "CODEOWNERS")]
        output = classifier.render_output(entries, ".")
        assert "codeowners-sensitive" in output

    def test_unclassified_in_output(self):
        """Output mentions unclassified-path for unknown files."""
        entries = [("M", "completely/unknown/path.xyz")]
        output = classifier.render_output(entries, ".")
        assert "unclassified-path" in output

    def test_deletion_in_output(self):
        """Output mentions deletion detected."""
        entries = [("D", "old_legacy.py")]
        output = classifier.render_output(entries, ".")
        assert "DELETION DETECTED" in output
        assert "deletion(s) detected" in output

    def test_rename_in_output(self):
        """Output mentions rename detected."""
        entries = [("R100", "new_path.py")]
        output = classifier.render_output(entries, ".")
        assert "RENAME/MOVE DETECTED" in output

    def test_markdown_table_present(self):
        """Output contains markdown table."""
        entries = [("M", "src/main.py")]
        output = classifier.render_output(entries, ".")
        assert "| Status | Path | Labels | Attention |" in output

    def test_empty_entries(self):
        """Output handles empty entries gracefully."""
        output = classifier.render_output([], ".")
        assert "No changed files detected" in output

    def test_non_blocking_footer(self):
        """Output contains non-blocking footer."""
        entries = [("M", "src/main.py")]
        output = classifier.render_output(entries, ".")
        assert "[L3-ENFORCEMENT][Layer-2][WARNING-ONLY]" in output
        assert "does not block CI" in output

    def test_summary_stats_present(self):
        """Output contains summary statistics."""
        entries = [
            ("M", "src/main.py"),
            ("M", "docs/techdebt/L3_FOO.md"),
            ("M", "scripts/ops/sentinel_watch.js"),
        ]
        output = classifier.render_output(entries, ".")
        assert "Changed file count: 3" in output
        assert "Labels touched:" in output


class TestHelperFunctions:
    """Test helper functions."""

    def test_is_deletion(self):
        assert classifier._is_deletion("D")
        assert not classifier._is_deletion("M")
        assert not classifier._is_deletion("A")
        assert not classifier._is_deletion("R100")

    def test_is_rename(self):
        assert classifier._is_rename("R100")
        assert classifier._is_rename("R050")
        assert classifier._is_rename("R")
        assert not classifier._is_rename("M")
        assert not classifier._is_rename("D")


class TestCLI:
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
                "--changed-files-file",
                tmp_path,
            ]
            try:
                classifier.main()
            except SystemExit as e:
                assert e.code == 0  # noqa: PT017
            finally:
                sys.argv = old_argv
        finally:
            Path(tmp_path).unlink()

    def test_changed_files_file_prints_header(self):
        """CLI with --changed-files-file prints warning-only header."""
        content = "docs/techdebt/L3_FOO.md\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            old_argv = sys.argv
            old_stdout = sys.stdout
            sys.argv = [
                "l3_changed_file_classifier.py",
                "--changed-files-file",
                tmp_path,
            ]
            captured = io.StringIO()
            sys.stdout = captured

            try:
                classifier.main()
            except SystemExit as e:
                assert e.code == 0  # noqa: PT017
            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout

            output = captured.getvalue()
            assert "TECHDEBT-L3G warning-only changed-file classifier" in output
            assert "warning-only" in output.lower()
        finally:
            Path(tmp_path).unlink()


class TestSummaryMarkdown:
    """Test _build_summary_markdown() and write_summary() for L3H visibility."""

    @staticmethod
    def _sample_md():
        """Build summary markdown from sample entries."""
        entries = [
            ("M", "docs/techdebt/L3_WARNING_ONLY_CHANGED_FILE_CLASSIFIER.md"),
            ("M", "scripts/ops/sentinel_watch.js"),
            ("M", "scripts/ops/fotmob_probe.py"),
            ("M", "completely/unknown/path.xyz"),
            ("D", "old_legacy.py"),
        ]
        classified, cnt = [], Counter()
        dc = rc = rlc = hrc = uc = 0
        for status, path in entries:
            labels = classifier.classify_path(path)
            notes = classifier.attention_notes(path, status, labels)
            classified.append({"status": status, "path": path, "labels": labels, "notes": notes})
            for lbl in labels:
                cnt[lbl] += 1
            if classifier._is_deletion(status):
                dc += 1
            if classifier._is_rename(status):
                rc += 1
            if classifier.LABEL_RESTRICTED_LEGACY in labels:
                rlc += 1
            if classifier.LABEL_HIGH_RISK in labels:
                hrc += 1
            if classifier.LABEL_UNCLASSIFIED in labels:
                uc += 1
        falses = (
            False,
        ) * 7  # codeowners, github, gate, docker, db_migration, scraper_training, archive
        return (
            classifier._build_summary_markdown(
                entries, classified, cnt, dc, rc, rlc, hrc, uc, *falses
            ),
            entries,
            classified,
            cnt,
        )

    def test_summary_warning_only_and_no_blocking(self):
        """Summary contains warning-only and No blocking decision."""
        md, _, _, _ = self._sample_md()
        assert "warning-only" in md.lower()
        assert "No blocking decision is made" in md

    def test_summary_key_fields(self):
        """Summary: changed file count, high-risk, restricted-legacy, unclassified, deletion."""
        md, _, _, _ = self._sample_md()
        assert "Changed files | 5" in md
        assert "high-risk" in md.lower()
        assert "restricted-legacy" in md
        assert "unclassified" in md.lower()
        assert "deletion" in md.lower()

    def test_summary_file_writes_markdown(self):
        """--summary-file writes markdown to the specified file."""
        md, _, _, _ = self._sample_md()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            tmp_path = f.name
        try:
            assert classifier.write_summary(md, summary_file=tmp_path) is True
            written = Path(tmp_path).read_text(encoding="utf-8")
            assert "TECHDEBT-L3G Warning-Only" in written
            assert "No blocking decision is made" in written
        finally:
            Path(tmp_path).unlink()

    def test_github_step_summary_env_writes(self):
        """GITHUB_STEP_SUMMARY env var triggers summary write."""
        md, _, _, _ = self._sample_md()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            tmp_path = f.name
        try:
            with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": tmp_path}):
                assert classifier.write_summary(md, summary_file=None) is True
            written = Path(tmp_path).read_text(encoding="utf-8")
            assert "TECHDEBT-L3G Warning-Only" in written
            assert "No blocking decision is made" in written
        finally:
            Path(tmp_path).unlink()

    def test_summary_write_failure_does_not_raise(self):
        """write_summary returns False on unwritable path, never raises."""
        assert classifier.write_summary("# Test\n", summary_file="/nonexistent/dir/s.md") is False

    def _run_cli_exit_zero(self, content):
        """Helper: run CLI with content, assert exit 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            old_argv = sys.argv
            sys.argv = ["l3_changed_file_classifier.py", "--changed-files-file", tmp_path]
            try:
                classifier.main()
            except SystemExit as e:
                assert e.code == 0  # noqa: PT017
            finally:
                sys.argv = old_argv
        finally:
            Path(tmp_path).unlink()

    def test_stdout_preserved_with_summary(self):
        """Original stdout is preserved when --summary-file is used."""
        content = "docs/techdebt/L3_FOO.md\nsrc/main.py\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as sf:
            summary_path = sf.name
        try:
            old_argv, old_stdout = sys.argv, sys.stdout
            sys.argv = [
                "l3_changed_file_classifier.py",
                "--changed-files-file",
                tmp_path,
                "--summary-file",
                summary_path,
            ]
            captured = io.StringIO()
            sys.stdout = captured
            try:
                classifier.main()
            except SystemExit as e:
                assert e.code == 0  # noqa: PT017
            finally:
                sys.argv, sys.stdout = old_argv, old_stdout
            out = captured.getvalue()
            assert "TECHDEBT-L3G warning-only changed-file classifier" in out
            assert "| Status | Path | Labels | Attention |" in out
        finally:
            Path(tmp_path).unlink()
            Path(summary_path).unlink()

    def test_restricted_legacy_exits_zero(self):
        """restricted-legacy files still exit 0."""
        self._run_cli_exit_zero("scripts/ops/sentinel_watch.js\n")

    def test_unclassified_exits_zero(self):
        """unclassified paths still exit 0."""
        self._run_cli_exit_zero("completely/unknown/file.xyz\n")

    def test_deletion_exits_zero(self):
        """deletion signals still exit 0."""
        self._run_cli_exit_zero("D    old_legacy.py\n")

    def test_rename_exits_zero(self):
        """rename signals still exit 0."""
        self._run_cli_exit_zero("R100    old.py    new.py\n")
