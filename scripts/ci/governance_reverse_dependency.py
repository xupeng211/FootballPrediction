#!/usr/bin/env python3
"""Governance growth freeze — reverse dependency scanner.

lifecycle: permanent

Detects src → scripts/ops reverse dependencies in Python and JavaScript
source files using AST parsing and bounded call-expression extraction.
"""

from __future__ import annotations

import ast
import re
import subprocess
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
ERR_REVERSE_DEP = "GOV-GROWTH-REVERSE-DEPENDENCY"
_SCRIPTS_OPS_MODULE_RE = re.compile(r"scripts[/.]ops")

# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


class DepFingerprint(NamedTuple):
    """A normalized reverse-dependency fingerprint."""

    path: str
    language: str
    kind: str
    target: str


# ---------------------------------------------------------------------------
# Python AST scanner — decomposed into single-responsibility collectors
# ---------------------------------------------------------------------------

_SUBPROCESS_FUNCTIONS: frozenset[str] = frozenset(
    {"run", "call", "Popen", "check_call", "check_output"}
)


def _target_has_scripts_ops(value: str) -> bool:
    return bool(_SCRIPTS_OPS_MODULE_RE.search(value))


def _extract_strings_from_ast_node(node: ast.expr) -> list[str]:
    strings: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        strings.append(node.value)
    elif isinstance(node, (ast.List, ast.Tuple)):
        strings.extend(s for elt in node.elts for s in _extract_strings_from_ast_node(elt))
    return strings


def _make_py_fingerprint(path: str, kind: str, target: str) -> DepFingerprint:
    return DepFingerprint(path, "python", kind, target)


def _collect_static_imports(node: ast.AST, path: str) -> list[DepFingerprint]:
    """Collect fingerprints from import / from-import statements."""
    results: list[DepFingerprint] = []
    if isinstance(node, ast.Import):
        results.extend(
            _make_py_fingerprint(path, "static-import", alias.name)
            for alias in node.names
            if _target_has_scripts_ops(alias.name)
        )
    elif isinstance(node, ast.ImportFrom) and node.module and _target_has_scripts_ops(node.module):
        results.append(_make_py_fingerprint(path, "static-import", node.module))
    return results


def _is_dynamic_import_call(node: ast.Call) -> bool:
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
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr in _SUBPROCESS_FUNCTIONS
    )


def _collect_dynamic_imports(node: ast.Call, path: str) -> list[DepFingerprint]:
    """Collect fingerprints from importlib.import_module / __import__ calls."""
    if not _is_dynamic_import_call(node) or not node.args:
        return []
    return [
        _make_py_fingerprint(path, "dynamic-import", s)
        for s in _extract_strings_from_ast_node(node.args[0])
        if _target_has_scripts_ops(s)
    ]


def _collect_subprocess_targets(node: ast.Call, path: str) -> list[DepFingerprint]:
    """Collect fingerprints from subprocess.run / call / Popen etc."""
    if not _is_subprocess_call(node):
        return []
    results: list[DepFingerprint] = []
    for arg in node.args:
        results.extend(
            _make_py_fingerprint(path, "subprocess", s)
            for s in _extract_strings_from_ast_node(arg)
            if _target_has_scripts_ops(s)
        )
    for kw in node.keywords:
        results.extend(
            _make_py_fingerprint(path, "subprocess", s)
            for s in _extract_strings_from_ast_node(kw.value)
            if _target_has_scripts_ops(s)
        )
    return results


def _scan_python_file_ast(content: str, path: str) -> list[DepFingerprint]:
    """Scan a Python source file with the `ast` module."""
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError:
        return [_make_py_fingerprint(path, "parse-error", f"SyntaxError: cannot parse {path}")]

    fingerprints: list[DepFingerprint] = []
    for node in ast.walk(tree):
        fingerprints.extend(_collect_static_imports(node, path))
        if isinstance(node, ast.Call):
            fingerprints.extend(_collect_dynamic_imports(node, path))
            fingerprints.extend(_collect_subprocess_targets(node, path))
    return fingerprints


# ---------------------------------------------------------------------------
# JavaScript string/comment state machine — shared helpers
# ---------------------------------------------------------------------------

_JS_STATE_CODE = 0
_JS_STATE_SINGLE = 1
_JS_STATE_DOUBLE = 2
_JS_STATE_BACKTICK = 3
_JS_STATE_LINE_COMMENT = 4
_JS_STATE_BLOCK_COMMENT = 5

