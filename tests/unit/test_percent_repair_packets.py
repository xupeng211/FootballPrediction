"""固定 repair 输入离线回归；所有 backend/receipt 均为替身，不是正式审核。

lifecycle: permanent
"""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_chunk_receipt_validation as validator
from scripts.devops import deepseek_review_chunks as chunks
from scripts.devops import independent_review_receipt as receipts
from scripts.devops import percent_repair_input as consumer
from scripts.devops import percent_repair_packets as producer
from scripts.devops.deepseek_receipt_evidence import _deepseek_receipt_evidence
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from tests.unit.test_deepseek_frozen_source_context import git
from tests.unit.test_deepseek_review_chunks import _chunk_validation_fixture


def _repair_sample(destination, source_root):
    """仅投影表内源码到私有 TEST Git；不写源仓库，不改变正式完整 diff 规则。"""
    try:
        git(source_root, "cat-file", "-e", producer.BASE + "^{commit}")
    except subprocess.CalledProcessError:
        pytest.fail("repair TEST sample requires the original BASE object; no network fetch")
    current = git(source_root, "rev-parse", "HEAD").decode().strip()
    raw = git(source_root, "show", current + ":" + producer.TABLE)
    assert chunks.sha256_bytes(raw) == producer.TABLE_SHA256
    paths = tuple(dict.fromkeys(row["diff_path"] for row in json.loads(raw)["packets"]))
    destination.mkdir()
    git(destination, "init", "-q")
    common = git(source_root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    # Git 只读借用来源对象，所有新增对象、索引和 refs 都在临时仓库。
    (destination / ".git/objects/info/alternates").write_text(
        str(Path(common.decode().strip()) / "objects") + "\n"
    )
    git(destination, "read-tree", producer.BASE + "^{tree}")
    for path in paths:
        entry = git(source_root, "ls-tree", "-z", current, "--", path).rstrip(b"\0")
        metadata, actual = entry.split(b"\t")
        mode, kind, oid = metadata.decode().split()
        assert actual.decode() == path
        assert kind == "blob"
        assert mode in {"100644", "100755"}
        git(destination, "update-index", "--add", "--cacheinfo", mode + "," + oid + "," + path)
    tree = git(destination, "write-tree").decode().strip()
    head = (
        git(
            destination,
            "-c",
            "user.name=offline",
            "-c",
            "user.email=offline@example.invalid",
            "commit-tree",
            tree,
            "-p",
            producer.BASE,
            "-m",
            "TEST ONLY table-path sample",
        )
        .decode()
        .strip()
    )
    git(destination, "checkout", "-q", "-b", "repair-test", head)
    git(destination, "checkout-index", "--all")
    return destination


def _repair_inputs(root):
    head = git(root, "rev-parse", "HEAD").decode().strip()
    diff = git(root, "diff", "--binary", "--no-ext-diff", producer.BASE + "..." + head)
    manifest = chunks.plan(
        diff,
        base_sha=producer.BASE,
        head_sha=head,
        mission_id=producer.MISSION,
        mission_scope_sha256="c" * 64,
        source_context_version=producer.VERSION,
        repo_root=root,
    )
    return root, head, diff, manifest


@pytest.fixture
def repair(tmp_path):
    source_root = Path(__file__).resolve().parents[2]
    return _repair_inputs(_repair_sample(tmp_path / "repair", source_root))


def test_independent_reconstruction_and_complete_coverage(repair):
    root, head, diff, manifest = repair
    rebuilt = consumer.reconstruct(root, producer.BASE, head, producer.MISSION, "c" * 64, diff)
    assert rebuilt.payload() == manifest.payload()
    assert b"".join(diff[c.start : c.end] for c in manifest.chunks) == diff
    for c, expected in zip(manifest.chunks, rebuilt.prompts, strict=True):
        actual = chunks.build_chunk_prompt(
            chunk=c, source=diff[c.start : c.end], manifest=manifest, scope_sha="c" * 64
        ).encode()
        assert actual == expected
        assert len(actual) <= chunks.MAX_CHUNK_PROMPT_BYTES
        assert c.end - c.start <= chunks.MAX_CHUNK_DIFF_BYTES
    assert len(manifest.chunks) <= chunks.MAX_CHUNK_COUNT


def test_isolated_sample_survives_unrelated_live_path(repair, tmp_path):
    root, _, _, _ = repair
    test_independent_reconstruction_and_complete_coverage(repair)
    added = "docs/offline-test-unrelated.txt"
    (root / added).write_text("TEST ONLY ordinary new path\n")
    git(root, "add", "--", added)
    git(
        root,
        "-c",
        "user.name=offline",
        "-c",
        "user.email=offline@example.invalid",
        "commit",
        "-q",
        "-m",
        "TEST ONLY unrelated development",
    )
    live = git(root, "rev-parse", "HEAD").decode().strip()
    full = git(root, "diff", "--binary", "--no-ext-diff", producer.BASE + "..." + live)
    with pytest.raises(ValueError, match=r"^repair table does not cover the exact changed paths$"):
        chunks.plan(
            full,
            base_sha=producer.BASE,
            head_sha=live,
            mission_id=producer.MISSION,
            mission_scope_sha256="c" * 64,
            source_context_version=producer.VERSION,
            repo_root=root,
        )
    with pytest.raises(ValueError, match=r"^repair fixed ranges mismatch$"):
        consumer.reconstruct(root, producer.BASE, live, producer.MISSION, "c" * 64, full)
    projected = _repair_inputs(_repair_sample(tmp_path / "projected", root))
    test_independent_reconstruction_and_complete_coverage(projected)
    assert added not in projected[3].full_changed_paths
    assert git(root, "rev-parse", "HEAD").decode().strip() == live


def fake_evidence(repair):
    root, head, diff, manifest = repair
    return _chunk_validation_fixture(
        root,
        diff,
        base_sha=producer.BASE,
        head_sha=head,
        mission_id=producer.MISSION,
        manifest=manifest,
    )


def test_real_runner_and_consumer_use_identical_inputs(repair, monkeypatch):
    root, head, diff, manifest = repair
    receipt, context, _, _ = fake_evidence(repair)
    calls = []

    def fake_backend(**kw):
        item = context.chunked_claude_evidence[len(calls)]
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
    runner._run_chunked_review(
        diff=diff,
        base=producer.BASE,
        head=head,
        scope=SimpleNamespace(mission_id=producer.MISSION),
        scope_sha="c" * 64,
        worktree=root,
    )
    assert len(calls) == len(manifest.chunks)
    # 合法 fixture 和 runner 输入已准备好，再禁止验证路径借用 producer。
    # 同时拦截直接导入的绑定别名，不能只 patch 定义模块的属性。
    producer_entries = (chunks.plan, producer.repair_plan)

    def producer_called(*_a, **_k):
        pytest.fail("producer called by consumer")

    for module in (chunks, producer, validator, consumer, runner):
        for name, value in tuple(vars(module).items()):
            if any(value is entry for entry in producer_entries):
                monkeypatch.setattr(module, name, producer_called)
    validator._validate_chunked_claude_evidence(receipt, context)


@pytest.mark.parametrize(
    "damage", ["missing", "argv", "prompt", "source", "manifest", "raw", "session", "range"]
)
def test_synthetic_execution_tampering_rejected(repair, damage):
    receipt, context, item, _ = fake_evidence(repair)
    if damage == "missing":
        context.chunked_claude_evidence = context.chunked_claude_evidence[:-1]
    elif damage == "argv":
        item["execution"] = replace(
            item["execution"], reviewer_command=(*item["execution"].reviewer_command[:-1], "wrong")
        )
    elif damage == "prompt":
        item["prompt"] += b"tamper"
    elif damage == "source":
        item["source"] += b"tamper"
    elif damage == "manifest":
        receipt["provenance"]["chunk_manifest_sha256"] = "0" * 64
    elif damage == "raw":
        item["raw"] = canonical_json({"is_error": True})
    elif damage == "session":
        item["execution"] = replace(item["execution"], session_id="other")
    else:
        top = json.loads(context.raw_output_bytes)
        top["manifest"]["chunks"][0]["end"] -= 1
        context.raw_output_bytes = canonical_json(top)
    with pytest.raises(IndependentReviewProtocolError):
        validator._validate_chunked_claude_evidence(receipt, context)


@pytest.mark.parametrize("damage", ["table", "source", "overcap"])
def test_preflight_rejects_before_any_backend(repair, monkeypatch, damage):
    root, head, diff, _ = repair
    read = producer._blob

    def changed(root, revision, path):
        raw, identity = read(root, revision, path)
        if path == producer.TABLE:
            if damage == "table":
                return raw + b" ", identity
        elif damage == "source":
            return None, "ABSENT"
        return raw, identity

    monkeypatch.setattr(producer, "_blob", changed)
    if damage == "overcap":
        monkeypatch.setattr(chunks, "build_chunk_prompt", lambda **_k: "x" * 40001)
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    with pytest.raises((ValueError, chunks.ChunkReviewError)):
        runner._run_chunked_review(
            diff=diff,
            base=producer.BASE,
            head=head,
            scope=SimpleNamespace(mission_id=producer.MISSION),
            scope_sha="c" * 64,
            worktree=root,
        )
    assert calls == []
    if damage != "overcap":
        monkeypatch.setattr(consumer, "_read", changed)
        with pytest.raises(ValueError, match=r"unapproved|missing"):
            consumer.reconstruct(root, producer.BASE, head, producer.MISSION, "c" * 64, diff)


def _admit_terminal_gap(repair, monkeypatch):
    """只在测试进程内提供身份正确、摘要匹配的终端缺口表。"""
    root, head, diff, _ = repair
    original_blob, original_read = producer._blob, consumer._read
    raw, identity = original_blob(root, head, producer.TABLE)
    table = json.loads(raw)
    table["packets"].pop()
    damaged = canonical_json(table)

    def changed_blob(root, revision, path):
        return (
            (damaged, identity) if path == producer.TABLE else original_blob(root, revision, path)
        )

    def changed_read(root, revision, path):
        return (
            (damaged, identity) if path == consumer.TABLE else original_read(root, revision, path)
        )

    monkeypatch.setattr(producer, "_blob", changed_blob)
    monkeypatch.setattr(consumer, "_read", changed_read)
    monkeypatch.setattr(producer, "TABLE_SHA256", chunks.sha256_bytes(damaged))
    monkeypatch.setattr(consumer, "TABLE_SHA256", chunks.sha256_bytes(damaged))
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kw: calls.append(kw))
    return root, head, diff, calls


