#!/usr/bin/env python3
"""Machine-readable current-state documentation backflow checks.

lifecycle: permanent

This helper extends the existing AI Workflow Gate.  It does not define a new
authority: the mapping only points changed long-lived behavior to the existing
README, capability, milestone, status, and domain current-state documents.
"""

from __future__ import annotations

import re

DOCUMENTATION_IMPACT_HEADING = "## Documentation Impact"
DOCUMENTATION_IMPACT_FIELDS: tuple[str, ...] = (
    "Capability changed?",
    "Milestone changed?",
    "Canonical entrypoint changed?",
    "Current blocker changed?",
    "Data/model/authorization contract changed?",
    "Repository structure/authority navigation changed?",
    "Source-of-truth docs updated",
    "Updated authoritative docs",
    "If not updated, explicit reason",
)

YES_NO_FIELDS: dict[str, str] = {
    "capability": "Capability changed?",
    "milestone": "Milestone changed?",
    "entrypoint": "Canonical entrypoint changed?",
    "blocker": "Current blocker changed?",
    "contract": "Data/model/authorization contract changed?",
    "navigation": "Repository structure/authority navigation changed?",
    "source_of_truth": "Source-of-truth docs updated",
}

PATH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "capability",
        (
            "src/ml/",
            "src/infrastructure/golden_dataset/",
            "src/infrastructure/odds_staging/",
            "src/infrastructure/fotmob/",
            "scripts/model_training/",
            "scripts/ops/odds_staging/",
            "scripts/ops/gd_a01_",
            "scripts/ops/gd_a02_",
            "scripts/ops/gd_a03_",
            "scripts/ops/canonical_prematch_feature_frame",
            "config/model_feature_contracts.json",
            "config/model_artifacts.json",
            "config/canonical_offline_model_evaluation_protocol.json",
            "docs/CAPABILITY_INDEX.md",
            "docs/MODEL_ARTIFACTS.md",
        ),
    ),
    (
        "milestone",
        ("docs/ACTIVE_MILESTONE.md",),
    ),
    (
        "entrypoint",
        (
            "README.md",
            "package.json",
            "Makefile",
        ),
    ),
    (
        "blocker",
        (
            "docs/PROJECT_STATUS.md",
            "docs/data/FOTMOB_CURRENT_STATE.md",
        ),
    ),
    (
        "navigation",
        ("docs/PROJECT_MAP.md",),
    ),
    (
        "contract",
        (
            "AGENTS.md",
            "docs/AGENT_WORKFLOW.md",
            "docs/DOCUMENTATION_GOVERNANCE.md",
            "database/migrations/",
            "docs/data/*_CONTRACT.md",
            "scripts/ops/ai_workflow_gate.py",
            "scripts/ops/helpers/documentation_backflow.py",
        ),
    ),
)

REQUIRED_DOCS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "capability": ("docs/CAPABILITY_INDEX.md",),
    "milestone": ("docs/ACTIVE_MILESTONE.md",),
    "entrypoint": ("README.md", "docs/CAPABILITY_INDEX.md"),
    "blocker": ("docs/PROJECT_STATUS.md",),
    "navigation": ("docs/PROJECT_MAP.md",),
    "contract": ("AGENTS.md", "docs/AGENT_WORKFLOW.md"),
}

HOLLOW_REASON_VALUES = frozenset(
    {
        "",
        "n/a",
        "na",
        "none",
        "null",
        "no",
        "not needed",
        "not applicable",
        "no update needed",
        "no documentation update needed",
        "no documentation impact",
        "无",
        "无需",
        "无需更新",
        "无需更新文档",
        "不需要",
        "不需要更新",
    }
)
MIN_REASON_CHARS = 20


def _matches(path: str, rule: str) -> bool:
    """Match an exact path or a stable prefix/glob rule."""
    if rule.endswith("/"):
        return path.startswith(rule)
    if rule.endswith("*_CONTRACT.md"):
        return path.startswith(rule[: -len("*_CONTRACT.md")]) and path.endswith("_CONTRACT.md")
    return path == rule or path.startswith(rule)


def classify_changed_paths(changed: set[str]) -> dict[str, set[str]]:
    """Return the small, stable backflow categories touched by *changed*."""
    classified: dict[str, set[str]] = {}
    for category, rules in PATH_RULES:
        matches = {path for path in changed if any(_matches(path, rule) for rule in rules)}
        if matches:
            classified[category] = matches
    return classified


