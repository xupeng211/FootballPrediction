"""Stage D 后续记账仅允许已批准的业务范围及实际 Git 文档变更。

lifecycle: permanent
"""

from dataclasses import replace
import json

import pytest

from scripts.ops.helpers import git_change_helpers
from scripts.ops.helpers.agent_workflow_contract import MissionScope
from scripts.ops.helpers.documentation_backflow import check_documentation_backflow
from tests.unit.test_fotmob_final_result_documentation_backflow import _commit, _git, _write
from tests.unit.test_project_knowledge_convergence import _impact_body

_MISSION = "FP_STAGE_D_FORWARD_ACCOUNTING_OFFLINE"
_SCOPE_PATH = f"docs/agentic/missions/{_MISSION}.json"
_DOMAIN = "docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md"
_CYCLE = "scripts/ops/stage_d_cycle.js"
_ACCOUNTING = "src/infrastructure/market_evidence/stageDForwardAccounting.js"
_DOCS = {
    _DOMAIN,
    "README.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/ACTIVE_MILESTONE.md",
    "docs/PROJECT_STATUS.md",
}
_PATHS = _DOCS | {
    _SCOPE_PATH,
    _CYCLE,
    _ACCOUNTING,
    "tests/unit/market_evidence/stage_d_forward_accounting.test.js",
}
_SCOPE = MissionScope.from_mapping(
    {
        "schema_version": "agentic-mission-scope/v1",
        "mission_id": _MISSION,
        "task_type": "source-code",
        "workflow_class": "CRITICAL",
        "authorized_paths": sorted(_PATHS),
        "authorized_prefixes": [],
        "excluded_paths": [],
        "excluded_prefixes": [],
        "excluded_tokens": [],
        "protected_invariants": ["保留旧账及历史缺口。"],
        "forbidden_side_effects": ["禁止供应商调用。"],
    }
)


def _body(**overrides):
    fields = {
        "capability": "yes",
        "entrypoint": "yes",
        "milestone": "yes",
        "blocker": "yes",
        "contract": "yes",
        "source_updated": "yes",
        "updated_docs": ", ".join(sorted(_DOCS)),
    }
    fields.update(overrides)
    return (
        "## Scope\n\n"
        "| Task type | source-code |\n"
        "| Workflow class | CRITICAL |\n"
        f"| Mission ID | {_MISSION} |\n"
        f"| Mission scope contract | `{_SCOPE_PATH}` |\n\n" + _impact_body(**fields)
    )


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(git_change_helpers, "ROOT_HELPER", tmp_path)
    _git(tmp_path, "init", "-q")
    for file_path in _DOCS | {_CYCLE}:
        _write(tmp_path, file_path, "原有项目内容\n")
    base = _commit(tmp_path, "Base")
    for file_path in _PATHS:
        content = json.dumps(_SCOPE.to_dict()) if file_path == _SCOPE_PATH else "后续记账的变更。\n"
        _write(tmp_path, file_path, content)
    return tmp_path, base, _commit(tmp_path, "Forward accounting")


def _run(base, head, *, body=None, paths=None, scope=_SCOPE):
    return check_documentation_backflow(
        _body() if body is None else body,
        _PATHS if paths is None else paths,
        mission_scope=scope,
        base_ref=base,
        head_ref=head,
    )


def test_exact_stage_d_forward_paths_use_business_documents(candidate):
    _, base, head = candidate
    assert _run(base, head) == []


@pytest.mark.parametrize(
    "extra",
    [
        "AGENTS.md",
        "scripts/ops/helpers/documentation_backflow.py",
        "scripts/ops/stage_d_quota_adjudication.js",
        "src/unknown/budget.js",
    ],
)
def test_forward_accounting_rejects_mixed_or_unrelated_paths(candidate, extra):
    _, base, head = candidate
    errors = _run(base, head, paths=_PATHS | {extra})
    assert any("exact nine mission paths" in error and extra in error for error in errors)


def test_forward_accounting_requires_complete_scope_and_matching_declaration(candidate):
    _, base, head = candidate
    assert any("exact nine mission paths" in e for e in _run(base, head, paths=_PATHS - {_DOMAIN}))
    for scope in (
        None,
        replace(_SCOPE, workflow_class="STRICT"),
        replace(_SCOPE, mission_id="OTHER"),
    ):
        assert any(
            "validated CRITICAL business mission scope" in e for e in _run(base, head, scope=scope)
        )
    wrong_reference = _body().replace(_SCOPE_PATH, "docs/agentic/missions/OTHER.json")
    assert _run(base, head, body=wrong_reference)
    wrong_declaration = _body(contract="no")
    assert any("contract changed?" in e for e in _run(base, head, body=wrong_declaration))
    assert any(
        "declaring all five" in e for e in _run(base, head, body=_body(updated_docs=_DOMAIN))
    )


@pytest.mark.parametrize("broken", ["deleted", "symlink", "unchanged", "blank"])
def test_committed_authority_is_required_even_when_caller_claims_all_paths(candidate, broken):
    root, base, _ = candidate
    target = root / _DOMAIN
    if broken in {"deleted", "symlink"}:
        target.unlink()
        if broken == "symlink":
            target.symlink_to(root / "README.md")
    else:
        target.write_text("原有项目内容\n" if broken == "unchanged" else "  \n", encoding="utf-8")
    bad_head = _commit(root, broken)
    assert _run(base, bad_head)


def test_missing_exact_commit_cannot_use_caller_paths(candidate):
    _, base, _ = candidate
    assert any("exact committed base/head revisions" in e for e in _run(base, "HEAD"))


def test_existing_cycle_can_still_have_an_ordinary_non_contract_fix():
    assert check_documentation_backflow("", {_CYCLE}) == []
