#!/usr/bin/env python3
"""TECHDEBT-G2 P1 governance rules — CI-enforceable checks.

lifecycle: permanent

Contains:
- P1-1: no-archive-runtime-import — prevents active code from importing archive code
- P1-2: dangerous-auth path cross-validation — ensures authorized paths cover actual changes
- P1-3: script lifecycle requirement — new scripts must declare purpose/owner/lifecycle

Usage:
  from scripts.ops.helpers.governance_p1_checks import (
      check_no_archive_runtime_import,
      check_dangerous_auth_path_cross_validation,
      check_script_lifecycle_requirement,
  )
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]

# ============================================================================
# P1-1: no-archive-runtime-import
# ============================================================================

# Patterns that indicate a dependency on archive code.
_ARCHIVE_IMPORT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"archive_vault_2026",
        r"from\s+archive_vault",
        r"import\s+archive_vault",
        r"from\s+archive\b",
        r"import\s+archive\b",
    )
)

# Changed paths under these prefixes are CHECKED (hard-fail).
_ARCHIVE_CHECK_PREFIXES: tuple[str, ...] = (
    "src/",
    "scripts/ops/",
    "scripts/devops/",
    "scripts/data/",
)

# Changed paths under these prefixes are REPORT-ONLY (not hard-fail).
_ARCHIVE_REPORT_ONLY_PREFIXES: tuple[str, ...] = ("tests/",)

# Changed paths under these prefixes are NEVER scanned.
_ARCHIVE_EXEMPT_PREFIXES: tuple[str, ...] = (
    "docs/",
    "archive_vault_2026/",
    ".github/",
)


def _is_archive_check_target(path: str) -> bool:
    """Return True if *path* should be checked for archive imports (hard-fail)."""
    return any(path.startswith(px) for px in _ARCHIVE_CHECK_PREFIXES)


def _is_archive_report_only(path: str) -> bool:
    """Return True if *path* should be checked for archive imports (report-only)."""
    return any(path.startswith(px) for px in _ARCHIVE_REPORT_ONLY_PREFIXES)


def _is_archive_exempt(path: str) -> bool:
    """Return True if *path* is exempt from archive import checks."""
    return any(path.startswith(px) for px in _ARCHIVE_EXEMPT_PREFIXES)


def _scan_file_for_archive_imports(file_path: Path) -> list[str]:
    """Scan *file_path* for patterns that reference archive code.

    Returns a list of matched pattern snippets.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    hits: list[str] = []
    for pat in _ARCHIVE_IMPORT_PATTERNS:
        for m in pat.finditer(text):
            snippet = m.group()[:80]
            hits.append(f"  pattern '{pat.pattern}' matched '{snippet}'")
    return hits


def check_no_archive_runtime_import(
    changed: set[str],
) -> list[str]:
    """P1-1: Prevent active runtime code from importing or depending on archive code.

    Only scans *changed* files to avoid flagging pre-existing debt.
    - ``src/**`` and ``scripts/**`` paths: hard-fail.
    - ``tests/**`` paths: report-only (printed to stdout, not blocking).
    - ``docs/**`` and ``archive_vault_2026/**`` paths: never scanned.

    Returns a list of error strings (hard-fail only).
    """
    errors: list[str] = []
    report_only: list[str] = []

    for rel_path in sorted(changed):
        if _is_archive_exempt(rel_path):
            continue

        abs_path = ROOT / rel_path
        if not abs_path.is_file():
            continue

        hits = _scan_file_for_archive_imports(abs_path)
        if not hits:
            continue

        detail = f"Archive runtime import detected:\n- path: {rel_path}\n" + "\n".join(hits)

        if _is_archive_report_only(rel_path):
            report_only.append(detail)
        elif _is_archive_check_target(rel_path):
            errors.append(detail)
        # Paths that are neither check-target nor report-only nor exempt
        # (e.g., config files) are silently skipped.

    # Print report-only findings to stdout for visibility.
    if report_only:
        sys.stdout.write(
            "[P1-1 archive-import][report-only] "
            f"{len(report_only)} file(s) reference archive code:\n"
        )
        for r in report_only:
            sys.stdout.write(f"{r}\n")
        sys.stdout.write(
            "[P1-1 archive-import][report-only] tests/ references are non-blocking in this phase.\n"
        )

    return errors


# ============================================================================
# P1-2: dangerous-auth path cross-validation
# ============================================================================

# High-risk paths that require explicit authorization coverage.
_DANGEROUS_AUTH_PATHS: tuple[str, ...] = (
    ".github/workflows/",
    "scripts/devops/gatekeeper.sh",
    "scripts/ops/ai_workflow_gate.py",
    "scripts/ops/helpers/pr_authorization_matrix.py",
    "scripts/ops/helpers/pr_authorization_rules.py",
    "scripts/ops/helpers/garbage_prevention_checks.py",
    "scripts/ops/helpers/governance_p1_checks.py",
    "Dockerfile",
    "alembic/",
    "migrations/",
    "scripts/devops/check_",
)


