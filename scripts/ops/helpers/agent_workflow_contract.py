#!/usr/bin/env python3
"""Agentic Engineering Workflow V1 的共享机器合同。

lifecycle: permanent
owner: engineering workflow governance

该模块只承载稳定的 workflow policy、PR metadata contract 和 mission scope
分类。它不运行测试、不调用 GitHub、不启动 Codex，也不决定 merge；本地
preflight 与远端 AI Workflow Gate 都通过它读取同一组规则。
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

from scripts.ops.helpers.pr_authorization_matrix import KNOWN_TASK_TYPES, parse_task_type
from scripts.ops.helpers.strict_review_evidence import parse_workflow_class

CONTRACT_SCHEMA_VERSION = "agentic-engineering-workflow/v1"

ROLE_EXECUTION_CONTROLLER = "EXECUTION_CONTROLLER"
ROLE_BUILDER = "BUILDER"
ROLE_INDEPENDENT_REVIEWER = "INDEPENDENT_REVIEWER"
ROLE_CHIEF_ENGINEER = "CHIEF_ENGINEER"

DECISION_AUTO_REMEDIATE = "AUTO_REMEDIATE"
DECISION_ESCALATE = "ESCALATE"

REVIEW_ENGINE_CODEX = "codex"
REVIEW_ROLE_INDEPENDENT = "independent_reviewer"
REVIEW_RESULT_PASS = "PASS"
REVIEW_RESULT_FAIL = "FAIL"
ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW = "engineering_independent_review"
# This workflow deliberately provides engineering/context separation, not a
# cryptographic or hostile-builder-resistant attestation system.  The values
# are exported so local tooling, receipts and tests cannot silently drift.
CRYPTOGRAPHIC_REVIEWER_PROVENANCE_REQUIRED = False
HOSTILE_SAME_UID_FORGE_RESISTANCE = False
BLOCKING_REVIEW_SEVERITIES: tuple[str, ...] = ("P0", "P1", "P2")
ALL_REVIEW_SEVERITIES: tuple[str, ...] = (*BLOCKING_REVIEW_SEVERITIES, "P3")

MISSION_SCOPE_SCHEMA_VERSION = "agentic-mission-scope/v1"
MISSION_SCOPE_REFERENCE_FIELD = "Mission scope contract"
MISSION_ID_REFERENCE_FIELD = "Mission ID"
# The only root a PR-metadata-supplied scope reference may resolve to.  PR text
# selects a contract; it never supplies content and never names an arbitrary
# filesystem path, so this root stays deliberately narrow.
MISSION_SCOPE_ALLOWED_ROOT = "docs/agentic/missions/"
MISSION_SCOPE_FIELDS: tuple[str, ...] = (
    "schema_version",
    "mission_id",
    "task_type",
    "workflow_class",
    "authorized_paths",
    "authorized_prefixes",
    "excluded_paths",
    "excluded_prefixes",
    "excluded_tokens",
    "protected_invariants",
    "forbidden_side_effects",
)
_MISSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

# 这些类别是当前 mission 内修复的边界，不授予越过业务/授权边界的权力。
AUTO_REMEDIATE_CATEGORIES: frozenset[str] = frozenset(
    {
        "compile",
        "syntax",
        "lint",
        "format",
        "test",
        "integration_test",
        "ci",
        "pr_metadata",
        "task_type",
        "workflow_class",
        "documentation_impact",
        "report_lifecycle",
        "script_lifecycle",
        "pr_body_schema",
        "governance_preflight",
        "reviewer_narrow_defect",
        "missing_negative_test",
        "documentation_correction",
    }
)

ESCALATE_CATEGORIES: frozenset[str] = frozenset(
    {
        "mission_scope_expansion",
        "product_requirement",
        "architecture_decision",
        "chief_engineer_gate",
        "protected_invariant",
        "excluded_blocker",
        "provider_request",
        "production_mutation",
        "destructive_action",
        "secret",
        "authorization_uncertainty",
        "quota_semantics",
        "request_accounting_semantics",
        "identity_semantics",
        "transaction_authority_semantics",
        "external_service",
        "security_broader_design",
        "strict_review_weakening",
        "ci_bypass",
        "self_merge",
    }
)

REQUIRED_DOCUMENTATION_IMPACT_FIELDS: tuple[str, ...] = (
    "Capability changed?",
    "Milestone changed?",
    "Canonical entrypoint changed?",
    "Current blocker changed?",
    "Data/model/authorization contract changed?",
    "Repository structure/authority navigation changed?",
    "Project vision / target-state changed?",
    "Source-of-truth docs updated",
    "Updated authoritative docs",
    "If not updated, explicit reason",
)
DOCUMENTATION_IMPACT_BOOLEAN_FIELDS: frozenset[str] = frozenset(
    {
        "capability changed?",
        "milestone changed?",
        "canonical entrypoint changed?",
        "current blocker changed?",
        "data/model/authorization contract changed?",
        "repository structure/authority navigation changed?",
        "project vision / target-state changed?",
        "source-of-truth docs updated",
    }
)
_HOLLOW_VALUES = frozenset(
    {"", "n/a", "na", "none", "not needed", "not applicable", "no", "无", "无需"}
)
TABLE_COLUMN_COUNT = 2
MIN_REASON_CHARS = 12


class MissionScopeError(ValueError):
    """Raised when an explicit mission scope contract is invalid."""


# Fail-closed codes for the PR-metadata → tracked-contract → exact-HEAD chain.
# They are stable machine identifiers: the remote gate reports them verbatim so
# a failure names the precise control that refused, never a generic error.
MISSION_SCOPE_REFERENCE_MISSING = "MISSION_SCOPE_REFERENCE_MISSING"
MISSION_SCOPE_REFERENCE_EMPTY = "MISSION_SCOPE_REFERENCE_EMPTY"
MISSION_SCOPE_REFERENCE_MULTIPLE = "MISSION_SCOPE_REFERENCE_MULTIPLE"
MISSION_SCOPE_REFERENCE_CONFLICTING = "MISSION_SCOPE_REFERENCE_CONFLICTING"
MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH = "MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH"
MISSION_SCOPE_REFERENCE_TRAVERSAL = "MISSION_SCOPE_REFERENCE_TRAVERSAL"
MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT = "MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT"
MISSION_SCOPE_REFERENCE_SYNTAX_INVALID = "MISSION_SCOPE_REFERENCE_SYNTAX_INVALID"
MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE = "MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE"
MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD = "MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD"
MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD = "MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD"
MISSION_SCOPE_SCHEMA_INVALID = "MISSION_SCOPE_SCHEMA_INVALID"
MISSION_SCOPE_MISSION_ID_MISMATCH = "MISSION_SCOPE_MISSION_ID_MISMATCH"
MISSION_SCOPE_TASK_TYPE_MISMATCH = "MISSION_SCOPE_TASK_TYPE_MISMATCH"
MISSION_SCOPE_WORKFLOW_CLASS_MISMATCH = "MISSION_SCOPE_WORKFLOW_CLASS_MISMATCH"
MISSION_SCOPE_PR_METADATA_MISMATCH = "MISSION_SCOPE_PR_METADATA_MISMATCH"


class MissionScopeReferenceError(MissionScopeError):
    """One fail-closed mission-scope reference violation, with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.detail = message


