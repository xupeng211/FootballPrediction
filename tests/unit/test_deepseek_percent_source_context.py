"""离线 Git/伪 backend 回归；不产生正式 receipt 或审核结论。"""

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_chunk_receipt_validation as validator
from scripts.devops import deepseek_review_chunks as chunks
from scripts.devops import independent_review_receipt as receipts
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from tests.unit.test_deepseek_frozen_source_context import evidence, git, rebind


def commit(root):
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=offline",
        "-c",
        "user.email=offline@example.invalid",
        "commit",
        "-qm",
        "offline fixture",
    )
    return git(root, "rev-parse", "HEAD").decode().strip()


@pytest.fixture
def pilot(tmp_path):
    git(tmp_path, "init", "-q")
    for path in chunks.PILOT_SOURCE_CONTEXT_FILES:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("// complete immutable fixture file\n")
    base = commit(tmp_path)
    target = tmp_path / "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Offline fixture, no business implementation.\n")
    head = commit(tmp_path)
    diff = git(tmp_path, "diff", "--binary", "--no-ext-diff", f"{base}...{head}")
    manifest = make_plan(tmp_path, base, head, diff)
    return tmp_path, diff, manifest


def make_plan(root, base, head, diff, **kwargs):
    return chunks.plan(
        diff,
        base_sha=base,
        head_sha=head,
        mission_id=chunks.PILOT_SOURCE_CONTEXT_MISSION,
        mission_scope_sha256="c" * 64,
        source_context_version=chunks.PILOT_SOURCE_CONTEXT_VERSION,
        repo_root=root,
        **kwargs,
    )


def test_complete_git_files_and_validator_agree(pilot):
    root, diff, manifest = pilot
    data = json.loads(manifest.source_context)
    assert [item["path"] for item in data["files"]] == list(chunks.PILOT_SOURCE_CONTEXT_FILES)
    for item in data["files"]:
        assert item["source"].encode() == git(root, "show", f"{manifest.head_sha}:{item['path']}")
    receipt, context, _, _ = evidence(pilot)
    validator._validate_chunked_claude_evidence(receipt, context)
    assert b"".join(item["source"] for item in context.chunked_claude_evidence) == diff
    (root / chunks.PILOT_SOURCE_CONTEXT_FILES[0]).write_text("dirty worktree")
    assert make_plan(root, manifest.base_sha, manifest.head_sha, diff) == manifest


@pytest.mark.parametrize("mutation", ["source", "commit", "remove", "path"])
def test_rehash_cannot_replace_frozen_git_input(pilot, mutation):
    receipt, context, _, _ = evidence(pilot)
    manifest = pilot[2]
    data = json.loads(manifest.source_context)
    if mutation == "remove":
        data["files"].pop()
    elif mutation == "source":
        data["files"][0]["source"] += "tampered"
    elif mutation == "commit":
        data["files"][0]["commit"] = "0" * 40
    else:
        data["files"][0]["path"] = "unauthorized.js"
    rebind(receipt, context, replace(manifest, source_context=canonical_json(data)))
    with pytest.raises(IndependentReviewProtocolError):
        validator._validate_chunked_claude_evidence(receipt, context)


@pytest.mark.parametrize("version", [None, chunks.SOURCE_CONTEXT_VERSION, "unknown"])
def test_pilot_cannot_downgrade(pilot, version):
    root, diff, manifest = pilot
    with pytest.raises(chunks.ChunkReviewError):
        chunks.plan(
            diff,
            base_sha=manifest.base_sha,
            head_sha=manifest.head_sha,
            mission_id=manifest.mission_id,
            mission_scope_sha256="c" * 64,
            source_context_version=version,
            repo_root=root,
        )


@pytest.mark.parametrize("damage", ["missing", "symlink", "utf8", "scope", "capacity"])
def test_invalid_input_rejects_before_backend(pilot, monkeypatch, damage):
    root, _, manifest = pilot
    target = root / chunks.PILOT_SOURCE_CONTEXT_FILES[0]
    if damage == "missing":
        target.unlink()
    elif damage == "symlink":
        target.unlink()
        target.symlink_to("not-a-source")
    elif damage == "utf8":
        target.write_bytes(b"\xff")
    elif damage == "scope":
        (root / "unrelated.txt").write_text("not authorized")
    else:
        target.write_text("x" * chunks.MAX_CHUNK_PROMPT_BYTES)
    head = commit(root)
    diff = git(root, "diff", "--binary", "--no-ext-diff", f"{manifest.base_sha}...{head}")
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
    assert calls == []


