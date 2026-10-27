#!/usr/bin/env python3
"""Machine-readable current-state documentation backflow checks.

lifecycle: permanent

This helper extends the existing AI Workflow Gate.  It does not define a new
authority: the mapping only points changed long-lived behavior to the existing
README, capability, milestone, status, and domain current-state documents.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from scripts.ops.helpers.git_change_helpers import Change

from scripts.ops.helpers.pr_authorization_matrix import CATEGORY_WORKFLOW_GOVERNANCE, classify_path

DOCUMENTATION_IMPACT_HEADING = "## Documentation Impact"
VISION_IMPACT_FIELD = "Project vision / target-state changed?"
DOCUMENTATION_IMPACT_FIELDS: tuple[str, ...] = (
    "Capability changed?",
    "Milestone changed?",
    "Canonical entrypoint changed?",
    "Current blocker changed?",
    "Data/model/authorization contract changed?",
    "Repository structure/authority navigation changed?",
    VISION_IMPACT_FIELD,
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
    "vision": VISION_IMPACT_FIELD,
    "source_of_truth": "Source-of-truth docs updated",
}

PATH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "capability",
        (
            "src/api/",
            "src/feature_engine/",
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
        "vision",
        ("docs/PROJECT_VISION.md",),
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
    "vision": ("docs/PROJECT_VISION.md",),
    "contract": ("AGENTS.md", "docs/AGENT_WORKFLOW.md"),
}

# Audited business domains have exact mappings. Other domains and
# cross-domain/workflow changes must not borrow their documents as substitutes.
STAGE_D_CONTRACT_DOC = "docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md"
STAGE_D_CONTRACT_PATHS = frozenset(
    {
        "src/infrastructure/market_evidence/stageDOperations.js",
        "scripts/ops/stage_d_quota_adjudication.js",
        "tests/unit/market_evidence/stage_d_billing_period_rollover.test.js",
        STAGE_D_CONTRACT_DOC,
    }
)
STAGE_D_COMPANION_DOC_PATHS = frozenset(
    {
        "README.md",
        "docs/CAPABILITY_INDEX.md",
        "docs/ACTIVE_MILESTONE.md",
        "docs/PROJECT_STATUS.md",
        "docs/agentic/missions/FP_STAGE_D_MINIMUM_BILLING_PERIOD_ROLLOVER.json",
    }
)

CANONICAL_PREMATCH_CONTRACT_DOC = "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md"
CANONICAL_PREMATCH_CONTRACT_PATHS = frozenset(
    {
        CANONICAL_PREMATCH_CONTRACT_DOC,
        "src/infrastructure/golden_dataset/CanonicalPrematchFeatureQualityDiagnostics.js",
        "scripts/ops/canonical_prematch_feature_frame.js",
        "tests/unit/canonical_prematch_feature_frame.test.js",
        "tests/unit/canonical_prematch_feature_quality_diagnostics.test.js",
    }
)
CANONICAL_PREMATCH_COMPANION_DOC_PATHS = frozenset(
    {
        "README.md",
        "docs/CAPABILITY_INDEX.md",
        "docs/ACTIVE_MILESTONE.md",
        "docs/PROJECT_STATUS.md",
        "docs/agentic/missions/FP_CANONICAL_PREMATCH_FEATURE_QUALITY_DIAGNOSTICS_V1.json",
        "docs/agentic/missions/FP_FEATURE_QUALITY_CRITICAL_SCOPE_BRIDGE.json",
        "docs/agentic/missions/FP_FEATURE_QUALITY_REPACKAGE_BUSINESS.json",
    }
)

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
    if stage_d_paths := changed & STAGE_D_CONTRACT_PATHS:
        classified.setdefault("contract", set()).update(stage_d_paths)
    if canonical_paths := changed & CANONICAL_PREMATCH_CONTRACT_PATHS:
        classified.setdefault("contract", set()).update(canonical_paths)
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
    if (
        category == "contract"
        and changed & STAGE_D_CONTRACT_PATHS
        and not changed - (STAGE_D_CONTRACT_PATHS | STAGE_D_COMPANION_DOC_PATHS)
    ):
        return (STAGE_D_CONTRACT_DOC,)
    if (
        category == "contract"
        and changed & CANONICAL_PREMATCH_CONTRACT_PATHS
        and not changed
        - (CANONICAL_PREMATCH_CONTRACT_PATHS | CANONICAL_PREMATCH_COMPANION_DOC_PATHS)
    ):
        return (CANONICAL_PREMATCH_CONTRACT_DOC,)
    return REQUIRED_DOCS_BY_CATEGORY[category]


def _contract_mapping_errors(changed: set[str]) -> list[str]:
    """Reject unsupported domains and ambiguous business/workflow mixtures."""
    unmapped_paths = {
        path
        for path in changed
        if (
            _matches(path, "docs/data/*_CONTRACT.md")
            and path not in {STAGE_D_CONTRACT_DOC, CANONICAL_PREMATCH_CONTRACT_DOC}
        )
        or (
            (
                path.startswith(("src/", "database/migrations/", "models/", "training/"))
                or (
                    path.startswith("scripts/")
                    and CATEGORY_WORKFLOW_GOVERNANCE not in classify_path(path)
                )
            )
            and path not in STAGE_D_CONTRACT_PATHS
            and path not in CANONICAL_PREMATCH_CONTRACT_PATHS
        )
    }
    if unmapped_paths:
        return [
            "contract paths have no approved domain mapping: " + ", ".join(sorted(unmapped_paths))
        ]
    if changed & CANONICAL_PREMATCH_CONTRACT_PATHS:
        unsupported = changed - (
            CANONICAL_PREMATCH_CONTRACT_PATHS | CANONICAL_PREMATCH_COMPANION_DOC_PATHS
        )
        if unsupported:
            return [
                "contract mapping mixes Canonical prematch with other domains or workflow paths: "
                + ", ".join(sorted(unsupported))
            ]
        if CANONICAL_PREMATCH_CONTRACT_DOC not in changed:
            return [
                f"Canonical prematch contract requires actual update of {CANONICAL_PREMATCH_CONTRACT_DOC}"
            ]
    if changed & STAGE_D_CONTRACT_PATHS:
        unsupported = changed - (STAGE_D_CONTRACT_PATHS | STAGE_D_COMPANION_DOC_PATHS)
        if unsupported:
            return [
                "contract mapping mixes Stage D with workflow or unmapped paths: "
                + ", ".join(sorted(unsupported))
            ]
    elif "contract" not in classify_changed_paths(changed):
        return ["contract changed=yes has no approved domain or workflow mapping"]
    return []


def _canonical_contract_status_errors(
    changed: set[str], changes: Iterable[Change] | None
) -> list[str]:
    """Use Git change facts, never worktree existence, to reject lost authority."""
    if changes is None or not changed & CANONICAL_PREMATCH_CONTRACT_PATHS:
        return []
    for change in changes:
        deleted = change.status == "D" and change.path == CANONICAL_PREMATCH_CONTRACT_DOC
        moved = (
            change.status == "R"
            and change.old_path == CANONICAL_PREMATCH_CONTRACT_DOC
            and change.path != CANONICAL_PREMATCH_CONTRACT_DOC
        )
        if deleted or moved:
            return [
                "Canonical prematch contract cannot be deleted or renamed away as an update: "
                + CANONICAL_PREMATCH_CONTRACT_DOC
            ]
    return []


def check_documentation_backflow(  # noqa: C901, PLR0912
    pr_body: str, changed: set[str], *, changes: Iterable[Change] | None = None
) -> list[str]:
    """Validate declarations and mapped current-state backflow for a PR.

    Ordinary paths are intentionally ignored.  Long-lived capability and state
    paths must declare the impact fields; a concrete reason can explain a
    legitimate bugfix that does not change the declared category.  A positive
    capability/status/entrypoint/milestone/vision declaration cannot be bypassed
    by a generic no-update reason.

    The shared gate supplies its actual Git changes so deletion/rename-away
    cannot satisfy Canonical authority backflow. Path-only callers retain their
    declaration checks, but cannot establish a file's change status.
    """
    classified = classify_changed_paths(changed)
    vision_value = _table_value(pr_body, VISION_IMPACT_FIELD)
    contract_value = _table_value(pr_body, YES_NO_FIELDS["contract"])
    if not classified and _normalise(vision_value) != "yes" and _normalise(contract_value) != "yes":
        return []

    # Actual contract paths must not borrow a workflow mapping via a false declaration.
    errors = _canonical_contract_status_errors(changed, changes)
    errors.extend(
        _contract_mapping_errors(changed)
        if "contract" in classified or _normalise(contract_value) == "yes"
        else []
    )
    if DOCUMENTATION_IMPACT_HEADING not in pr_body:
        return [
            *errors,
            "Documentation Impact is required for long-lived capability/status paths: "
            + ", ".join(sorted(classified)),
        ]

    values = {name: _table_value(pr_body, label) for name, label in YES_NO_FIELDS.items()}
    if CANONICAL_PREMATCH_CONTRACT_DOC in changed and _normalise(values["contract"]) != "yes":
        errors.append("Canonical prematch contract document changes require contract changed=yes")
    missing_fields = [
        label
        for name, label in YES_NO_FIELDS.items()
        if name != "vision" and not _table_value(pr_body, label)
    ]
    if missing_fields:
        errors.append(
            "Documentation Impact is missing machine-readable fields: " + ", ".join(missing_fields)
        )
    if "vision" in classified and not vision_value:
        errors.append(
            f"Documentation Impact is missing machine-readable field: {VISION_IMPACT_FIELD}"
        )

    for name, value in values.items():
        if value and _normalise(value) not in {"yes", "no"}:
            errors.append(f"Documentation Impact field '{YES_NO_FIELDS[name]}' must be yes or no")

    source_updated = _normalise(values["source_of_truth"]) == "yes"
    updated_docs = _table_value(pr_body, "Updated authoritative docs")
    declared_docs = {token.strip("`\"'") for token in re.split(r"[,;\s]+", updated_docs) if token}
    reason = _table_value(pr_body, "If not updated, explicit reason")
    if _normalise(values["contract"]) == "yes":
        classified.setdefault("contract", set())
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
                if required_doc not in changed or required_doc not in declared_docs
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
                "vision",
            )
            if _normalise(values[category]) == "yes"
        )

    if _normalise(values["vision"]) == "yes":
        if not source_updated:
            errors.append(
                "vision changed=yes cannot use no-update reason instead of docs/PROJECT_VISION.md"
            )
        if "docs/PROJECT_VISION.md" not in changed or "docs/PROJECT_VISION.md" not in declared_docs:
            errors.append(
                "vision changed=yes requires docs/PROJECT_VISION.md in the changed and declared docs"
            )

    return errors
