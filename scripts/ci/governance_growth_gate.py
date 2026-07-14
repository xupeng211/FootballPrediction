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

import re
import subprocess
from pathlib import Path

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
# Matches basenames containing "phase" or "adg" followed by optional
# separator (underscore or dash) and at least one digit.
# Case-insensitive. Designed to NOT match:
#   - plain "phase" or "adg" without digits
#   - words containing "phase" without adjacent digits (e.g. "phase_transition")
#   - business data files with version numbers
# ---------------------------------------------------------------------------
_GOVERNANCE_SCRIPT_RE = re.compile(
    r"(?:phase|adg)[-_]?\d",
    re.IGNORECASE,
)


def _is_numbered_governance_basename(basename: str) -> bool:
    """Return True if *basename* matches the numbered governance pattern."""
    return bool(_GOVERNANCE_SCRIPT_RE.search(basename))


# ---------------------------------------------------------------------------
# src → scripts/ops reverse dependency patterns
#
# These patterns detect runtime imports/requires/calls from src/ files
# that reference scripts/ops paths. They are designed to match real
# code dependencies, NOT comments, docstrings, logger messages, or
# test fixtures.
#
# Each pattern uses a negative lookbehind for common comment/doc/log
# markers to reduce false positives. The caller additionally filters
# out lines that are clearly in comments or string literals.
# ---------------------------------------------------------------------------

# Python import patterns
_PYTHON_IMPORT_RE = re.compile(
    r"""^[^#]*\b(?:from\s+['"]?(scripts\.ops|scripts/ops)|import\s+['"]?(scripts\.ops|scripts/ops))""",
    re.MULTILINE,
)

# Python dynamic import patterns (importlib, __import__)
_PYTHON_DYNAMIC_IMPORT_RE = re.compile(
    r"""(?:importlib\.import_module\s*\(\s*['"](scripts\.ops[^'"]*)['"]|"""
    r"""__import__\s*\(\s*['"](scripts\.ops[^'"]*)['"])""",
)

# Python subprocess calling scripts/ops
_PYTHON_SUBPROCESS_SCRIPTS_OPS_RE = re.compile(
    r"""subprocess\.(?:run|call|Popen|check_call|check_output)\s*\(.*['"](?:.*scripts/ops[^'"]*|.*scripts\.ops[^'"]*)['"]""",
    re.DOTALL,
)

# JavaScript require/import patterns
_JS_REQUIRE_RE = re.compile(
    r"""(?:require\s*\(\s*['"](?:.*scripts/ops[^'"]*|.*scripts\.ops[^'"]*)['"]\s*\)|"""
    r"""import\s+.*\s+from\s+['"](?:.*scripts/ops[^'"]*|.*scripts\.ops[^'"]*)['"]|"""
    r"""import\s*\(\s*['"](?:.*scripts/ops[^'"]*|.*scripts\.ops[^'"]*)['"]\s*\))""",
)

# JavaScript spawn/exec/fork calling scripts/ops paths
_JS_SPAWN_SCRIPTS_OPS_RE = re.compile(
    r"""(?:spawn|exec|fork|execFile|execSync|spawnSync)\s*\(.*['"](?:.*scripts/ops[^'"]*|.*scripts\.ops[^'"]*)['"]""",
    re.DOTALL,
)


