#!/usr/bin/env python3
"""Governance growth freeze gate — prevent unauthorized growth of governance artifacts.

lifecycle: permanent

This module implements M2 PR1 growth-freeze checks. It compares base vs head
revisions and blocks only NEW violations — historical debt in base is allowed.

Three categories are blocked:
  1. New reports/manifests under docs/_reports/ or docs/_manifests/
  2. New numbered governance scripts (Phase/ADG patterns)
  3. New src → scripts/ops reverse dependencies

Usage:
  from scripts.ci.governance_growth_gate import run_governance_growth_gate
  errors = run_governance_growth_gate(repo_root, base_ref, head_ref)
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Authorized exceptions — must remain empty in M2 PR1.
# Future exceptions require a gate code change with explicit path-level entries.
# Glob patterns, directory wildcards, and "*" are NOT supported.
# ---------------------------------------------------------------------------
AUTHORIZED_GOVERNANCE_ADDITIONS: frozenset[str] = frozenset()

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------
ERR_REPORT = "GOV-GROWTH-REPORT"
ERR_MANIFEST = "GOV-GROWTH-MANIFEST"
ERR_PHASE = "GOV-GROWTH-PHASE"
ERR_REVERSE_DEP = "GOV-GROWTH-REVERSE-DEPENDENCY"

# ---------------------------------------------------------------------------
# Path prefixes for report/manifest detection
# ---------------------------------------------------------------------------
REPORT_PREFIX = "docs/_reports/"
MANIFEST_PREFIX = "docs/_manifests/"

# ---------------------------------------------------------------------------
# Numbered governance script matcher
#
# Matches basenames that contain "phase" or "adg" followed by optional
# separator (underscore or dash) and at least one digit, but ONLY when:
#   - the governance keyword is at the start of the basename, OR
#   - the governance keyword is preceded by a clear separator (_, -, .)
#
# This boundary requirement avoids false matches on:
#   - biophase9_data.csv   (phase9 preceded by "o", not a separator)
#   - metadg10_result.py   (adg10 preceded by "t")
#   - prephase2_transform.js (phase2 preceded by "e")
#   - photographer.py      (no digit adjacent)
#
# Case-insensitive. Uses search() for substring matching with boundary.
# ---------------------------------------------------------------------------
_GOVERNANCE_SCRIPT_RE = re.compile(
    r"(?:^|[_.-])(phase|adg)[-_]?\d",
    re.IGNORECASE,
)


def _is_numbered_governance_basename(basename: str) -> bool:
    """Return True if *basename* matches the numbered governance pattern."""
    return bool(_GOVERNANCE_SCRIPT_RE.search(basename))


# ---------------------------------------------------------------------------
# Reverse-dependency fingerprint
#
# Each fingerprint captures a specific dependency from a src/ file to a
# scripts/ops target.  Line numbers are excluded so that moving a dependency
# within the same file does not count as "new".
# ---------------------------------------------------------------------------


class DepFingerprint(NamedTuple):
    """A normalized reverse-dependency fingerprint."""

    path: str
    language: str  # "python" | "javascript"
    kind: str  # "static-import" | "static-import-from" | "dynamic-import"
    # | "subprocess" | "require" | "es-import"
    # | "dynamic-es-import" | "spawn"
    target: str  # normalized target (module path or script path)


# ---------------------------------------------------------------------------
# Python AST-based scanner
#
# Uses the standard-library `ast` module instead of regex.  This eliminates
# false positives from comments, docstrings, and plain strings that happen
# to mention scripts/ops.
# ---------------------------------------------------------------------------

_SUBPROCESS_FUNCTIONS: frozenset[str] = frozenset(
    {
        "run",
        "call",
        "Popen",
        "check_call",
        "check_output",
    },
)


def _extract_strings_from_ast_node(node: ast.expr) -> list[str]:
    """Extract string constants from an AST expression node (recursively)."""
    strings: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        strings.append(node.value)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            strings.extend(_extract_strings_from_ast_node(elt))
    return strings


def _target_has_scripts_ops(value: str) -> bool:
    """Check whether a string value references scripts/ops or scripts.ops."""
    return "scripts/ops" in value or "scripts.ops" in value


def _scan_python_file_ast(content: str, path: str) -> list[DepFingerprint]:
    """Scan a Python source file with the `ast` module.

    Detects:
      - Static imports:  ``import scripts.ops.foo``
                          ``from scripts.ops.foo import bar``
      - Dynamic imports: ``importlib.import_module("scripts.ops.foo")``
                          ``__import__("scripts.ops.foo")``
      - Subprocess calls: ``subprocess.run(["python", "scripts/ops/x.py"])``
                           (only when the argument is a string constant that
                            references scripts/ops or scripts.ops)

    Returns a list of DepFingerprint records (or a single sentinel on parse
    failure for src/ files to fail-closed).
    """
    fingerprints: list[DepFingerprint] = []

    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError:
        # Fail closed for src/ files — return a sentinel so callers can
        # produce a clear error rather than silently skipping the file.
        return [DepFingerprint(path, "python", "parse-error", f"SyntaxError: cannot parse {path}")]

    for node in ast.walk(tree):
        # --- static imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _target_has_scripts_ops(alias.name):
                    fingerprints.append(
                        DepFingerprint(
                            path,
                            "python",
                            "static-import",
                            alias.name,
                        ),
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module and _target_has_scripts_ops(node.module):
                fingerprints.append(
                    DepFingerprint(
                        path,
                        "python",
                        "static-import-from",
                        node.module,
                    ),
                )

        # --- dynamic imports ---
        elif isinstance(node, ast.Call):
            # importlib.import_module("scripts.ops.foo")
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
            ) or (isinstance(node.func, ast.Name) and node.func.id == "__import__"):
                if node.args:
                    strings = _extract_strings_from_ast_node(node.args[0])
                    for s in strings:
                        if _target_has_scripts_ops(s):
                            fingerprints.append(
                                DepFingerprint(
                                    path,
                                    "python",
                                    "dynamic-import",
                                    s,
                                ),
                            )

            # subprocess.run / call / Popen / check_call / check_output
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr in _SUBPROCESS_FUNCTIONS
            ):
                for arg in node.args:
                    strings = _extract_strings_from_ast_node(arg)
                    for s in strings:
                        if _target_has_scripts_ops(s):
                            fingerprints.append(
                                DepFingerprint(
                                    path,
                                    "python",
                                    "subprocess",
                                    s[:200],
                                ),
                            )
                # Also check keyword args like cwd, executable
                for kw in node.keywords:
                    strings = _extract_strings_from_ast_node(kw.value)
                    for s in strings:
                        if _target_has_scripts_ops(s):
                            fingerprints.append(
                                DepFingerprint(
                                    path,
                                    "python",
                                    "subprocess",
                                    s[:200],
                                ),
                            )

    return fingerprints


# ---------------------------------------------------------------------------
# JavaScript bounded call-expression scanner
#
# Replaces the previous re.DOTALL approach that could cross function
# boundaries.  For each occurrence of a tracked function name the scanner
# extracts *only* the immediate call's argument list using balanced-
# parenthesis matching (string- and comment-aware), then checks whether
# those arguments contain scripts/ops references.
# ---------------------------------------------------------------------------

# Function names that indicate a runtime dependency on an external script.
_JS_EXEC_FUNCTIONS: tuple[str, ...] = (
    "spawn",
    "spawnSync",
    "exec",
    "execSync",
    "execFile",
    "fork",
)


def _balanced_paren_range(text: str, start: int) -> int | None:
    """Return the index of the matching close-paren for the '(' at `start`,
    or None if unbalanced.  String- and comment-aware.
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

        # Detect comment starts (before string handling)
        if not in_single and not in_double and not in_backtick and ch == "/" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if nxt == "*":
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

        # Not in any string or comment
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


