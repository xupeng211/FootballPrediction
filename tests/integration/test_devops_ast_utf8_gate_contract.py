# ruff: noqa: PLR2004 (magic values in test assertions are intentional)

"""Integration tests for the UTF-8 / AST parse validation gate.

Validates the core validate_file() function from scripts/devops/check_python_ast_utf8.py
against real files written to temporary directories.

The function under test is a pure function — it reads a file, validates strict UTF-8
decoding, and runs ast.parse. We do NOT call _run_git_ls_files or the main() entry
point in order to keep these tests fully self-contained.

No DB, Docker, network, or secrets are required. Uses tmp_path for file isolation.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from scripts.devops.check_python_ast_utf8 import ParseIssue, validate_file


def _write_python_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write *content* to *name* inside *tmp_path* and return the full path."""
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestValidateFileValid:
    """validate_file returns None for valid Python files."""

    def test_simple_valid_file(self, tmp_path: Path):
        """A minimal valid Python file passes validation."""
        path = _write_python_file(tmp_path, "valid.py", "x = 1\n")
        assert validate_file(str(path)) is None

    def test_file_with_unicode_literals(self, tmp_path: Path):
        """A file containing unicode string literals passes."""
        path = _write_python_file(
            tmp_path,
            "unicode_literals.py",
            '# -*- coding: utf-8 -*-\nmsg = "café 北京 モスクワ"\n',
        )
        assert validate_file(str(path)) is None

    def test_multi_line_function(self, tmp_path: Path):
        """A multi-line function definition passes."""
        path = _write_python_file(
            tmp_path,
            "function.py",
            "def greet(name: str) -> str:\n    return f'Hello, {name}'\n",
        )
        assert validate_file(str(path)) is None

    def test_class_with_method(self, tmp_path: Path):
        """A class definition passes."""
        path = _write_python_file(
            tmp_path,
            "class_def.py",
            "class Foo:\n    def bar(self) -> int:\n        return 42\n",
        )
        assert validate_file(str(path)) is None


class TestValidateFileInvalid:
    """validate_file returns a ParseIssue for broken files."""

    def test_syntax_error(self, tmp_path: Path):
        """A file with a Python syntax error returns a SyntaxError ParseIssue."""
        path = _write_python_file(tmp_path, "broken.py", "def broken(\n")
        issue = validate_file(str(path))
        assert issue is not None
        assert issue.kind == "SyntaxError"
        assert issue.path == str(path)

    def test_non_utf8_file(self, tmp_path: Path):
        """A file with non-UTF-8 bytes returns a UnicodeDecodeError ParseIssue."""
        path = tmp_path / "latin1.py"
        # Write raw bytes that are valid Latin-1 but invalid UTF-8
        path.write_bytes(b"# coding: latin1\nx = '\xff\xfe'\n")
        issue = validate_file(str(path))
        assert issue is not None
        assert issue.kind == "UnicodeDecodeError"

    def test_empty_file(self, tmp_path: Path):
        """An empty file is syntactically valid Python."""
        path = _write_python_file(tmp_path, "empty.py", "")
        assert validate_file(str(path)) is None

    def test_missing_file(self, tmp_path: Path):
        """A non-existent path returns an OSError-related ParseIssue."""
        issue = validate_file(str(tmp_path / "does_not_exist.py"))
        assert issue is not None
        assert "Error" in issue.kind or issue.kind == "FileNotFoundError"


class TestParseIssueDataclass:
    """ParseIssue is a frozen dataclass with structured error information."""

    def test_parse_issue_fields(self):
        """ParseIssue stores path, line, column, kind, and message."""
        issue = ParseIssue(
            path="tests/fake.py",
            line=10,
            column=5,
            kind="SyntaxError",
            message="invalid syntax",
        )
        assert issue.path == "tests/fake.py"
        assert issue.line == 10
        assert issue.column == 5
        assert issue.kind == "SyntaxError"
        assert "invalid" in issue.message

    def test_parse_issue_is_immutable(self):
        """ParseIssue is frozen and cannot be mutated."""
        issue = ParseIssue(path="a.py", line=1, column=1, kind="X", message="m")
        with pytest.raises(FrozenInstanceError):
            issue.path = "b.py"  # type: ignore[misc]