def _normalize_repo_path(value: object, *, field: str) -> str:
    """Normalize one repository-relative path without permitting traversal."""

    if not isinstance(value, str) or not value.strip():
        raise MissionScopeError(f"{field} must contain a non-empty path")
    raw = value.strip().replace("\\", "/")
    if "\x00" in raw:
        raise MissionScopeError(f"{field} contains NUL")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise MissionScopeError(f"{field} must be repository-relative: {value!r}")
    parts: list[str] = []
    for part in re.split(r"/+", raw):
        if part in {"", "."}:
            continue
        if part == "..":
            raise MissionScopeError(f"{field} must not contain '..': {value!r}")
        parts.append(part)
    if not parts:
        raise MissionScopeError(f"{field} must not refer to the repository root")
    return "/".join(parts)


def _normalize_scope_entries(values: object, *, field: str, prefix: bool) -> tuple[str, ...]:
    """Normalize a list of exact paths or directory-boundary prefixes."""

    if not isinstance(values, list):
        raise MissionScopeError(f"{field} must be a JSON array")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized_value = _normalize_repo_path(value, field=field)
        if prefix:
            normalized_value = normalized_value.rstrip("/") + "/"
        elif str(value).strip().replace("\\", "/").endswith("/"):
            raise MissionScopeError(f"{field} exact paths must not end with '/': {value!r}")
        if normalized_value in seen:
            raise MissionScopeError(f"{field} contains duplicate path: {normalized_value}")
        seen.add(normalized_value)
        normalized.append(normalized_value)
    return tuple(sorted(normalized))


