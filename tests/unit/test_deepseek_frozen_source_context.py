"""冻结源码合同离线验收；内存执行证据不是真实审核Receipt。"""

from dataclasses import replace
import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_chunk_receipt_validation as validator
from scripts.devops import deepseek_review_chunks as chunks
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
    sha256_bytes,
)
from tests.unit.test_deepseek_review_chunks import _chunk_validation_fixture


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


@pytest.fixture
def frozen(tmp_path):
    git(tmp_path, "init")
    for path, symbols in chunks.SOURCE_CONTEXT_DEFINITIONS.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(f"def {symbol}():\n    return 1\n\n" for symbol in symbols))
    git(tmp_path, "add", ".")
    git(
        tmp_path,
        "-c",
        "user.name=offline",
        "-c",
        "user.email=offline@example.invalid",
        "commit",
        "-m",
        "base",
    )
    base = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    (tmp_path / "change.txt").write_text("new\n" * 200)
    git(tmp_path, "add", ".")
    git(
        tmp_path,
        "-c",
        "user.name=offline",
        "-c",
        "user.email=offline@example.invalid",
        "commit",
        "-m",
        "head",
    )
    head = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    diff = git(tmp_path, "diff", "--binary", "--no-ext-diff", f"{base}...{head}")
    manifest = chunks.plan(
        diff,
        base_sha=base,
        head_sha=head,
        mission_id=chunks.SOURCE_CONTEXT_MISSION,
        mission_scope_sha256="c" * 64,
        source_context_version=chunks.SOURCE_CONTEXT_VERSION,
        repo_root=tmp_path,
    )
    return tmp_path, diff, manifest


def evidence(frozen):
    root, diff, manifest = frozen
    return _chunk_validation_fixture(
        root,
        diff,
        base_sha=manifest.base_sha,
        head_sha=manifest.head_sha,
        mission_id=manifest.mission_id,
        manifest=manifest,
    )


def rebind(receipt, context, manifest):
    """模拟攻击者重算所有本地摘要，仍须被独立Git重建拒绝。"""
    top = json.loads(context.raw_output_bytes)
    top["manifest"] = manifest.payload()
    top["manifest_sha256"] = manifest.sha256
    receipt["provenance"]["chunk_manifest_sha256"] = manifest.sha256
    for descriptor, item, entry in zip(
        manifest.chunks, context.chunked_claude_evidence, top["chunks"], strict=True
    ):
        item["prompt"] = chunks.build_chunk_prompt(
            chunk=descriptor, source=item["source"], manifest=manifest, scope_sha="c" * 64
        ).encode()
        item["execution"] = replace(
            item["execution"],
            reviewer_command=(*item["execution"].reviewer_command[:-1], item["prompt"].decode()),
        )
        entry["prompt_sha256"] = sha256_bytes(item["prompt"])
    receipt["provenance"]["chunk_evidence_manifest_sha256"] = sha256_bytes(
        chunks.chunk_evidence_manifest_bytes(top["chunks"])
    )
    context.raw_output_bytes = canonical_json(top)


def test_legacy_and_complete_context_are_distinct_valid_contracts(frozen):
    root, diff, manifest = frozen
    receipt, context, _, _ = evidence(frozen)
    validator._validate_chunked_claude_evidence(receipt, context)
    legacy = chunks.plan(
        diff,
        base_sha=manifest.base_sha,
        head_sha=manifest.head_sha,
        mission_id=manifest.mission_id,
        mission_scope_sha256="c" * 64,
    )
    assert "source_context_version" not in legacy.payload()
    old_receipt, old_context, _, _ = _chunk_validation_fixture(
        root,
        diff,
        base_sha=manifest.base_sha,
        head_sha=manifest.head_sha,
        mission_id=manifest.mission_id,
    )
    validator._validate_chunked_claude_evidence(old_receipt, old_context)
    data = json.loads(manifest.source_context)
    assert len(data["definitions"]) == sum(map(len, chunks.SOURCE_CONTEXT_DEFINITIONS.values()))
    assert all(
        [v["version"] for v in d["versions"]] == ["BASE", "HEAD"] for d in data["definitions"]
    )
    assert b"".join(diff[c.start : c.end] for c in manifest.chunks) == diff
    assert all(
        len(i["prompt"]) <= chunks.MAX_CHUNK_PROMPT_BYTES for i in context.chunked_claude_evidence
    )


