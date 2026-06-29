from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.devops.check_python_ast_utf8 import _is_excluded, validate_file

if TYPE_CHECKING:
    from pathlib import Path


def test_validate_file_accepts_valid_python(tmp_path: Path) -> None:
    target = tmp_path / "valid.py"
    target.write_text("x = 1\n", encoding="utf-8")

    assert validate_file(str(target)) is None


def test_validate_file_reports_invalid_utf8(tmp_path: Path) -> None:
    target = tmp_path / "invalid_utf8.py"
    target.write_bytes(b"\xff\xfe\x00")

    issue = validate_file(str(target))

    assert issue is not None
    assert issue.kind == "UnicodeDecodeError"


def test_validate_file_reports_syntax_error(tmp_path: Path) -> None:
    target = tmp_path / "bad_syntax.py"
    target.write_text("def broken(:\n    pass\n", encoding="utf-8")

    issue = validate_file(str(target))

    assert issue is not None
    assert issue.kind == "SyntaxError"
    assert issue.line == 1


def test_is_excluded_matches_globs() -> None:
    assert _is_excluded(".venv/lib/example.py", [".venv/*"])
    assert _is_excluded("pkg/__pycache__/x.py", ["**/__pycache__/*"])
    assert not _is_excluded("src/example.py", [".venv/*"])
