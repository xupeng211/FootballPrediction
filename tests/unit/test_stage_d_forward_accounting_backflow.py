"""Stage D 后续记账仅允许已批准的业务范围及实际 Git 文档变更。

lifecycle: permanent
"""

from dataclasses import replace
import json

import pytest

from scripts.devops import fotmob_markdown
from scripts.ops.helpers import documentation_backflow, git_change_helpers
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
_ACCOUNTING_TEST = "tests/unit/market_evidence/stage_d_forward_accounting.test.js"
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
    _ACCOUNTING_TEST,
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


def _body(mission=_MISSION, **overrides):
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
        f"| Mission ID | {mission} |\n"
        f"| Mission scope contract | `docs/agentic/missions/{mission}.json` |\n\n"
        + _impact_body(**fields)
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


@pytest.mark.parametrize("path", [_ACCOUNTING, _ACCOUNTING_TEST])
@pytest.mark.parametrize("has_scope", [False, True], ids=["no-scope", "other-scope"])
def test_ordinary_non_contract_fix_does_not_trigger_stage_d_gate(path, has_scope):
    scope = (
        replace(_SCOPE, mission_id="OTHER", workflow_class="NORMAL", authorized_paths=(path,))
        if has_scope
        else None
    )
    assert check_documentation_backflow(_impact_body(), {path}, mission_scope=scope) == []


def test_ordinary_workflow_still_rejects_unmapped_contract_changes():
    unknown_doc = "docs/data/UNKNOWN_CONTRACT.md"
    errors = check_documentation_backflow(_impact_body(contract="yes"), {_ACCOUNTING, unknown_doc})
    assert errors[0] == (
        f"contract paths have no approved domain mapping: {unknown_doc}, {_ACCOUNTING}"
    )


@pytest.mark.parametrize("scope", [None, replace(_SCOPE, mission_id="OTHER")])
def test_dedicated_scope_path_still_requires_the_validated_stage_d_mission(candidate, scope):
    _, base, head = candidate
    assert _run(base, head, scope=scope) == [
        "Stage D forward accounting requires its validated CRITICAL business mission scope"
    ]


def test_stage_d_mission_without_its_scope_path_still_enters_exact_gate(candidate):
    _, base, head = candidate
    errors = _run(base, head, paths=_PATHS - {_SCOPE_PATH})
    assert (
        f"Stage D forward accounting requires the exact nine mission paths (missing: {_SCOPE_PATH}; extra: none)"
        in errors
    )


def test_diverged_base_uses_merge_base_for_paths_and_visible_documents(candidate):
    root, base, head = candidate
    _git(root, "switch", "-c", "advanced-base", base)
    _write(root, _DOMAIN, "后续记账的变更。\n")
    _write(root, "only-on-advanced-base.txt", "目标分支的独立变更。\n")
    advanced_base = _commit(root, "Advance target branch independently")

    assert _git(root, "merge-base", advanced_base, head) == base
    assert _run(advanced_base, head) == []


_RUNTIME = "FP_STAGE_D_FORWARD_ACCOUNTING_RUNTIME"
_RUNTIME_SCOPE_PATH = f"docs/agentic/missions/{_RUNTIME}.json"
_INITIALIZE = "scripts/ops/stage_d_controlled_initialization.js"
_OPERATIONS = "src/infrastructure/market_evidence/stageDOperations.js"
_INITIALIZE_TEST = "tests/unit/market_evidence/stage_d_controlled_initialization.test.js"
_RUNTIME_PATHS = _DOCS | {
    _RUNTIME_SCOPE_PATH,
    _INITIALIZE,
    _OPERATIONS,
    _ACCOUNTING,
    _INITIALIZE_TEST,
    _ACCOUNTING_TEST,
}
_RUNTIME_SCOPE = replace(
    _SCOPE, mission_id=_RUNTIME, authorized_paths=tuple(sorted(_RUNTIME_PATHS))
)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(git_change_helpers, "ROOT_HELPER", tmp_path)
    _git(tmp_path, "init", "-q")
    for path in _RUNTIME_PATHS - {_RUNTIME_SCOPE_PATH}:
        _write(tmp_path, path, _ORIGINAL)
    base = _commit(tmp_path, "Existing main with the offline accounting module")
    for path in _RUNTIME_PATHS:
        value = (
            json.dumps(_RUNTIME_SCOPE.to_dict())
            if path == _RUNTIME_SCOPE_PATH
            else _ORIGINAL + "正式入口接入记账。\n"
        )
        _write(tmp_path, path, value)
    return tmp_path, base, _commit(tmp_path, "Runtime integration")


