"""Tests for static_quality_changed_lines.py — focus on hunk header parsing.

The key fix: ``endswith("@@")`` is too strict; git unified diff hunk headers
may have trailing context text, e.g. ``@@ -9,7 +9,7 @@ import logging``.
The correct detection uses both the opening ``@@`` and the closing ``@@``
anywhere after column 2.
"""

# ruff: noqa: PLR2004 — magic numbers are hunk line numbers from test diff data

import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import patch

# Load the module from the scripts/devops directory.
_MODULE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "devops"
    / "static_quality_changed_lines.py"
)
_spec = importlib.util.spec_from_file_location("static_quality_changed_lines", _MODULE_PATH)
_static_ql = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_static_ql)

_parse_hunk_new_start = _static_ql._parse_hunk_new_start
_collect_changed_lines_for_file = _static_ql._collect_changed_lines_for_file
_normalize_path = _static_ql._normalize_path
_classify_diagnostics = _static_ql.classify_diagnostics
_parse_mypy_output = _static_ql.parse_mypy_output


class TestParseHunkNewStart:
    """Unit tests for _parse_hunk_new_start — the hunk-header line-number parser."""

    def test_standard_hunk_with_context(self):
        """@@ -9,7 +9,7 @@ import logging → new_start = 9"""
        assert _parse_hunk_new_start("@@ -9,7 +9,7 @@ import logging") == 9

    def test_hunk_with_no_context(self):
        """@@ -43,6 +43,7 @@ → new_start = 43"""
        assert _parse_hunk_new_start("@@ -43,6 +43,7 @@") == 43

    def test_hunk_with_multi_word_context(self):
        """@@ -115,6 +116,11 @@ app = FastAPI( → new_start = 116"""
        assert _parse_hunk_new_start("@@ -115,6 +116,11 @@ app = FastAPI(") == 116

    def test_hunk_single_line_new(self):
        """@@ -238,7 +244,7 @@ def get_predictor() → new_start = 244"""
        assert _parse_hunk_new_start("@@ -238,7 +244,7 @@ def get_predictor() ->") == 244

    def test_hunk_no_count(self):
        """@@ -1 +1 @@ → new_start = 1 (no comma in new part)"""
        assert _parse_hunk_new_start("@@ -1 +1 @@") == 1

    def test_hunk_new_file(self):
        """@@ -0,0 +1,275 @@ → new_start = 1 (new file)"""
        assert _parse_hunk_new_start("@@ -0,0 +1,275 @@") == 1

    def test_short_hunk_header_line_returns_none(self):
        """Only two parts → cannot parse new_start."""
        assert _parse_hunk_new_start("@@ -9") is None


# ---------------------------------------------------------------------------
# Integration tests — hunk detection with context text
# ---------------------------------------------------------------------------


DIFF_WITH_CONTEXT_TEXT = """\
diff --git a/fake.py b/fake.py
index 1111111..2222222 100644
--- a/fake.py
+++ b/fake.py
@@ -9,7 +9,7 @@ import logging
 import os
 from pathlib import Path

-from fastapi import FastAPI
+from fastapi import Body, FastAPI
 from starlette import status
@@ -43,6 +43,7 @@ def setup_metrics_exporter(port: int = 9090) -> None:
     start_http_server(port)
     logger.info("started")
+
 # comment
@@ -115,6 +116,11 @@ app = FastAPI(
 init_rate_limiter(app)
+# new comment line
+# another new line
+# third new line
+# fourth new line
+# fifth new line
 logger.info("limiter ok")
"""


