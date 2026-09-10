#!/usr/bin/env python3
"""Agentic Engineering Workflow V1 的共享机器合同。

lifecycle: permanent
owner: engineering workflow governance

该模块只承载稳定的 workflow policy、PR metadata contract 和 mission scope
分类。它不运行测试、不调用 GitHub、不启动 Codex，也不决定 merge；本地
preflight 与远端 AI Workflow Gate 都通过它读取同一组规则。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

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
BLOCKING_REVIEW_SEVERITIES: tuple[str, ...] = ("P0", "P1", "P2")
ALL_REVIEW_SEVERITIES: tuple[str, ...] = (*BLOCKING_REVIEW_SEVERITIES, "P3")

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

# 当前任务只允许修改 workflow/governance surface。显式 allowlist 让 scope
# 判断 fail-closed，并把 Stage D / PR #1903 业务路径留在任务外。
MISSION_ALLOWED_PREFIXES: tuple[str, ...] = (
    ".github/",
    "docs/",
    "schemas/agentic/",
    "scripts/ci/",
    "scripts/devops/",
    "scripts/ops/helpers/",
    "tests/",
)
MISSION_ALLOWED_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CLAUDE.md",
        "Makefile",
        ".github/pull_request_template.md",
        "scripts/ops/ai_workflow_gate.py",
    }
)
MISSION_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "database/",
    "src/",
    "models/",
    "training/",
    "data/",
    "scripts/ops/stage_d",
    "scripts/ops/the_odds_api",
    "scripts/ops/odds_api",
    "docs/data/",
    "tests/unit/market_evidence/",
    "scripts/ops/helpers/db_write_guard",
    "scripts/ops/helpers/python_db_write_guard",
    "scripts/ops/helpers/python_db_write_enforcement_check",
    "scripts/ops/helpers/sql_migration_policy_enforcement_check",
    "scripts/ops/helpers/dbBlueprint.js",
)
MISSION_EXCLUDED_TOKENS: tuple[str, ...] = (
    "blocker_1",
    "blocker_2",
    "blocker_3",
    "pr1903",
    "stage-d-business",
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
) -> list[str]:
    """Validate V1 Task type, Workflow class, and Documentation Impact.

    Existing `ai_workflow_gate` remains the authority for the broader PR
    checks. This function owns only the reusable V1 metadata contract. The
    mission-specific path allowlist is opt-in so the permanent remote PR gate
    cannot accidentally block unrelated business PRs; local mission preflight
    and merge-readiness explicitly enable it.
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
        errors.extend(validate_mission_scope(changed_paths or ()))
    return errors


def validate_mission_scope(paths: Iterable[str]) -> list[str]:
    """Reject changes outside this bounded workflow-infrastructure mission."""

    errors: list[str] = []
    for raw_path in sorted({str(path).replace("\\", "/") for path in paths}):
        if any(token in raw_path.casefold() for token in MISSION_EXCLUDED_TOKENS):
            errors.append(
                f"AGENT_WORKFLOW_SCOPE_ESCALATE: excluded blocker/Stage D token in path '{raw_path}'."
            )
            continue
        if any(raw_path.startswith(prefix) for prefix in MISSION_EXCLUDED_PREFIXES):
            errors.append(
                f"AGENT_WORKFLOW_SCOPE_ESCALATE: protected business/runtime path '{raw_path}' is outside this mission."
            )
            continue
        if raw_path in MISSION_ALLOWED_FILES or any(
            raw_path.startswith(prefix) for prefix in MISSION_ALLOWED_PREFIXES
        ):
            continue
        errors.append(
            f"AGENT_WORKFLOW_SCOPE_ESCALATE: path '{raw_path}' is not an allowed workflow-infrastructure path."
        )
    return errors


def contract_summary() -> dict[str, object]:
    """Return stable machine-readable policy metadata for diagnostics/tests."""

    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "review_engine": REVIEW_ENGINE_CODEX,
        "review_role": REVIEW_ROLE_INDEPENDENT,
        "blocking_review_severities": list(BLOCKING_REVIEW_SEVERITIES),
        "auto_remediate_categories": sorted(AUTO_REMEDIATE_CATEGORIES),
        "escalate_categories": sorted(ESCALATE_CATEGORIES),
        "known_task_types": sorted(KNOWN_TASK_TYPES),
        "mission_allowed_prefixes": list(MISSION_ALLOWED_PREFIXES),
    }
