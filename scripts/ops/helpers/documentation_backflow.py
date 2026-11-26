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
    from collections import Counter
    from collections.abc import Iterable

    from scripts.ops.helpers.agent_workflow_contract import MissionScope
    from scripts.ops.helpers.git_change_helpers import Change

from scripts.devops.exact_head import is_full_sha
from scripts.devops.fotmob_markdown import visible_documents
from scripts.ops.helpers.agent_workflow_contract import validate_mission_scope_reference
from scripts.ops.helpers.git_change_helpers import changed_paths, collect_changes, git_output
from scripts.ops.helpers.pr_authorization_matrix import (
    CATEGORY_WORKFLOW_GOVERNANCE,
    classify_path,
    parse_task_type,
)
from scripts.ops.helpers.strict_review_evidence import parse_workflow_class

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

STAGE_D_FORWARD_MISSION = "FP_STAGE_D_FORWARD_ACCOUNTING_OFFLINE"
STAGE_D_FORWARD_SCOPE = f"docs/agentic/missions/{STAGE_D_FORWARD_MISSION}.json"
STAGE_D_FORWARD_AUTHORITY_DOCS = frozenset(
    {
        STAGE_D_CONTRACT_DOC,
        "README.md",
        "docs/CAPABILITY_INDEX.md",
        "docs/ACTIVE_MILESTONE.md",
        "docs/PROJECT_STATUS.md",
    }
)
STAGE_D_FORWARD_CYCLE = "scripts/ops/stage_d_cycle.js"
STAGE_D_FORWARD_MISSION_PATHS = frozenset(
    {
        STAGE_D_FORWARD_SCOPE,
        STAGE_D_FORWARD_CYCLE,
        "src/infrastructure/market_evidence/stageDForwardAccounting.js",
        "tests/unit/market_evidence/stage_d_forward_accounting.test.js",
    }
)
STAGE_D_FORWARD_PATHS = STAGE_D_FORWARD_AUTHORITY_DOCS | STAGE_D_FORWARD_MISSION_PATHS
STAGE_D_RUNTIME_MISSION = "FP_STAGE_D_FORWARD_ACCOUNTING_RUNTIME"
STAGE_D_RUNTIME_PATHS = STAGE_D_FORWARD_AUTHORITY_DOCS | {
    f"docs/agentic/missions/{STAGE_D_RUNTIME_MISSION}.json",
    "scripts/ops/stage_d_controlled_initialization.js",
    "src/infrastructure/market_evidence/stageDOperations.js",
    "src/infrastructure/market_evidence/stageDForwardAccounting.js",
    "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
    "tests/unit/market_evidence/stage_d_forward_accounting.test.js",
}
STAGE_D_FORWARD_MAPPINGS = {
    STAGE_D_FORWARD_MISSION: STAGE_D_FORWARD_PATHS,
    STAGE_D_RUNTIME_MISSION: STAGE_D_RUNTIME_PATHS,
}

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

# 新试点身份只伴随这四条精确路径；不放开其他 mission 或扩大既有领域组合。
PERCENT_PILOT_MISSION_PATH = "docs/agentic/missions/FP_QUALITY_MARKDOWN_PERCENT_20261105.json"
PERCENT_PILOT_PATHS = frozenset(
    {
        PERCENT_PILOT_MISSION_PATH,
        CANONICAL_PREMATCH_CONTRACT_DOC,
        "src/infrastructure/golden_dataset/CanonicalPrematchFeatureQualityDiagnostics.js",
        "tests/unit/canonical_prematch_feature_quality_diagnostics.test.js",
    }
)

