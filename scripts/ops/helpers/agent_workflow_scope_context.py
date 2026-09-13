#!/usr/bin/env python3
"""Exact-head binding for a mission scope contract.

lifecycle: permanent
owner: engineering workflow governance

Two ways to reach one enforced mission scope:

* an explicitly supplied worktree file (local/controlled calls), whose bytes
  must equal the exact candidate HEAD blob;
* a PR-metadata-supplied reference resolved by the remote PR gate, where the
  contract CONTENT is read from the PR HEAD commit object itself.

Neither path ever substitutes a default, and neither turns a missing or
ambiguous scope into allow-all.  A PR body may only *select* a bounded tracked
contract; it can never supply the authorization bytes.

The module therefore owns both halves of the chain: parsing the untrusted
PR-metadata reference into a safe repository path, and reading that path's
bytes out of the exact HEAD commit.  ``agent_workflow_contract`` keeps the
mission-scope *policy* (schema, codes, ``validate_mission_scope``); this module
keeps the resolution *mechanism*.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

from scripts.devops.exact_head import ExactHeadError, normalize_full_sha
from scripts.ops.helpers.agent_workflow_contract import (
    MISSION_SCOPE_ALLOWED_ROOT,
    MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH,
    MISSION_SCOPE_REFERENCE_CONFLICTING,
    MISSION_SCOPE_REFERENCE_EMPTY,
    MISSION_SCOPE_REFERENCE_FIELD,
    MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD,
    MISSION_SCOPE_REFERENCE_MISSING,
    MISSION_SCOPE_REFERENCE_MULTIPLE,
    MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD,
    MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT,
    MISSION_SCOPE_REFERENCE_SYNTAX_INVALID,
    MISSION_SCOPE_REFERENCE_TRAVERSAL,
    MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE,
    MISSION_SCOPE_SCHEMA_INVALID,
    MissionScope,
    MissionScopeError,
    MissionScopeReferenceError,
    _normalize_repo_path,
    _one_section,
    _table_rows,
    mission_scope_reference_findings,
    mission_scope_relative_path,
    mission_scope_sha256,
    validate_mission_scope_reference,
)

# Only a regular tracked file may carry a mission contract: a symlink or a
# gitlink would let the reference point at bytes outside the reviewed tree.
TRACKED_FILE_MODES: frozenset[str] = frozenset({"100644", "100755"})

# The reference must name <mission-id>.json directly under the one allowed
# root: a nested or non-JSON path would widen the contract surface silently.
_MISSION_SCOPE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$")

# C0 control characters plus DEL: PR text containing them can never be a
# repository path, and letting one through would let a reference smuggle a
# newline or NUL into a Git argument or a log line.
_CONTROL_CHARACTERS = frozenset(chr(code) for code in range(32)) | {"\x7f"}

# Machine-readable evidence lines.  The remote PR gate writes these verbatim, so
# a green run cannot be mistaken for one that never resolved a scope.
REMOTE_SCOPE_LOG_PREFIX = "[AI Workflow Gate] "


@dataclass(frozen=True)
class ExactHeadMissionScope:
    """One mission scope proven to come from an exact commit object."""

    scope: MissionScope
    relative_path: str
    sha256: str
    head_sha: str
    reference: str


# ---------------------------------------------------------------------------
# PR metadata → one safe repository-relative reference
# ---------------------------------------------------------------------------


def validate_mission_scope_reference_path(
    reference: object, *, allowed_root: str = MISSION_SCOPE_ALLOWED_ROOT
) -> str:
    """Return one normalized tracked path for an untrusted scope reference.

    The reference is attacker-influenced PR text.  It may only ever select a
    bounded tracked contract, so absolute paths, traversal, non-repository
    syntax and anything outside *allowed_root* are rejected before the value
    reaches Git or the filesystem.
    """

    if not isinstance(reference, str) or not reference.strip():
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_EMPTY,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must name a non-empty tracked contract",
        )
    raw = reference.strip()
    if any(char in _CONTROL_CHARACTERS for char in raw):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_SYNTAX_INVALID,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must not contain control characters",
        )
    if raw.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must be repository-relative: {raw!r}",
        )
    if "\\" in raw:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_SYNTAX_INVALID,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must use '/' separators: {raw!r}",
        )
    if ".." in raw.split("/"):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_TRAVERSAL,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must not contain '..': {raw!r}",
        )
    normalized = _normalize_repo_path(raw, field=MISSION_SCOPE_REFERENCE_FIELD)
    if not normalized.startswith(allowed_root):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must live under {allowed_root!r}: {normalized!r}",
        )
    basename = normalized[len(allowed_root) :]
    if "/" in basename or not _MISSION_SCOPE_FILENAME_RE.fullmatch(basename):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_SYNTAX_INVALID,
            f"'{MISSION_SCOPE_REFERENCE_FIELD}' must be a single "
            f"<mission-id>.json file under {allowed_root!r}: {normalized!r}",
        )
    return normalized


def mission_scope_reference(pr_body: str) -> str:
    """Return the one tracked mission-scope path this PR metadata selects.

    Exactly one reference is required.  Zero, several, several-with-different
    values, or a Scope table whose rows cannot be parsed all fail closed: an
    ambiguous contract selection must never fall back to "no scope".
    """

    section, section_errors = _one_section(pr_body, "## Scope")
    if section is None:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_MISSING,
            "; ".join(section_errors)
            or f"Scope must contain exactly one '{MISSION_SCOPE_REFERENCE_FIELD}' row.",
        )
    rows, row_errors = _table_rows(section)
    if row_errors:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE, "; ".join(row_errors)
        )
    values = rows.get(MISSION_SCOPE_REFERENCE_FIELD.casefold(), [])
    if not values:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_MISSING,
            f"Scope must contain exactly one '{MISSION_SCOPE_REFERENCE_FIELD}' row.",
        )
    if len(values) > 1:
        code = (
            MISSION_SCOPE_REFERENCE_CONFLICTING
            if len(set(values)) > 1
            else MISSION_SCOPE_REFERENCE_MULTIPLE
        )
        raise MissionScopeReferenceError(
            code,
            f"Scope must contain exactly one '{MISSION_SCOPE_REFERENCE_FIELD}' row; "
            f"found {len(values)}.",
        )
    return validate_mission_scope_reference_path(values[0])


# ---------------------------------------------------------------------------
# Exact commit-object loading
# ---------------------------------------------------------------------------


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run one Git command with argv only — no shell, no PR-controlled syntax."""

    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )


