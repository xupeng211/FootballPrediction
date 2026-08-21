"""Minimal, provider-neutral STRICT review evidence validation.

lifecycle: permanent

This helper validates only the small PR metadata contract needed to bind one
independent review to the current full PR HEAD.  It does not run a reviewer,
tests, lint, fixes, merge, or maintain review history.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

from scripts.devops.exact_head import ExactHeadError, assert_review_is_current
from scripts.ops.helpers.pr_authorization_matrix import (
    CATEGORY_DATA_ARTIFACT,
    CATEGORY_DB_MIGRATION_SQL,
    CATEGORY_DOCKER_DEPLOY,
    CATEGORY_ENV_SECRET,
    CATEGORY_MODEL_ARTIFACT,
    CATEGORY_RUNTIME_CONFIG,
    CATEGORY_SC002_DB_GOVERNANCE,
    CATEGORY_UNKNOWN,
    CATEGORY_WORKFLOW_GOVERNANCE,
    TASK_TYPE_CONFIG_RUNTIME,
    TASK_TYPE_DATA_ARTIFACT,
    TASK_TYPE_DB_MIGRATION_SQL,
    TASK_TYPE_DOCKER_DEPLOY,
    TASK_TYPE_MIXED,
    TASK_TYPE_MODEL_ARTIFACT,
    TASK_TYPE_SC002_DB_GOVERNANCE,
    TASK_TYPE_WORKFLOW_GOVERNANCE,
    classify_paths,
)

WORKFLOW_CLASS_NORMAL = "NORMAL"
WORKFLOW_CLASS_STRICT = "STRICT"
ACCEPTED_RESULTS: frozenset[str] = frozenset({"PASS", "FINDINGS_RESOLVED"})
EVIDENCE_HEADING = "## Strict Review Evidence"
MAX_PROVIDER_LENGTH = 128
_TABLE_COLUMN_COUNT = 2
_EVIDENCE_FIELDS = frozenset(
    {"Version", "Task type", "Provider", "Reviewed full SHA", "Result", "Timestamp"}
)
_STRICT_REVIEW_TASK_TYPES = frozenset(
    {
        TASK_TYPE_CONFIG_RUNTIME,
        TASK_TYPE_DATA_ARTIFACT,
        TASK_TYPE_DB_MIGRATION_SQL,
        TASK_TYPE_DOCKER_DEPLOY,
        TASK_TYPE_MIXED,
        TASK_TYPE_MODEL_ARTIFACT,
        TASK_TYPE_SC002_DB_GOVERNANCE,
        TASK_TYPE_WORKFLOW_GOVERNANCE,
    }
)
_STRICT_REVIEW_CATEGORIES = frozenset(
    {
        CATEGORY_DATA_ARTIFACT,
        CATEGORY_DB_MIGRATION_SQL,
        CATEGORY_DOCKER_DEPLOY,
        CATEGORY_ENV_SECRET,
        CATEGORY_MODEL_ARTIFACT,
        CATEGORY_RUNTIME_CONFIG,
        CATEGORY_SC002_DB_GOVERNANCE,
        CATEGORY_UNKNOWN,
        CATEGORY_WORKFLOW_GOVERNANCE,
    }
)
_STRICT_REVIEW_PATH_PREFIXES = (
    "scripts/capture_auth",
    "scripts/model_training/",
    "src/api/model_management.py",
    "src/api/predictions/",
    "src/api/",
    "src/config/",
    "src/core/",
    "src/core/database/",
    "src/core/harvesters/",
    "src/data/",
    "src/database/",
    "src/feature_engine/",
    "src/infrastructure/auth/",
    "src/infrastructure/database/",
    "src/infrastructure/harvesters/",
    "src/infrastructure/recon/",
    "src/infrastructure/services/",
    "src/infrastructure/services/migrations/",
    "src/ml/",
    "src/parsers/",
    "src/schemas/",
    "src/services/",
    "src/strategy/",
)
_STRICT_REVIEW_SCRIPT_TOKENS = frozenset(
    {"harvest", "ingest", "migration", "predict", "raw", "train", "write"}
)

_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^[ \t]{0,3}##[ \t]+(.+?)\s*$")


def _without_html_comments(text: str) -> str:
    """Ignore commented template examples when parsing PR metadata."""

    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _normalize_heading(heading: str) -> str:
    """Normalize an ATX heading name for exact section matching."""

    return re.sub(r"[ \t]+#+[ \t]*$", "", heading.strip()).casefold()


def _sections(pr_body: str) -> list[tuple[str, str]]:
    """Parse real top-level ``##`` sections, excluding fenced code blocks."""

    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    fence: str | None = None

    for line in _without_html_comments(pr_body).splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence is not None:
            if (
                fence_match
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= len(fence)
            ):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = _normalize_heading(heading_match.group(1))
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_lines)))
    return sections