def _runtime_check(base, head, *, paths=None, scope=_RUNTIME_SCOPE, body=None):
    return _run(
        base,
        head,
        body=_body(_RUNTIME) if body is None else body,
        paths=_RUNTIME_PATHS if paths is None else paths,
        scope=scope,
    )


def test_independent_runtime_path_set_and_diverged_target(runtime):
    root, base, head = runtime
    assert _runtime_check(base, head) == []
    _git(root, "switch", "-c", "advanced-target", base)
    _write(root, _DOMAIN, _ORIGINAL + "正式入口接入记账。\n")
    _write(root, "target-only.txt", "only on main")
    advanced = _commit(root, "Independent target change")
    assert _git(root, "merge-base", advanced, head) == base
    assert _runtime_check(advanced, head) == []


@pytest.mark.parametrize("document", sorted(_DOCS))
@pytest.mark.parametrize(
    "content",
    [
        "# 新标题\n\n原有 项目内容\n",
        _ORIGINAL + "<!-- 隐藏 -->\n",
        _ORIGINAL + "  \n",
        "# 空壳\n",
    ],
)
def test_each_runtime_authority_must_change_committed_visible_body(runtime, document, content):
    root, base, _ = runtime
    _write(root, document, content)
    head = _commit(root, "Replace an authority update")
    _write(root, document, _ORIGINAL + "只有工作区里的更新。\n")
    assert any(document in e for e in _runtime_check(base, head))


@pytest.mark.parametrize(
    "operation", ["delete", "rename", "symlink", "extra-governance", "mixed-offline"]
)
def test_runtime_exact_commit_rejects_removed_replaced_and_extra_paths(runtime, operation):
    root, base, _ = runtime
    target = root / _DOMAIN
    if operation == "delete":
        target.unlink()
    elif operation == "rename":
        target.rename(target.with_suffix(".moved"))
    elif operation == "symlink":
        target.unlink()
        target.symlink_to("README.md")
    elif operation == "extra-governance":
        _write(root, "AGENTS.md", "混入治理。")
    else:
        _write(root, _SCOPE_PATH, json.dumps(_SCOPE.to_dict()))
    head = _commit(root, operation)
    assert _runtime_check(base, head)


def test_runtime_scope_identity_authority_and_metadata_are_bound(runtime):
    _, base, head = runtime
    for scope in (
        None,
        _SCOPE,
        replace(_RUNTIME_SCOPE, mission_id="OTHER"),
        replace(_RUNTIME_SCOPE, workflow_class="STRICT"),
        replace(_RUNTIME_SCOPE, task_type="workflow-governance"),
        replace(_RUNTIME_SCOPE, authorized_prefixes=("src/",)),
        replace(_RUNTIME_SCOPE, authorized_paths=tuple(sorted(_RUNTIME_PATHS | {_CYCLE}))),
    ):
        assert _runtime_check(base, head, scope=scope)
    for body in (
        _body(),
        _body(_RUNTIME).replace(_RUNTIME_SCOPE_PATH, _SCOPE_PATH),
        _body(_RUNTIME).replace("CRITICAL", "STRICT"),
        _body(_RUNTIME).replace("source-code", "docs-only"),
        _body(_RUNTIME, updated_docs=_DOMAIN),
        _body(_RUNTIME, navigation="yes"),
        _body(_RUNTIME, vision="yes"),
        _body(_RUNTIME, updated_docs=", ".join(_DOCS | {"AGENTS.md"})),
        *(
            _body(_RUNTIME, **{key: "no"})
            for key in (
                "capability",
                "entrypoint",
                "milestone",
                "contract",
                "blocker",
                "source_updated",
            )
        ),
    ):
        assert _runtime_check(base, head, body=body)
    for path in _RUNTIME_PATHS:
        assert _runtime_check(base, head, paths=_RUNTIME_PATHS - {path})
    assert _runtime_check(base, head, paths=_RUNTIME_PATHS | _PATHS)
    assert _runtime_check(base, head, paths=_RUNTIME_PATHS | {_SCOPE_PATH}, scope=_SCOPE)