_JS_EXEC_FUNCTIONS: tuple[str, ...] = (
    "spawn",
    "spawnSync",
    "exec",
    "execSync",
    "execFile",
    "fork",
)


def _js_transition_string_state(ch: str, state: int, next_ch: str | None) -> tuple[int, bool]:
    """Handle state transitions when inside a string, template, or comment."""
    if state == _JS_STATE_LINE_COMMENT:
        return (_JS_STATE_CODE if ch == "\n" else state, False)

    if state == _JS_STATE_BLOCK_COMMENT:
        return (_JS_STATE_CODE, True) if (ch == "*" and next_ch == "/") else (state, False)

    # String/template literal states — escape skips next char, delimiter exits
    _string_delimiters = {_JS_STATE_SINGLE: "'", _JS_STATE_DOUBLE: '"', _JS_STATE_BACKTICK: "`"}
    delim = _string_delimiters.get(state)
    if delim is not None:
        if ch == "\\":
            return (state, True)
        return (_JS_STATE_CODE if ch == delim else state, False)

    return (state, False)


def _js_transition_code_state(ch: str, next_ch: str | None) -> tuple[int, bool]:
    """Handle state transitions when in normal code (not inside a string)."""
    if ch == "'":
        return (_JS_STATE_SINGLE, False)
    if ch == '"':
        return (_JS_STATE_DOUBLE, False)
    if ch == "`":
        return (_JS_STATE_BACKTICK, False)
    if ch == "/" and next_ch == "/":
        return (_JS_STATE_LINE_COMMENT, True)
    if ch == "/" and next_ch == "*":
        return (_JS_STATE_BLOCK_COMMENT, True)
    return (_JS_STATE_CODE, False)


def _js_char_transition(ch: str, state: int, next_ch: str | None) -> tuple[int, bool]:
    """Single-character state transition for JS string/comment tracking.

    Returns (new_state, skip_next).  Callers advance i by 2 when
    skip_next is True (for escaped chars or two-char comment starts).
    """
    if state != _JS_STATE_CODE:
        return _js_transition_string_state(ch, state, next_ch)
    return _js_transition_code_state(ch, next_ch)


def _is_pos_inside_js_string_or_comment(text: str, end_pos: int) -> bool:
    """Check if *end_pos* is inside a JS string or comment."""
    state = _JS_STATE_CODE
    i = 0
    while i < end_pos:
        ch = text[i]
        next_ch = text[i + 1] if i + 1 < len(text) else None
        state, skip_next = _js_char_transition(ch, state, next_ch)
        if skip_next:
            i += 2
        else:
            i += 1
    return state != _JS_STATE_CODE


def _balanced_paren_range(text: str, start: int) -> int | None:
    """Return index of matching close-paren for '(' at *start*, or None."""
    depth = 0
    state = _JS_STATE_CODE
    i = start
    while i < len(text):
        ch = text[i]
        next_ch = text[i + 1] if i + 1 < len(text) else None
        state, skip_next = _js_char_transition(ch, state, next_ch)
        if skip_next:
            i += 2
            continue
        if state == _JS_STATE_CODE:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


def _extract_call_args(text: str, func_match_end: int) -> str | None:
    """Extract text between balanced parentheses of a function call."""
    pos = func_match_end
    while pos < len(text) and text[pos] in (" ", "\t", "\n"):
        pos += 1
    if pos >= len(text) or text[pos] != "(":
        return None
    close = _balanced_paren_range(text, pos)
    if close is None:
        return None
    return text[pos + 1 : close]


def _extract_js_string_literals(text: str) -> list[str]:
    """Extract all string literal values from JS expression text.

    Handles single-quoted, double-quoted, and constant backtick
    template literals (backtick strings without ``${...}``
    interpolation).  Interpolated template literals are skipped
    because the resolved path cannot be determined statically.
    """
    literals: list[str] = []
    state = _JS_STATE_CODE
    literal_start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        next_ch = text[i + 1] if i + 1 < len(text) else None
        prev_state = state
        state, skip_next = _js_char_transition(ch, state, next_ch)
        if skip_next:
            i += 2
            continue
        if (
            prev_state in (_JS_STATE_SINGLE, _JS_STATE_DOUBLE, _JS_STATE_BACKTICK)
            and state == _JS_STATE_CODE
        ):
            literal = text[literal_start:i]
            # Backtick templates with interpolation cannot be resolved
            # statically — skip them rather than guessing a path.
            if prev_state == _JS_STATE_BACKTICK and "${" in literal:
                pass
            else:
                literals.append(literal)
        if (
            state in (_JS_STATE_SINGLE, _JS_STATE_DOUBLE, _JS_STATE_BACKTICK)
            and prev_state == _JS_STATE_CODE
        ):
            literal_start = i + 1
        i += 1
    return literals


