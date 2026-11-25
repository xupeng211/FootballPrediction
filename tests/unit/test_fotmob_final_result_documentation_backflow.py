"""用独立 Git 提交覆盖 FotMob 单场赛果的精确文档回流。

lifecycle: permanent
"""

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from scripts.ops.helpers import git_change_helpers
from scripts.ops.helpers.agent_workflow_contract import MissionScope
from scripts.ops.helpers.documentation_backflow import check_documentation_backflow

_MISSION = "FP_FOTMOB_FINAL_RESULT_ASOF_OFFLINE"
_SCOPE_PATH = f"docs/agentic/missions/{_MISSION}.json"
_GD_DOC = "docs/data/GD_A02_FACTS_CONTRACT.md"
_ASOF_DOC = "docs/data/MODEL_ASOF_CONTRACT.md"
_CAPABILITY = "docs/CAPABILITY_INDEX.md"
_DOCS = (_GD_DOC, _ASOF_DOC, _CAPABILITY)
_PATHS = {
    _SCOPE_PATH,
    *_DOCS,
    "src/infrastructure/fotmob/FotMobDetailCaptureContract.js",
    "src/infrastructure/fotmob/FotMobDetailCapturePipeline.js",
    "src/infrastructure/golden_dataset/FotMobPriorResultProjection.js",
    "src/ml/inference/fotmob_prior_result_asof.py",
    "tests/unit/fotmob_detail_transport_observability.test.js",
    "tests/unit/fotmob_prior_result_projection.test.js",
    "tests/unit/ml/test_fotmob_prior_result_asof.py",
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
        "protected_invariants": ["Keep original authorization."],
        "forbidden_side_effects": ["Do not create external side effects."],
    }
)
_BASE_DOC = """# Existing authority
Existing introductory context.

## Existing scope
Existing source and content requirements.

## Existing cutoff
Existing timing boundary.
"""
_UPDATE = "\n## One archived result\nRetain one validated result and its timing proof.\n"


def _body(*, declared=_DOCS, contract="yes", capability="yes", source_updated="yes"):
    return f"""## Scope

| Task type | source-code |
| Workflow class | CRITICAL |
| Mission ID | {_MISSION} |
| Mission scope contract | `{_SCOPE_PATH}` |

## Documentation Impact

| Capability changed? | {capability} |
| Milestone changed? | no |
| Canonical entrypoint changed? | no |
| Current blocker changed? | no |
| Data/model/authorization contract changed? | {contract} |
| Repository structure/authority navigation changed? | no |
| Project vision / target-state changed? | no |
| Source-of-truth docs updated | {source_updated} |
| Updated authoritative docs | {", ".join(declared)} |
| If not updated, explicit reason | The existing entrypoint and milestone remain scoped to offline validation. |
"""


def _git(root, *args):
    return subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _commit(root, title):
    _git(root, "add", "-A")
    _git(root, "commit", "-m", title)
    return _git(root, "rev-parse", "HEAD")


def _write(root, path, value):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(value, encoding="utf-8")


def _commit_candidate(tmp_path, monkeypatch, base_doc):
    monkeypatch.setattr(git_change_helpers, "ROOT_HELPER", tmp_path)
    _git(tmp_path, "init", "-q")
    for path in _DOCS:
        _write(tmp_path, path, base_doc)
    base = _commit(tmp_path, "Existing docs")
    for path in _DOCS:
        _write(tmp_path, path, base_doc + _UPDATE)
    for path in _PATHS - set(_DOCS):
        value = json.dumps(_SCOPE.to_dict()) if path == _SCOPE_PATH else "bounded fixture change\n"
        _write(tmp_path, path, value)
    head = _commit(tmp_path, "One business change")
    return tmp_path, base, head


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    return _commit_candidate(tmp_path, monkeypatch, _BASE_DOC)


def _check(base, head, *, body=None, scope=_SCOPE, changed=None):
    changes = git_change_helpers.collect_changes(base, head, include_worktree=False)
    return check_documentation_backflow(
        _body() if body is None else body,
        git_change_helpers.changed_paths(changes) if changed is None else changed,
        changes=changes,
        mission_scope=scope,
        base_ref=base,
        head_ref=head,
    )


def test_uses_exact_git_documents_even_with_different_checkout_bytes(candidate):
    root, base, head = candidate
    assert _check(base, head) == []
    _write(root, _GD_DOC, "# Shell in the checkout\n")
    assert _check(base, head) == []
    invalid_head = _commit(root, "Replace the committed doc")
    _write(root, _GD_DOC, _BASE_DOC + _UPDATE)
    assert any("changed visible document body" in error for error in _check(base, invalid_head))