def _mission_scope_blob_sha256(repo_root: Path, relative_path: str, commit_sha: str) -> str:
    """Hash scope bytes from an exact commit rather than a dirty worktree."""

    result = _run_git(repo_root, ["show", f"{commit_sha}:{relative_path}"])
    if result.returncode != 0:
        raise MissionScopeError(
            f"mission scope is not tracked at exact CI HEAD {commit_sha}: {relative_path}"
        )
    return hashlib.sha256(result.stdout).hexdigest()


def _tracked_blob_mode(repo_root: Path, relative_path: str, commit_sha: str) -> str | None:
    """Return the tree entry mode of *relative_path* at *commit_sha*, if any."""

    result = _run_git(repo_root, ["ls-tree", "-z", commit_sha, "--", relative_path])
    if result.returncode != 0:
        return None
    entry = result.stdout.split(b"\x00", 1)[0].decode("utf-8", "surrogateescape").strip()
    if not entry:
        return None
    return entry.split(None, 2)[0]


def load_mission_scope_blob(
    repo_root: Path, commit_sha: str, relative_path: str
) -> tuple[MissionScope, str]:
    """Load and validate a mission scope from one exact commit object.

    Fails closed when the reference is not a regular tracked file at that
    commit, when the JSON cannot be parsed, or when the payload violates the
    canonical mission-scope contract.  The returned bytes are the commit's
    bytes: this is provenance, not an equality check against a checkout that
    GitHub may have produced from a merge ref.
    """

    mode = _tracked_blob_mode(repo_root, relative_path, commit_sha)
    if mode not in TRACKED_FILE_MODES:
        if (repo_root / relative_path).exists():
            raise MissionScopeReferenceError(
                MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD,
                f"{relative_path!r} is not a regular tracked file at {commit_sha} "
                f"(mode={mode or 'absent'})",
            )
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD,
            f"{relative_path!r} does not exist at {commit_sha}",
        )
    blob = _run_git(repo_root, ["show", f"{commit_sha}:{relative_path}"])
    if blob.returncode != 0:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD,
            f"cannot read {relative_path!r} at {commit_sha}",
        )
    try:
        payload = json.loads(blob.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_SCHEMA_INVALID,
            f"mission scope JSON at {commit_sha}:{relative_path} is invalid",
        ) from exc
    if not isinstance(payload, dict):
        raise MissionScopeReferenceError(
            MISSION_SCOPE_SCHEMA_INVALID,
            f"mission scope JSON at {commit_sha}:{relative_path} must be an object",
        )
    scope = MissionScope.from_mapping(payload)
    return scope, hashlib.sha256(blob.stdout).hexdigest()


