#!/usr/bin/env python3
"""Governance growth freeze — reverse dependency scanner.

lifecycle: permanent

Detects src → scripts/ops reverse dependencies in Python and JavaScript
source files using AST parsing and bounded call-expression extraction.

Public API:
    check_new_reverse_dependencies(repo_root, base_ref, head_ref) -> list[str]
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Re-export error code for caller convenience
# ---------------------------------------------------------------------------
ERR_REVERSE_DEP = "GOV-GROWTH-REVERSE-DEPENDENCY"

# ---------------------------------------------------------------------------
# Reverse-dependency fingerprint
# ---------------------------------------------------------------------------


class DepFingerprint(NamedTuple):
    """A normalized reverse-dependency fingerprint."""

    path: str
    language: str
    kind: str
    target: str


# ---------------------------------------------------------------------------
# Python AST-based scanner
# ---------------------------------------------------------------------------

_SUBPROCESS_FUNCTIONS: frozenset[str] = frozenset(
    {"run", "call", "Popen", "check_call", "check_output"}
)

_SCRIPTS_OPS_MODULE_RE = re.compile(r"scripts[/.]ops")


def _target_has_scripts_ops(value: str) -> bool:
    """Check whether a string value references scripts/ops or scripts.ops."""
    return bool(_SCRIPTS_OPS_MODULE_RE.search(value))


def _extract_strings_from_ast_node(node: ast.expr) -> list[str]:
    """Extract string constants from an AST expression node (recursively)."""
    strings: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        strings.append(node.value)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            strings.extend(_extract_strings_from_ast_node(elt))
    return strings


def _scan_python_file_ast(
    content: str,
    path: str,
) -> list[DepFingerprint]:
    """Scan a Python source file with the `ast` module."""
    fingerprints: list[DepFingerprint] = []

    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError:
        return [DepFingerprint(path, "python", "parse-error", f"SyntaxError: cannot parse {path}")]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _target_has_scripts_ops(alias.name):
                    fingerprints.append(DepFingerprint(path, "python", "static-import", alias.name))

        elif isinstance(node, ast.ImportFrom):
            if node.module and _target_has_scripts_ops(node.module):
                fingerprints.append(DepFingerprint(path, "python", "static-import", node.module))

        elif isinstance(node, ast.Call):
            if _is_dynamic_import_call(node):
                if node.args:
                    for s in _extract_strings_from_ast_node(node.args[0]):
                        if _target_has_scripts_ops(s):
                            fingerprints.append(DepFingerprint(path, "python", "dynamic-import", s))

            elif _is_subprocess_call(node):
                for arg in node.args:
                    for s in _extract_strings_from_ast_node(arg):
                        if _target_has_scripts_ops(s):
                            fingerprints.append(DepFingerprint(path, "python", "subprocess", s))
                for kw in node.keywords:
                    for s in _extract_strings_from_ast_node(kw.value):
                        if _target_has_scripts_ops(s):
                            fingerprints.append(DepFingerprint(path, "python", "subprocess", s))

    return fingerprints


def _is_dynamic_import_call(node: ast.Call) -> bool:
    """Check if an AST Call node is importlib.import_module() or __import__()."""
    if isinstance(node.func, ast.Attribute):
        return (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
            and node.func.attr == "import_module"
        )
    if isinstance(node.func, ast.Name):
        return node.func.id == "__import__"
    return False


def _is_subprocess_call(node: ast.Call) -> bool:
    """Check if an AST Call node is a subprocess.run/call/Popen/... call."""
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr in _SUBPROCESS_FUNCTIONS
    )


# ---------------------------------------------------------------------------
# JavaScript bounded call-expression scanner
# ---------------------------------------------------------------------------

_JS_EXEC_FUNCTIONS: tuple[str, ...] = (
    "spawn",
    "spawnSync",
    "exec",
    "execSync",
    "execFile",
    "fork",
)


def _balanced_paren_range(
    text: str,
    start: int,
) -> int | None:
    """Return index of matching close-paren for '(' at *start*, or None.

    String- and comment-aware.
    """
    depth = 0
    i = start
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < len(text) and text[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick:
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

        if in_single:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if in_backtick:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_backtick = False
            i += 1
            continue

        if ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch == "`":
            in_backtick = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return None


def _scan_state_until_pos(
    text: str,
    end_pos: int,
) -> bool:
    """Check if position *end_pos* is inside a JS string or comment."""
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0

    while i < end_pos:
        ch = text[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < len(text) and text[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick:
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

        if in_single:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if in_backtick:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_backtick = False
            i += 1
            continue

        if ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch == "`":
            in_backtick = True

        i += 1

    return in_single or in_double or in_backtick or in_line_comment or in_block_comment


def _extract_balanced_call_args(text: str, func_match_end: int) -> str | None:
    """Extract text between the balanced parentheses of a function call."""
    pos = func_match_end
    while pos < len(text) and text[pos] in (" ", "\t", "\n"):
        pos += 1
    if pos >= len(text) or text[pos] != "(":
        return None
    close = _balanced_paren_range(text, pos)
    if close is None:
        return None
    return text[pos + 1 : close]


def _extract_string_literals_from_js(
    text: str,
) -> list[str]:
    """Extract all string literal values from a JS expression text."""
    literals: list[str] = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    literal_start = 0
    i = 0

    while i < len(text):
        ch = text[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < len(text) and text[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick:
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

        if in_single:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                literals.append(text[literal_start:i])
                in_single = False
            i += 1
            continue

        if in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                literals.append(text[literal_start:i])
                in_double = False
            i += 1
            continue

        if in_backtick:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_backtick = False
            i += 1
            continue

        if ch == "'":
            in_single = True
            literal_start = i + 1
        elif ch == '"':
            in_double = True
            literal_start = i + 1
        elif ch == "`":
            in_backtick = True

        i += 1

    return literals


def _normalize_js_target(raw: str) -> str:
    """Normalize a JS dependency target for fingerprint comparison."""
    normalized = raw.strip().replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _scan_js_file_bounded(content: str, path: str) -> list[DepFingerprint]:
    """Scan a JS/TS source file with a bounded scanner.

    Handles single-line and multi-line require(), import...from,
    import(), and spawn/exec/fork calls.
    """
    fingerprints: list[DepFingerprint] = []
    lines = content.splitlines()

    line_starts: list[int] = []
    pos = 0
    for line in lines:
        line_starts.append(pos)
        pos += len(line) + 1

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        line_start = line_starts[line_num - 1]
        _scan_require_patterns(content, path, line, line_start, fingerprints)
        _scan_es_import_patterns(content, path, line, line_start, fingerprints)
        _scan_dynamic_import_patterns(content, path, line, line_start, fingerprints)

    for func_name in _JS_EXEC_FUNCTIONS:
        pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
        for m in pattern.finditer(content):
            if _scan_state_until_pos(content, m.start()):
                continue
            arg_text = _extract_balanced_call_args(content, m.end() - 1)
            if arg_text is None:
                continue
            for lit in _extract_string_literals_from_js(arg_text):
                if _target_has_scripts_ops(lit):
                    fingerprints.append(
                        DepFingerprint(
                            path,
                            "javascript",
                            func_name,
                            _normalize_js_target(lit),
                        )
                    )

    return fingerprints


def _scan_require_patterns(
    content: str,
    path: str,
    line: str,
    line_start: int,
    fingerprints: list[DepFingerprint],
) -> None:
    """Scan for require("...scripts/ops...") — single and multi-line."""
    for m in re.finditer(
        r"""require\s*\(\s*(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1\s*\)""",
        line,
    ):
        abs_pos = line_start + m.start()
        if not _scan_state_until_pos(content, abs_pos):
            fingerprints.append(
                DepFingerprint(
                    path,
                    "javascript",
                    "require",
                    _normalize_js_target(m.group(2)),
                )
            )

    _scan_multiline_call(content, path, line, line_start, "require", fingerprints)


def _scan_es_import_patterns(
    content: str,
    path: str,
    line: str,
    line_start: int,
    fingerprints: list[DepFingerprint],
) -> None:
    """Scan for import ... from "...scripts/ops..." — single and multi-line."""
    for m in re.finditer(
        r"""import\s+.*?\s+from\s+(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1""",
        line,
    ):
        abs_pos = line_start + m.start()
        if not _scan_state_until_pos(content, abs_pos):
            fingerprints.append(
                DepFingerprint(
                    path,
                    "javascript",
                    "es-import",
                    _normalize_js_target(m.group(2)),
                )
            )

    _scan_multiline_import_from(content, path, line, line_start, fingerprints)


def _scan_dynamic_import_patterns(
    content: str,
    path: str,
    line: str,
    line_start: int,
    fingerprints: list[DepFingerprint],
) -> None:
    """Scan for import("...scripts/ops...") — single and multi-line."""
    for m in re.finditer(
        r"""import\s*\(\s*(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1\s*\)""",
        line,
    ):
        abs_pos = line_start + m.start()
        if not _scan_state_until_pos(content, abs_pos):
            fingerprints.append(
                DepFingerprint(
                    path,
                    "javascript",
                    "dynamic-es-import",
                    _normalize_js_target(m.group(2)),
                )
            )

    _scan_multiline_call(content, path, line, line_start, "import", fingerprints)


def _scan_multiline_call(
    content: str,
    path: str,
    line: str,
    line_start: int,
    func_name: str,
    fingerprints: list[DepFingerprint],
) -> None:
    """Detect multi-line calls like require(\\n"...") or import(\\n"...")."""
    pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
    m = pattern.search(line)
    if not m:
        return

    abs_pos = line_start + m.start()
    if _scan_state_until_pos(content, abs_pos):
        return

    arg_text = _extract_balanced_call_args(content, m.end() - 1)
    if arg_text is None:
        return

    if "\n" not in arg_text:
        return

    for lit in _extract_string_literals_from_js(arg_text):
        if _target_has_scripts_ops(lit):
            fingerprints.append(
                DepFingerprint(
                    path,
                    "javascript",
                    func_name,
                    _normalize_js_target(lit),
                )
            )


def _scan_multiline_import_from(
    content: str,
    path: str,
    line: str,
    line_start: int,
    fingerprints: list[DepFingerprint],
) -> None:
    """Detect multi-line `import { ... } from "...scripts/ops..."`."""
    m = re.search(r"""\bfrom\s+(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1""", line)
    if not m:
        return

    abs_pos = line_start + m.start()
    if _scan_state_until_pos(content, abs_pos):
        return

    line_num = content[:line_start].count("\n")
    lookback_start = max(0, line_num - 5)
    lookback_lines = content.splitlines()[lookback_start:line_num]
    lookback_text = "\n".join(lookback_lines)
    if not re.search(r"\bimport\b", lookback_text):
        return

    fingerprints.append(
        DepFingerprint(
            path,
            "javascript",
            "es-import",
            _normalize_js_target(m.group(2)),
        )
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_output(repo_root: Path, args: list[str]) -> str:
    """Run a git command in *repo_root*, return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _read_file_at_revision(repo_root: Path, revision: str, path: str) -> str | None:
    """Read a file's content from a specific git revision."""
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


# ---------------------------------------------------------------------------
# Fingerprint-based dependency collection and comparison
# ---------------------------------------------------------------------------


def _find_src_reverse_dep_fingerprints(
    repo_root: Path,
    revision: str,
) -> dict[str, set[DepFingerprint]]:
    """Find all src → scripts/ops dependency fingerprints in a revision."""
    deps: dict[str, set[DepFingerprint]] = {}

    src_files = _git_output(
        repo_root,
        ["ls-tree", "-r", "--name-only", revision, "src/"],
    ).splitlines()

    for raw_path in src_files:
        file_path = raw_path.strip()
        if not file_path:
            continue
        content = _read_file_at_revision(repo_root, revision, file_path)
        if content is None:
            continue

        if file_path.endswith(".py"):
            fps = _scan_python_file_ast(content, file_path)
        elif file_path.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")):
            fps = _scan_js_file_bounded(content, file_path)
        else:
            continue

        if fps:
            deps[file_path] = set(fps)

    return deps


def check_new_reverse_dependencies(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block NEW src → scripts/ops reverse dependencies.

    Uses fingerprint set difference: head_fingerprints - base_fingerprints.
    """
    errors: list[str] = []

    base_deps = _find_src_reverse_dep_fingerprints(repo_root, base_ref)
    head_deps = _find_src_reverse_dep_fingerprints(repo_root, head_ref)

    all_head_paths = set(head_deps.keys())

    for file_path in sorted(all_head_paths):
        head_fps = head_deps.get(file_path, set())
        base_fps = base_deps.get(file_path, set())

        for fp in head_fps:
            if fp.kind == "parse-error":
                errors.append(
                    f"{ERR_REVERSE_DEP}: {file_path}: "
                    f"AST parse failure — cannot scan (fail-closed). {fp.target}"
                )
                break
        else:
            new_fps = head_fps - base_fps
            for fp in sorted(new_fps, key=lambda f: (f.kind, f.target)):
                errors.append(
                    f"{ERR_REVERSE_DEP}: {file_path}: "
                    f"New {fp.language} {fp.kind} → {fp.target}. "
                    f"Growth freeze is active."
                )

    return errors