def test_final_prompt_capacity_checked_before_dispatch(pilot, monkeypatch):
    root, diff, manifest = pilot
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    monkeypatch.setattr(chunks, "build_chunk_prompt", lambda **_kw: "x" * 40001)
    with pytest.raises(chunks.ChunkReviewError, match="final prompt"):
        runner._run_chunked_review(
            diff=diff,
            base=manifest.base_sha,
            head=manifest.head_sha,
            scope=SimpleNamespace(mission_id=manifest.mission_id),
            scope_sha="c" * 64,
            worktree=root,
        )
    assert calls == []


def test_runner_final_prompt_capacity_checked_after_planning(pilot, monkeypatch):
    root, diff, manifest = pilot
    calls = []
    oversized = "界" * (chunks.MAX_CHUNK_PROMPT_BYTES // len("界".encode()) + 1)
    assert len(oversized) <= chunks.MAX_CHUNK_PROMPT_BYTES < len(oversized.encode())
    monkeypatch.setattr(runner, "plan", lambda *_a, **_k: manifest)
    monkeypatch.setattr(runner, "_chunk_prompt", lambda **_kw: oversized)
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    with pytest.raises(
        runner.DeepSeekReviewError, match="chunk prompt exceeds canonical byte limit"
    ):
        runner._run_chunked_review(
            diff=diff,
            base=manifest.base_sha,
            head=manifest.head_sha,
            scope=SimpleNamespace(mission_id=manifest.mission_id),
            scope_sha="c" * 64,
            worktree=root,
        )
    assert calls == []


def test_real_runner_uses_exact_planner_prompts(pilot, monkeypatch):
    root, diff, manifest = pilot
    _, context, _, _ = evidence(pilot)
    calls = []

    def fake_backend(**kw):
        index = len(calls)
        item = context.chunked_claude_evidence[index]
        assert kw["prompt"].encode() == item["prompt"]
        calls.append(kw)
        e = item["execution"]
        return (
            item["raw"],
            json.loads(item["final"]),
            SimpleNamespace(
                command=e.reviewer_command,
                resolved_model=e.resolved_model,
                cli_version=e.claude_cli_version,
                binary_sha256=e.claude_binary_sha256,
                settings_sha256=e.settings_sha256,
                endpoint=e.provider_endpoint,
                session_id=e.session_id,
            ),
        )

    monkeypatch.setattr(runner.backend, "run", fake_backend)
    _, result, trusted = runner._run_chunked_review(
        diff=diff,
        base=manifest.base_sha,
        head=manifest.head_sha,
        scope=SimpleNamespace(mission_id=manifest.mission_id),
        scope_sha="c" * 64,
        worktree=root,
    )
    assert len(calls) == len(manifest.chunks) == len(trusted)
    assert result["review_result"] == "PASS"
    assert b"".join(item["source"] for item in trusted) == diff


def test_supplied_diff_must_be_exact(pilot):
    root, diff, manifest = pilot
    with pytest.raises(chunks.ChunkReviewError, match="diff"):
        make_plan(root, manifest.base_sha, manifest.head_sha, diff + b"extra\n")


def test_nonchunk_receipt_cannot_skip_pilot_source(pilot):
    receipt, context, _, _ = evidence(pilot)
    receipt["provenance"]["chunked_review"] = False
    with pytest.raises(IndependentReviewProtocolError, match="frozen-source"):
        receipts._validate_claude_deepseek_provenance(
            receipt, {"backend_id": "claude-code-deepseek"}, context
        )


def test_invalid_utf8_diff_is_never_replaced(pilot):
    root, diff, manifest = pilot
    with pytest.raises(chunks.ChunkReviewError, match="UTF-8"):
        make_plan(root, manifest.base_sha, manifest.head_sha, diff + b"\xff")
