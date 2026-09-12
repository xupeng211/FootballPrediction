"""Synthetic repositories and PR bodies for remote mission-scope tests.

lifecycle: test-fixture
owner: engineering workflow governance

The remote per-mission scope chain reads a contract out of an exact commit
object, so its tests need repositories with controlled commit histories rather
than one shared checkout.  Everything here is deliberately tiny and synthetic:
no test touches the real repository's HEAD, index or worktree.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.ops.helpers import agent_workflow_scope_context as scope_context
from scripts.ops.helpers.agent_workflow_contract import (
    MissionScope,
    MissionScopeError,
    MissionScopeReferenceError,
)
from tests.helpers.agentic_workflow_fixtures import (
    MISSION_ID,
    MISSION_SCOPE_PATH,
    mission_scope_payload,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "production-gate.yml"

SHA256_HEX_LENGTH = 64

DRIFT_SCOPE = "docs/agentic/missions/drift.json"
DELETED_SCOPE = "docs/agentic/missions/deleted.json"
OTHER_SCOPE = "docs/agentic/missions/other.json"
MALFORMED_SCOPE = "docs/agentic/missions/malformed.json"
BAD_SCHEMA_SCOPE = "docs/agentic/missions/bad_schema.json"
SYMLINK_SCOPE = "docs/agentic/missions/link.json"
UNTRACKED_SCOPE = "docs/agentic/missions/untracked.json"
OUTSIDE_ROOT = "not-a-scope.json"
UNAUTHORIZED_PATH = "scripts/unauthorized_change.py"


# ---------------------------------------------------------------------------
# Synthetic repositories
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _scope_document(mission_id: str, authorized: list[str]) -> str:
    payload = mission_scope_payload(mission_id=mission_id)
    payload["authorized_paths"] = authorized
    return json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"


def _scope(**overrides: object) -> MissionScope:
    payload = mission_scope_payload()
    payload.update(overrides)
    return MissionScope.from_mapping(payload)


class Repo:
    """One synthetic repository plus the commits its tests bind to."""

    def __init__(self, path: Path, **commits: str) -> None:
        self.path = path
        self.__dict__.update(commits)

    def path_of(self, relative: str) -> Path:
        return self.path / relative


def _write_unauthorized(repo: Path) -> None:
    target = repo / UNAUTHORIZED_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# outside every scope here\n", encoding="utf-8")


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Remote Scope Test")


def make_gate_repo(tmp_path: Path) -> Repo:
    """Minimal repo whose head changes only an authorized path."""

    repo = tmp_path / "gate-repo"
    _init_repo(repo)
    scope_path = repo / MISSION_SCOPE_PATH
    scope_path.parent.mkdir(parents=True)
    (repo / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    scope_path.write_text(_scope_document(MISSION_ID, ["Makefile"]), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")

    (repo / "Makefile").write_text("all:\n\t@echo workflow\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")

    _write_unauthorized(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "unauthorized")
    head_bad = _git(repo, "rev-parse", "HEAD")
    return Repo(repo, base=base, head=head, head_bad=head_bad)


def make_scope_repo(tmp_path: Path) -> Repo:
    """Repository holding every tracked-scope fixture the path tests need."""

    repo = tmp_path / "scope-repo"
    _init_repo(repo)
    (repo / "docs" / "agentic" / "missions").mkdir(parents=True)
    (repo / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (repo / MISSION_SCOPE_PATH).write_text(
        _scope_document(MISSION_ID, ["Makefile"]), encoding="utf-8"
    )
    # Base and head disagree about what this contract authorizes.
    (repo / DRIFT_SCOPE).write_text(
        _scope_document("DRIFT_MISSION", ["Makefile"]), encoding="utf-8"
    )
    (repo / OTHER_SCOPE).write_text(
        _scope_document("OTHER_MISSION", [UNAUTHORIZED_PATH]), encoding="utf-8"
    )
    (repo / MALFORMED_SCOPE).write_text("{not json at all\n", encoding="utf-8")
    (repo / BAD_SCHEMA_SCOPE).write_text(
        _scope_document("BAD_SCHEMA_MISSION", ["Makefile"]).replace(
            "agentic-mission-scope/v1", "agentic-mission-scope/v9"
        ),
        encoding="utf-8",
    )
    (repo / SYMLINK_SCOPE).symlink_to("current.json")
    (repo / DELETED_SCOPE).write_text(
        _scope_document("DELETED_MISSION", ["Makefile"]), encoding="utf-8"
    )
    (repo / OUTSIDE_ROOT).write_text(
        _scope_document("OUTSIDE_ROOT_MISSION", ["Makefile"]), encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")

    (repo / DRIFT_SCOPE).write_text(
        _scope_document("DRIFT_MISSION", ["Makefile", "scripts/ops/ai_workflow_gate.py"]),
        encoding="utf-8",
    )
    (repo / DELETED_SCOPE).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")
    # Worktree-only file: tracked at no commit at all.
    (repo / UNTRACKED_SCOPE).write_text(
        _scope_document("UNTRACKED_MISSION", ["Makefile"]), encoding="utf-8"
    )
    return Repo(repo, base=base, head=head)


# ---------------------------------------------------------------------------
# PR bodies
# ---------------------------------------------------------------------------


def _scope_row(value: str, mission_id: str = MISSION_ID) -> str:
    return f"| Mission scope contract | `{value}` |\n| Mission ID | {mission_id} |"


def _minimal_body(reference: str, *, mission_id: str = MISSION_ID, rows: int = 1) -> str:
    row = _scope_row(reference, mission_id)
    extra = "\n".join(row for _ in range(rows))
    return f"""## Summary

Bounded workflow governance change.

## Scope

| Field | Value |
| --- | --- |
| Task type | workflow-governance |
| Workflow class | STRICT |
{extra}

## Tests

pytest.

## Risk

None.

## Rollback

Revert.
"""


_USE_HEAD = object()


def _resolve(repo: Repo, body: str, *, head_sha: object = _USE_HEAD):
    return scope_context.resolve_exact_head_mission_scope(
        body,
        repo_root=repo.path,
        head_sha=repo.head if head_sha is _USE_HEAD else head_sha,  # type: ignore[arg-type]
    )


def _code(exc_info: pytest.ExceptionInfo[MissionScopeError]) -> str:
    assert isinstance(exc_info.value, MissionScopeReferenceError), exc_info.value
    return exc_info.value.code


def _assert_error(errors: list[str], fragment: str) -> None:
    """Assert the first gate error carries *fragment* (repository convention)."""

    assert errors
    assert fragment in errors[0]