def _section_matches(pr_body: str, heading: str) -> list[str]:
    """Return every exact top-level section matching *heading*."""

    expected = _normalize_heading(heading.removeprefix("##"))
    return [body for title, body in _sections(pr_body) if title == expected]


def _table_values(text: str, label: str) -> tuple[list[str], bool]:
    """Return all exact table values and whether a matching row is malformed."""

    values: list[str] = []
    malformed = False
    expected = label.casefold()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0].casefold() != expected:
            continue
        if len(cells) != _TABLE_COLUMN_COUNT:
            malformed = True
            continue
        values.append(cells[1].strip().strip("`").strip())
    return values, malformed


def _evidence_table_errors(text: str) -> list[str]:
    """Reject duplicate, unknown, or multi-column evidence rows."""

    counts: dict[str, int] = {}
    errors: list[str] = []
    labels = {label.casefold() for label in _EVIDENCE_FIELDS}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if len(cells) == _TABLE_COLUMN_COUNT and cells[0].casefold() == "field":
            continue
        if len(cells) != _TABLE_COLUMN_COUNT:
            errors.append(
                "STRICT_REVIEW_INVALID: evidence table rows must have exactly two columns."
            )
            continue
        label = cells[0].casefold()
        if label not in labels:
            errors.append(f"STRICT_REVIEW_INVALID: unsupported evidence field '{cells[0]}'.")
            continue
        counts[label] = counts.get(label, 0) + 1

    for label in _EVIDENCE_FIELDS:
        count = counts.get(label.casefold(), 0)
        if count > 1:
            errors.append(f"STRICT_REVIEW_INVALID: evidence field '{label}' must appear once.")
    return errors


def _strict_classification_reasons(
    changed_paths: Iterable[str] | None,
    task_type: str | None,
) -> list[str]:
    """Return reasons a PR cannot waive STRICT review by declaring NORMAL."""

    paths = tuple(changed_paths or ())
    normalized_task = (task_type or "").strip().lower()
    reasons: list[str] = []
    if normalized_task in _STRICT_REVIEW_TASK_TYPES:
        reasons.append(f"task type '{normalized_task}'")

    categories = classify_paths(paths)
    category_hits = sorted(set(categories) & _STRICT_REVIEW_CATEGORIES)
    if category_hits:
        reasons.append("path categories " + ", ".join(category_hits))

    for path in paths:
        normalized_path = path.replace("\\", "/")
        basename = normalized_path.rsplit("/", 1)[-1].casefold()
        if normalized_path.startswith(_STRICT_REVIEW_PATH_PREFIXES) or (
            normalized_path.startswith("scripts/ops/")
            and any(token in basename for token in _STRICT_REVIEW_SCRIPT_TOKENS)
        ):
            reasons.append(f"high-risk path '{path}'")
    return reasons


def parse_workflow_class(pr_body: str) -> str | None:
    """Return NORMAL/STRICT from the Scope table, or None when invalid/missing."""

    scope_sections = _section_matches(pr_body, "## Scope")
    if len(scope_sections) != 1:
        return None
    values, malformed = _table_values(scope_sections[0], "Workflow class")
    if malformed or len(values) != 1:
        return None
    raw = values[0]
    normalized = raw.upper()
    return normalized if normalized in {WORKFLOW_CLASS_NORMAL, WORKFLOW_CLASS_STRICT} else None