@pytest.mark.parametrize(
    "path", [_INITIALIZE, _INITIALIZE_TEST, _OPERATIONS, _ACCOUNTING, _ACCOUNTING_TEST]
)
def test_shared_runtime_file_does_not_select_either_forward_mission(path):
    other = replace(_RUNTIME_SCOPE, mission_id="OTHER", authorized_paths=(path,))
    errors = check_documentation_backflow(_impact_body(), {path}, mission_scope=other)
    assert errors == []


def test_runtime_non_document_must_also_be_a_regular_file(runtime):
    root, base, _ = runtime
    source = root / _INITIALIZE
    source.unlink()
    source.symlink_to("stage_d_cycle.js")
    head = _commit(root, "Substitute a symlink for the runtime entry")
    assert any("regular tracked files" in e for e in _runtime_check(base, head))


def test_runtime_cannot_repurpose_an_existing_nonregular_path(runtime):
    root, base, head = runtime
    _git(root, "switch", "-c", "alternate-history", base)
    source = root / _INITIALIZE
    source.unlink()
    source.symlink_to("stage_d_cycle.js")
    other_base = _commit(root, "An old symbolic link")
    _git(root, "restore", "--source", head, "--", *sorted(_RUNTIME_PATHS))
    other_head = _commit(root, "Use the runtime tree on a different baseline")
    assert any("regular tracked files" in e for e in _runtime_check(other_base, other_head))


def test_added_runtime_scope_is_absent_at_base_and_regular_at_head(runtime):
    root, base, head = runtime
    assert not _git(root, "ls-tree", base, "--", _RUNTIME_SCOPE_PATH)
    assert _git(root, "ls-tree", head, "--", _RUNTIME_SCOPE_PATH).startswith("100644 blob ")
    assert _runtime_check(base, head) == []
    added = root / _RUNTIME_SCOPE_PATH
    added.unlink()
    added.symlink_to("other.json")
    wrong_type = _commit(root, "A new scope must be a regular file at HEAD")
    assert any("regular tracked files" in e for e in _runtime_check(base, wrong_type))


@pytest.mark.parametrize(
    ("path", "wrong_status"),
    [(_RUNTIME_SCOPE_PATH, "M"), (_INITIALIZE, "A"), (_ACCOUNTING_TEST, "M")],
    ids=["missing-modified-at-base", "present-added-at-base", "missing-modified-at-head"],
)
def test_runtime_tree_must_agree_with_changed_file_status(runtime, monkeypatch, path, wrong_status):
    root, base, head = runtime
    if path == _ACCOUNTING_TEST:
        (root / path).unlink()
        head = _commit(root, "Remove an existing test from the candidate")
    changes = git_change_helpers.collect_changes(base, head, include_worktree=False)
    assert next(change for change in changes if change.path == path).status != wrong_status
    conflicting = [
        replace(change, status=wrong_status) if change.path == path else change
        for change in changes
    ]
    # 仅注入与实际树条目不一致的差异状态，两次 ls-tree 均读取上述真实 Git 提交。
    monkeypatch.setattr(
        documentation_backflow, "collect_changes", lambda *_args, **_kwargs: conflicting
    )
    assert any("regular tracked files" in e for e in _runtime_check(base, head))


def test_impact_diagnostics_identify_the_runtime_mission(runtime):
    _, base, head = runtime
    errors = _runtime_check(
        base, head, body=_body(_RUNTIME, capability="no", navigation="yes", vision="yes")
    )
    assert f"{_RUNTIME} requires 'Capability changed?' = yes" in errors
    assert (
        f"{_RUNTIME} requires 'Repository structure/authority navigation changed?' = no" in errors
    )
    assert f"{_RUNTIME} requires 'Project vision / target-state changed?' = no" in errors


def test_offline_mission_keeps_its_own_impact_expectations(candidate):
    _, base, head = candidate
    errors = _run(base, head, body=_body(capability="no", navigation="yes", vision="yes"))
    assert f"{_MISSION} requires 'Capability changed?' = yes" in errors
    assert not any(" = no" in error for error in errors)