def _is_dangerous_auth_path(path: str) -> bool:
    """Check if *path* matches any dangerous-auth-category pattern.

    Supports exact match, prefix match (ends with ``/``), and prefix match
    for file-name prefixes like ``scripts/devops/check_``.
    """
    for pattern in _DANGEROUS_AUTH_PATHS:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif pattern == path:
            return True
        elif path.startswith(pattern):
            # e.g., pattern = "scripts/devops/check_" matches
            # "scripts/devops/check_python_ast_utf8.py"
            return True
    # Also check docker-compose* patterns
    return bool(path.startswith("docker-compose"))


def _authorized_path_covers(authorized: str, changed_path: str) -> bool:
    """Check if *authorized* path pattern covers *changed_path*.

    Supports:
    - Exact match: ``foo.py`` covers ``foo.py``
    - Prefix/** match: ``prefix/**`` covers ``prefix/bar/baz.py``
    - Prefix match (no wildcard but ends with /): ``prefix/`` covers ``prefix/bar.py``
    """
    # Exact match
    if authorized == changed_path:
        return True
    # ** wildcard: prefix/** covers path if path starts with prefix/
    if authorized.endswith("/**"):
        prefix = authorized[:-3]  # Remove trailing '**' but keep '/'
        return changed_path.startswith(prefix)
    # ends with / but no **: still treat as directory prefix
    if authorized.endswith("/"):
        return changed_path.startswith(authorized)
    # Single * wildcard within a path segment
    if "*" in authorized and "/**" not in authorized:
        escaped = re.escape(authorized).replace(r"\*", "[^/]*")
        return bool(re.match("^" + escaped + "$", changed_path))
    return False


def _parse_authorized_paths_from_body(pr_body: str) -> set[str]:
    """Extract authorized paths from PR body's authorization sections.

    Reuses the parse_authorized_paths function if available; otherwise
    falls back to a lightweight inline parser.
    """
    try:
        from scripts.ops.helpers.pr_authorization_matrix import (  # noqa: PLC0415
            parse_authorized_paths,
        )

        return parse_authorized_paths(pr_body)
    except ImportError:
        pass

    # Lightweight fallback: look for "Authorized paths" in the body
    paths: set[str] = set()
    for m in re.finditer(
        r"\|\s*Authorized\s+paths\s*\|\s*([^|]+)\s*\|",
        pr_body,
        re.IGNORECASE,
    ):
        cell = m.group(1).strip()
        for token in re.split(r"[,;]+", cell):
            cleaned = token.strip().strip("`\"'")
            if cleaned:
                paths.add(cleaned)
    for m in re.finditer(
        r"-\s*Authorized\s+paths\s*:\s*(.+)",
        pr_body,
        re.IGNORECASE,
    ):
        line = m.group(1).strip()
        for token in re.split(r"[,;]+", line):
            cleaned = token.strip().strip("`\"'")
            if cleaned:
                paths.add(cleaned)
    return paths


def _has_dangerous_auth_section(pr_body: str) -> bool:
    """Check if PR body has a substantive Dangerous File Authorization section."""
    idx = pr_body.find("## Dangerous File Authorization")
    if idx == -1:
        return False
    suffix = pr_body[idx + len("## Dangerous File Authorization") :]
    end = re.search(r"\n##\s", suffix)
    if end:
        suffix = suffix[: end.start()]
    lines = [
        ln.strip() for ln in suffix.splitlines() if ln.strip() and not ln.strip().startswith("<!--")
    ]
    if len(lines) < 1:
        return False
    hollow = re.compile(
        r"^(?:N/?A|none\.?|no\s+dangerous\s+files?\.?|not\s+applicable\.?)$",
        re.IGNORECASE,
    )
    return not any(hollow.match(line) for line in lines)


def _has_pr_authorization_matrix_section(pr_body: str) -> bool:
    """Check if PR body has a PR Authorization Matrix section."""
    return "## PR Authorization Matrix" in pr_body


