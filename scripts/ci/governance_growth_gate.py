#!/usr/bin/env python3
"""Governance growth freeze gate — prevent unauthorized growth of governance artifacts.

lifecycle: permanent

Compares base vs head revisions and blocks only NEW violations.
Three categories:
  1. New reports/manifests under docs/_reports/ or docs/_manifests/
  2. New numbered governance scripts (Phase/ADG patterns) under scripts/
  3. New src → scripts/ops reverse dependencies (delegated to
     governance_reverse_dependency.py)
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from scripts.ci.governance_reverse_dependency import check_new_reverse_dependencies

# ---------------------------------------------------------------------------
AUTHORIZED_GOVERNANCE_ADDITIONS: frozenset[str] = frozenset()
ERR_REPORT = "GOV-GROWTH-REPORT"
ERR_MANIFEST = "GOV-GROWTH-MANIFEST"
ERR_PHASE = "GOV-GROWTH-PHASE"
REPORT_PREFIX = "docs/_reports/"
MANIFEST_PREFIX = "docs/_manifests/"

_GOVERNANCE_SCRIPT_RE = re.compile(r"(?:^|[_.-])(phase|adg)[-_]?\d", re.IGNORECASE)


def _is_numbered_governance_basename(basename: str) -> bool:
    return bool(_GOVERNANCE_SCRIPT_RE.search(basename))


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


def _git_diff_name_status(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[tuple[str, str, str | None]]:
    """Return (status, path, old_path|None) from git diff --name-status -M."""
    output = _git_output(
        repo_root,
        ["diff", "--name-status", "-M", f"{base_ref}...{head_ref}"],
    )
    entries: list[tuple[str, str, str | None]] = []
    min_rename_parts = 3
    min_normal_parts = 2
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= min_rename_parts:
            entries.append((status, parts[2], parts[1]))
        elif len(parts) >= min_normal_parts:
            entries.append((status, parts[1], None))
    return entries


def _list_files_at_revision(repo_root: Path, revision: str, prefix: str) -> set[str]:
    output = _git_output(
        repo_root,
        ["ls-tree", "-r", "--name-only", revision, prefix],
    )
    return {line for line in output.splitlines() if line}


# ---------------------------------------------------------------------------
# Check 1: New reports and manifests
# ---------------------------------------------------------------------------


def _format_report_error(path: str) -> str:
    return f"{ERR_REPORT}: Unauthorized new report under docs/_reports: {path}. Growth freeze is active."


def _format_manifest_error(path: str) -> str:
    return f"{ERR_MANIFEST}: Unauthorized new manifest under docs/_manifests: {path}. Growth freeze is active."


def check_new_reports_and_manifests(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Block new or renamed files under docs/_reports/ and docs/_manifests/."""
    errors: list[str] = []
    base_files = _list_files_at_revision(repo_root, base_ref, REPORT_PREFIX)
    head_files = _list_files_at_revision(repo_root, head_ref, REPORT_PREFIX)
    errors.extend(
        _format_report_error(p)
        for p in sorted(head_files - base_files)
        if p not in AUTHORIZED_GOVERNANCE_ADDITIONS
    )
    base_m = _list_files_at_revision(repo_root, base_ref, MANIFEST_PREFIX)
    head_m = _list_files_at_revision(repo_root, head_ref, MANIFEST_PREFIX)
    errors.extend(
        _format_manifest_error(p)
        for p in sorted(head_m - base_m)
        if p not in AUTHORIZED_GOVERNANCE_ADDITIONS
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
    """Block new scripts with Phase/ADG numbered governance naming patterns."""
    errors: list[str] = []
    entries = _git_diff_name_status(repo_root, base_ref, head_ref)
    for status, path, _old_path in entries:
        if status != "A" and not status.startswith("R"):
            continue
        if not path.startswith("scripts/"):
            continue
        basename = Path(path).name
        if (
            _is_numbered_governance_basename(basename)
            and path not in AUTHORIZED_GOVERNANCE_ADDITIONS
        ):
            errors.append(
                f"{ERR_PHASE}: Unauthorized new numbered governance script: "
                f"{path}. Governance script number growth is frozen."
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
    """Run all governance growth freeze checks."""
    root = Path(repo_root)
    errors: list[str] = []
    for label, fn in [
        ("reports/manifests", check_new_reports_and_manifests),
        ("governance scripts", check_new_numbered_governance_scripts),
        ("reverse deps", check_new_reverse_dependencies),
    ]:
        try:
            errors.extend(fn(root, base_ref, head_ref))
        except RuntimeError as exc:
            errors.append(
                f"GOV-GROWTH-GATE: Governance growth freeze check failed ({label}): {exc}"
            )
    errors.sort()
    return errors
