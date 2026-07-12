#!/usr/bin/env python3
"""Git change detection helpers — extracted from ai_workflow_gate.py.

lifecycle: permanent

Provides git diff/status parsing to keep the main gate file under 800 lines.

Usage:
  from scripts.ops.helpers.git_change_helpers import (
      Change,
      NAME_STATUS_PATH_PARTS,
      NAME_STATUS_RENAME_PARTS,
      collect_changes,
      added_paths,
      changed_paths,
  )
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT_HELPER = Path(__file__).resolve().parents[3]


# fmt: off
@dataclass(frozen=True)
class Change:
    """A single git change entry."""
    status: str  # A, M, D, R
    path: str
    old_path: str | None = None

NAME_STATUS_PATH_PARTS = 2
NAME_STATUS_RENAME_PARTS = 3
# fmt: on


def git_output(args: list[str], *, check: bool = True) -> str:
    """Run a local Git command, return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT_HELPER,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def _resolve_commit(ref: str | None) -> str | None:
    """Resolve a commit ref, rejecting an unavailable or all-zero ref."""
    if not ref or not ref.strip() or not set(ref.strip()) - {"0"}:
        return None

    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref.strip()}^{{commit}}"],
        cwd=ROOT_HELPER,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def find_base_ref() -> str | None:
    """Find a local base ref without network access."""
    for ref in ("origin/main", "main"):
        if _resolve_commit(ref):
            return ref
    if _resolve_commit("HEAD^"):
        return "HEAD^"
    return None


def resolve_comparison_refs(
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> tuple[str, str]:
    """Resolve explicit or environment-provided base/head commits safely."""
    requested_base = base_ref
    if requested_base is None:
        requested_base = os.environ.get("GITHUB_BASE_SHA")
    if requested_base is None:
        requested_base = os.environ.get("GITHUB_EVENT_BEFORE")
    if requested_base is None:
        requested_base = find_base_ref()

    requested_head = head_ref
    if requested_head is None:
        requested_head = os.environ.get("GITHUB_SHA") or "HEAD"

    resolved_base = _resolve_commit(requested_base)
    resolved_head = _resolve_commit(requested_head)
    if resolved_base is None:
        raise RuntimeError(
            f"incremental baseline unavailable; unable to resolve base revision {requested_base!r}"
        )
    if resolved_head is None:
        raise RuntimeError(
            f"incremental head unavailable; unable to resolve head revision {requested_head!r}"
        )
    return resolved_base, resolved_head


def parse_name_status(output: str) -> list[Change]:
    """Parse 'git diff --name-status' output."""

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
    """Parse 'git status --porcelain' output."""
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


def _unique_changes(changes: list[Change]) -> list[Change]:
    """Deduplicate changes by (status, path, old_path)."""

    seen: dict[tuple[str, str, str | None], Change] = {}
    for c in changes:
        key = (c.status, c.path, c.old_path)
        seen[key] = c
    return list(seen.values())


def collect_changes(
    base_ref: str | None = None,
    head_ref: str | None = None,
    *,
    include_worktree: bool | None = None,
) -> list[Change]:
    """Return all committed + uncommitted changes on the current branch."""

    base, head = resolve_comparison_refs(base_ref, head_ref)
    diff_out = git_output(["diff", "--name-status", "-M", f"{base}...{head}"])
    if include_worktree is None:
        include_worktree = head_ref is None and not os.environ.get("GITHUB_SHA")
    status_out = git_output(["status", "--porcelain"]) if include_worktree else ""
    return _unique_changes(
        [
            *parse_name_status(diff_out),
            *parse_porcelain(status_out),
        ]
    )


@dataclass(frozen=True)
class IncrementalViolation:
    """A normalized finding from one revision."""

    rule: str
    pattern: str
    matched_text: str
    logical_path: str
    display_path: str
    line: int

    @property
    def key(self) -> tuple[str, str, str, str]:
        """Return a line-number-independent identity for the finding."""
        normalized = re.sub(r"\s+", " ", self.matched_text).strip().lower()
        return (self.logical_path, self.rule, self.pattern, normalized)

    def render(self) -> str:
        """Render a concise diagnostic without surrounding file content."""
        snippet = self.matched_text[:80]
        return (
            f"[{self.rule}] {self.display_path}:{self.line}: "
            f"pattern '{self.pattern}' matched '{snippet}'"
        )


@dataclass(frozen=True)
class IncrementalScanSummary:
    """Counts emitted by a base/head incremental scan."""

    base_ref: str
    head_ref: str
    scanned_files: int
    base_violations: int
    head_violations: int
    new_violations: int
    removed_violations: int
    unchanged_historical_violations: int


@dataclass(frozen=True)
class IncrementalScanResult:
    """Detailed result returned by an incremental finding scan."""

    errors: tuple[str, ...]
    summary: IncrementalScanSummary


def _read_revision_file(revision: str, relative_path: str) -> str | None:
    """Read a text file from a Git revision without touching the worktree."""
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=ROOT_HELPER,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _read_worktree_file(relative_path: str) -> str | None:
    """Read an existing local worktree file for explicit local checks."""
    file_path = ROOT_HELPER / relative_path
    if not file_path.is_file():
        return None
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _scan_text_for_patterns(
    text: str,
    *,
    logical_path: str,
    display_path: str,
    pattern_groups: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...],
) -> list[IncrementalViolation]:
    findings: list[IncrementalViolation] = []
    for rule, patterns in pattern_groups:
        for pattern in patterns:
            findings.extend(
                IncrementalViolation(
                    rule=rule,
                    pattern=pattern.pattern,
                    matched_text=match.group(),
                    logical_path=logical_path,
                    display_path=display_path,
                    line=text.count("\n", 0, match.start()) + 1,
                )
                for match in pattern.finditer(text)
            )
    return findings