class TestChangedLineDetection:
    """Verify that changed lines are correctly extracted from unified diffs,
    including hunks with trailing context text on the @@ header line."""

    def test_hunk_with_context_text_detects_changed_lines(self):
        """Hunk headers like ``@@ -9,7 +9,7 @@ import logging`` must be recognised."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = DIFF_WITH_CONTEXT_TEXT.encode("utf-8")

            lines = _collect_changed_lines_for_file("HEAD~1", "fake.py")
            assert len(lines) > 0, "Should find changed lines when hunk has context text"
            # Verify key changed lines are detected:
            # Line 12: +from fastapi import Body, FastAPI (first hunk)
            # Lines 117+: + lines in third hunk
            assert 12 in lines, "First hunk: Body import line must be detected"
            assert 117 in lines, "Third hunk: first new comment line"

    def test_no_changed_lines_when_diff_empty(self):
        """Empty diff → no changed lines."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b""

            lines = _collect_changed_lines_for_file("HEAD~1", "fake.py")
            assert lines == set()

    def test_diff_failure_returns_empty(self):
        """Non-zero git diff exit → empty set."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = b""

            lines = _collect_changed_lines_for_file("HEAD~1", "fake.py")
            assert lines == set()


# ---------------------------------------------------------------------------
# Path normalization tests
# ---------------------------------------------------------------------------


class TestNormalizePath:
    """Unit tests for _normalize_path — Docker path → repo-relative path."""

    def test_docker_app_prefix_stripped(self):
        assert _normalize_path("/app/src/main.py") == "src/main.py"

    def test_docker_app_nested_test_file(self):
        result = _normalize_path("/app/tests/unit/devops/test_static_quality_changed_lines.py")
        assert result == "tests/unit/devops/test_static_quality_changed_lines.py"

    def test_relative_path_unchanged(self):
        assert _normalize_path("src/main.py") == "src/main.py"

    def test_dot_slash_unchanged(self):
        """Preserve ./ prefix — it is not a known container mount."""
        assert _normalize_path("./src/main.py") == "./src/main.py"

    def test_unknown_absolute_path_unchanged(self):
        path = "/home/runner/work/FootballPrediction/FootballPrediction/src/main.py"
        assert _normalize_path(path) == path

    def test_already_relative_test_path_unchanged(self):
        assert _normalize_path("tests/unit/foo.py") == "tests/unit/foo.py"


# ---------------------------------------------------------------------------
# Integration tests — diagnostic classification with Docker paths
# ---------------------------------------------------------------------------


class TestClassifyDiagnosticsPathNormalization:
    """Verify that classify_diagnostics matches Docker-path diagnostics
    against repo-relative changed_lines keys."""

    def test_docker_path_matches_relative_changed_lines(self):
        """Diagnostic /app/src/main.py:12 should match changed_lines['src/main.py']={12}."""
        diags = [
            {
                "filename": "/app/src/main.py",
                "location": {"row": 12, "column": 1},
                "code": "I001",
                "message": "Import block is un-sorted",
            }
        ]
        changed = {"src/main.py": {12}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 1, "Should be new (on changed line)"
        assert len(existing) == 0

    def test_docker_path_on_unchanged_line_is_existing(self):
        """Diagnostic on line NOT in changed_lines → existing."""
        diags = [
            {
                "filename": "/app/src/main.py",
                "location": {"row": 27, "column": 16},
                "code": "F401",
                "message": "unused import",
            }
        ]
        changed = {"src/main.py": {12, 247}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 0
        assert len(existing) == 1

    def test_unknown_path_fallback_new(self):
        """Diagnostic with unmatched path → still treated as new (fail-safe)."""
        diags = [
            {
                "filename": "/unknown/prefix/main.py",
                "location": {"row": 1, "column": 1},
                "code": "F999",
                "message": "test",
            }
        ]
        changed = {"src/main.py": {1}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 1
        assert len(existing) == 0


# ---------------------------------------------------------------------------
# Mypy output parsing tests
# ---------------------------------------------------------------------------

MYPY_OUTPUT = """\
src/main.py:160: error: Function is missing a return type annotation  [no-untyped-def]
src/main.py:247: error: Missing type parameters for generic type "dict"  [type-arg]
src/main.py:293: error: Returning Any from function declared to return "dict"  [no-any-return]
"""

MYPY_OUTPUT_WITH_NOTE = """\
src/main.py:247: error: Argument 1 has incompatible type "int"; expected "str"  [arg-type]
src/main.py:250: note: This is a note about the error above
src/main.py:320: error: Function is missing a return type annotation  [no-untyped-def]
"""

MYPY_OUTPUT_DOCKER_PATHS = """\
/app/src/main.py:247: error: Missing type parameters for generic type "dict"  [type-arg]
/app/src/main.py:160: error: Function is missing a return type annotation  [no-untyped-def]
"""


class TestParseMypyOutput:
    """Unit tests for parse_mypy_output — mypy text → diagnostic dicts."""

    def test_parses_error_lines(self):
        diags = _parse_mypy_output(MYPY_OUTPUT)
        assert len(diags) == 3
        codes = {d["code"] for d in diags}
        assert codes == {"no-untyped-def", "type-arg", "no-any-return"}

    def test_error_lines_have_correct_fields(self):
        diags = _parse_mypy_output(MYPY_OUTPUT)
        line_247 = next(d for d in diags if d["location"]["row"] == 247)
        assert line_247["filename"] == "src/main.py"
        assert line_247["code"] == "type-arg"
        assert "dict" in line_247["message"]

    def test_note_lines_are_skipped(self):
        diags = _parse_mypy_output(MYPY_OUTPUT_WITH_NOTE)
        assert len(diags) == 2  # note on line 250 is excluded
        rows = {d["location"]["row"] for d in diags}
        assert 250 not in rows

    def test_empty_input_returns_empty(self):
        assert _parse_mypy_output("") == []

    def test_unparseable_lines_are_skipped(self):
        diags = _parse_mypy_output("some garbage\nsrc/main.py:1: error: real one  [misc]")
        assert len(diags) == 1

    def test_docker_paths_are_preserved_for_normalization(self):
        """Docker paths are kept raw; _normalize_path handles them later."""
        diags = _parse_mypy_output(MYPY_OUTPUT_DOCKER_PATHS)
        paths = {d["filename"] for d in diags}
        assert "/app/src/main.py" in paths


class TestMypyChangedLineClassification:
    """Integration: mypy diagnostics → classify_diagnostics with Docker paths."""

    def test_error_on_changed_line_is_new(self):
        diags = _parse_mypy_output("src/main.py:247: error: type-arg  [type-arg]")
        changed = {"src/main.py": {247}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 1
        assert len(existing) == 0

    def test_error_on_unchanged_line_is_existing(self):
        diags = _parse_mypy_output("src/main.py:160: error: no-untyped-def  [no-untyped-def]")
        changed = {"src/main.py": {247}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 0
        assert len(existing) == 1

    def test_mixed_new_and_existing(self):
        diags = _parse_mypy_output(MYPY_OUTPUT)
        changed = {"src/main.py": {247}}  # only line 247 changed
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 1  # only line 247
        assert len(existing) == 2  # lines 160, 293

    def test_docker_path_matches_normalized_changed(self):
        diags = _parse_mypy_output(MYPY_OUTPUT_DOCKER_PATHS)
        # changed_lines uses repo-relative paths
        changed = {"src/main.py": {247}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 1  # line 247 matches after normalization
        assert len(existing) == 1  # line 160 is existing

    def test_simulates_1676_scenario(self):
        """20 mypy errors, only changed lines {247,248,249,291,292,293} — 0 NEW."""
        many_errors = "\n".join(
            f"src/main.py:{line}: error: pre-existing issue {i}  [misc]"
            for i, line in enumerate(
                [
                    7,
                    27,
                    28,
                    29,
                    30,
                    31,
                    41,
                    44,
                    55,
                    71,
                    87,
                    89,
                    94,
                    148,
                    150,
                    155,
                    231,
                    234,
                    241,
                    246,
                ]
            )
        )
        diags = _parse_mypy_output(many_errors)
        assert len(diags) == 20
        changed = {"src/main.py": {247, 248, 249, 291, 292, 293}}
        new, existing = _classify_diagnostics(diags, changed)
        assert len(new) == 0, "No mypy errors should be on changed lines"
        assert len(existing) == 20, "All 20 pre-existing errors should be WARN"
