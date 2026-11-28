"""已保存响应补录的文件动作与文档门禁。

lifecycle: permanent
"""

from dataclasses import replace

import pytest

from scripts.ops.helpers import git_change_helpers
from scripts.ops.helpers.agent_workflow_contract import MissionScope
from scripts.ops.helpers.stage_d_quota_atomic_backflow import (
    STAGE_D_BOUNDED_BACKFLOWS,
    validate_stage_d_bounded_backflow,
)
from tests.unit.test_fotmob_final_result_documentation_backflow import _commit, _git, _write
from tests.unit.test_stage_d_forward_accounting_backflow import _body

_MISSION = "FP_STAGE_D_CAPTURE_BACKFILL"
_SPEC = next(spec for spec in STAGE_D_BOUNDED_BACKFLOWS if spec.mission_id == _MISSION)
_CLI = "scripts/ops/stage_d_capture_backfill.js"
_SCOPE = MissionScope.from_mapping(
    {
        "schema_version": "agentic-mission-scope/v1",
        "mission_id": _MISSION,
        "task_type": "source-code",
        "workflow_class": "CRITICAL",
        "authorized_paths": sorted(_SPEC.paths),
        "authorized_prefixes": [],
        "excluded_paths": [],
        "excluded_prefixes": [],
        "excluded_tokens": [],
        "protected_invariants": ["既有事务门禁继续适用。"],
        "forbidden_side_effects": ["不得发出供应商请求。"],
    }
)


@pytest.mark.parametrize("preexisting", [False, True])
def test_backfill_gate_requires_new_entrypoint_and_existing_docs(
    tmp_path, monkeypatch, preexisting
):
    monkeypatch.setattr(git_change_helpers, "ROOT_HELPER", tmp_path)
    _git(tmp_path, "init", "-q")
    for document in _SPEC.authority_docs:
        _write(tmp_path, document, "已知状态。\n")
    if preexisting:
        _write(tmp_path, _CLI, "// 文件已经存在。\n")
    base = _commit(tmp_path, "Backfill base")
    for file_path in _SPEC.paths:
        _write(tmp_path, file_path, "已补偿的状态说明。\n")
    head = _commit(tmp_path, "Backfill change")
    checked_docs = []

    def visible_update(base_ref, head_ref, document):
        assert (base_ref, head_ref) == (base, head)
        checked_docs.append(document)
        return True

    body = _body(_MISSION)
    result = validate_stage_d_bounded_backflow(
        _SPEC,
        body,
        set(_SCOPE.authorized_paths),
        _SCOPE,
        base,
        head,
        document_has_update=visible_update,
    )
    if preexisting:
        assert result == [
            "Stage D retained capture backfill requires in-place edits and the specified new files"
        ]
        assert checked_docs == []
    else:
        assert result == []
        assert set(checked_docs) == set(_SPEC.authority_docs)
        assert validate_stage_d_bounded_backflow(
            _SPEC,
            body,
            set(_SCOPE.authorized_paths),
            replace(_SCOPE, mission_id=f"{_MISSION}_GATE"),
            base,
            head,
            document_has_update=visible_update,
        ) == ["Stage D retained capture backfill requires its validated CRITICAL eight-file scope"]