def test_producer_terminal_gap_rejected_after_digest(repair, monkeypatch):
    # fixture 已由真实 planner 生成合法 manifest，然后才损坏覆盖。
    assert repair[3].full_diff_bytes == len(repair[2])
    root, head, diff, calls = _admit_terminal_gap(repair, monkeypatch)
    with pytest.raises(ValueError, match=r"^repair packets are incomplete or over count$"):
        runner._run_chunked_review(
            diff=diff,
            base=producer.BASE,
            head=head,
            scope=SimpleNamespace(mission_id=producer.MISSION),
            scope_sha="c" * 64,
            worktree=root,
        )
    assert calls == []


def test_reader_terminal_gap_rejected_after_digest(repair, monkeypatch):
    root, head, diff, manifest = repair
    # reader 的合法基线与错误预期独立定义，不借 producer 生成期望答案。
    legal = consumer.reconstruct(root, producer.BASE, head, producer.MISSION, "c" * 64, diff)
    assert legal.payload() == manifest.payload()
    root, head, diff, calls = _admit_terminal_gap(repair, monkeypatch)
    with pytest.raises(ValueError, match=r"^repair coverage/count rejected$"):
        consumer.reconstruct(root, producer.BASE, head, producer.MISSION, "c" * 64, diff)
    assert calls == []