@pytest.mark.parametrize(
    "extra",
    [
        "notes.md",
        "scripts/ops/helpers/documentation_backflow.py",
        "src/infrastructure/market_evidence/stageDOperations.js",
        "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md",
        "docs/agentic/missions/FP_QUALITY_MARKDOWN_PERCENT_20261105.json",
    ],
)
def test_added_paths_cannot_be_authorized_by_scope_list(candidate, extra):
    root, base, _ = candidate
    _write(root, extra, "outside the exact combination\n")
    head = _commit(root, "One extra file")
    broad_scope = replace(_SCOPE, authorized_paths=(*_SCOPE.authorized_paths, extra))
    assert any(
        "exact 11 mission paths" in error and extra in error
        for error in _check(base, head, scope=broad_scope)
    )


@pytest.mark.parametrize("missing", [_GD_DOC, _ASOF_DOC, _CAPABILITY, _SCOPE_PATH])
def test_missing_required_git_change_is_rejected(candidate, missing):
    root, base, _ = candidate
    file = root / missing
    if missing == _SCOPE_PATH:
        file.unlink()
    else:
        _write(root, missing, _BASE_DOC)
    head = _commit(root, "Omit required delta")
    assert any(
        "exact 11 mission paths" in error and missing in error for error in _check(base, head)
    )


@pytest.mark.parametrize(
    "declared",
    [
        (_ASOF_DOC, _CAPABILITY),
        (_GD_DOC, _CAPABILITY),
        (_GD_DOC, _ASOF_DOC),
        (_GD_DOC, _CAPABILITY, "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md"),
    ],
)
def test_must_name_all_three_authoritative_docs(candidate, declared):
    _, base, head = candidate
    missing = next(iter(set(_DOCS) - set(declared)))
    assert any(
        "in the changed and declared docs" in error and missing in error
        for error in _check(base, head, body=_body(declared=declared))
    )


@pytest.mark.parametrize("field", ["contract", "capability", "source_updated"])
def test_false_impact_declarations_cannot_open_the_mapping(candidate, field):
    _, base, head = candidate
    assert any("= yes" in error for error in _check(base, head, body=_body(**{field: "no"})))


def test_scope_and_body_identity_and_class_are_bound(candidate):
    _, base, head = candidate
    assert _check(base, head, scope=None)
    assert _check(base, head, scope=replace(_SCOPE, mission_id="UNAPPROVED"))
    assert _check(
        base, head, body=_body().replace(f"Mission ID | {_MISSION}", "Mission ID | UNAPPROVED")
    )
    assert _check(base, head, scope=replace(_SCOPE, workflow_class="STRICT"))
    assert _check(
        base, head, body=_body().replace("Workflow class | CRITICAL", "Workflow class | STRICT")
    )


@pytest.mark.parametrize(
    "mode",
    [
        "delete",
        "rename",
        "symlink",
        "empty",
        "headings",
        "setext-heading",
        "comment",
        "multiline-comment",
        "unclosed-comment",
        "unclosed-comment-before-body",
        "hidden-html",
        "multiline-hidden-html",
        "heading-and-whitespace",
        "line-break-only",
        "line-break-with-attributes",
        "shell",
    ],
)
def test_non_updates_cannot_satisfy_authoritative_backflow(candidate, mode):
    root, base, _ = candidate
    doc = root / _ASOF_DOC
    if mode == "delete":
        doc.unlink()
    elif mode == "rename":
        _git(root, "mv", _ASOF_DOC, _ASOF_DOC + ".bak")
    elif mode == "symlink":
        doc.unlink()
        doc.symlink_to(Path(_GD_DOC).name)
    else:
        replacement = {
            "empty": "",
            "headings": "# Existing authority\n## Existing scope\n## Existing cutoff\n",
            "setext-heading": "A title with an underline\n=========================\n",
            "comment": _BASE_DOC + "\n<!-- A claimed update. -->",
            "multiline-comment": _BASE_DOC + "\n<!--\nA claimed update.\n-->\n",
            "unclosed-comment": _BASE_DOC + "\n<!-- A claimed update.\n",
            "unclosed-comment-before-body": "# Existing authority\n<!--\n" + _BASE_DOC + _UPDATE,
            "hidden-html": _BASE_DOC + "\n<div hidden>A claimed update.</div>\n",
            "multiline-hidden-html": _BASE_DOC + "\n<div\nhidden>\nA claimed update.\n</div>\n",
            "heading-and-whitespace": _BASE_DOC.replace("# Existing authority", "# Updated title")
            + "\n\n",
            "line-break-only": _BASE_DOC.replace("Existing timing", "Existing<br />timing"),
            "line-break-with-attributes": _BASE_DOC + "\n<br hidden>Claimed update.\n",
            "shell": "# Placeholder\n\n<!-- A claimed update. -->\n",
        }
        _write(root, _ASOF_DOC, replacement[mode])
    head = _commit(root, f"Invalid authoritative update: {mode}")
    assert _check(base, head)