def _valid_timestamp(value: str) -> bool:
    """Require an ISO-8601 timestamp with an explicit timezone."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_strict_review_evidence(  # noqa: C901, PLR0911, PLR0912
    pr_body: str,
    current_pr_head: str | None,
    *,
    changed_paths: Iterable[str] | None = None,
    task_type: str | None = None,
) -> list[str]:
    """Validate the STRICT review contract against one current full SHA.

    NORMAL PRs intentionally return no evidence error.  STRICT PRs fail closed
    when the classification, evidence section, fields, result, timestamp, or
    exact reviewed HEAD is absent or malformed.
    """

    scope_sections = _section_matches(pr_body, "## Scope")
    if len(scope_sections) != 1:
        return [
            "STRICT_REVIEW_CLASSIFICATION_INVALID: PR body must contain exactly one "
            "top-level Scope section."
        ]
    workflow_values, workflow_malformed = _table_values(scope_sections[0], "Workflow class")
    if workflow_malformed or len(workflow_values) != 1:
        return [
            "STRICT_REVIEW_CLASSIFICATION_INVALID: Scope must contain exactly one valid "
            "Workflow class row."
        ]
    workflow_raw = workflow_values[0]
    workflow_class = workflow_raw.upper()
    classification_reasons = _strict_classification_reasons(changed_paths, task_type)
    if workflow_class == WORKFLOW_CLASS_NORMAL:
        if classification_reasons:
            return [
                "STRICT_REVIEW_CLASSIFICATION_REQUIRED: changed paths/task type require "
                "STRICT review; NORMAL cannot waive exact-head evidence ("
                + "; ".join(classification_reasons)
                + ")."
            ]
        return []
    if workflow_class != WORKFLOW_CLASS_STRICT:
        return [
            "STRICT_REVIEW_CLASSIFICATION_INVALID: Scope must declare "
            "Workflow class as NORMAL or STRICT."
        ]

    evidence_sections = _section_matches(pr_body, EVIDENCE_HEADING)
    if not evidence_sections:
        return ["STRICT_REVIEW_MISSING: STRICT PR requires one Strict Review Evidence section."]
    if len(evidence_sections) != 1:
        return [
            "STRICT_REVIEW_INVALID: PR body must contain exactly one top-level "
            "Strict Review Evidence section."
        ]
    evidence = evidence_sections[0]

    values = dict.fromkeys(
        ("version", "task_type", "provider", "reviewed_sha", "result", "timestamp"), ""
    )
    errors: list[str] = []
    errors.extend(_evidence_table_errors(evidence))
    for label, key in (
        ("Version", "version"),
        ("Task type", "task_type"),
        ("Provider", "provider"),
        ("Reviewed full SHA", "reviewed_sha"),
        ("Result", "result"),
        ("Timestamp", "timestamp"),
    ):
        field_values, malformed = _table_values(evidence, label)
        if malformed or len(field_values) != 1:
            values[key] = ""
        elif field_values:
            values[key] = field_values[0].upper() if key == "result" else field_values[0]
    if values["version"] != "1":
        errors.append("STRICT_REVIEW_INVALID: evidence Version must be 1.")
    if values["task_type"].upper() != WORKFLOW_CLASS_STRICT:
        errors.append("STRICT_REVIEW_INVALID: evidence Task type must be STRICT.")
    if not values["provider"] or len(values["provider"]) > MAX_PROVIDER_LENGTH:
        errors.append("STRICT_REVIEW_INVALID: evidence Provider is required.")
    if values["result"] not in ACCEPTED_RESULTS:
        errors.append("STRICT_REVIEW_INVALID: evidence Result must be PASS or FINDINGS_RESOLVED.")
    if not _valid_timestamp(values["timestamp"]):
        errors.append("STRICT_REVIEW_INVALID: evidence Timestamp must be ISO-8601 with timezone.")

    if not values["reviewed_sha"]:
        errors.append("STRICT_REVIEW_MISSING: evidence Reviewed full SHA is required.")
    else:
        try:
            assert_review_is_current(values["reviewed_sha"], current_pr_head)
        except ExactHeadError as exc:
            errors.append(f"STRICT_REVIEW_STALE: {exc}")

    return errors
