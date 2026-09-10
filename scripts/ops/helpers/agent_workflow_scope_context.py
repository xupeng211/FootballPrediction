#!/usr/bin/env python3
"""Optional exact-head binding for an explicitly supplied mission scope."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from scripts.ops.helpers.agent_workflow_contract import (
    MissionScope,
    MissionScopeError,
    mission_scope_relative_path,
    mission_scope_sha256,
    validate_mission_scope_reference,
)


def _mission_scope_blob_sha256(repo_root: Path, relative_path: str, commit_sha: str) -> str:
    """Hash scope bytes from an exact commit rather than a dirty worktree."""

    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{relative_path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise MissionScopeError(
            f"mission scope is not tracked at exact CI HEAD {commit_sha}: {relative_path}"
        )
    return hashlib.sha256(result.stdout).hexdigest()


def validate_mission_scope_context(
    pr_body: str,
    scope_file: Path,
    scope: MissionScope,
    *,
    repo_root: Path,
    resolved_head: str,
    skip_body_checks: bool,
) -> list[str]:
    """Bind an explicitly enabled scope to CI HEAD and PR metadata."""

    try:
        relative_path = mission_scope_relative_path(scope_file, repo_root)
        if mission_scope_sha256(scope_file) != _mission_scope_blob_sha256(
            repo_root, relative_path, resolved_head
        ):
            return ["AGENT_WORKFLOW_SCOPE_INVALID: mission scope bytes differ from exact CI HEAD"]
        if skip_body_checks:
            return []
        return validate_mission_scope_reference(
            pr_body, mission_scope=scope, scope_path=relative_path
        )
    except (MissionScopeError, OSError) as exc:
        return [f"AGENT_WORKFLOW_SCOPE_INVALID: {exc}"]