@pytest.mark.parametrize("mutation", ["source", "commit", "path", "remove", "downgrade", "unknown"])
def test_rehashed_context_mutations_rejected_by_git_reconstruction(frozen, mutation):
    receipt, context, _, _ = evidence(frozen)
    manifest = frozen[2]
    data = json.loads(manifest.source_context)
    if mutation == "source":
        data["definitions"][0]["source"] += "# tampered\n"
    elif mutation == "commit":
        data["definitions"][0]["versions"][0]["commit"] = "0" * 40
    elif mutation == "path":
        data["definitions"][0]["path"] = "private/unauthorized.py"
    elif mutation == "remove":
        data["definitions"].pop()
    version = (
        None
        if mutation == "downgrade"
        else "unknown/v9"
        if mutation == "unknown"
        else chunks.SOURCE_CONTEXT_VERSION
    )
    rebind(
        receipt,
        context,
        replace(manifest, source_context=canonical_json(data), source_context_version=version),
    )
    with pytest.raises(IndependentReviewProtocolError):
        validator._validate_chunked_claude_evidence(receipt, context)


def test_worktree_is_never_used_and_unauthorized_path_rejected(frozen, monkeypatch):
    root, _, manifest = frozen
    (root / next(iter(chunks.SOURCE_CONTEXT_DEFINITIONS))).write_text("untrusted worktree bytes")
    assert (
        chunks._source_context(root, manifest.base_sha, manifest.head_sha)
        == manifest.source_context
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("不得读取未授权路径")

    with monkeypatch.context() as patch:
        patch.setattr(chunks.subprocess, "run", forbidden)
        with pytest.raises(chunks.ChunkReviewError, match="not authorized"):
            chunks._frozen_context_file(root, manifest.head_sha, "../secret")


@pytest.mark.parametrize("damage", ["missing", "ambiguous", "symlink"])
def test_invalid_frozen_definition_stops_before_any_dispatch(frozen, monkeypatch, damage):
    root, diff, manifest = frozen
    target = root / next(iter(chunks.SOURCE_CONTEXT_DEFINITIONS))
    if damage == "symlink":
        target.unlink()
        target.symlink_to("change.txt")
    else:
        target.write_text(
            ""
            if damage == "missing"
            else target.read_text() + "\ndef _fixture_items():\n    pass\n"
        )
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=offline",
        "-c",
        "user.email=offline@example.invalid",
        "commit",
        "-m",
        "damaged",
    )
    head = git(root, "rev-parse", "HEAD").decode().strip()
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    with pytest.raises(chunks.ChunkReviewError):
        runner._run_chunked_review(
            diff=diff,
            base=manifest.base_sha,
            head=head,
            scope=SimpleNamespace(mission_id=manifest.mission_id),
            scope_sha="c" * 64,
            worktree=root,
        )
    assert not calls


def test_oversize_and_coverage_fail_closed_before_dispatch(frozen, monkeypatch):
    root, diff, manifest = frozen
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    with monkeypatch.context() as patch:
        patch.setattr(
            chunks, "_source_context", lambda *_args: b"x" * chunks.MAX_CHUNK_PROMPT_BYTES
        )
        with pytest.raises(chunks.ChunkReviewError, match="capacity"):
            runner._run_chunked_review(
                diff=diff,
                base=manifest.base_sha,
                head=manifest.head_sha,
                scope=SimpleNamespace(mission_id=manifest.mission_id),
                scope_sha="c" * 64,
                worktree=root,
            )
    with monkeypatch.context() as patch:
        patch.setattr(
            runner, "_chunk_prompt", lambda **_kw: "x" * (chunks.MAX_CHUNK_PROMPT_BYTES + 1)
        )
        with pytest.raises(runner.DeepSeekReviewError, match="byte limit"):
            runner._run_chunked_review(
                diff=diff,
                base=manifest.base_sha,
                head=manifest.head_sha,
                scope=SimpleNamespace(mission_id=manifest.mission_id),
                scope_sha="c" * 64,
                worktree=root,
            )
    assert not calls
    with pytest.raises(chunks.ChunkReviewError):
        chunks.validate_manifest(replace(manifest, chunks=manifest.chunks[1:]), diff)


def test_versioned_contract_preserves_tool_isolation(frozen):
    receipt, context, item, _ = evidence(frozen)
    command = list(item["execution"].reviewer_command)
    command[command.index("--tools") + 1] = "Read"
    item["execution"] = replace(item["execution"], reviewer_command=tuple(command))
    with pytest.raises(IndependentReviewProtocolError, match="canonical isolated"):
        validator._validate_chunked_claude_evidence(receipt, context)