def _normalize_js_target(raw: str) -> str:
    """Normalize a JS dependency target for fingerprint comparison.

    - Backslashes → forward slashes
    - Collapses repeated slashes
    - Strips leading ``./`` (but preserves ``../``)
    """
    normalized = raw.strip().replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    # Strip one or more leading ./ prefixes — ``./scripts/foo`` and
    # ``scripts/foo`` refer to the same file.
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


# ---------------------------------------------------------------------------
# JavaScript dependency collection — decomposed collectors
# ---------------------------------------------------------------------------

_REQUIRE_RE = re.compile(r"""require\s*\(\s*(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1\s*\)""")
_ES_IMPORT_RE = re.compile(r"""import\s+.*?\s+from\s+(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1""")
_DYNAMIC_IMPORT_RE = re.compile(r"""import\s*\(\s*(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1\s*\)""")
_MULTILINE_FROM_RE = re.compile(r"""\bfrom\s+(['"])([^'"]*?scripts[/.]+ops[^'"]*?)\1""")


def _make_js_fingerprint(path: str, kind: str, target: str) -> DepFingerprint:
    return DepFingerprint(path, "javascript", kind, _normalize_js_target(target))


def _collect_single_line_requires(
    content: str,
    path: str,
    line: str,
    line_start: int,
) -> list[DepFingerprint]:
    """Collect require('...scripts/ops...') from a single line."""
    return [
        _make_js_fingerprint(path, "require", m.group(2))
        for m in _REQUIRE_RE.finditer(line)
        if not _is_pos_inside_js_string_or_comment(content, line_start + m.start())
    ]


def _collect_single_line_es_imports(
    content: str,
    path: str,
    line: str,
    line_start: int,
) -> list[DepFingerprint]:
    """Collect import ... from '...scripts/ops...' from a single line."""
    return [
        _make_js_fingerprint(path, "es-import", m.group(2))
        for m in _ES_IMPORT_RE.finditer(line)
        if not _is_pos_inside_js_string_or_comment(content, line_start + m.start())
    ]


def _collect_single_line_dynamic_imports(
    content: str,
    path: str,
    line: str,
    line_start: int,
) -> list[DepFingerprint]:
    """Collect import('...scripts/ops...') from a single line.

    Handles single-quoted, double-quoted, and constant backtick
    template strings.  Interpolated backtick templates (``${...}``)
    are skipped because the resolved path cannot be determined
    statically.
    """
    results: list[DepFingerprint] = []
    results.extend(
        _make_js_fingerprint(path, "dynamic-es-import", m.group(2))
        for m in _DYNAMIC_IMPORT_RE.finditer(line)
        if not _is_pos_inside_js_string_or_comment(content, line_start + m.start())
    )
    # Backtick template: import(`...scripts/ops...`)
    for m in re.finditer(r"""import\s*\(\s*`([^`]*)`\s*\)""", line):
        if _is_pos_inside_js_string_or_comment(content, line_start + m.start()):
            continue
        target = m.group(1)
        if _target_has_scripts_ops(target) and "${" not in target:
            results.append(_make_js_fingerprint(path, "dynamic-es-import", target))
    return results


def _collect_multiline_call_targets(
    content: str,
    path: str,
    line: str,
    line_start: int,
    func_name: str,
) -> list[DepFingerprint]:
    """Detect multi-line require(\n"...") or import(\n"...")."""
    results: list[DepFingerprint] = []
    pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
    for m in pattern.finditer(line):
        abs_pos = line_start + m.start()
        if _is_pos_inside_js_string_or_comment(content, abs_pos):
            continue
        arg_text = _extract_call_args(content, line_start + m.end() - 1)
        if arg_text is None or "\n" not in arg_text:
            continue
        results.extend(
            _make_js_fingerprint(path, func_name, lit)
            for lit in _extract_js_string_literals(arg_text)
            if _target_has_scripts_ops(lit)
        )
    return results


