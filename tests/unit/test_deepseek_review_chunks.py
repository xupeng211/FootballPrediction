from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from scripts.devops import deepseek_chunk_receipt_validation as chunk_validation
from scripts.devops.deepseek_review_chunks import (
    MAX_CHUNK_COUNT,
    MAX_CHUNK_DIFF_BYTES,
    ChunkReviewError,
    aggregate,
    build_chunk_prompt,
    chunk_evidence_manifest_bytes,
    plan,
    validate_manifest,
)
from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    IndependentReviewProtocolError,
    canonical_json,
    sha256_bytes,
)
from scripts.devops.independent_review_receipt import ClaudeDeepSeekExecutionEvidence


def test_chunk_evidence_manifest_ignores_transport_only_execution_metadata():
    entry = {
        "index": 0,
        "source_sha256": "a" * 64,
        "prompt_sha256": "b" * 64,
        "raw_sha256": "c" * 64,
        "final_sha256": "d" * 64,
        "session_id": "fresh",
        "execution": {"provider_endpoint": "https://api.deepseek.com/anthropic"},
    }
    assert chunk_evidence_manifest_bytes([entry]) == chunk_evidence_manifest_bytes(
        [{key: value for key, value in entry.items() if key != "execution"}]
    )


def _manifest():
    return plan(
        (b"diff --git a/a b/a\n+line\n" * 3000),
        base_sha="a" * 40,
        head_sha="b" * 40,
        mission_id="MISSION",
        mission_scope_sha256="c" * 64,
    )


def _result(index: int, severity: str | None = None):
    findings = (
        []
        if severity is None
        else [{"severity": severity, "title": "finding", "evidence": "evidence"}]
    )
    return {
        "chunk_index": index,
        "result": {
            "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
            "review_result": "FAIL" if severity in {"P0", "P1", "P2"} else "PASS",
            "findings": findings,
        },
    }


def test_manifest_is_deterministic_and_reconstructable():
    manifest = _manifest()
    assert manifest.sha256 == _manifest().sha256
    validate_manifest(manifest, b"diff --git a/a b/a\n+line\n" * 3000)
    assert len(manifest.chunks) > 1


def test_manifest_rejects_gap_overlap_or_tampered_source():
    manifest = _manifest()
    with pytest.raises(ChunkReviewError):
        validate_manifest(manifest, b"x" + b"diff --git a/a b/a\n+line\n" * 3000)


def test_manifest_rejects_unbounded_provider_request_count():
    diff = b"x" * ((MAX_CHUNK_DIFF_BYTES * (MAX_CHUNK_COUNT + 1)) + 1)
    with pytest.raises(ChunkReviewError, match="chunk count exceeds"):
        plan(
            diff,
            base_sha="a" * 40,
            head_sha="b" * 40,
            mission_id="MISSION",
            mission_scope_sha256="c" * 64,
        )


def test_aggregate_is_fail_closed_and_surfaces_p3():
    manifest = _manifest()
    passed = aggregate(
        [_result(index, "P3" if index == 0 else None) for index in range(len(manifest.chunks))],
        manifest,
    )
    assert passed["review_result"] == "PASS"
    assert passed["finding_counts_by_severity"]["P3"] == 1
    failed = aggregate(
        [_result(index, "P2" if index == 1 else None) for index in range(len(manifest.chunks))],
        manifest,
    )
    assert failed["review_result"] == "FAIL"
    with pytest.raises(ChunkReviewError):
        aggregate([_result(0)], manifest)


