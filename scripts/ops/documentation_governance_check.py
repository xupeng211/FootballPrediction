#!/usr/bin/env python3
"""Check documentation governance rules for documentation cleanup PRs.

lifecycle: permanent
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[2]
MAX_ADDED_FILES = 5
NAME_STATUS_PATH_PARTS = 2
NAME_STATUS_RENAME_PARTS = 3
PHASE1_MAX_ADDED_FILES = 1
PHASE2_MAX_ADDED_FILES = 1
PHASE3A_MAX_ADDED_FILES = 1
AI_AUDIT_MAX_ADDED_FILES = 1
TEST_DEBT_AUDIT_MAX_ADDED_FILES = 1
WILDCARD_CHARS = frozenset("*?[]")

PHASE0_ALLOWED_ADDED = frozenset(
    {
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md",
        "scripts/ops/documentation_governance_check.py",
        "tests/unit/test_documentation_governance_check.py",
    }
)

PHASE1_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE1_SOURCE_OF_TRUTH_NO_DELETION.md",
    }
)

PHASE2_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE2_ARCHIVE_CANDIDATE_MARKING_NO_MOVE.md",
    }
)

PHASE3A_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE3A_ARCHIVE_MOVE_PLAN_NO_DELETION_NO_MOVE.md",
    }
)

AI_AUDIT_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/AI_WORKFLOW_AND_TECH_DEBT_AUDIT_NO_CODE_CHANGES.md",
    }
)

TEST_DEBT_AUDIT_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/TEST_DEBT_AUDIT_NO_RUNTIME_CHANGE.md",
    }
)

SOURCE_OF_TRUTH_ALLOWED_CHANGED = frozenset(
    {
        ".github/pull_request_template.md",
        "README.md",
        "docs/PROJECT_STATUS.md",
        "docs/DATA_SOURCE_STRATEGY.md",
        "docs/data/FOTMOB_CURRENT_STATE.md",
        "docs/CANONICAL_MATCH_SCHEMA.md",
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
    }
)

ALLOWED_ADDED = (
    PHASE0_ALLOWED_ADDED
    | PHASE1_ALLOWED_ADDED
    | PHASE2_ALLOWED_ADDED
    | PHASE3A_ALLOWED_ADDED
    | AI_AUDIT_ALLOWED_ADDED
    | TEST_DEBT_AUDIT_ALLOWED_ADDED
)
ALLOWED_CHANGED = ALLOWED_ADDED | SOURCE_OF_TRUTH_ALLOWED_CHANGED

REQUIRED_DOCS = (
    "docs/DOCUMENTATION_GOVERNANCE.md",
    "docs/CODEX_WORKFLOW.md",
    "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md",
)

GOVERNANCE_SECTIONS = (
    "Document Classes",
    "Documentation Budget",
    "Documentation Impact Requirement",
    "Source of Truth Rule",
    "Report Lifecycle",
    "Codex Documentation Rules",
)

CODEX_SECTIONS = (
    "Core Rules",
    "Task Types",
    "Mandatory PR Body Sections",
    "Documentation Creation Decision Tree",
    "Prohibited Habits",
)

AUDIT_SECTIONS = (
    "Inventory",
    "Top Problem Areas",
    "Proposed Source of Truth Docs",
    "Archive Candidates",
    "Phase 1 Cleanup Proposal",
)

ALLOWLIST_GROUPS = (
    PHASE0_ALLOWED_ADDED,
    PHASE1_ALLOWED_ADDED,
    PHASE2_ALLOWED_ADDED,
    PHASE3A_ALLOWED_ADDED,
    AI_AUDIT_ALLOWED_ADDED,
    TEST_DEBT_AUDIT_ALLOWED_ADDED,
)


@dataclass(frozen=True)
class Change:
    """A normalized Git change entry."""

    status: str
    path: str
    old_path: str | None = None


def git_output(args: list[str], *, check: bool = True) -> str:
    """Run a local Git command and return stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def find_base_ref() -> str:
    """Find a local base ref without fetching from the network."""

    for ref in ("origin/main", "main"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return ref
    return "HEAD"


def parse_name_status(output: str) -> list[Change]:
    """Parse git diff --name-status output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= NAME_STATUS_RENAME_PARTS:
            changes.append(Change("R", parts[2], parts[1]))
            continue
        if status.startswith("D") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("D", parts[1]))
            continue
        if status.startswith("A") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("A", parts[1]))
            continue
        if len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("M", parts[1]))
    return changes


def parse_porcelain(output: str) -> list[Change]:
    """Parse git status --porcelain output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            old_path, new_path = path.split(" -> ", 1)
            changes.append(Change("R", new_path, old_path))
        elif code == "??" or "A" in code:
            changes.append(Change("A", path))
        elif "D" in code:
            changes.append(Change("D", path))
        else:
            changes.append(Change("M", path))
    return changes


def collect_changes(base_ref: str | None = None) -> list[Change]:
    """Collect committed and uncommitted changes for the branch."""

    base = base_ref or find_base_ref()
    diff_output = git_output(["diff", "--name-status", f"{base}...HEAD"])
    status_output = git_output(["status", "--porcelain"])
    unique: dict[tuple[str, str, str | None], Change] = {}
    for change in [*parse_name_status(diff_output), *parse_porcelain(status_output)]:
        unique[(change.status, change.path, change.old_path)] = change
    return list(unique.values())


def added_paths(changes: list[Change]) -> set[str]:
    """Return paths added by the current branch or working tree."""

    return {change.path for change in changes if change.status == "A"}


def changed_paths(changes: list[Change]) -> set[str]:
    """Return all changed paths, including old rename paths."""

    paths = {change.path for change in changes}
    paths.update(change.old_path for change in changes if change.old_path)
    return paths


def read_text(path: str) -> str:
    """Read a repository file as UTF-8 text."""

    return (ROOT / path).read_text(encoding="utf-8")


def iter_allowlist_paths() -> Iterable[str]:
    """Yield all exact paths from governance allowlists."""

    yield from ALLOWED_ADDED
    yield from SOURCE_OF_TRUTH_ALLOWED_CHANGED


def validate_required_files(errors: list[str]) -> None:
    """Validate required governance files and sections."""

    errors.extend(
        f"missing required file: {path}" for path in REQUIRED_DOCS if not (ROOT / path).exists()
    )

    section_sets = (
        ("docs/DOCUMENTATION_GOVERNANCE.md", GOVERNANCE_SECTIONS),
        ("docs/CODEX_WORKFLOW.md", CODEX_SECTIONS),
        ("docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md", AUDIT_SECTIONS),
    )
    for path, sections in section_sets:
        file_path = ROOT / path
        if not file_path.exists():
            continue
        text = read_text(path)
        errors.extend(
            f"{path} missing section: {section}" for section in sections if section not in text
        )


def validate_exact_allowlist_paths(errors: list[str]) -> None:
    """Validate that allowlist paths are exact and do not target archives."""
    for path in sorted(iter_allowlist_paths()):
        if any(char in path for char in WILDCARD_CHARS):
            errors.append(f"allowlist path must be exact, not wildcard: {path}")
        if path.startswith("docs/_archive/"):
            errors.append(f"archive allowlist path is prohibited: {path}")


def validate_added_allowlist_paths(errors: list[str]) -> None:
    """Validate that added-file allowlists do not permit governance sprawl."""
    for path in sorted(ALLOWED_ADDED):
        lower = path.lower()
        if path.startswith("docs/_manifests/"):
            errors.append(f"manifest allowlist path is prohibited: {path}")
        if "next_plan" in lower or "next-plan" in lower:
            errors.append(f"next-plan allowlist path is prohibited: {path}")
        if path.startswith("docs/_reports/") and "review" in lower:
            errors.append(f"review report allowlist path is prohibited: {path}")
        if path.startswith("docs/_reports/") and "decision" in lower:
            errors.append(f"decision report allowlist path is prohibited: {path}")


def validate_allowlist_budgets(errors: list[str]) -> None:
    """Validate that phase allowlist groups stay within the file budget."""
    if any(len(group) > MAX_ADDED_FILES for group in ALLOWLIST_GROUPS):
        errors.append("allowlist group exceeds maximum added-file budget")


def validate_allowlist_hardening(errors: list[str]) -> None:
    """Validate that governance allowlists stay exact and non-destructive."""
    validate_exact_allowlist_paths(errors)
    validate_added_allowlist_paths(errors)
    validate_allowlist_budgets(errors)


def max_added_files_for(added: set[str]) -> int:
    """Return the added-file budget for the current documentation governance phase."""

    if PHASE1_ALLOWED_ADDED & added:
        return PHASE1_MAX_ADDED_FILES
    if PHASE2_ALLOWED_ADDED & added:
        return PHASE2_MAX_ADDED_FILES
    if PHASE3A_ALLOWED_ADDED & added:
        return PHASE3A_MAX_ADDED_FILES
    if AI_AUDIT_ALLOWED_ADDED & added:
        return AI_AUDIT_MAX_ADDED_FILES
    if TEST_DEBT_AUDIT_ALLOWED_ADDED & added:
        return TEST_DEBT_AUDIT_MAX_ADDED_FILES
    return MAX_ADDED_FILES


def validate_change_budget(changes: list[Change], errors: list[str]) -> None:
    """Validate file budget and allowed paths."""

    added = added_paths(changes)
    changed = changed_paths(changes)
    max_added = max_added_files_for(added)
    unexpected = sorted(changed - ALLOWED_CHANGED)
    missing = sorted(ALLOWED_ADDED - {path for path in ALLOWED_ADDED if (ROOT / path).exists()})

    if len(added) > max_added:
        errors.append(f"added file budget exceeded: {len(added)} > {max_added}")
    if unexpected:
        errors.append(f"unexpected changed paths: {', '.join(unexpected)}")
    if missing:
        errors.append(f"allowed governance files missing: {', '.join(missing)}")


def validate_prohibited_files(changes: list[Change], errors: list[str]) -> None:
    """Validate prohibited file patterns and destructive operations."""

    added = added_paths(changes)
    for path in sorted(added):
        lower = path.lower()
        if path.startswith("docs/_manifests/"):
            errors.append(f"new manifest is prohibited: {path}")
        if "next_plan" in lower or "next-plan" in lower:
            errors.append(f"new next-plan is prohibited: {path}")
        if path.startswith("docs/_reports/") and "review" in lower:
            errors.append(f"new review report is prohibited: {path}")
        if path.startswith("docs/_reports/") and "decision" in lower:
            errors.append(f"new decision report is prohibited: {path}")

    for change in changes:
        if change.status == "D":
            errors.append(f"deleted file is prohibited: {change.path}")
        if change.status == "R":
            errors.append(
                f"moved or renamed file is prohibited: {change.old_path} -> {change.path}"
            )
        if change.path.startswith("docs/_archive/"):
            errors.append(f"archive operation is prohibited: {change.path}")


def validate() -> list[str]:
    """Return all documentation governance validation errors."""

    errors: list[str] = []
    changes = collect_changes()
    validate_required_files(errors)
    validate_allowlist_hardening(errors)
    validate_change_budget(changes, errors)
    validate_prohibited_files(changes, errors)
    return errors


def main() -> int:
    """Run the checker CLI."""

    errors = validate()
    if errors:
        sys.stdout.write(f"FAIL: {len(errors)} documentation governance error(s)\n")
        for error in errors:
            sys.stdout.write(f"- {error}\n")
        return 1
    sys.stdout.write("PASS: documentation governance checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