def resolve_exact_head_mission_scope(
    pr_body: str, *, repo_root: Path, head_sha: str
) -> ExactHeadMissionScope:
    """Resolve THE mission scope for one PR from PR metadata and an exact HEAD.

    Chain: PR body → validated repo-relative reference → exact ``head_sha``
    tree entry → canonical schema validation → PR-metadata binding.  Any break
    raises a coded ``MissionScopeError``; nothing here is advisory.
    """

    try:
        commit_sha = normalize_full_sha(head_sha, role="mission scope exact head")
    except ExactHeadError as exc:
        raise MissionScopeReferenceError(
            MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD,
            "mission scope exact head must be a full 40-hex commit SHA",
        ) from exc
    reference = mission_scope_reference(pr_body)
    scope, digest = load_mission_scope_blob(repo_root, commit_sha, reference)
    findings = mission_scope_reference_findings(pr_body, mission_scope=scope, scope_path=reference)
    if findings:
        code, message = findings[0]
        raise MissionScopeReferenceError(code, message)
    return ExactHeadMissionScope(
        scope=scope,
        relative_path=reference,
        sha256=digest,
        head_sha=commit_sha,
        reference=reference,
    )


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


# ---------------------------------------------------------------------------
# Machine-readable evidence for the remote required PR gate
# ---------------------------------------------------------------------------


def _log(write: Callable[[str], None], line: str) -> None:
    write(f"{REMOTE_SCOPE_LOG_PREFIX}{line}\n")


def resolve_remote_mission_scope(
    pr_body: str, *, repo_root: Path, head_sha: str, write: Callable[[str], None]
) -> ExactHeadMissionScope:
    """Resolve THIS PR's scope from its exact head commit, emitting evidence.

    The remote required-PR-CI path: the PR body selects exactly one tracked
    contract, and the contract bytes come from the ``head_sha`` commit object —
    never from the checkout, which GitHub produces from the merge ref.  Each
    ``REMOTE_SCOPE_*`` line is CI-side proof of what was actually enforced, so a
    green run cannot be confused with one that resolved nothing.
    """

    _log(write, "REMOTE_SCOPE_ENFORCEMENT_ENABLED=YES")
    resolved = resolve_exact_head_mission_scope(pr_body, repo_root=repo_root, head_sha=head_sha)
    scope = resolved.scope
    for line in (
        "REMOTE_SCOPE_REFERENCE_RESOLVED=YES",
        "REMOTE_SCOPE_REFERENCE_SOURCE=pr_body_scope_table",
        f"REMOTE_SCOPE_REFERENCE_PATH={resolved.relative_path}",
        "REMOTE_SCOPE_BOUND_TO_EXACT_HEAD=YES",
        f"REMOTE_SCOPE_EXACT_HEAD_SHA={resolved.head_sha}",
        f"REMOTE_SCOPE_SHA256={resolved.sha256}",
        f"REMOTE_SCOPE_MISSION_ID={scope.mission_id}",
        f"REMOTE_SCOPE_WORKFLOW_CLASS={scope.workflow_class}",
        "REMOTE_SCOPE_SCHEMA_VALID=YES",
        "REMOTE_SCOPE_MISSION_MATCH=YES",
    ):
        _log(write, line)
    return resolved


def emit_remote_scope_refusal(write: Callable[[str], None], error: MissionScopeError) -> None:
    """Report one refused resolution.  Nothing about the PR is trusted here."""

    for line in (
        "REMOTE_SCOPE_REFERENCE_RESOLVED=NO",
        "REMOTE_SCOPE_BOUND_TO_EXACT_HEAD=NO",
        "REMOTE_SCOPE_SCHEMA_VALID=NO",
        "REMOTE_SCOPE_MISSION_MATCH=NO",
        "REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION=FAIL",
    ):
        _log(write, line)
    write("FAIL: mission scope resolution refused — failing closed\n")
    write(f"- AGENT_WORKFLOW_SCOPE_INVALID: {error}\n")


def emit_remote_scope_authorization(write: Callable[[str], None], errors: Iterable[str]) -> None:
    """Report whether every changed path survived the resolved contract."""

    refused = any("AGENT_WORKFLOW_SCOPE" in error for error in errors)
    _log(write, f"REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION={'FAIL' if refused else 'PASS'}")