def check_dangerous_auth_path_cross_validation(
    changed: set[str],
    pr_body: str,
) -> list[str]:
    """P1-2: Cross-validate dangerous changed paths against authorized paths.

    If any changed file matches a dangerous-auth path category, the PR body
    must:
    1. Have a ``## Dangerous File Authorization`` section.
    2. Have a ``## PR Authorization Matrix`` section.
    3. List authorized paths that cover every dangerous changed path.

    Path coverage supports exact match, ``prefix/**``, and ``prefix/`` patterns.

    Returns a list of error strings.
    """
    if not changed or not pr_body:
        return []

    errors: list[str] = []

    # Identify dangerous paths among changed files.
    dangerous_changed = sorted(p for p in changed if _is_dangerous_auth_path(p))
    if not dangerous_changed:
        return []

    # 1. Dangerous File Authorization section must exist.
    has_dangerous_auth = _has_dangerous_auth_section(pr_body)
    if not has_dangerous_auth:
        errors.append(
            "Dangerous authorization path cross-validation failed: "
            f"{len(dangerous_changed)} dangerous path(s) changed but no substantive "
            "'## Dangerous File Authorization' section found. "
            "Dangerous paths: " + ", ".join(dangerous_changed)
        )
        return errors

    # 2. PR Authorization Matrix section must exist.
    has_matrix = _has_pr_authorization_matrix_section(pr_body)
    if not has_matrix:
        errors.append(
            "Dangerous authorization path cross-validation failed: "
            f"{len(dangerous_changed)} dangerous path(s) changed but no "
            "'## PR Authorization Matrix' section found. "
            "Dangerous paths: " + ", ".join(dangerous_changed)
        )
        return errors

    # 3. Authorized paths must cover every dangerous changed path.
    authorized = _parse_authorized_paths_from_body(pr_body)
    if not authorized:
        errors.append(
            "Dangerous authorization path cross-validation failed: "
            f"{len(dangerous_changed)} dangerous path(s) changed but no "
            "'Authorized paths' entry found in PR Authorization Matrix. "
            "Dangerous paths: " + ", ".join(dangerous_changed)
        )
        return errors

    uncovered = [
        dpath
        for dpath in dangerous_changed
        if not any(_authorized_path_covers(auth, dpath) for auth in authorized)
    ]

    if uncovered:
        errors.append(
            "Dangerous authorization path mismatch: "
            f"{len(uncovered)} dangerous path(s) changed but not covered by "
            "Authorized paths in PR Authorization Matrix. "
            "Uncovered paths: " + ", ".join(uncovered) + ". "
            "Authorized paths: " + ", ".join(sorted(authorized)) + ". "
            "Add the uncovered paths or a valid prefix (e.g., 'scripts/devops/**') "
            "to the Authorized paths entry."
        )

    return errors


# ============================================================================
# P1-3: script lifecycle requirement
# ============================================================================

# Script paths that require lifecycle/ownership declaration.
_SCRIPT_LIFECYCLE_PREFIXES: tuple[str, ...] = (
    "scripts/ops/",
    "scripts/devops/",
)

# File types to check.
_SCRIPT_LIFECYCLE_EXTENSIONS: frozenset[str] = frozenset({".py", ".sh", ".js", ".ts"})

# Exemption: tests/ never requires lifecycle declaration.
_SCRIPT_LIFECYCLE_EXEMPT_PREFIXES: tuple[str, ...] = ("tests/",)

# Patterns to detect lifecycle or owner in file header.
_LIFECYCLE_HEADER_RE = re.compile(
    r"(?:Lifecycle|lifecycle)\s*:\s*\S+",
    re.IGNORECASE,
)
_OWNER_HEADER_RE = re.compile(
    r"(?:Owner|owner|Maintainer|maintainer)\s*:\s*\S+",
    re.IGNORECASE,
)


def _is_script_lifecycle_target(path: str) -> bool:
    """Return True if *path* is a new script requiring lifecycle declaration."""
    if any(path.startswith(px) for px in _SCRIPT_LIFECYCLE_EXEMPT_PREFIXES):
        return False
    if not any(path.startswith(px) for px in _SCRIPT_LIFECYCLE_PREFIXES):
        return False
    suffix = Path(path).suffix.lower()
    return suffix in _SCRIPT_LIFECYCLE_EXTENSIONS


def _file_has_lifecycle_header(abs_path: Path) -> bool:
    """Check if file contains a Lifecycle: or Owner: declaration in its header."""
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
        # Only check first 40 lines / 3000 chars for header.
        header_lines = text[:3000].splitlines()[:40]
        header_text = "\n".join(header_lines)
    except (OSError, UnicodeDecodeError):
        return False
    return bool(_LIFECYCLE_HEADER_RE.search(header_text) or _OWNER_HEADER_RE.search(header_text))


def _pr_has_script_lifecycle_section(pr_body: str) -> bool:
    """Check if PR body has a Script Lifecycle section."""
    return "## Script Lifecycle" in pr_body


def check_script_lifecycle_requirement(
    added: set[str],
    pr_body: str,
) -> list[str]:
    """P1-3: Require lifecycle/ownership declaration for newly added scripts.

    New files under ``scripts/ops/**`` or ``scripts/devops/**`` (with extensions
    ``.py``, ``.sh``, ``.js``, ``.ts``) must satisfy at least one:

    1. File header contains ``Lifecycle:`` or ``Owner:`` declaration.
    2. PR body contains a ``## Script Lifecycle`` section.

    Exceptions: ``tests/**`` paths are exempt.

    Returns a list of error strings.
    """
    if not added:
        return []

    errors: list[str] = []
    pr_has_lifecycle_section = _pr_has_script_lifecycle_section(pr_body)

    for rel_path in sorted(added):
        if not _is_script_lifecycle_target(rel_path):
            continue

        abs_path = ROOT / rel_path

        # Check if file exists and has header declaration
        if abs_path.is_file() and _file_has_lifecycle_header(abs_path):
            continue

        # Check if PR body has Script Lifecycle section
        if pr_has_lifecycle_section:
            continue

        errors.append(
            "Script lifecycle missing:\n"
            f"- path: {rel_path}\n"
            "- reason: new scripts must declare purpose, owner, and lifecycle\n"
            "- fix: add 'Lifecycle:' and 'Owner:' to the file header, "
            "or add a '## Script Lifecycle' section to the PR body"
        )

    return errors
