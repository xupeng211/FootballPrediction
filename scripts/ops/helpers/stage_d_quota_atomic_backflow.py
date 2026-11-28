"""核对有独立固定路径的 Stage D 修复工单。

lifecycle: permanent
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.devops.exact_head import is_full_sha
from scripts.ops.helpers.agent_workflow_contract import validate_mission_scope_reference
from scripts.ops.helpers.git_change_helpers import collect_changes, git_output
from scripts.ops.helpers.pr_authorization_matrix import parse_task_type
from scripts.ops.helpers.strict_review_evidence import parse_workflow_class

if TYPE_CHECKING:
    from collections.abc import Callable

    from scripts.ops.helpers.agent_workflow_contract import MissionScope


@dataclass(frozen=True)
class StageDBoundedBackflow:
    """固定工单、文件和可选领域合同。"""

    mission_id: str
    label: str
    count_label: str
    updated_paths: frozenset[str]
    authority_docs: tuple[str, ...] = ()
    additional_impacts: tuple[str, ...] = ()

    @property
    def scope(self) -> str:
        """返回工单范围文件路径。"""
        return f"docs/agentic/missions/{self.mission_id}.json"

    @property
    def paths(self) -> frozenset[str]:
        """返回允许的完整路径集合。"""
        return self.updated_paths | {self.scope}


_STAGE_D_OPERATIONS = "src/infrastructure/market_evidence/stageDOperations.js"
_STAGE_D_CONTRACT = "docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md"
STAGE_D_MARKER_COMPAT = StageDBoundedBackflow(
    "FP_STAGE_D_HISTORICAL_CONSUMPTION_MARKER_COMPAT",
    "Stage D historical consumption marker compatibility",
    "four",
    frozenset(
        {
            _STAGE_D_OPERATIONS,
            "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
            _STAGE_D_CONTRACT,
        }
    ),
    (_STAGE_D_CONTRACT,),
)
_PROJECTION_DOCS = (
    _STAGE_D_CONTRACT,
    "docs/ACTIVE_MILESTONE.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/PROJECT_STATUS.md",
)
STAGE_D_BOUNDED_BACKFLOWS = (
    StageDBoundedBackflow(
        "FP_STAGE_D_QUOTA_ADJUDICATION_ATOMIC_PUBLISH",
        "Stage D quota atomic publication",
        "three",
        frozenset(
            {
                _STAGE_D_OPERATIONS,
                "tests/unit/market_evidence/stage_d_quota_adjudication.test.js",
            }
        ),
    ),
    STAGE_D_MARKER_COMPAT,
    StageDBoundedBackflow(
        "FP_STAGE_D_SINGLE_CAPTURE_PROJECTION",
        "Stage D single capture projection",
        "nine",
        frozenset(
            {
                *_PROJECTION_DOCS,
                _STAGE_D_OPERATIONS,
                "src/infrastructure/market_evidence/prospectiveBatch.js",
                "src/infrastructure/market_evidence/theOddsApiAdapter.js",
                "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
            }
        ),
        _PROJECTION_DOCS,
        ("capability", "milestone", "blocker"),
    ),
)


def _stage_d_bounded_commit_errors(
    spec: StageDBoundedBackflow,
    base_ref: str | None,
    head_ref: str | None,
    document_has_update: Callable[[str, str, str], bool],
) -> list[str]:
    if not base_ref or not head_ref or not is_full_sha(base_ref) or not is_full_sha(head_ref):
        return [f"{spec.label} requires exact committed base/head revisions"]
    expected_changes = {(path, "M") for path in spec.updated_paths}
    expected_changes.add((spec.scope, "A"))
    try:
        committed = collect_changes(base_ref, head_ref, include_worktree=False)
        if {(change.path, change.status) for change in committed} != expected_changes:
            return [f"{spec.label} requires in-place edits to its existing paths and a new scope"]
        merge_base = git_output(["merge-base", base_ref, head_ref]).strip()
        for revision, required in (
            (merge_base, spec.updated_paths),
            (head_ref, spec.paths),
        ):
            entries = git_output(["ls-tree", revision, "--", *sorted(spec.paths)]).splitlines()
            regular = {
                entry.partition("\t")[2]
                for entry in entries
                if entry.startswith(("100644 blob ", "100755 blob "))
            }
            if regular != required or len(entries) != len(required):
                return [f"{spec.label} requires regular tracked files"]
        return [
            f"{spec.mission_id} requires changed visible document body: {document}"
            for document in spec.authority_docs
            if not document_has_update(merge_base, head_ref, document)
        ]
    except (RuntimeError, OSError, ValueError) as exc:
        return [f"{spec.label} could not verify committed paths: {exc}"]


def validate_stage_d_bounded_backflow(
    spec: StageDBoundedBackflow,
    pr_body: str,
    changed: set[str],
    mission_scope: MissionScope | None,
    base_ref: str | None,
    head_ref: str | None,
    *,
    document_has_update: Callable[[str, str, str], bool],
) -> list[str]:
    """核对专项范围、PR 引用及准确提交内的普通文件。"""
    if changed != spec.paths:
        return [f"{spec.label} requires its exact {spec.count_label} mission paths"]
    if (
        mission_scope is None
        or mission_scope.mission_id != spec.mission_id
        or mission_scope.task_type != "source-code"
        or mission_scope.workflow_class != "CRITICAL"
        or mission_scope.authorized_prefixes
        or set(mission_scope.authorized_paths) != spec.paths
        or parse_task_type(pr_body) != "source-code"
        or parse_workflow_class(pr_body) != "CRITICAL"
    ):
        return [f"{spec.label} requires its validated CRITICAL {spec.count_label}-file scope"]
    errors = validate_mission_scope_reference(
        pr_body, mission_scope=mission_scope, scope_path=spec.scope
    )
    errors.extend(_stage_d_bounded_commit_errors(spec, base_ref, head_ref, document_has_update))
    return errors