def _extract_call_arg_text(text: str, func_match_end: int) -> str | None:
    """Given the position just after a function name, find the opening paren
    and return the text between the outer parentheses (balanced).
    """
    # Find the opening '(' (skip whitespace)
    pos = func_match_end
    while pos < len(text) and text[pos] in (" ", "\t", "\n"):
        pos += 1
    if pos >= len(text) or text[pos] != "(":
        return None

    close = _balanced_paren_range(text, pos)
    if close is None:
        return None
    return text[pos + 1 : close]


def _js_arg_contains_scripts_ops(arg_text: str) -> bool:
    """Check whether the argument text of a JS call contains scripts/ops
    references in actual string literals (not in comments or bare words).
    """
    # Quick pre-check
    if "scripts/ops" not in arg_text and "scripts.ops" not in arg_text:
        return False

    # Simple string-literal-aware check: find string literals and see if
    # they contain scripts/ops.
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0

    while i < len(arg_text):
        ch = arg_text[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < len(arg_text) and arg_text[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick and ch == "/" and i + 1 < len(arg_text):
            nxt = arg_text[i + 1]
            if nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if nxt == "*":
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

        # Start of a string literal — scan forward for scripts/ops
        if ch in ("'", '"', "`"):
            quote = ch
            literal_start = i + 1
            j = i + 1
            while j < len(arg_text):
                if arg_text[j] == "\\":
                    j += 2
                    continue
                if arg_text[j] == quote:
                    break
                j += 1
            literal = arg_text[literal_start:j]
            if "scripts/ops" in literal or "scripts.ops" in literal:
                return True
            i = j + 1 if j < len(arg_text) else j
            continue

        i += 1

    return False


def _is_pos_inside_js_string_or_comment(content: str, pos: int) -> bool:
    """Check whether *pos* is inside a JS string literal or comment."""
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0

    while i < pos:
        ch = content[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < pos + 2 and i + 1 < len(content) and content[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick and ch == "/" and i + 1 < len(content):
            nxt = content[i + 1]
            if nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if nxt == "*":
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

        # Not in any string or comment — check for string/comment start
        if ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch == "`":
            in_backtick = True

        i += 1

    return in_single or in_double or in_backtick or in_line_comment or in_block_comment


def _scan_js_file_bounded(content: str, path: str) -> list[DepFingerprint]:
    """Scan a JavaScript/TypeScript source file with a bounded scanner.

    For require/import: checks each line individually.
    For spawn/exec/fork: extracts only the immediate call arguments
    using balanced-paren matching (no cross-function DOTALL).

    All patterns are string- and comment-aware: matches inside string
    literals or comments are ignored.

    Returns a list of DepFingerprint records.
    """
    fingerprints: list[DepFingerprint] = []
    lines = content.splitlines()

    # --- Line-based patterns: require, import, import() ---
    # Compute line start positions for position-based string check
    line_starts: list[int] = []
    pos = 0
    for line in lines:
        line_starts.append(pos)
        pos += len(line) + 1  # +1 for newline

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comment-only lines
        if stripped.startswith(("//", "/*")):
            continue

        line_start = line_starts[line_num - 1]

        # require("...scripts/ops...")
        for m in re.finditer(
            r"""require\s*\(\s*(['"])(.*?scripts[/.]+ops.*?)\1\s*\)""",
            line,
        ):
            abs_pos = line_start + m.start()
            if not _is_pos_inside_js_string_or_comment(content, abs_pos):
                fingerprints.append(
                    DepFingerprint(
                        path,
                        "javascript",
                        "require",
                        m.group(2)[:200],
                    ),
                )

        # import ... from "...scripts/ops..."
        for m in re.finditer(
            r"""import\s+.*?\s+from\s+(['"])(.*?scripts[/.]+ops.*?)\1""",
            line,
        ):
            abs_pos = line_start + m.start()
            if not _is_pos_inside_js_string_or_comment(content, abs_pos):
                fingerprints.append(
                    DepFingerprint(
                        path,
                        "javascript",
                        "es-import",
                        m.group(2)[:200],
                    ),
                )

        # import("...scripts/ops...")
        for m in re.finditer(
            r"""import\s*\(\s*(['"])(.*?scripts[/.]+ops.*?)\1\s*\)""",
            line,
        ):
            abs_pos = line_start + m.start()
            if not _is_pos_inside_js_string_or_comment(content, abs_pos):
                fingerprints.append(
                    DepFingerprint(
                        path,
                        "javascript",
                        "dynamic-es-import",
                        m.group(2)[:200],
                    ),
                )

    # --- Bounded call-expression scanning for spawn/exec/fork ---
    for func_name in _JS_EXEC_FUNCTIONS:
        pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
        for m in pattern.finditer(content):
            # Skip if the function name is inside a string/comment
            if _is_pos_inside_js_string_or_comment(content, m.start()):
                continue
            func_end = m.end() - 1  # position of '('
            arg_text = _extract_call_arg_text(content, func_end)
            if arg_text is None:
                continue
            if _js_arg_contains_scripts_ops(arg_text):
                fingerprints.append(
                    DepFingerprint(
                        path,
                        "javascript",
                        func_name,
                        arg_text.strip()[:200],
                    ),
                )

    return fingerprints


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


def _git_diff_name_status(repo_root: Path, base_ref: str, head_ref: str) -> list[tuple[str, str, str | None]]:
    """Return list of (status, path, old_path|None) from git diff --name-status.

    Uses -M to detect renames.  Git reports rename similarity as R100, R095,
    etc. — not a bare "R".  We use startswith("R") to handle all variants.
    """
    output = _git_output(repo_root, ["diff", "--name-status", "-M", f"{base_ref}...{head_ref}"])
    entries: list[tuple[str, str, str | None]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        # R100 / R095 / R087 etc. — use startswith for robustness
        if status.startswith("R") and len(parts) >= 3:
            entries.append((status, parts[2], parts[1]))
        elif len(parts) >= 2:
            entries.append((status, parts[1], None))
    return entries


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
    if result.returncode != 0:
        return None
    return result.stdout


def _list_files_at_revision(repo_root: Path, revision: str, prefix: str) -> set[str]:
    """List all files under *prefix* in a given revision."""
    output = _git_output(
        repo_root,
        ["ls-tree", "-r", "--name-only", revision, prefix],
    )
    return {line for line in output.splitlines() if line}


# ---------------------------------------------------------------------------
# Check 1: New reports and manifests
# ---------------------------------------------------------------------------


def check_new_reports_and_manifests(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block new or renamed files under docs/_reports/ and docs/_manifests/.

    Compares base vs head. Only blocks additions (A) and rename destinations.
    Modifications (M) and deletions (D) are allowed.
    """
    errors: list[str] = []

    base_files = _list_files_at_revision(repo_root, base_ref, REPORT_PREFIX)
    head_files = _list_files_at_revision(repo_root, head_ref, REPORT_PREFIX)

    new_reports = sorted(head_files - base_files)
    for p in new_reports:
        if p in AUTHORIZED_GOVERNANCE_ADDITIONS:
            continue
        errors.append(
            f"{ERR_REPORT}: Unauthorized new report under docs/_reports: "
            f"{p}. Growth freeze is active — no new reports allowed "
            f"without explicit gate authorization.",
        )

    base_manifest_files = _list_files_at_revision(repo_root, base_ref, MANIFEST_PREFIX)
    head_manifest_files = _list_files_at_revision(repo_root, head_ref, MANIFEST_PREFIX)

    new_manifests = sorted(head_manifest_files - base_manifest_files)
    for p in new_manifests:
        if p in AUTHORIZED_GOVERNANCE_ADDITIONS:
            continue
        errors.append(
            f"{ERR_MANIFEST}: Unauthorized new manifest under docs/_manifests: "
            f"{p}. Growth freeze is active — no new manifests allowed "
            f"without explicit gate authorization.",
        )

    return errors


# ---------------------------------------------------------------------------
# Check 2: New numbered governance scripts
# ---------------------------------------------------------------------------


def check_new_numbered_governance_scripts(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block new scripts with Phase/ADG numbered governance naming patterns.

    Only checks files under scripts/. Uses git diff --name-status to find
    new files (status A) and rename destinations (status R*, i.e. R100, R095).
    """
    errors: list[str] = []
    entries = _git_diff_name_status(repo_root, base_ref, head_ref)

    for status, path, _old_path in entries:
        # Only block additions and rename destinations (R100, R095, etc.)
        if status != "A" and not status.startswith("R"):
            continue
        if not path.startswith("scripts/"):
            continue
        basename = Path(path).name
        if _is_numbered_governance_basename(basename):
            if path in AUTHORIZED_GOVERNANCE_ADDITIONS:
                continue
            errors.append(
                f"{ERR_PHASE}: Unauthorized new numbered governance script: "
                f"{path}. Governance script number growth is frozen — "
                f"no new Phase/ADG-numbered scripts without explicit "
                f"gate authorization.",
            )

    return errors


# ---------------------------------------------------------------------------
# Check 3: New src → scripts/ops reverse dependencies (fingerprint-based)
#
# Each dependency is represented as a DepFingerprint(path, language, kind,
# target).  Fingerprints exclude line numbers so that moving a dependency
# within a file is not treated as a new dependency.
#
# Comparison: head_fingerprints - base_fingerprints → new dependencies.
# ---------------------------------------------------------------------------


def _find_src_reverse_dep_fingerprints(
    repo_root: Path,
    revision: str,
) -> dict[str, set[DepFingerprint]]:
    """Find all src → scripts/ops dependency fingerprints in a revision.

    Returns {path: set of DepFingerprint}.
    """
    deps: dict[str, set[DepFingerprint]] = {}

    src_files = _git_output(
        repo_root,
        ["ls-tree", "-r", "--name-only", revision, "src/"],
    ).splitlines()

    for path in src_files:
        path = path.strip()
        if not path:
            continue
        content = _read_file_at_revision(repo_root, revision, path)
        if content is None:
            continue

        if path.endswith(".py"):
            fps = _scan_python_file_ast(content, path)
        elif path.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")):
            fps = _scan_js_file_bounded(content, path)
        else:
            continue

        if fps:
            deps[path] = set(fps)

    return deps


def check_new_reverse_dependencies(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block NEW src → scripts/ops reverse dependencies.

    Uses fingerprint set difference: head_fingerprints - base_fingerprints.
    A dependency moved within the same file (different line, same target)
    is NOT reported as new.
    """
    errors: list[str] = []

    base_deps = _find_src_reverse_dep_fingerprints(repo_root, base_ref)
    head_deps = _find_src_reverse_dep_fingerprints(repo_root, head_ref)

    all_head_paths = set(head_deps.keys())

    for path in sorted(all_head_paths):
        head_fps = head_deps.get(path, set())
        base_fps = base_deps.get(path, set())

        # Check for parse-error sentinels first
        for fp in head_fps:
            if fp.kind == "parse-error":
                errors.append(
                    f"{ERR_REVERSE_DEP}: {path}: "
                    f"AST parse failure — cannot scan for reverse deps "
                    f"(fail-closed). {fp.target}",
                )
                # Don't report individual deps on top of parse failure
                break
        else:
            # No parse error — compute fingerprint set difference
            new_fps = head_fps - base_fps
            for fp in sorted(new_fps, key=lambda f: (f.kind, f.target)):
                errors.append(
                    f"{ERR_REVERSE_DEP}: {path}: "
                    f"New {fp.language} {fp.kind} → {fp.target}. "
                    f"Growth freeze is active — no new src → scripts/ops "
                    f"reverse dependencies allowed.",
                )

    return errors


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_governance_growth_gate(
    repo_root: str | Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Run all governance growth freeze checks.

    Args:
        repo_root: Path to the git repository root.
        base_ref: Base git ref (e.g. origin/main or commit SHA).
        head_ref: Head git ref (e.g. HEAD or PR head commit SHA).

    Returns:
        Sorted list of error strings. Empty list means all checks passed.
    """
    root = Path(repo_root)
    errors: list[str] = []

    # 1. New reports and manifests
    try:
        errors.extend(check_new_reports_and_manifests(root, base_ref, head_ref))
    except RuntimeError as exc:
        errors.append(f"{ERR_REPORT}: Governance growth gate failed to check reports/manifests: {exc}")

    # 2. New numbered governance scripts
    try:
        errors.extend(check_new_numbered_governance_scripts(root, base_ref, head_ref))
    except RuntimeError as exc:
        errors.append(f"{ERR_PHASE}: Governance growth gate failed to check governance scripts: {exc}")

    # 3. New src → scripts/ops reverse dependencies (fingerprint-based)
    try:
        errors.extend(check_new_reverse_dependencies(root, base_ref, head_ref))
    except RuntimeError as exc:
        errors.append(f"{ERR_REVERSE_DEP}: Governance growth gate failed to check reverse deps: {exc}")

    # Stable sort
    errors.sort()
    return errors