def test_wrong_diff_identity_and_downgrade_reject(repair):
    root, head, diff, _ = repair
    with pytest.raises(ValueError, match="diff"):
        consumer.reconstruct(root, producer.BASE, head, producer.MISSION, "c" * 64, diff + b"x")
    with pytest.raises(chunks.ChunkReviewError):
        chunks.plan(
            diff,
            base_sha=producer.BASE,
            head_sha=head,
            mission_id=producer.MISSION,
            mission_scope_sha256="c" * 64,
            repo_root=root,
        )
    receipt, context, _, _ = fake_evidence(repair)
    receipt["provenance"]["chunked_review"] = False
    with pytest.raises(IndependentReviewProtocolError):
        receipts._validate_claude_deepseek_provenance(
            receipt, {"backend_id": "claude-code-deepseek"}, context
        )


def test_physical_canonical_receipt_format_and_corruption(repair, monkeypatch, tmp_path):
    """Full durable file format, fake backend only; never a formal receipt approval."""
    root, head, _, _ = repair
    _, fake, _, _ = fake_evidence(repair)
    index = 0

    def fake_backend(**kw):
        nonlocal index
        item = fake.chunked_claude_evidence[index]
        index += 1
        e = item["execution"]
        return (
            item["raw"],
            json.loads(item["final"]),
            SimpleNamespace(
                command=(*e.reviewer_command[:-1], kw["prompt"]),
                resolved_model=e.resolved_model,
                cli_version=e.claude_cli_version,
                binary_sha256=e.claude_binary_sha256,
                settings_sha256=e.settings_sha256,
                endpoint=e.provider_endpoint,
                session_id=e.session_id,
            ),
        )

    monkeypatch.setattr(runner.backend, "run", fake_backend)
    scope_path = "docs/agentic/missions/" + producer.MISSION + ".json"
    evidence = tmp_path / "SYNTHETIC_NOT_FORMAL_REVIEW"
    args = SimpleNamespace(
        repo_root=root,
        base_sha=producer.BASE,
        head_sha=head,
        mission_id=producer.MISSION,
        mission_scope_file=root / scope_path,
        evidence_dir=evidence,
        retain_invocation=False,
    )
    receipt_path = runner.run_review(args)
    scope_hash = chunks.sha256_bytes(git(root, "show", head + ":" + scope_path))

    def consume():
        return _deepseek_receipt_evidence(
            receipt_path,
            repo_root=root,
            expected_base=producer.BASE,
            expected_head=head,
            expected_mission_id=producer.MISSION,
            expected_scope_hash=scope_hash,
        )

    assert consume().trusted is True
    prompt = next(evidence.glob("claude-deepseek-chunk-prompt-*.txt"))
    prompt.write_bytes(prompt.read_bytes() + b"corruption")
    assert consume().trusted is False
