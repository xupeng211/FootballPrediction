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

from dataclasses import dataclass
from pathlib import Path
import subprocess

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


def find_base_ref() -> str:
    """Find a local base ref without network access."""
    for ref in ("origin/main", "main"):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=ROOT_HELPER,
            text=True,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            return ref
    return "HEAD"


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


def collect_changes(base_ref: str | None = None) -> list[Change]:
    """Return all committed + uncommitted changes on the current branch."""

    base = base_ref or find_base_ref()
    diff_out = git_output(["diff", "--name-status", f"{base}...HEAD"])
    status_out = git_output(["status", "--porcelain"])
    return _unique_changes(
        [
            *parse_name_status(diff_out),
            *parse_porcelain(status_out),
        ]
    )


def added_paths(changes: list[Change]) -> set[str]:
    """Return the set of newly-added paths."""
    return {c.path for c in changes if c.status == "A"}


def changed_paths(changes: list[Change]) -> set[str]:
    """Return all changed paths (modified, added, renamed, deleted)."""

    paths = {c.path for c in changes}
    paths.update(c.old_path for c in changes if c.old_path)
    return paths
