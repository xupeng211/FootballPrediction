"""核对额度裁决原子发布修复的固定业务工单。

lifecycle: permanent
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.devops.exact_head import is_full_sha
from scripts.ops.helpers.agent_workflow_contract import validate_mission_scope_reference
from scripts.ops.helpers.git_change_helpers import collect_changes, git_output
from scripts.ops.helpers.pr_authorization_matrix import parse_task_type
from scripts.ops.helpers.strict_review_evidence import parse_workflow_class

if TYPE_CHECKING:
    from scripts.ops.helpers.agent_workflow_contract import MissionScope


STAGE_D_QUOTA_ATOMIC_MISSION = "FP_STAGE_D_QUOTA_ADJUDICATION_ATOMIC_PUBLISH"
STAGE_D_QUOTA_ATOMIC_SCOPE = f"docs/agentic/missions/{STAGE_D_QUOTA_ATOMIC_MISSION}.json"
STAGE_D_QUOTA_ATOMIC_UPDATES = frozenset(
    {
        "src/infrastructure/market_evidence/stageDOperations.js",
        "tests/unit/market_evidence/stage_d_quota_adjudication.test.js",
    }
)
STAGE_D_QUOTA_ATOMIC_PATHS = STAGE_D_QUOTA_ATOMIC_UPDATES | {STAGE_D_QUOTA_ATOMIC_SCOPE}


def _stage_d_quota_atomic_commit_errors(base_ref: str | None, head_ref: str | None) -> list[str]:
    if not base_ref or not head_ref or not is_full_sha(base_ref) or not is_full_sha(head_ref):
        return ["Stage D quota atomic publication requires exact committed base/head revisions"]
    expected_changes = {(path, "M") for path in STAGE_D_QUOTA_ATOMIC_UPDATES}
    expected_changes.add((STAGE_D_QUOTA_ATOMIC_SCOPE, "A"))
    try:
        committed = collect_changes(base_ref, head_ref, include_worktree=False)
        if {(change.path, change.status) for change in committed} != expected_changes:
            return ["Stage D quota atomic publication requires two in-place edits and a new scope"]
        merge_base = git_output(["merge-base", base_ref, head_ref]).strip()
        for revision, required in (
            (merge_base, STAGE_D_QUOTA_ATOMIC_UPDATES),
            (head_ref, STAGE_D_QUOTA_ATOMIC_PATHS),
        ):
            entries = git_output(
                ["ls-tree", revision, "--", *sorted(STAGE_D_QUOTA_ATOMIC_PATHS)]
            ).splitlines()
            regular = {
                entry.partition("\t")[2]
                for entry in entries
                if entry.startswith(("100644 blob ", "100755 blob "))
            }
            if regular != required or len(entries) != len(required):
                return ["Stage D quota atomic publication requires regular tracked files"]
    except (RuntimeError, OSError, ValueError) as exc:
        return [f"Stage D quota atomic publication could not verify committed paths: {exc}"]
    return []


def validate_stage_d_quota_atomic_backflow(
    pr_body: str,
    changed: set[str],
    mission_scope: MissionScope | None,
    base_ref: str | None,
    head_ref: str | None,
) -> list[str]:
    """核对专项范围、PR 引用及准确提交内的三个文件。"""
    if changed != STAGE_D_QUOTA_ATOMIC_PATHS:
        return ["Stage D quota atomic publication requires its exact three mission paths"]
    if (
        mission_scope is None
        or mission_scope.mission_id != STAGE_D_QUOTA_ATOMIC_MISSION
        or mission_scope.task_type != "source-code"
        or mission_scope.workflow_class != "CRITICAL"
        or mission_scope.authorized_prefixes
        or set(mission_scope.authorized_paths) != STAGE_D_QUOTA_ATOMIC_PATHS
        or parse_task_type(pr_body) != "source-code"
        or parse_workflow_class(pr_body) != "CRITICAL"
    ):
        return ["Stage D quota atomic publication requires its validated CRITICAL three-file scope"]
    errors = validate_mission_scope_reference(
        pr_body, mission_scope=mission_scope, scope_path=STAGE_D_QUOTA_ATOMIC_SCOPE
    )
    errors.extend(_stage_d_quota_atomic_commit_errors(base_ref, head_ref))
    return errors