def _is_comment_or_string_line(line: str) -> bool:
    """Heuristic: return True if *line* is likely a comment or string-only line."""
    stripped = line.strip()
    if not stripped:
        return True
    # Python/JS single-line comment
    if stripped.startswith("#") or stripped.startswith("//"):
        return True
    # Docstring / multiline string markers
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if stripped.startswith("/*") or stripped.startswith("*"):
        return True
    # Common logger patterns that mention scripts/ops as instructional text
    if re.search(
        r"""\.(?:info|debug|warn|error|log|warning)\s*\(\s*(?:f['"]|['"])""",
        stripped,
    ):
        # Contains a logger call — likely not a runtime dependency
        if "scripts/ops" in stripped or "scripts.ops" in stripped:
            return True
    return False


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
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def _git_diff_name_status(
    repo_root: Path, base_ref: str, head_ref: str
) -> list[tuple[str, str, str | None]]:
    """Return list of (status, path, old_path|None) from git diff --name-status."""
    output = _git_output(
        repo_root, ["diff", "--name-status", "-M", f"{base_ref}...{head_ref}"]
    )
    entries: list[tuple[str, str, str | None]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            entries.append((status, parts[2], parts[1]))
        elif len(parts) >= 2:
            entries.append((status, parts[1], None))
    return entries


def _read_file_at_revision(
    repo_root: Path, revision: str, path: str
) -> str | None:
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


def _list_files_at_revision(
    repo_root: Path, revision: str, prefix: str
) -> set[str]:
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

    Compares base vs head. Only blocks additions (A) and rename destinations (R).
    Modifications (M) and deletions (D) are allowed.
    """
    errors: list[str] = []

    base_files = _list_files_at_revision(repo_root, base_ref, REPORT_PREFIX)
    head_files = _list_files_at_revision(repo_root, head_ref, REPORT_PREFIX)

    # New report files = in head but not in base
    new_reports = sorted(head_files - base_files)
    for path in new_reports:
        if path in AUTHORIZED_GOVERNANCE_ADDITIONS:
            continue
        errors.append(
            f"{ERR_REPORT}: Unauthorized new report under docs/_reports: "
            f"{path}. Growth freeze is active — no new reports allowed "
            f"without explicit gate authorization."
        )

    base_manifest_files = _list_files_at_revision(
        repo_root, base_ref, MANIFEST_PREFIX
    )
    head_manifest_files = _list_files_at_revision(
        repo_root, head_ref, MANIFEST_PREFIX
    )

    new_manifests = sorted(head_manifest_files - base_manifest_files)
    for path in new_manifests:
        if path in AUTHORIZED_GOVERNANCE_ADDITIONS:
            continue
        errors.append(
            f"{ERR_MANIFEST}: Unauthorized new manifest under docs/_manifests: "
            f"{path}. Growth freeze is active — no new manifests allowed "
            f"without explicit gate authorization."
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
    new files (status A) and rename destinations (status R).
    """
    errors: list[str] = []
    entries = _git_diff_name_status(repo_root, base_ref, head_ref)

    for status, path, _old_path in entries:
        # Only block additions and rename destinations
        if status not in ("A", "R"):
            continue
        # Only check scripts/ directory
        if not path.startswith("scripts/"):
            continue
        # Check basename for numbered governance pattern
        basename = Path(path).name
        if _is_numbered_governance_basename(basename):
            if path in AUTHORIZED_GOVERNANCE_ADDITIONS:
                continue
            errors.append(
                f"{ERR_PHASE}: Unauthorized new numbered governance script: "
                f"{path}. Governance script number growth is frozen — "
                f"no new Phase/ADG-numbered scripts without explicit "
                f"gate authorization."
            )

    return errors


# ---------------------------------------------------------------------------
# Check 3: New src → scripts/ops reverse dependencies
# ---------------------------------------------------------------------------


def _scan_python_file_for_scripts_ops_deps(content: str, path: str) -> list[str]:
    """Scan Python source for scripts.ops runtime imports."""
    found: list[str] = []

    for line_num, line in enumerate(content.splitlines(), start=1):
        if _is_comment_or_string_line(line):
            continue

        # Static imports: from scripts.ops... import ... / import scripts.ops...
        if _PYTHON_IMPORT_RE.search(line):
            found.append(
                f"{ERR_REVERSE_DEP}: {path}:{line_num}: "
                f"Python import of scripts.ops: {line.strip()[:100]}"
            )
            continue

        # Dynamic imports: importlib.import_module("scripts.ops...") / __import__("scripts.ops...")
        m = _PYTHON_DYNAMIC_IMPORT_RE.search(line)
        if m:
            found.append(
                f"{ERR_REVERSE_DEP}: {path}:{line_num}: "
                f"Python dynamic import of scripts.ops: {line.strip()[:100]}"
            )
            continue

    # Subprocess calls (multiline-aware)
    for m in _PYTHON_SUBPROCESS_SCRIPTS_OPS_RE.finditer(content):
        # Estimate line number
        line_num = content[: m.start()].count("\n") + 1
        matched = m.group()[:120]
        found.append(
            f"{ERR_REVERSE_DEP}: {path}:{line_num}: "
            f"Python subprocess calling scripts/ops: {matched}"
        )

    return found


def _scan_js_file_for_scripts_ops_deps(content: str, path: str) -> list[str]:
    """Scan JavaScript/TypeScript source for scripts.ops runtime requires/imports."""
    found: list[str] = []

    for line_num, line in enumerate(content.splitlines(), start=1):
        if _is_comment_or_string_line(line):
            continue

        # require("...scripts/ops...") / import ... from "...scripts/ops..."
        m = _JS_REQUIRE_RE.search(line)
        if m:
            found.append(
                f"{ERR_REVERSE_DEP}: {path}:{line_num}: "
                f"JS require/import of scripts/ops: {line.strip()[:100]}"
            )
            continue

    # spawn/exec/fork calls (multiline-aware)
    for m in _JS_SPAWN_SCRIPTS_OPS_RE.finditer(content):
        line_num = content[: m.start()].count("\n") + 1
        matched = m.group()[:120]
        # Filter: spawn/exec calls that appear inside logger calls
        before = content[max(0, m.start() - 200) : m.start()]
        if re.search(r"""\.(?:info|debug|warn|error|log)\s*\(.*$""", before, re.DOTALL):
            continue
        found.append(
            f"{ERR_REVERSE_DEP}: {path}:{line_num}: "
            f"JS spawn/exec calling scripts/ops: {matched}"
        )

    return found


def _find_src_reverse_deps_at_revision(
    repo_root: Path,
    revision: str,
) -> dict[str, list[str]]:
    """Find all src → scripts/ops dependencies in a given revision.

    Returns a dict mapping {path: [error_messages]} for each src file
    that has a dependency.
    """
    deps: dict[str, list[str]] = {}

    # List all source files
    src_files = _git_output(
        repo_root,
        ["ls-tree", "-r", "--name-only", revision, "src/"],
    ).splitlines()

    for path in src_files:
        if not path:
            continue
        content = _read_file_at_revision(repo_root, revision, path)
        if content is None:
            continue

        if path.endswith(".py"):
            findings = _scan_python_file_for_scripts_ops_deps(content, path)
        elif path.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")):
            findings = _scan_js_file_for_scripts_ops_deps(content, path)
        else:
            continue

        if findings:
            deps[path] = findings

    return deps


def check_new_reverse_dependencies(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block NEW src → scripts/ops reverse dependencies.

    Scans src/ files in both base and head revisions. Only blocks
    dependencies that exist in head but not in base.
    """
    errors: list[str] = []

    base_deps = _find_src_reverse_deps_at_revision(repo_root, base_ref)
    head_deps = _find_src_reverse_deps_at_revision(repo_root, head_ref)

    for path, head_findings in sorted(head_deps.items()):
        base_findings = base_deps.get(path, [])
        # Check if there are new dependencies (more findings in head)
        if len(head_findings) > len(base_findings):
            # New file with dependencies, or existing file with new deps
            if not base_findings:
                # Entirely new reverse dependency file
                for finding in head_findings:
                    errors.append(finding)
            else:
                # Existing file with additional dependencies — report the new ones
                # We use a simple count comparison; in practice, if a file grew
                # new deps, flag all head findings for that file
                new_count = len(head_findings) - len(base_findings)
                errors.append(
                    f"{ERR_REVERSE_DEP}: {path}: "
                    f"New src → scripts/ops reverse dependency detected "
                    f"({new_count} new import(s)). Growth freeze is active."
                )
        elif not base_findings and head_findings:
            # File is new and has dependencies (caught by len diff above, but
            # belt-and-suspenders)
            for finding in head_findings:
                errors.append(finding)

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
        errors.append(
            f"{ERR_REPORT}: Governance growth gate failed to check reports/manifests: {exc}"
        )

    # 2. New numbered governance scripts
    try:
        errors.extend(
            check_new_numbered_governance_scripts(root, base_ref, head_ref)
        )
    except RuntimeError as exc:
        errors.append(
            f"{ERR_PHASE}: Governance growth gate failed to check governance scripts: {exc}"
        )

    # 3. New src → scripts/ops reverse dependencies
    try:
        errors.extend(check_new_reverse_dependencies(root, base_ref, head_ref))
    except RuntimeError as exc:
        errors.append(
            f"{ERR_REVERSE_DEP}: Governance growth gate failed to check reverse deps: {exc}"
        )

    # Stable sort
    errors.sort()
    return errors