def _table_value(pr_body: str, label: str) -> str:
    """Read one exact ``| label | value |`` row from Documentation Impact."""
    section_start = pr_body.find(DOCUMENTATION_IMPACT_HEADING)
    if section_start < 0:
        return ""
    section = pr_body[section_start:]
    next_heading = re.search(r"\n##\s", section[len(DOCUMENTATION_IMPACT_HEADING) :])
    if next_heading:
        section = section[: len(DOCUMENTATION_IMPACT_HEADING) + next_heading.start()]
    match = re.search(
        rf"(?im)^\s*\|\s*{re.escape(label)}\s*\|\s*([^|]*?)\s*\|",
        section,
    )
    if not match:
        return ""
    return match.group(1).strip().strip("`").strip()


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _is_substantive_reason(value: str) -> bool:
    normalized = _normalise(value).strip(".:-")
    return len(normalized) >= MIN_REASON_CHARS and normalized not in HOLLOW_REASON_VALUES


def _required_docs_for(category: str, changed: set[str]) -> tuple[str, ...]:
    """Return current-state docs required by a declared category."""
    if category == "blocker":
        required = list(REQUIRED_DOCS_BY_CATEGORY[category])
        if "docs/data/FOTMOB_CURRENT_STATE.md" in changed:
            required.append("docs/data/FOTMOB_CURRENT_STATE.md")
        return tuple(required)
    if category == "contract" and "AGENTS.md" in changed:
        return ("AGENTS.md", "docs/AGENT_WORKFLOW.md")
    return REQUIRED_DOCS_BY_CATEGORY[category]


def check_documentation_backflow(  # noqa: C901, PLR0912
    pr_body: str, changed: set[str]
) -> list[str]:
    """Validate declarations and mapped current-state backflow for a PR.

    Ordinary paths are intentionally ignored.  Long-lived capability and state
    paths must declare the impact fields; a concrete reason can explain a
    legitimate bugfix that does not change the declared category.  A positive
    capability/status/entrypoint/milestone declaration cannot be bypassed by a
    generic no-update reason.
    """
    classified = classify_changed_paths(changed)
    if not classified:
        return []

    errors: list[str] = []
    if DOCUMENTATION_IMPACT_HEADING not in pr_body:
        return [
            "Documentation Impact is required for long-lived capability/status paths: "
            + ", ".join(sorted(classified))
        ]

    values = {name: _table_value(pr_body, label) for name, label in YES_NO_FIELDS.items()}
    missing_fields = [label for label in YES_NO_FIELDS.values() if not _table_value(pr_body, label)]
    if missing_fields:
        errors.append(
            "Documentation Impact is missing machine-readable fields: " + ", ".join(missing_fields)
        )

    for name, value in values.items():
        if value and _normalise(value) not in {"yes", "no"}:
            errors.append(f"Documentation Impact field '{YES_NO_FIELDS[name]}' must be yes or no")

    source_updated = _normalise(values["source_of_truth"]) == "yes"
    updated_docs = _table_value(pr_body, "Updated authoritative docs")
    reason = _table_value(pr_body, "If not updated, explicit reason")
    if source_updated:
        if not updated_docs or _normalise(updated_docs) in HOLLOW_REASON_VALUES:
            errors.append(
                "Source-of-truth docs updated=yes requires non-empty Updated authoritative docs"
            )
        for category in classified:
            declared = _normalise(values[category])
            if declared == "no":
                if not _is_substantive_reason(reason):
                    errors.append(
                        f"{category} changed=no requires a specific reason for the unchanged current-state doc"
                    )
                continue
            if declared != "yes":
                continue
            errors.extend(
                f"{category} changed=yes requires {required_doc} in the changed and declared docs"
                for required_doc in _required_docs_for(category, changed)
                if required_doc not in changed or required_doc not in updated_docs
            )
    elif not _is_substantive_reason(reason):
        errors.append(
            "Source-of-truth docs updated=no requires a specific, non-hollow "
            "If not updated, explicit reason"
        )
    if not source_updated:
        errors.extend(
            f"{category} changed=yes cannot use no-update reason instead of its mapped current-state doc"
            for category in (
                "capability",
                "milestone",
                "entrypoint",
                "blocker",
                "contract",
                "navigation",
            )
            if _normalise(values[category]) == "yes"
        )

    return errors
