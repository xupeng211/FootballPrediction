"""Stage D 后续记账仅允许已批准的业务范围及实际 Git 文档变更。

lifecycle: permanent
"""

from dataclasses import replace
import json

import pytest

from scripts.devops import fotmob_markdown
from scripts.ops.helpers import git_change_helpers
from scripts.ops.helpers.agent_workflow_contract import MissionScope
from scripts.ops.helpers.documentation_backflow import check_documentation_backflow
from tests.unit.test_fotmob_final_result_documentation_backflow import _commit, _git, _write
from tests.unit.test_project_knowledge_convergence import _impact_body

_MISSION = "FP_STAGE_D_FORWARD_ACCOUNTING_OFFLINE"
_SCOPE_PATH = f"docs/agentic/missions/{_MISSION}.json"
_DOMAIN = "docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md"
_ORIGINAL = "# 原有标题\n\n原有 项目内容\n"
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
        _write(tmp_path, file_path, _ORIGINAL)
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
        target.write_text(_ORIGINAL if broken == "unchanged" else "  \n", encoding="utf-8")
    bad_head = _commit(root, broken)
    assert _run(base, bad_head)


@pytest.mark.parametrize(
    "replacement",
    [
        _ORIGINAL + "\n<!-- 仅有隐藏注释。 -->\n",
        _ORIGINAL.replace("原有标题", "新标题"),
        _ORIGINAL + "\n另一个 Setext 标题\n-------------------\n",
        _ORIGINAL + "\n<div hidden>仅有隐藏 HTML。</div>\n",
        _ORIGINAL + "\n<template>仅有模板内容。</template>\n",
        "# 空壳文档\n\n<!-- 仅有隐藏注释。 -->\n",
        "# 空壳文档\n\n<script>仅有脚本。</script>\n",
        "# 空壳文档\n\n<style>仅有样式。</style>\n",
        _ORIGINAL.replace("原有 项目", "原有<br />项目"),
    ],
    ids=["comment", "heading", "setext", "hidden", "template", "shell", "script", "style", "break"],
)
def test_non_body_edits_do_not_satisfy_forward_backflow(candidate, replacement):
    root, base, _ = candidate
    _write(root, _DOMAIN, replacement)
    head = _commit(root, "Only non-body changes in the authority")
    assert any("changed visible document body" in e and _DOMAIN in e for e in _run(base, head))


@pytest.mark.parametrize("document", sorted(_DOCS))
def test_each_committed_authority_needs_a_visible_update(candidate, document):
    root, base, _ = candidate
    _write(root, document, _ORIGINAL + "\n<!-- 仅有隐藏注释。 -->\n")
    head = _commit(root, "One authority lacks a visible change")
    _write(root, document, _ORIGINAL + "\n工作区有未提交的正文。\n")
    errors = _run(base, head)
    assert [e for e in errors if "changed visible document body" in e] == [
        f"Stage D forward accounting requires changed visible document body: {document}"
    ]


def test_unclosed_comment_rejects_the_committed_authority(candidate):
    root, base, _ = candidate
    _write(root, _DOMAIN, _ORIGINAL + "\n<!-- 未闭合注释。\n")
    head = _commit(root, "Unclosed authoritative comment")
    assert any("invalid authoritative Markdown" in e for e in _run(base, head))


def test_new_raw_html_is_rejected_even_with_a_visible_body_change(candidate):
    root, base, _ = candidate
    _write(root, _DOMAIN, _ORIGINAL + "\n<div>新增可见内容。</div>\n")
    head = _commit(root, "New raw HTML in the authority")
    assert any("changed visible document body" in e and _DOMAIN in e for e in _run(base, head))


def test_unavailable_parser_rejects_valid_scope_only(candidate, monkeypatch):
    root, base, head = candidate
    monkeypatch.delenv("FP_FOTMOB_MARKDOWN_INSTALL", raising=False)
    monkeypatch.setattr(fotmob_markdown, "_locked_target", lambda: root / "missing-parser")
    assert any(fotmob_markdown.PARSER_UNAVAILABLE in e for e in _run(base, head))
    errors = _run(base, head, paths=_PATHS - {_DOMAIN})
    assert errors
    assert all(fotmob_markdown.PARSER_UNAVAILABLE not in e for e in errors)


def test_missing_exact_commit_cannot_use_caller_paths(candidate):
    _, base, _ = candidate
    assert any("exact committed base/head revisions" in e for e in _run(base, "HEAD"))


def test_existing_cycle_can_still_have_an_ordinary_non_contract_fix():
    assert check_documentation_backflow("", {_CYCLE}) == []
