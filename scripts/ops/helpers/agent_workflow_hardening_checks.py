#!/usr/bin/env python3
"""Agent workflow hardening checks — Phase1 CI-enforceable rules.

lifecycle: permanent

Extracted from ai_workflow_gate.py to keep gate file under length limits.
Covers: forbidden rewrite patterns, large risky change detection, forbidden
safety claims, cleanup/scanner phase declaration helpers.

Usage:
  from scripts.ops.helpers.agent_workflow_hardening_checks import (
      check_forbidden_rewrite_patterns,
      check_large_risky_change,
      check_forbidden_safety_claims,
  )
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.ops.ai_workflow_gate import Change

# Patterns that indicate forbidden V2/rewritten/replacement file naming.
# Only checked for NEW files (status A), not existing historical files.
# Exempt paths: docs/, database/migrations/ (alembic version dirs).
FORBIDDEN_REWRITE_NAME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r".*_v2\.(?:py|js)$",
        r".*_new\.(?:py|js)$",
        r".*_final\.(?:py|js)$",
        r".*_rewritten\.(?:py|js)$",
        r".*_replacement\.(?:py|js)$",
        r".*_backup\.(?:py|js)$",
    )
)

REWRITE_CHECK_EXEMPT_PREFIXES: tuple[str, ...] = (
    "database/migrations/",
    "docs/",
)

# Forbidden phrases that must not appear in PR body unless an approved
# release closure task with satisfied closure criteria exists.
FORBIDDEN_SAFETY_CLAIMS: tuple[str, ...] = (
    "SC-002 fully fixed",
    "safe to train",
    "safe to write",
    "production ready",
    "real DB write ready",
    "data expansion ready",
    "training unblocked",
)

# Scanner/enforcement file name patterns for risky-change detection.
SCANNER_FILE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r".*scanner.*\.py$",
        r".*scanner.*\.js$",
        r".*enforcement.*\.py$",
        r".*enforcement.*\.js$",
        r".*_check\.py$",
        r".*_check\.js$",
        r".*_gate\.py$",
        r".*_gate\.js$",
    )
)

MAX_DELETION_WITHOUT_CLEANUP = 3
MAX_RENAME_WITHOUT_CLEANUP = 3
MAX_SCANNER_FILES_WITHOUT_SCANNER_PHASE = 2


def _pr_declares_cleanup_task(pr_body: str) -> bool:
    """Check if PR body declares this as a cleanup task."""
    return bool(
        re.search(r"Task type\s*\|\s*.*cleanup", pr_body, re.IGNORECASE)
        or re.search(r"cleanup\s*phase", pr_body, re.IGNORECASE)
    )


def _pr_declares_scanner_phase(pr_body: str) -> bool:
    """Check if PR body declares this as a scanner phase task."""
    return bool(
        re.search(r"Task type\s*\|\s*.*scanner", pr_body, re.IGNORECASE)
        or re.search(r"scanner\s*phase", pr_body, re.IGNORECASE)
    )


def check_forbidden_rewrite_patterns(added: set[str], pr_body: str) -> list[str]:
    """Flag newly-added files matching forbidden V2/rewritten/replacement naming.

    Only checks *new* files (status A). Historical files already in the tree
    are not flagged. Documentation paths and alembic migration directories are
    exempt.
    """
    is_cleanup = _pr_declares_cleanup_task(pr_body)
    errors: list[str] = []
    for path in sorted(added):
        if any(path.startswith(px) for px in REWRITE_CHECK_EXEMPT_PREFIXES):
            continue
        filename = Path(path).name
        for pat in FORBIDDEN_REWRITE_NAME_PATTERNS:
            if pat.match(filename):
                if is_cleanup:
                    continue
                errors.append(
                    f"Forbidden rewrite file pattern: '{path}' matches "
                    f"'{pat.pattern}'. V2/FINAL/rewritten/replacement/backup "
                    "files are prohibited unless this PR is an explicitly "
                    "approved cleanup/refactor task. Declare 'cleanup phase' "
                    "in the task type to override."
                )
                break
    return errors


def check_large_risky_change(
    changes: list[Change],
    pr_body: str,
) -> list[str]:
    """Flag large-scale deletion, rename, or scanner sprawl without declaration."""
    errors: list[str] = []
    is_cleanup = _pr_declares_cleanup_task(pr_body)
    is_scanner_phase = _pr_declares_scanner_phase(pr_body)

    deleted = [c for c in changes if c.status == "D"]
    if len(deleted) >= MAX_DELETION_WITHOUT_CLEANUP and not is_cleanup:
        sample = ", ".join(c.path for c in deleted[:5])
        errors.append(
            f"Large deletion detected: {len(deleted)} files deleted. "
            "Deleting >= 3 files requires an explicit cleanup task declaration "
            f"in the PR body (Task type = cleanup phase). Deleted: {sample}"
        )

    renamed = [c for c in changes if c.status == "R"]
    if len(renamed) >= MAX_RENAME_WITHOUT_CLEANUP and not is_cleanup:
        sample = ", ".join(f"{c.old_path} -> {c.path}" for c in renamed[:5])
        errors.append(
            f"Large rename/move detected: {len(renamed)} files renamed. "
            "Renaming >= 3 files requires an explicit cleanup task declaration. "
            f"Renamed: {sample}"
        )

    # Reconstruct added paths from changes
    added = {c.path for c in changes if c.status == "A"}
    new_scanners = sorted(
        p
        for p in added
        if p.startswith("scripts/ops/")
        and any(pat.match(Path(p).name) for pat in SCANNER_FILE_PATTERNS)
    )
    if len(new_scanners) >= MAX_SCANNER_FILES_WITHOUT_SCANNER_PHASE and not is_scanner_phase:
        errors.append(
            f"Multiple new scanner/enforcement files without scanner phase "
            f"declaration: {len(new_scanners)} added. "
            "Adding >= 2 scanner files requires an explicit scanner phase "
            "declaration in the PR body. "
            f"New scanner files: {', '.join(new_scanners)}"
        )

    return errors


def check_forbidden_safety_claims(pr_body: str) -> list[str]:
    """Flag forbidden safety claims that prematurely declare SC-002 resolved."""
    body_lower = pr_body.lower()
    return [
        f"Forbidden safety claim detected: '{claim}'. "
        "SC-002 is partial mitigation only. Do not claim SC-002 "
        "complete, safe to train/write, production ready, or "
        "training/data expansion unblocked unless an approved "
        "release closure task with satisfied closure criteria exists."
        for claim in FORBIDDEN_SAFETY_CLAIMS
        if claim.lower() in body_lower
    ]