def _chunk_validation_fixture(tmp_path: Path):
    diff = b"diff --git a/a b/a\n+line\n"
    base_sha, head_sha, scope_sha = "a" * 40, "b" * 40, "c" * 64
    manifest = plan(
        diff,
        base_sha=base_sha,
        head_sha=head_sha,
        mission_id="MISSION",
        mission_scope_sha256=scope_sha,
    )
    descriptor = manifest.chunks[0]
    prompt = build_chunk_prompt(
        chunk=descriptor, source=diff, manifest=manifest, scope_sha=scope_sha
    ).encode()
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": "PASS",
        "findings": [],
    }
    final = canonical_json(result)
    raw = json.dumps(
        {
            "is_error": False,
            "session_id": "fresh-session",
            "structured_output": result,
        },
        separators=(",", ":"),
    ).encode()
    command = (
        "/trusted/claude",
        "--bare",
        "--print",
        "--model",
        "deepseek-flash",
        "--settings",
        "/trusted/settings.json",
        "--strict-mcp-config",
        "--restricted",
        "--tools",
        "",
        "--disallowed-tools",
        "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch",
        "--output-format",
        "json",
        "--json-schema",
        "{}",
        prompt.decode(),
    )
    execution = ClaudeDeepSeekExecutionEvidence(
        reviewer_command=command,
        resolved_model="deepseek-flash",
        claude_cli_version="2.1.276 (Claude Code)",
        claude_binary_sha256="d" * 64,
        settings_sha256="e" * 64,
        provider_endpoint="https://api.deepseek.com/anthropic",
        session_id="fresh-session",
    )
    evidence_payload = [
        {
            "index": 0,
            "source_sha256": descriptor.source_sha256,
            "prompt_sha256": sha256_bytes(prompt),
            "raw_sha256": sha256_bytes(raw),
            "final_sha256": sha256_bytes(final),
            "session_id": "fresh-session",
        }
    ]
    item = {
        "index": 0,
        "source": diff,
        "source_sha256": descriptor.source_sha256,
        "prompt": prompt,
        "raw": raw,
        "final": final,
        "execution": execution,
        "session_id": "fresh-session",
    }
    receipt = {
        "mission_id": "MISSION",
        "mission_scope_sha256": scope_sha,
        "review_result": "PASS",
        "findings": [],
        "final_result_sha256": sha256_bytes(final),
        "provenance": {
            "chunk_count": 1,
            "chunk_manifest_sha256": manifest.sha256,
            "full_diff_sha256": sha256_bytes(diff),
            "chunk_evidence_manifest_sha256": sha256_bytes(
                chunk_evidence_manifest_bytes(evidence_payload)
            ),
            "aggregate_result_sha256": sha256_bytes(final),
        },
    }
    top = {
        "manifest": manifest.payload(),
        "manifest_sha256": manifest.sha256,
        "chunks": evidence_payload,
    }
    context = SimpleNamespace(
        repo_root=tmp_path,
        base_sha=base_sha,
        head_sha=head_sha,
        raw_output_bytes=canonical_json(top),
        final_result_bytes=final,
        chunked_claude_evidence=(item,),
    )
    return receipt, context, item, diff


def test_chunk_validator_binds_command_prompt_to_canonical_source(monkeypatch, tmp_path: Path):
    receipt, context, _item, diff = _chunk_validation_fixture(tmp_path)
    monkeypatch.setattr(
        chunk_validation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=diff),
    )
    chunk_validation._validate_chunked_claude_evidence(receipt, context)


def test_chunk_validator_rejects_tampered_command_prompt(monkeypatch, tmp_path: Path):
    receipt, context, item, diff = _chunk_validation_fixture(tmp_path)
    item["execution"] = ClaudeDeepSeekExecutionEvidence(
        reviewer_command=(*item["execution"].reviewer_command[:-1], "tampered prompt"),
        resolved_model=item["execution"].resolved_model,
        claude_cli_version=item["execution"].claude_cli_version,
        claude_binary_sha256=item["execution"].claude_binary_sha256,
        settings_sha256=item["execution"].settings_sha256,
        provider_endpoint=item["execution"].provider_endpoint,
        session_id=item["execution"].session_id,
    )
    monkeypatch.setattr(
        chunk_validation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=diff),
    )
    with pytest.raises(IndependentReviewProtocolError, match="chunk prompt is not bound"):
        chunk_validation._validate_chunked_claude_evidence(receipt, context)