def _normalize_tokens(values: object, *, field: str) -> tuple[str, ...]:
    """Normalize explicit path-fragment exclusions while preserving semantics."""

    if not isinstance(values, list):
        raise MissionScopeError(f"{field} must be a JSON array")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise MissionScopeError(f"{field} must contain non-empty strings")
        token = value.strip().casefold()
        if "/" in token or "\\" in token or ".." in token:
            raise MissionScopeError(f"{field} entries must be simple path fragments: {value!r}")
        if token in seen:
            raise MissionScopeError(f"{field} contains duplicate token: {token}")
        seen.add(token)
        normalized.append(token)
    return tuple(sorted(normalized))


def _normalize_text_list(values: object, *, field: str) -> tuple[str, ...]:
    """Normalize required human-auditable invariant/side-effect lists."""

    if not isinstance(values, list) or not values:
        raise MissionScopeError(f"{field} must be a non-empty JSON array")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise MissionScopeError(f"{field} must contain non-empty strings")
        text = re.sub(r"\s+", " ", value.strip())
        if text.casefold() in seen:
            raise MissionScopeError(f"{field} contains duplicate declaration: {text!r}")
        seen.add(text.casefold())
        normalized.append(text)
    return tuple(normalized)


@dataclass(frozen=True)
class MissionScope:
    """One explicit, versioned authorization scope for one bounded mission."""

    schema_version: str
    mission_id: str
    task_type: str
    workflow_class: str
    authorized_paths: tuple[str, ...]
    authorized_prefixes: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    excluded_prefixes: tuple[str, ...]
    excluded_tokens: tuple[str, ...]
    protected_invariants: tuple[str, ...]
    forbidden_side_effects: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> MissionScope:
        """Validate and construct a scope; unknown/missing fields fail closed."""

        expected = set(MISSION_SCOPE_FIELDS)
        actual = set(value)
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        if missing or unknown:
            detail = []
            if missing:
                detail.append("missing=" + ",".join(missing))
            if unknown:
                detail.append("unknown=" + ",".join(unknown))
            raise MissionScopeError("mission scope fields invalid: " + "; ".join(detail))

        schema_version = value["schema_version"]
        if schema_version != MISSION_SCOPE_SCHEMA_VERSION:
            raise MissionScopeError(f"schema_version must be {MISSION_SCOPE_SCHEMA_VERSION!r}")
        mission_id = value["mission_id"]
        if not isinstance(mission_id, str) or not _MISSION_ID_RE.fullmatch(mission_id.strip()):
            raise MissionScopeError("mission_id must be a non-empty safe identifier")
        task_type = value["task_type"]
        if not isinstance(task_type, str) or task_type.strip().lower() not in KNOWN_TASK_TYPES:
            raise MissionScopeError(f"task_type is not a known task type: {task_type!r}")
        workflow_class = value["workflow_class"]
        if workflow_class not in {"NORMAL", "STRICT"}:
            raise MissionScopeError("workflow_class must be NORMAL or STRICT")

        authorized_paths = _normalize_scope_entries(
            value["authorized_paths"], field="authorized_paths", prefix=False
        )
        authorized_prefixes = _normalize_scope_entries(
            value["authorized_prefixes"], field="authorized_prefixes", prefix=True
        )
        excluded_paths = _normalize_scope_entries(
            value["excluded_paths"], field="excluded_paths", prefix=False
        )
        excluded_prefixes = _normalize_scope_entries(
            value["excluded_prefixes"], field="excluded_prefixes", prefix=True
        )
        if not authorized_paths and not authorized_prefixes:
            raise MissionScopeError("authorized_paths and authorized_prefixes cannot both be empty")
        return cls(
            schema_version=MISSION_SCOPE_SCHEMA_VERSION,
            mission_id=mission_id.strip(),
            task_type=task_type.strip().lower(),
            workflow_class=workflow_class,
            authorized_paths=authorized_paths,
            authorized_prefixes=authorized_prefixes,
            excluded_paths=excluded_paths,
            excluded_prefixes=excluded_prefixes,
            excluded_tokens=_normalize_tokens(value["excluded_tokens"], field="excluded_tokens"),
            protected_invariants=_normalize_text_list(
                value["protected_invariants"], field="protected_invariants"
            ),
            forbidden_side_effects=_normalize_text_list(
                value["forbidden_side_effects"], field="forbidden_side_effects"
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Return canonical JSON-compatible scope data."""

        return {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "task_type": self.task_type,
            "workflow_class": self.workflow_class,
            "authorized_paths": list(self.authorized_paths),
            "authorized_prefixes": list(self.authorized_prefixes),
            "excluded_paths": list(self.excluded_paths),
            "excluded_prefixes": list(self.excluded_prefixes),
            "excluded_tokens": list(self.excluded_tokens),
            "protected_invariants": list(self.protected_invariants),
            "forbidden_side_effects": list(self.forbidden_side_effects),
        }


def load_mission_scope_file(
    path: Path, *, repo_root: Path | None = None, expected_mission_id: str | None = None
) -> MissionScope:
    """Load one explicit tracked mission scope; never substitute a default."""

    if path.is_symlink():
        raise MissionScopeError(f"mission scope file must not be a symlink: {path}")
    resolved = path.resolve(strict=False)
    if not resolved.is_file():
        raise MissionScopeError(f"mission scope file must be a regular file: {resolved}")
    if repo_root is not None:
        try:
            resolved.relative_to(repo_root.resolve(strict=False))
        except ValueError as exc:
            raise MissionScopeError("mission scope file must be inside the repository") from exc
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionScopeError(f"mission scope JSON is invalid: {resolved}") from exc
    if not isinstance(payload, dict):
        raise MissionScopeError("mission scope JSON must be an object")
    scope = MissionScope.from_mapping(payload)
    if expected_mission_id is not None and scope.mission_id != expected_mission_id:
        raise MissionScopeError(
            f"mission scope mission_id={scope.mission_id!r} does not match expected {expected_mission_id!r}"
        )
    return scope


def mission_scope_relative_path(path: Path, repo_root: Path) -> str:
    """Return one normalized repository-relative scope path."""

    try:
        relative = path.resolve(strict=False).relative_to(repo_root.resolve(strict=False))
    except ValueError as exc:
        raise MissionScopeError("mission scope file must be inside the repository") from exc
    return _normalize_repo_path(relative.as_posix(), field="mission_scope_file")


def mission_scope_sha256(path: Path) -> str:
    """Hash the scope bytes for exact-head evidence and prompt binding."""

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise MissionScopeError(f"cannot hash mission scope file: {path}") from exc


def classify_failure(category: str, *, in_current_mission: bool = True) -> str:
    """Return the only permitted next action for one failure category.

    Unknown categories and findings outside the current mission escalate. This
    is deliberately conservative so adding a new failure kind cannot create an
    implicit self-remediation permission.
    """

    normalized = category.strip().lower().replace("-", "_")
    if not in_current_mission or normalized in ESCALATE_CATEGORIES:
        return DECISION_ESCALATE
    if normalized in AUTO_REMEDIATE_CATEGORIES:
        return DECISION_AUTO_REMEDIATE
    return DECISION_ESCALATE


def is_blocking_severity(severity: str) -> bool:
    """Return whether an independent-review severity blocks merge."""

    return severity.strip().upper() in BLOCKING_REVIEW_SEVERITIES


def _without_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current: str | None = None
    lines: list[str] = []
    for line in _without_html_comments(text).splitlines():
        match = re.match(r"^[ \t]{0,3}##[ \t]+(.+?)\s*$", line)
        if match:
            if current is not None:
                sections.append((current, "\n".join(lines)))
            current = match.group(1).strip().casefold()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections.append((current, "\n".join(lines)))
    return sections


def _table_rows(section: str) -> tuple[dict[str, list[str]], list[str]]:
    rows: dict[str, list[str]] = {}
    errors: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != TABLE_COLUMN_COUNT:
            if cells and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                errors.append(
                    "AGENT_WORKFLOW_METADATA_INVALID: table rows need exactly two columns."
                )
            continue
        label, value = cells[0], cells[1]
        if label.casefold() == "field" or re.fullmatch(r":?-{3,}:?", label):
            continue
        key = label.casefold()
        rows.setdefault(key, []).append(value.strip().strip("`").strip())
    return rows, errors


def _scope_reference_rows(pr_body: str) -> tuple[dict[str, list[str]], list[str]]:
    """Return Scope-table rows used to bind a PR to its mission contract."""

    section, errors = _one_section(pr_body, "## Scope")
    if section is None:
        return {}, errors
    rows, row_errors = _table_rows(section)
    return rows, [*errors, *row_errors]


def mission_scope_reference_findings(
    pr_body: str, *, mission_scope: MissionScope, scope_path: str
) -> list[tuple[str, str]]:
    """Return (code, message) pairs binding PR metadata to one scope contract.

    This is the single canonical implementation of the PR-metadata ↔ scope
    binding.  Local preflight and the remote PR gate both consume it, so the
    two paths cannot drift into different notions of "the PR names this
    mission".
    """

    rows, errors = _scope_reference_rows(pr_body)
    findings: list[tuple[str, str]] = [
        (MISSION_SCOPE_PR_METADATA_MISMATCH, error) for error in errors
    ]
    path_values = rows.get(MISSION_SCOPE_REFERENCE_FIELD.casefold(), [])
    if len(path_values) != 1:
        findings.append(
            (
                MISSION_SCOPE_PR_METADATA_MISMATCH,
                f"AGENT_WORKFLOW_SCOPE_INVALID: Scope must contain exactly one '{MISSION_SCOPE_REFERENCE_FIELD}' row.",
            )
        )
    elif path_values[0] != scope_path:
        findings.append(
            (
                MISSION_SCOPE_PR_METADATA_MISMATCH,
                f"AGENT_WORKFLOW_SCOPE_INVALID: PR scope reference {path_values[0]!r} does not match {scope_path!r}.",
            )
        )
    mission_values = rows.get(MISSION_ID_REFERENCE_FIELD.casefold(), [])
    if len(mission_values) != 1:
        findings.append(
            (
                MISSION_SCOPE_PR_METADATA_MISMATCH,
                f"AGENT_WORKFLOW_SCOPE_INVALID: Scope must contain exactly one '{MISSION_ID_REFERENCE_FIELD}' row.",
            )
        )
    elif mission_values[0] != mission_scope.mission_id:
        findings.append(
            (
                MISSION_SCOPE_MISSION_ID_MISMATCH,
                f"AGENT_WORKFLOW_SCOPE_INVALID: PR Mission ID {mission_values[0]!r} does not match the scope contract.",
            )
        )
    task_values = rows.get("task type", [])
    if len(task_values) == 1 and task_values[0].strip().lower() != mission_scope.task_type:
        findings.append(
            (
                MISSION_SCOPE_TASK_TYPE_MISMATCH,
                "AGENT_WORKFLOW_SCOPE_INVALID: PR Task type does not match the mission scope contract.",
            )
        )
    workflow_values = rows.get("workflow class", [])
    if (
        len(workflow_values) == 1
        and workflow_values[0].strip().upper() != mission_scope.workflow_class
    ):
        findings.append(
            (
                MISSION_SCOPE_WORKFLOW_CLASS_MISMATCH,
                "AGENT_WORKFLOW_SCOPE_INVALID: PR Workflow class does not match the mission scope contract.",
            )
        )
    return findings


def validate_mission_scope_reference(
    pr_body: str, *, mission_scope: MissionScope, scope_path: str
) -> list[str]:
    """Require PR metadata to name the exact mission-scope contract file."""

    return [
        message
        for _code, message in mission_scope_reference_findings(
            pr_body, mission_scope=mission_scope, scope_path=scope_path
        )
    ]


def _one_section(text: str, heading: str) -> tuple[str | None, list[str]]:
    expected = heading.removeprefix("##").strip().casefold()
    matches = [body for title, body in _sections(text) if title == expected]
    if len(matches) != 1:
        return None, [
            f"AGENT_WORKFLOW_METADATA_INVALID: PR body must contain exactly one '## {expected.title()}' section."
        ]
    return matches[0], []


def _substantive_reason(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value).strip().strip(".:-").casefold()
    return len(normalized) >= MIN_REASON_CHARS and normalized not in _HOLLOW_VALUES


def validate_pr_metadata(  # noqa: C901, PLR0912
    pr_body: str,
    changed_paths: Iterable[str] | None = None,
    *,
    enforce_mission_scope: bool = False,
    mission_scope: MissionScope | None = None,
) -> list[str]:
    """Validate V1 Task type, Workflow class, and Documentation Impact.

    Existing `ai_workflow_gate` remains the authority for the broader PR
    checks. This function owns only the reusable V1 metadata contract. The
    mission scope is opt-in and supplied by the current mission contract, so
    the permanent remote PR gate cannot accidentally block unrelated business
    PRs; local mission preflight and merge-readiness explicitly enable it.
    """

    errors: list[str] = []
    scope, scope_errors = _one_section(pr_body, "## Scope")
    errors.extend(scope_errors)
    if scope is not None:
        rows, row_errors = _table_rows(scope)
        errors.extend(row_errors)
        task_values = rows.get("task type", [])
        if len(task_values) != 1:
            errors.append(
                "AGENT_WORKFLOW_TASK_TYPE_INVALID: Scope must contain exactly one Task type row."
            )
        else:
            declared = task_values[0].strip().lower()
            if declared not in KNOWN_TASK_TYPES:
                errors.append(
                    f"AGENT_WORKFLOW_TASK_TYPE_INVALID: unsupported Task type '{declared}'."
                )
            if parse_task_type(pr_body) != declared:
                errors.append(
                    "AGENT_WORKFLOW_TASK_TYPE_INVALID: Scope Task type must be the single parsed task type."
                )

        workflow_values = rows.get("workflow class", [])
        if len(workflow_values) != 1 or parse_workflow_class(pr_body) is None:
            errors.append(
                "AGENT_WORKFLOW_CLASS_INVALID: Scope must contain exactly one Workflow class of NORMAL or STRICT."
            )

    documentation, documentation_errors = _one_section(pr_body, "## Documentation Impact")
    errors.extend(documentation_errors)
    if documentation is not None:
        rows, row_errors = _table_rows(documentation)
        errors.extend(row_errors)
        for field in REQUIRED_DOCUMENTATION_IMPACT_FIELDS:
            key = field.casefold()
            values = rows.get(key, [])
            if len(values) != 1:
                errors.append(
                    f"AGENT_WORKFLOW_DOCUMENTATION_IMPACT_INVALID: field '{field}' must appear exactly once."
                )
                continue
            value = values[0].strip()
            if key in DOCUMENTATION_IMPACT_BOOLEAN_FIELDS and value.casefold() not in {"yes", "no"}:
                errors.append(
                    f"AGENT_WORKFLOW_DOCUMENTATION_IMPACT_INVALID: field '{field}' must be yes or no."
                )

        source_values = rows.get("source-of-truth docs updated", [])
        updated_values = rows.get("updated authoritative docs", [])
        reason_values = rows.get("if not updated, explicit reason", [])
        if source_values and source_values[0].casefold() == "yes":
            if not updated_values or not _substantive_reason(updated_values[0]):
                errors.append(
                    "AGENT_WORKFLOW_DOCUMENTATION_IMPACT_INVALID: yes requires named authoritative docs."
                )
        elif reason_values and not _substantive_reason(reason_values[0]):
            errors.append(
                "AGENT_WORKFLOW_DOCUMENTATION_IMPACT_INVALID: no requires a concrete no-update reason."
            )

    if enforce_mission_scope:
        errors.extend(validate_mission_scope(changed_paths or (), mission_scope))
    return errors


def _scope_matches(path: str, exact_paths: tuple[str, ...], prefixes: tuple[str, ...]) -> bool:
    """Match exact files and directory prefixes without prefix confusion."""

    return path in exact_paths or any(path.startswith(prefix) for prefix in prefixes)


def validate_mission_scope(
    paths: Iterable[str], mission_scope: MissionScope | None = None
) -> list[str]:
    """Reject changes outside the explicitly supplied bounded mission scope."""

    if not isinstance(mission_scope, MissionScope):
        return [
            "AGENT_WORKFLOW_SCOPE_INVALID: current mission scope contract is required; "
            "missing/UNKNOWN scope never means allow-all."
        ]

    errors: list[str] = []
    normalized_paths: list[tuple[str, str]] = []
    for raw_path in sorted({str(path) for path in paths}):
        try:
            normalized = _normalize_repo_path(raw_path, field="changed path")
        except MissionScopeError as exc:
            errors.append(f"AGENT_WORKFLOW_SCOPE_INVALID: {exc}")
            continue
        normalized_paths.append((raw_path, normalized))

    for raw_path, normalized in normalized_paths:
        if (
            normalized in mission_scope.excluded_paths
            or any(normalized.startswith(prefix) for prefix in mission_scope.excluded_prefixes)
            or any(token in normalized.casefold() for token in mission_scope.excluded_tokens)
        ):
            errors.append(f"AGENT_WORKFLOW_SCOPE_ESCALATE: explicitly excluded path '{raw_path}'.")
            continue
        if _scope_matches(
            normalized, mission_scope.authorized_paths, mission_scope.authorized_prefixes
        ):
            continue
        errors.append(
            f"AGENT_WORKFLOW_SCOPE_ESCALATE: path '{raw_path}' is not authorized by mission "
            f"'{mission_scope.mission_id}'."
        )
    return errors


def contract_summary() -> dict[str, object]:
    """Return stable machine-readable policy metadata for diagnostics/tests."""

    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "review_engine": REVIEW_ENGINE_CODEX,
        "review_role": REVIEW_ROLE_INDEPENDENT,
        "assurance_model": ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW,
        "cryptographic_reviewer_provenance_required": CRYPTOGRAPHIC_REVIEWER_PROVENANCE_REQUIRED,
        "hostile_same_uid_forge_resistance": HOSTILE_SAME_UID_FORGE_RESISTANCE,
        "blocking_review_severities": list(BLOCKING_REVIEW_SEVERITIES),
        "auto_remediate_categories": sorted(AUTO_REMEDIATE_CATEGORIES),
        "escalate_categories": sorted(ESCALATE_CATEGORIES),
        "known_task_types": sorted(KNOWN_TASK_TYPES),
        "mission_scope_schema_version": MISSION_SCOPE_SCHEMA_VERSION,
        "mission_scope_fields": list(MISSION_SCOPE_FIELDS),
        "mission_scope_required_for_scoped_checks": True,
        "mission_scope_allowed_root": MISSION_SCOPE_ALLOWED_ROOT,
        "mission_scope_reference_field": MISSION_SCOPE_REFERENCE_FIELD,
    }
