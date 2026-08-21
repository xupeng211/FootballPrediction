"""Minimal, provider-neutral STRICT review evidence validation.

lifecycle: permanent

This helper validates only the small PR metadata contract needed to bind one
independent review to the current full PR HEAD.  It does not run a reviewer,
tests, lint, fixes, merge, or maintain review history.
"""

from __future__ import annotations

from datetime import datetime
import re

from scripts.devops.exact_head import ExactHeadError, assert_review_is_current

WORKFLOW_CLASS_NORMAL = "NORMAL"
WORKFLOW_CLASS_STRICT = "STRICT"
ACCEPTED_RESULTS: frozenset[str] = frozenset({"PASS", "FINDINGS_RESOLVED"})
EVIDENCE_HEADING = "## Strict Review Evidence"
MAX_PROVIDER_LENGTH = 128

_TABLE_VALUE_RE_TEMPLATE = r"^\|\s*{label}\s*\|\s*([^|]*?)\s*\|"
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


def _section_text(pr_body: str, heading: str) -> str:
    """Return a section only when exactly one unambiguous match exists."""

    matches = _section_matches(pr_body, heading)
    return matches[0] if len(matches) == 1 else ""


def _table_value(text: str, label: str) -> str:
    """Read a single Markdown table value by exact case-insensitive label."""

    pattern = re.compile(
        _TABLE_VALUE_RE_TEMPLATE.format(label=re.escape(label)),
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip().strip("`").strip() if match else ""


def parse_workflow_class(pr_body: str) -> str | None:
    """Return NORMAL/STRICT from the Scope table, or None when invalid/missing."""

    scope_sections = _section_matches(pr_body, "## Scope")
    if len(scope_sections) != 1:
        return None
    raw = _table_value(scope_sections[0], "Workflow class")
    normalized = raw.upper()
    return normalized if normalized in {WORKFLOW_CLASS_NORMAL, WORKFLOW_CLASS_STRICT} else None


def _valid_timestamp(value: str) -> bool:
    """Require an ISO-8601 timestamp with an explicit timezone."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_strict_review_evidence(  # noqa: C901, PLR0912
    pr_body: str,
    current_pr_head: str | None,
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
    workflow_raw = _table_value(scope_sections[0], "Workflow class")
    workflow_class = workflow_raw.upper()
    if workflow_class == WORKFLOW_CLASS_NORMAL:
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

    values = {
        "version": _table_value(evidence, "Version"),
        "task_type": _table_value(evidence, "Task type"),
        "provider": _table_value(evidence, "Provider"),
        "reviewed_sha": _table_value(evidence, "Reviewed full SHA"),
        "result": _table_value(evidence, "Result").upper(),
        "timestamp": _table_value(evidence, "Timestamp"),
    }
    errors: list[str] = []
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
