#!/usr/bin/env python3
"""Validate tracked Python files can be decoded as UTF-8 and parsed as AST.

This script intentionally does not import project modules. It only reads
tracked Python source files as text, validates strict UTF-8 decoding, and
runs ast.parse on each file.

Usage:
    python scripts/devops/check_python_ast_utf8.py
    python scripts/devops/check_python_ast_utf8.py --json
    python scripts/devops/check_python_ast_utf8.py --paths src/ tests/
    python scripts/devops/check_python_ast_utf8.py --exclude-glob "archive_vault_2026/*"
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import fnmatch
import json
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


DEFAULT_EXCLUDE_GLOBS = (
    ".git/*",
    ".venv/*",
    "venv/*",
    "**/__pycache__/*",
    ".mypy_cache/*",
    ".ruff_cache/*",
    ".pytest_cache/*",
    "htmlcov/*",
    "node_modules/*",
    "archive_vault_2026/*",
)


@dataclass(frozen=True)
class ParseIssue:
    """A single Python parse or encoding issue with location info."""

    path: str
    line: int | None
    column: int | None
    kind: str
    message: str


def _run_git_ls_files(paths: list[str]) -> list[str]:
    """Return the list of tracked Python files via git ls-files."""
    cmd = ["git", "ls-files"]
    if paths:
        cmd.extend(["--", *paths])
    else:
        cmd.append("*.py")

    result = subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")

    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [f for f in files if f.endswith(".py")]


def _is_excluded(path: str, exclude_globs: Iterable[str]) -> bool:
    """Return True if *path* matches any of the *exclude_globs* patterns."""
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in exclude_globs)


def validate_file(path: str) -> ParseIssue | None:
    """Validate that *path* decodes as strict UTF-8 and parses as Python AST.

    Returns a ``ParseIssue`` on failure, ``None`` on success.
    """
    file_path = Path(path)

    try:
        text = file_path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return ParseIssue(
            path=path,
            line=None,
            column=(exc.start + 1) if exc.start is not None else None,
            kind="UnicodeDecodeError",
            message=str(exc),
        )
    except OSError as exc:
        return ParseIssue(
            path=path,
            line=None,
            column=None,
            kind=type(exc).__name__,
            message=str(exc),
        )

    try:
        ast.parse(text, filename=path)
    except SyntaxError as exc:
        return ParseIssue(
            path=path,
            line=exc.lineno,
            column=exc.offset,
            kind=type(exc).__name__,
            message=exc.msg,
        )

    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate tracked Python files decode as UTF-8 and parse as AST.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[],
        help="Optional tracked paths or pathspecs to check. Defaults to all tracked *.py.",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Additional glob pattern to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Entry point — run UTF-8 / AST validation and return exit code."""
    args = parse_args(argv)

    try:
        files = _run_git_ls_files(args.paths)
    except Exception as exc:
        print(f"check_python_ast_utf8: tool error: {exc}", file=sys.stderr)
        return 2

    exclude_globs = (*DEFAULT_EXCLUDE_GLOBS, *tuple(args.exclude_glob))
    checked_files = [f for f in files if not _is_excluded(f, exclude_globs)]

    issues: list[ParseIssue] = []
    for path in checked_files:
        issue = validate_file(path)
        if issue is not None:
            issues.append(issue)

    if args.json:
        print(
            json.dumps(
                {
                    "checked_files": len(checked_files),
                    "issues": [asdict(issue) for issue in issues],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
    else:
        print(f"Python UTF-8 / AST validation checked {len(checked_files)} files.")
        if issues:
            print(f"Found {len(issues)} Python parse/encoding issue(s):")
            for issue in issues:
                line = "?" if issue.line is None else issue.line
                column = "?" if issue.column is None else issue.column
                print(
                    f"{issue.path}:{line}:{column}: {issue.kind}: {issue.message}",
                )
        else:
            print("All checked Python files decode as UTF-8 and parse as AST.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