def test_worktree_paths_cannot_claim_authoritative_update_at_same_revision(candidate):
    _, base, _ = candidate
    assert any("exact revisions" in error for error in _check(base, base, changed=_PATHS))


def test_title_and_entire_short_section_can_be_rewritten(candidate):
    root, base, _ = candidate
    doc = _BASE_DOC.replace("# Existing authority", "# Revised authority").replace(
        "## Existing cutoff\nExisting timing boundary.",
        "## Verified observation boundary\nAdmit only an observation verified before the cutoff.",
    )
    _write(root, _ASOF_DOC, doc)
    head = _commit(root, "Rewrite one authority section")
    assert _check(base, head) == []


def test_visible_body_after_multiline_comment_is_accepted(candidate):
    root, base, _ = candidate
    _write(
        root,
        _ASOF_DOC,
        _BASE_DOC + "\n<!--\nLocal writing note.\n-->\n" + _UPDATE + "Use `--file <path>`.\n",
    )
    head = _commit(root, "Update visible text and retain a comment")
    assert _check(base, head) == []


@pytest.mark.parametrize("line_break", ["<br>", "<br/>", "<BR />"])
def test_visible_body_after_line_break_is_accepted(candidate, line_break):
    root, base, _ = candidate
    _write(root, _ASOF_DOC, _BASE_DOC + f"\n{line_break}记录终场比分及其观察时间。\n")
    head = _commit(root, "Add a visible sentence after a line break")
    assert _check(base, head) == []


@pytest.mark.parametrize("format_character", ["\u200b", "\u200d"])
def test_unicode_format_character_alone_is_not_a_body_update(candidate, format_character):
    root, base, _ = candidate
    _write(root, _ASOF_DOC, _BASE_DOC.replace("introductory", f"intro{format_character}ductory"))
    head = _commit(root, "Change only a zero-width character")
    assert any("changed visible document body" in error for error in _check(base, head))


@pytest.mark.parametrize("phrase", ["曼城", "City", "2–1"])
def test_combining_grapheme_joiner_alone_is_not_a_body_update(tmp_path, monkeypatch, phrase):
    base_doc = _BASE_DOC + f"\n终场记录：{phrase}。\n"
    root, base, _ = _commit_candidate(tmp_path, monkeypatch, base_doc)
    revised = base_doc.replace(phrase, f"{phrase[0]}\u034f{phrase[1:]}")
    _write(root, _ASOF_DOC, revised)
    head = _commit(root, "Change only a combining grapheme joiner")
    assert any("changed visible document body" in error for error in _check(base, head))


@pytest.mark.parametrize(("original", "revised"), [("Malmo", "Malmo\u0308"), ("♥", "♥\ufe0f")])
def test_team_name_accent_and_emoji_selection_are_preserved(
    tmp_path, monkeypatch, original, revised
):
    base_doc = _BASE_DOC + "\n终场比分：Malmo 2–1 哥德堡。记录标记：♥。\n"
    root, base, _ = _commit_candidate(tmp_path, monkeypatch, base_doc)
    _write(root, _ASOF_DOC, base_doc.replace(original, revised))
    head = _commit(root, "Keep an author-visible text change")
    assert _check(base, head) == []


@pytest.mark.parametrize("change_visible_score", [False, True])
def test_existing_hidden_body_does_not_count_but_visible_score_does(
    tmp_path, monkeypatch, change_visible_score
):
    base_doc = (
        _BASE_DOC + "\n<div hidden><p>内部备注。<br>暂存。</p></div>\n\n终场比分：曼城 1–1 狼队。\n"
    )
    root, base, _ = _commit_candidate(tmp_path, monkeypatch, base_doc)
    revised = base_doc.replace("内部备注", "更新内部备注")
    if change_visible_score:
        revised = revised.replace("曼城 1–1", "曼城 2–1")
    _write(root, _ASOF_DOC, revised)
    head = _commit(root, "Edit hidden notes and optionally correct a visible score")
    assert (not _check(base, head)) is change_visible_score


def test_author_can_add_a_fenced_code_example(candidate):
    root, base, _ = candidate
    _write(
        root,
        _ASOF_DOC,
        _BASE_DOC + "\n示例命令<br>输出模板如下。\n\n```text\n<result>2–1</result>\n```\n",
    )
    head = _commit(root, "Add a markup example as literal text")
    assert _check(base, head) == []
