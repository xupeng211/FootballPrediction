"""固定 repair 输入离线回归；所有 backend/receipt 均为替身，不是正式审核。

lifecycle: permanent
"""

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_chunk_receipt_validation as validator
from scripts.devops import deepseek_review_chunks as chunks
from scripts.devops import independent_review_receipt as receipts
from scripts.devops import percent_repair_input as consumer
from scripts.devops import percent_repair_packets as producer
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from tests.unit.test_deepseek_frozen_source_context import git
from tests.unit.test_deepseek_review_chunks import _chunk_validation_fixture


@pytest.fixture
def repair():
    root = Path(__file__).resolve().parents[2]
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
    # A broken producer cannot become the consumer's expected answer.
    monkeypatch.setattr(
        chunks, "plan", lambda *_a, **_k: pytest.fail("producer called by consumer")
    )
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


@pytest.mark.parametrize("damage", ["table", "source", "range", "overcap"])
def test_preflight_rejects_before_any_backend(repair, monkeypatch, damage):
    root, head, diff, _ = repair
    read = producer._blob

    def changed(root, revision, path):
        raw, identity = read(root, revision, path)
        if path == producer.TABLE:
            if damage == "table":
                return raw + b" ", identity
            if damage == "range":
                value = json.loads(raw)
                value["packets"].pop()
                return canonical_json(value), identity
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