# 本业务任务只能使用实际验收的十一条路径。scope 自填列表不能扩展映射。
FOTMOB_FINAL_RESULT_MISSION = "FP_FOTMOB_FINAL_RESULT_ASOF_OFFLINE"
FOTMOB_FINAL_RESULT_SCOPE = f"docs/agentic/missions/{FOTMOB_FINAL_RESULT_MISSION}.json"
FOTMOB_FINAL_RESULT_CONTRACT_DOCS = (
    "docs/data/GD_A02_FACTS_CONTRACT.md",
    "docs/data/MODEL_ASOF_CONTRACT.md",
)
FOTMOB_FINAL_RESULT_DOCS = (*FOTMOB_FINAL_RESULT_CONTRACT_DOCS, "docs/CAPABILITY_INDEX.md")
FOTMOB_FINAL_RESULT_PATHS = frozenset(
    {
        FOTMOB_FINAL_RESULT_SCOPE,
        *FOTMOB_FINAL_RESULT_DOCS,
        "src/infrastructure/fotmob/FotMobDetailCaptureContract.js",
        "src/infrastructure/fotmob/FotMobDetailCapturePipeline.js",
        "src/infrastructure/golden_dataset/FotMobPriorResultProjection.js",
        "src/ml/inference/fotmob_prior_result_asof.py",
        "tests/unit/fotmob_detail_transport_observability.test.js",
        "tests/unit/fotmob_prior_result_projection.test.js",
        "tests/unit/ml/test_fotmob_prior_result_asof.py",
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
    if category == "contract" and changed == FOTMOB_FINAL_RESULT_PATHS:
        return FOTMOB_FINAL_RESULT_CONTRACT_DOCS
    if category == "contract" and PERCENT_PILOT_MISSION_PATH in changed:
        return (CANONICAL_PREMATCH_CONTRACT_DOC,)
    if category == "blocker":
        required = list(REQUIRED_DOCS_BY_CATEGORY[category])
        if "docs/data/FOTMOB_CURRENT_STATE.md" in changed:
            required.append("docs/data/FOTMOB_CURRENT_STATE.md")
        return tuple(required)
    if category == "contract" and (
        changed in STAGE_D_FORWARD_MAPPINGS.values()
        or (
            changed & STAGE_D_CONTRACT_PATHS
            and not changed - (STAGE_D_CONTRACT_PATHS | STAGE_D_COMPANION_DOC_PATHS)
        )
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
        allowed = (
            PERCENT_PILOT_PATHS
            if PERCENT_PILOT_MISSION_PATH in changed
            else CANONICAL_PREMATCH_CONTRACT_PATHS | CANONICAL_PREMATCH_COMPANION_DOC_PATHS
        )
        unsupported = changed - allowed
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


def _read_regular_git_markdown(revision: str, path: str) -> str:
    entry = git_output(["ls-tree", revision, "--", path])
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise RuntimeError(f"{path} is not a regular tracked document at {revision}")
    return git_output(["show", f"{revision}:{path}"])


def _has_visible_document_update(
    original: tuple[str, Counter[str]], candidate: tuple[str, Counter[str]]
) -> bool:
    before, before_tags = original
    after, after_tags = candidate
    return bool(after) and after != before and not (after_tags - before_tags)


def _fotmob_document_has_update(base: str, head: str, path: str) -> bool:
    try:
        before, after = visible_documents(
            _read_regular_git_markdown(base, path), _read_regular_git_markdown(head, path)
        )
    except ValueError:
        return False
    return _has_visible_document_update(before, after)


def _fotmob_committed_document_errors(base_ref: str | None, head_ref: str | None) -> list[str]:
    if not base_ref or not head_ref or not is_full_sha(base_ref) or not is_full_sha(head_ref):
        return ["FotMob final-result backflow requires exact committed base/head revisions"]
    try:
        committed = collect_changes(base_ref, head_ref, include_worktree=False)
        if changed_paths(committed) != FOTMOB_FINAL_RESULT_PATHS:
            return [
                "FotMob final-result backflow requires all 11 changed paths at the exact revisions"
            ]
        if any(change.status not in {"A", "M"} for change in committed):
            return ["FotMob final-result cannot delete or rename away a path as an update"]
        updated = {change.path for change in committed if change.status == "M"}
        if missing := set(FOTMOB_FINAL_RESULT_DOCS) - updated:
            return [
                "FotMob final-result requires in-place updates of existing authoritative documents: "
                + ", ".join(sorted(missing))
            ]
        merge_base = git_output(["merge-base", base_ref, head_ref]).strip()
        return [
            f"FotMob final-result requires changed visible document body: {path}"
            for path in FOTMOB_FINAL_RESULT_DOCS
            if not _fotmob_document_has_update(merge_base, head_ref, path)
        ]
    except (RuntimeError, OSError, UnicodeError) as exc:
        return [f"FotMob final-result could not verify authoritative Git documents: {exc}"]


def _fotmob_backflow_errors(
    pr_body: str,
    changed: set[str],
    mission_scope: MissionScope | None,
    base_ref: str | None,
    head_ref: str | None,
) -> list[str]:
    if changed != FOTMOB_FINAL_RESULT_PATHS:
        return [
            "FotMob final-result requires the exact 11 mission paths"
            f" (missing: {', '.join(sorted(FOTMOB_FINAL_RESULT_PATHS - changed)) or 'none'}"
            f"; extra: {', '.join(sorted(changed - FOTMOB_FINAL_RESULT_PATHS)) or 'none'})"
        ]
    if (
        mission_scope is None
        or mission_scope.mission_id != FOTMOB_FINAL_RESULT_MISSION
        or mission_scope.task_type != "source-code"
        or mission_scope.workflow_class != "CRITICAL"
        or parse_task_type(pr_body) != "source-code"
        or parse_workflow_class(pr_body) != "CRITICAL"
    ):
        return ["FotMob final-result requires its validated CRITICAL business mission scope"]
    errors = validate_mission_scope_reference(
        pr_body, mission_scope=mission_scope, scope_path=FOTMOB_FINAL_RESULT_SCOPE
    )
    errors.extend(_fotmob_committed_document_errors(base_ref, head_ref))
    for category in ("contract", "capability", "source_of_truth"):
        if _normalise(_table_value(pr_body, YES_NO_FIELDS[category])) != "yes":
            errors.append(f"FotMob final-result requires '{YES_NO_FIELDS[category]}' = yes")
    return errors


def _stage_d_forward_commit_errors(
    base_ref: str | None, head_ref: str | None, required_paths: frozenset[str]
) -> list[str]:
    if not base_ref or not head_ref or not is_full_sha(base_ref) or not is_full_sha(head_ref):
        return ["Stage D forward accounting requires exact committed base/head revisions"]
    try:
        committed = collect_changes(base_ref, head_ref, include_worktree=False)
        if changed_paths(committed) != required_paths or any(
            change.status not in {"A", "M"} for change in committed
        ):
            return [
                "Stage D forward accounting requires its exact committed paths with no removal or rename"
            ]
        updated = {change.path for change in committed if change.status == "M"}
        if STAGE_D_FORWARD_AUTHORITY_DOCS - updated:
            return [
                "Stage D forward accounting requires in-place updates to all five authority documents"
            ]
        merge_base = git_output(["merge-base", base_ref, head_ref]).strip()
        if required_paths == STAGE_D_RUNTIME_PATHS:
            # 查询全部授权路径。在共同祖先只应看到 M，在 HEAD 应看到 M 和 A。
            for revision, expected in ((merge_base, updated), (head_ref, required_paths)):
                entries = git_output(
                    ["ls-tree", revision, "--", *sorted(required_paths)]
                ).splitlines()
                returned_paths = sorted(line.partition("\t")[2] for line in entries)
                if returned_paths != sorted(expected) or any(
                    not line.startswith(("100644 blob ", "100755 blob ")) for line in entries
                ):
                    return [
                        f"{STAGE_D_RUNTIME_MISSION} requires the expected regular tracked files at {revision}"
                    ]
        paths = sorted(STAGE_D_FORWARD_AUTHORITY_DOCS)
        projections = visible_documents(
            *(
                _read_regular_git_markdown(revision, path)
                for path in paths
                for revision in (merge_base, head_ref)
            )
        )
        errors = [
            f"Stage D forward accounting requires changed visible document body: {path}"
            for path, before, after in zip(paths, projections[::2], projections[1::2], strict=True)
            if not _has_visible_document_update(before, after)
        ]
    except (RuntimeError, OSError, ValueError) as exc:
        return [f"Stage D forward accounting could not verify authoritative Git documents: {exc}"]
    else:
        return errors


def _declared_document_paths(value: str) -> set[str]:
    return {token.strip("`\"'") for token in re.split(r"[,;\s]+", value) if token}


def _stage_d_forward_backflow_errors(
    pr_body: str,
    changed: set[str],
    mission_scope: MissionScope | None,
    base_ref: str | None,
    head_ref: str | None,
    required_mission: str,
) -> list[str]:
    required_paths = STAGE_D_FORWARD_MAPPINGS[required_mission]
    if changed != required_paths:
        count = "nine" if required_mission == STAGE_D_FORWARD_MISSION else "11"
        missing = ", ".join(sorted(required_paths - changed)) or "none"
        extra = ", ".join(sorted(changed - required_paths)) or "none"
        return [
            f"Stage D forward accounting requires the exact {count} mission paths (missing: {missing}; extra: {extra})"
        ]
    if (
        mission_scope is None
        or mission_scope.mission_id != required_mission
        or mission_scope.task_type != "source-code"
        or mission_scope.workflow_class != "CRITICAL"
        or parse_task_type(pr_body) != "source-code"
        or parse_workflow_class(pr_body) != "CRITICAL"
    ):
        return ["Stage D forward accounting requires its validated CRITICAL business mission scope"]
    if required_mission == STAGE_D_RUNTIME_MISSION and (
        mission_scope.authorized_prefixes or set(mission_scope.authorized_paths) != required_paths
    ):
        return [
            "Stage D runtime accounting requires exactly 11 authorized files and no authorized prefixes"
        ]
    errors = validate_mission_scope_reference(
        pr_body,
        mission_scope=mission_scope,
        scope_path=f"docs/agentic/missions/{required_mission}.json",
    )
    errors.extend(_stage_d_forward_commit_errors(base_ref, head_ref, required_paths))
    declared_docs = _declared_document_paths(_table_value(pr_body, "Updated authoritative docs"))
    impacts = dict.fromkeys(
        ("contract", "capability", "entrypoint", "milestone", "blocker", "source_of_truth"), "yes"
    )
    if required_mission == STAGE_D_RUNTIME_MISSION:
        impacts.update(navigation="no", vision="no")
        if declared_docs - STAGE_D_FORWARD_AUTHORITY_DOCS:
            errors.append(
                f"{required_mission} must declare only its five updated authority documents"
            )
    for category, expected in impacts.items():
        if _normalise(_table_value(pr_body, YES_NO_FIELDS[category])) != expected:
            errors.append(f"{required_mission} requires '{YES_NO_FIELDS[category]}' = {expected}")
    if missing_docs := STAGE_D_FORWARD_AUTHORITY_DOCS - declared_docs:
        errors.append(
            f"{required_mission} requires declaring all five authority documents: "
            + ", ".join(sorted(missing_docs))
        )
    return errors


def _exact_mission_backflow_errors(
    pr_body: str,
    changed: set[str],
    mission_scope: MissionScope | None,
    base_ref: str | None,
    head_ref: str | None,
) -> list[str] | None:
    mission_id = mission_scope.mission_id if mission_scope is not None else None
    if FOTMOB_FINAL_RESULT_SCOPE in changed or mission_id == FOTMOB_FINAL_RESULT_MISSION:
        return _fotmob_backflow_errors(pr_body, changed, mission_scope, base_ref, head_ref)
    for required_mission in STAGE_D_FORWARD_MAPPINGS:
        if (
            mission_id == required_mission
            or f"docs/agentic/missions/{required_mission}.json" in changed
        ):
            return _stage_d_forward_backflow_errors(
                pr_body, changed, mission_scope, base_ref, head_ref, required_mission
            )
    return None


def check_documentation_backflow(  # noqa: C901, PLR0912
    pr_body: str,
    changed: set[str],
    *,
    changes: Iterable[Change] | None = None,
    mission_scope: MissionScope | None = None,
    base_ref: str | None = None,
    head_ref: str | None = None,
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
    Exact FotMob and Stage D forward mappings require committed Git
    documentation and the canonical mission-scope validation context.
    """
    classified = classify_changed_paths(changed)
    vision_value = _table_value(pr_body, VISION_IMPACT_FIELD)
    contract_value = _table_value(pr_body, YES_NO_FIELDS["contract"])
    special_errors = _exact_mission_backflow_errors(
        pr_body, changed, mission_scope, base_ref, head_ref
    )
    if (
        not classified
        and special_errors is None
        and _normalise(vision_value) != "yes"
        and _normalise(contract_value) != "yes"
    ):
        return []

    # Actual contract paths must not borrow a workflow mapping via a false declaration.
    errors = _canonical_contract_status_errors(changed, changes)
    if special_errors is not None:
        errors.extend(special_errors)
    elif "contract" in classified or _normalise(contract_value) == "yes":
        errors.extend(_contract_mapping_errors(changed))
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
    declared_docs = _declared_document_paths(updated_docs)
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