def scan_incremental_findings(  # noqa: C901
    changes: list[Change],
    *,
    path_predicate: Callable[[str], bool],
    pattern_groups: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...],
    base_ref: str | None = None,
    head_ref: str | None = None,
    error_prefix: str = "new finding",
) -> IncrementalScanResult:
    """Compare normalized findings between base and head revisions."""
    resolved_base, resolved_head = resolve_comparison_refs(base_ref, head_ref)
    use_worktree_head = head_ref is None and not os.environ.get("GITHUB_SHA")
    base_findings: list[IncrementalViolation] = []
    head_findings: list[IncrementalViolation] = []
    scanned_logical_paths: set[str] = set()

    for change in changes:
        old_path = change.old_path if change.status == "R" else None
        if change.status not in {"R", "A"}:
            old_path = change.path
        new_path = None if change.status == "D" else change.path
        if not any(path_predicate(path) for path in (old_path, new_path) if path is not None):
            continue

        logical_path = old_path or new_path
        if logical_path is None:
            continue
        scanned_logical_paths.add(logical_path)

        if old_path is not None and path_predicate(old_path):
            base_text = _read_revision_file(resolved_base, old_path)
            if base_text is not None:
                base_findings.extend(
                    _scan_text_for_patterns(
                        base_text,
                        logical_path=logical_path,
                        display_path=old_path,
                        pattern_groups=pattern_groups,
                    )
                )

        if new_path is not None and path_predicate(new_path):
            head_text = (
                _read_worktree_file(new_path)
                if use_worktree_head
                else _read_revision_file(resolved_head, new_path)
            )
            if head_text is not None:
                head_findings.extend(
                    _scan_text_for_patterns(
                        head_text,
                        logical_path=logical_path,
                        display_path=new_path,
                        pattern_groups=pattern_groups,
                    )
                )

    base_by_key: dict[tuple[str, str, str, str], list[IncrementalViolation]] = defaultdict(list)
    head_by_key: dict[tuple[str, str, str, str], list[IncrementalViolation]] = defaultdict(list)
    for finding in base_findings:
        base_by_key[finding.key].append(finding)
    for finding in head_findings:
        head_by_key[finding.key].append(finding)

    new_findings: list[IncrementalViolation] = []
    removed_count = 0
    unchanged_count = 0
    for key in sorted(set(base_by_key) | set(head_by_key)):
        base_items = base_by_key.get(key, [])
        head_items = head_by_key.get(key, [])
        unchanged = min(len(base_items), len(head_items))
        unchanged_count += unchanged
        removed_count += max(len(base_items) - len(head_items), 0)
        new_findings.extend(head_items[len(base_items) :])

    new_findings.sort(key=lambda finding: (finding.logical_path, finding.line, finding.rule))
    summary = IncrementalScanSummary(
        base_ref=resolved_base,
        head_ref=resolved_head,
        scanned_files=len(scanned_logical_paths),
        base_violations=len(base_findings),
        head_violations=len(head_findings),
        new_violations=len(new_findings),
        removed_violations=removed_count,
        unchanged_historical_violations=unchanged_count,
    )
    return IncrementalScanResult(
        errors=tuple(f"{error_prefix}: {finding.render()}" for finding in new_findings),
        summary=summary,
    )


def added_paths(changes: list[Change]) -> set[str]:
    """Return the set of newly-added paths."""
    return {c.path for c in changes if c.status == "A"}


def changed_paths(changes: list[Change]) -> set[str]:
    """Return all changed paths (modified, added, renamed, deleted)."""

    paths = {c.path for c in changes}
    paths.update(c.old_path for c in changes if c.old_path)
    return paths