def _collect_multiline_import_from(
    content: str,
    path: str,
    line: str,
    line_start: int,
) -> list[DepFingerprint]:
    """Detect multi-line `import { ... } from '...scripts/ops...'`.

    Scans backwards from the *from* keyword to locate the matching
    *import* keyword.  The scan is bounded by real statement
    boundaries (semicolons in code, function/class declarations) rather
    than an arbitrary line count, so imports spanning more than a
    handful of lines are still detected.
    """
    m = _MULTILINE_FROM_RE.search(line)
    if not m:
        return []
    abs_pos = line_start + m.start()
    if _is_pos_inside_js_string_or_comment(content, abs_pos):
        return []
    line_num = content[:line_start].count("\n")
    lines = content.splitlines()

    # Reverse-scan from the line just before 'from' to find 'import'.
    for i in range(line_num - 1, -1, -1):
        prev = lines[i]
        import_m = re.search(r"\bimport\b", prev)
        if import_m:
            prev_line_start = sum(len(ll) + 1 for ll in lines[:i])
            if not _is_pos_inside_js_string_or_comment(
                content, prev_line_start + import_m.start() + 1
            ):
                return [_make_js_fingerprint(path, "es-import", m.group(2))]
            break
        # Semicolons in code-level context terminate the statement.
        for semi_m in re.finditer(r";", prev):
            prev_line_start = sum(len(ll) + 1 for ll in lines[:i])
            if not _is_pos_inside_js_string_or_comment(
                content, prev_line_start + semi_m.start() + 1
            ):
                return []
        # Don't cross function / class / const / let / var declarations.
        if re.match(
            r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s",
            prev,
        ):
            break

    return []


def _collect_process_call_targets(content: str, path: str) -> list[DepFingerprint]:
    """Collect spawn/exec/fork calls referencing scripts/ops."""
    results: list[DepFingerprint] = []
    for func_name in _JS_EXEC_FUNCTIONS:
        pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
        for m in pattern.finditer(content):
            if _is_pos_inside_js_string_or_comment(content, m.start()):
                continue
            arg_text = _extract_call_args(content, m.end() - 1)
            if arg_text is None:
                continue
            results.extend(
                _make_js_fingerprint(path, func_name, lit)
                for lit in _extract_js_string_literals(arg_text)
                if _target_has_scripts_ops(lit)
            )
    return results


def _scan_js_file_bounded(content: str, path: str) -> list[DepFingerprint]:
    """Scan a JS/TS source file with a bounded scanner."""
    fingerprints: list[DepFingerprint] = []
    lines = content.splitlines()

    line_starts: list[int] = []
    pos = 0
    for line in lines:
        line_starts.append(pos)
        pos += len(line) + 1

    for line_num, line in enumerate(lines, start=1):
        if line.lstrip().startswith("//"):
            continue
        ls = line_starts[line_num - 1]
        fingerprints.extend(_collect_single_line_requires(content, path, line, ls))
        fingerprints.extend(_collect_single_line_es_imports(content, path, line, ls))
        fingerprints.extend(_collect_single_line_dynamic_imports(content, path, line, ls))
        fingerprints.extend(_collect_multiline_call_targets(content, path, line, ls, "require"))
        fingerprints.extend(_collect_multiline_call_targets(content, path, line, ls, "import"))
        fingerprints.extend(_collect_multiline_import_from(content, path, line, ls))

    fingerprints.extend(_collect_process_call_targets(content, path))
    return fingerprints


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_output(repo_root: Path, args: list[str]) -> str:
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
# Fingerprint collection and comparison
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

    Uses fingerprint set difference (head_fps - base_fps) so that
    same-target dependencies moved to a different line, reformatted,
    or extracted from differently-indented call expressions are not
    reported as new. Only genuinely new or changed targets are blocked.
    """
    errors: list[str] = []
    base_deps = _find_src_reverse_dep_fingerprints(repo_root, base_ref)
    head_deps = _find_src_reverse_dep_fingerprints(repo_root, head_ref)

    for file_path in sorted(head_deps):
        head_fps = head_deps.get(file_path, set())
        base_fps = base_deps.get(file_path, set())

        parse_errors = [fp for fp in head_fps if fp.kind == "parse-error"]
        if parse_errors:
            errors.extend(
                f"{ERR_REVERSE_DEP}: {file_path}: AST parse failure — "
                f"cannot scan (fail-closed). {fp.target}"
                for fp in parse_errors
            )
            continue

        new_fps = head_fps - base_fps
        errors.extend(
            f"{ERR_REVERSE_DEP}: {file_path}: "
            f"New {fp.language} {fp.kind} → {fp.target}. "
            f"Growth freeze is active."
            for fp in sorted(new_fps, key=lambda f: (f.kind, f.target))
        )

    return errors