_ATOMIC = "FP_STAGE_D_QUOTA_ADJUDICATION_ATOMIC_PUBLISH"
_ATOMIC_SCOPE_PATH = f"docs/agentic/missions/{_ATOMIC}.json"
_ATOMIC_SOURCE = "src/infrastructure/market_evidence/stageDOperations.js"
_ATOMIC_TEST = "tests/unit/market_evidence/stage_d_quota_adjudication.test.js"
_ATOMIC_PATHS = {_ATOMIC_SCOPE_PATH, _ATOMIC_SOURCE, _ATOMIC_TEST}
_ATOMIC_SCOPE = replace(_SCOPE, mission_id=_ATOMIC, authorized_paths=tuple(sorted(_ATOMIC_PATHS)))


@pytest.fixture
def atomic_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(git_change_helpers, "ROOT_HELPER", tmp_path)
    _git(tmp_path, "init", "-q")
    for file_path in (_ATOMIC_SOURCE, _ATOMIC_TEST):
        _write(tmp_path, file_path, "原有内容\n")
    base = _commit(tmp_path, "Base")
    for file_path in (_ATOMIC_SOURCE, _ATOMIC_TEST):
        _write(tmp_path, file_path, "修复后的内容\n")
    _write(tmp_path, _ATOMIC_SCOPE_PATH, json.dumps(_ATOMIC_SCOPE.to_dict()))
    return tmp_path, base, _commit(tmp_path, "Atomic publication")


def _atomic_check(base, head, *, body=None, paths=None, scope=_ATOMIC_SCOPE):
    if body is None:
        body = (
            "## Scope\n\n"
            "| Task type | source-code |\n"
            "| Workflow class | CRITICAL |\n"
            f"| Mission ID | {_ATOMIC} |\n"
            f"| Mission scope contract | `{_ATOMIC_SCOPE_PATH}` |\n\n" + _impact_body()
        )
    return check_documentation_backflow(
        body,
        _ATOMIC_PATHS if paths is None else paths,
        mission_scope=scope,
        base_ref=base,
        head_ref=head,
    )


def test_atomic_publication_accepts_exact_scope_without_markdown_parser(
    atomic_candidate, monkeypatch
):
    def unexpected_parser(*_args):
        pytest.fail("The narrowly scoped bugfix must not initialize the Markdown parser")

    monkeypatch.setattr(documentation_backflow, "visible_documents", unexpected_parser)
    _, base, head = atomic_candidate
    assert _atomic_check(base, head) == []


def test_atomic_publication_rejects_other_scope_paths_and_declarations(atomic_candidate):
    _, base, head = atomic_candidate
    for paths in (_ATOMIC_PATHS - {_ATOMIC_TEST}, _ATOMIC_PATHS | {"AGENTS.md"}):
        assert any("exact three mission paths" in e for e in _atomic_check(base, head, paths=paths))
    for scope in (
        None,
        replace(_ATOMIC_SCOPE, mission_id="OTHER"),
        replace(_ATOMIC_SCOPE, workflow_class="STRICT"),
        replace(_ATOMIC_SCOPE, authorized_prefixes=("src/",)),
        replace(_ATOMIC_SCOPE, authorized_paths=tuple(sorted(_ATOMIC_PATHS | {"README.md"}))),
    ):
        assert any(
            "validated CRITICAL three-file scope" in e
            for e in _atomic_check(base, head, scope=scope)
        )
    body = _body(_ATOMIC, contract="yes").replace(_ATOMIC_SCOPE_PATH, _RUNTIME_SCOPE_PATH)
    assert any(
        "requires 'Data/model/authorization contract changed?' = no" in e
        for e in _atomic_check(base, head, body=body)
    )
    assert any("scope" in e for e in _atomic_check(base, head, body=body))


@pytest.mark.parametrize("invalid", ["delete", "symlink", "extra"])
def test_atomic_publication_verifies_committed_paths(atomic_candidate, invalid):
    root, base, _ = atomic_candidate
    target = root / _ATOMIC_TEST
    if invalid in {"delete", "symlink"}:
        target.unlink()
        if invalid == "symlink":
            target.symlink_to("other.test.js")
    else:
        _write(root, "AGENTS.md", "unexpected governance change\n")
    bad_head = _commit(root, invalid)
    assert _atomic_check(base, bad_head)
    assert _atomic_check(base[:8], bad_head)
