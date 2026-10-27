from __future__ import annotations

import codecs
from dataclasses import replace
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
    _decode_path,
    _quote_path,
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


def _chunk_validation_fixture(
    tmp_path: Path,
    diff: bytes = b"diff --git a/a b/a\n+line\n",
    *,
    base_sha: str = "a" * 40,
    head_sha: str = "b" * 40,
    scope_sha: str = "c" * 64,
    mission_id: str = "MISSION",
    manifest=None,
):
    manifest = manifest or plan(
        diff,
        base_sha=base_sha,
        head_sha=head_sha,
        mission_id=mission_id,
        mission_scope_sha256=scope_sha,
    )
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": "PASS",
        "findings": [],
    }
    final = canonical_json(result)
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
        "",
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
    items = []
    evidence_payload = []
    for chunk in manifest.chunks:
        source = diff[chunk.start : chunk.end]
        chunk_prompt = build_chunk_prompt(
            chunk=chunk, source=source, manifest=manifest, scope_sha=scope_sha
        ).encode()
        session = f"fresh-session-{chunk.index}"
        chunk_raw = canonical_json(
            {"is_error": False, "session_id": session, "structured_output": result}
        )
        items.append(
            {
                "final": final,
                "index": chunk.index,
                "source": source,
                "source_sha256": chunk.source_sha256,
                "prompt": chunk_prompt,
                "raw": chunk_raw,
                "session_id": session,
                "execution": replace(
                    execution,
                    reviewer_command=(*command[:-1], chunk_prompt.decode()),
                    session_id=session,
                ),
            }
        )
        evidence_payload.append(
            {
                "index": chunk.index,
                "source_sha256": chunk.source_sha256,
                "prompt_sha256": sha256_bytes(chunk_prompt),
                "raw_sha256": sha256_bytes(chunk_raw),
                "final_sha256": sha256_bytes(final),
                "session_id": session,
            }
        )
    receipt = {
        "mission_id": mission_id,
        "mission_scope_sha256": scope_sha,
        "review_result": "PASS",
        "findings": [],
        "final_result_sha256": sha256_bytes(final),
        "provenance": {
            "chunk_count": len(manifest.chunks),
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
        chunked_claude_evidence=tuple(items),
    )
    return receipt, context, items[0], diff


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


def _plan(diff: bytes):
    return plan(
        diff,
        base_sha="a" * 40,
        head_sha="b" * 40,
        mission_id="MISSION",
        mission_scope_sha256="c" * 64,
    )


def _split_file_diff() -> bytes:
    return (
        b"diff --git a/src/module.py b/src/module.py\n"
        + b"+implementation\n" * 4000
        + b"diff --git a/tests/module_test.py b/tests/module_test.py\n"
        + b"new file mode 100644\n--- /dev/null\n+++ b/tests/module_test.py\n@@ -0,0 +1 @@\n+test\n"
    )


def test_every_chunk_has_global_inventory_and_accurate_overlapping_local_paths():
    diff = _split_file_diff()
    original_sha = sha256_bytes(diff)
    manifest = _plan(diff)
    assert manifest.full_changed_paths == ("src/module.py", "tests/module_test.py")
    test_start = diff.index(b"diff --git a/tests/")
    assert manifest.chunks[1].start < test_start
    assert not diff[manifest.chunks[1].start : manifest.chunks[1].end].startswith(b"diff --git")
    for chunk in manifest.chunks:
        expected_local = (
            ("src/module.py",)
            if chunk.end <= test_start
            else ("src/module.py", "tests/module_test.py")
        )
        assert chunk.changed_paths == expected_local
        source = diff[chunk.start : chunk.end]
        prompt = build_chunk_prompt(
            chunk=chunk, source=source, manifest=manifest, scope_sha="c" * 64
        )
        assert 'Full PR changed paths: ["src/module.py","tests/module_test.py"]' in prompt
        assert (
            f"Current chunk changed paths: {canonical_json(list(expected_local)).decode()}"
            in prompt
        )
        assert "Do not assert that the PR omits a test or other asset solely" in prompt
        assert "state the evidence limitation" in prompt
        assert prompt.endswith(source.decode())
    assert b"".join(diff[chunk.start : chunk.end] for chunk in manifest.chunks) == diff
    assert manifest.full_diff_sha256 == original_sha == sha256_bytes(diff)
    validate_manifest(manifest, diff)


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        (
            b"diff --git a/new b/new\nnew file mode 100644\n--- /dev/null\n+++ b/new\n+new\n",
            ("new",),
        ),
        (
            b"diff --git a/old b/old\ndeleted file mode 100644\n--- a/old\n+++ /dev/null\n-old\n",
            ("old",),
        ),
        (b"diff --git a/modified b/modified\n-old\n+new\n", ("modified",)),
        (
            b"diff --git a/old b/new\nsimilarity index 100%\nrename from old\nrename to new\n",
            ("old", "new"),
        ),
        (
            b"diff --git a/old b/new\nsimilarity index 100%\ncopy from old\ncopy to new\n",
            ("old", "new"),
        ),
        (b"diff --git a/a b/part b/a b/part\n-old\n+new\n", ("a b/part",)),
        (b'diff --git "a/tab\\tname" "b/tab\\tname"\n+line\n', ("tab\tname",)),
        (b'diff --git "a/\\344\\270\\255.txt" "b/\\344\\270\\255.txt"\n+line\n', ("中.txt",)),
        (b'diff --git "a/quote\\"name" "b/quote\\"name"\n+line\n', ('quote"name',)),
        (
            b'diff --git "a/old\\tname" "b/new name"\nrename from "old\\tname"\nrename to new name\n',
            ("old\tname", "new name"),
        ),
        (b"diff --git a/binary b/binary\nGIT binary patch\nliteral 1\nA000\n", ("binary",)),
        (
            b'diff --git "a/bad\\377name" "b/bad\\377name"\n+line\n',
            ('"bad\\377name"',),
        ),
        (
            b'diff --git "a/old\\377" "b/new\\376"\nsimilarity index 100%\n'
            b'rename from "old\\377"\nrename to "new\\376"\n',
            ('"old\\377"', '"new\\376"'),
        ),
        (
            b'diff --git "a/old\\377" "b/new\\376"\nsimilarity index 100%\n'
            b'copy from "old\\377"\ncopy to "new\\376"\n',
            ('"old\\377"', '"new\\376"'),
        ),
        (
            b'diff --git "a/space \\"quote\\\\name\\377" "b/space \\"quote\\\\name\\377"\n+line\n',
            ('"space \\"quote\\\\name\\377"',),
        ),
    ],
)
def test_full_inventory_is_deterministic_for_git_change_kinds_and_quoted_paths(diff, expected):
    manifest = _plan(diff)
    assert manifest.full_changed_paths == expected
    assert manifest.chunks[0].changed_paths == expected
    assert _plan(diff).full_changed_paths == expected
    assert _plan(diff).sha256 == manifest.sha256


def test_inventory_deduplicates_in_full_diff_first_appearance_order():
    diff = b"diff --git a/z b/z\n+line\ndiff --git a/a b/a\n+line\ndiff --git a/z b/z\n+line\n"
    assert _plan(diff).full_changed_paths == ("z", "a")


@pytest.mark.parametrize("header", [b'diff --git "a/bad\\q" "b/bad\\q"\n', b"diff --git invalid\n"])
def test_invalid_path_header_fails_closed(header):
    with pytest.raises(ChunkReviewError, match="ambiguous or invalid"):
        _plan(header + b"+line\n")


def test_path_representation_roundtrips_and_never_collides_with_literal_quoted_names():
    # No files are created. Include every non-NUL byte and UTF-8 lookalikes of
    # the escaped representation; replacements/Latin-1 would lose identity.
    raw_paths = [b"name" + bytes([byte]) + b".txt" for byte in range(1, 256)]
    raw_paths += ["中.txt".encode(), b'"name\\377.txt"', b'"quoted"', b"name\xef\xbf\xbd.txt"]
    rendered = [_decode_path(_quote_path(raw).encode()) for raw in raw_paths]
    assert len(set(rendered)) == len(set(raw_paths))
    for raw, path in zip(raw_paths, rendered, strict=True):
        recovered = (
            codecs.escape_decode(path[1:-1].encode())[0] if path.startswith('"') else path.encode()
        )
        assert recovered == raw
        assert json.loads(canonical_json([path])) == [path]
    assert _decode_path(b"ordinary.txt") == "ordinary.txt"
    assert _decode_path("中文.txt".encode()) == "中文.txt"
    assert _decode_path(b'"bad\\377name"') != _decode_path(b'"\\"bad\\\\377name\\""')


def test_diff_prefixes_are_removed_before_rendering_non_utf8_and_literal_quoted_paths():
    raw_paths = (b"bad\xffname", b'"bad\\377name"')
    diff = b"".join(
        b"diff --git "
        + _quote_path(b"a/" + path).encode()
        + b" "
        + _quote_path(b"b/" + path).encode()
        + b"\n+line\n"
        for path in raw_paths
    )
    manifest = _plan(diff)
    assert manifest.full_changed_paths == tuple(_quote_path(path) for path in raw_paths)
    assert len(set(manifest.full_changed_paths)) == len(raw_paths)
    assert manifest.chunks[0].changed_paths == manifest.full_changed_paths


@pytest.mark.parametrize(
    "path",
    [
        b'"bad\\q"',
        b'"bad\\400"',
        b'"bad\\777"',
        b'"bad\\37"',
        b'"unfinished',
        b'"bad\\000"',
        b"bad\0",
        b"",
    ],
)
def test_malformed_quoted_or_impossible_git_paths_fail_closed(path):
    with pytest.raises(ChunkReviewError):
        _decode_path(path)


def test_non_utf8_multichunk_prompt_and_strict_validator_reconstruction(monkeypatch, tmp_path):
    diff = (
        b'diff --git "a/bad\\377name" "b/bad\\377name"\n'
        + b"+implementation\n" * 4000
        + b'diff --git "a/tests\\376.py" "b/tests\\376.py"\n+test\n'
    )
    manifest = _plan(diff)
    assert manifest.full_changed_paths == ('"bad\\377name"', '"tests\\376.py"')
    assert manifest.chunks[0].changed_paths == ('"bad\\377name"',)
    assert b"".join(diff[c.start : c.end] for c in manifest.chunks) == diff
    validate_manifest(manifest, diff)
    assert json.loads(canonical_json(manifest.payload())) == manifest.payload()
    receipt, context, _item, _diff = _chunk_validation_fixture(tmp_path, diff)
    for chunk, item in zip(manifest.chunks, context.chunked_claude_evidence, strict=True):
        prompt = item["prompt"].decode()
        assert (
            "Full PR changed paths: " + canonical_json(list(manifest.full_changed_paths)).decode()
            in prompt
        )
        assert (
            "Current chunk changed paths: " + canonical_json(list(chunk.changed_paths)).decode()
            in prompt
        )
        assert prompt.encode() == item["prompt"]
    monkeypatch.setattr(
        chunk_validation.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(stdout=diff)
    )
    chunk_validation._validate_chunked_claude_evidence(receipt, context)


@pytest.mark.parametrize("inventory", ["global", "local"])
def test_manifest_rejects_tampered_path_inventory(inventory):
    diff = _split_file_diff()
    manifest = _plan(diff)
    tampered = (
        replace(manifest, full_changed_paths=("invented.py",))
        if inventory == "global"
        else replace(
            manifest, chunks=(replace(manifest.chunks[0], changed_paths=()), *manifest.chunks[1:])
        )
    )
    with pytest.raises(ChunkReviewError, match="changed paths binding mismatch"):
        validate_manifest(tampered, diff)


def test_multichunk_validator_reconstructs_full_context(monkeypatch, tmp_path: Path):
    receipt, context, _item, diff = _chunk_validation_fixture(tmp_path, _split_file_diff())
    monkeypatch.setattr(
        chunk_validation.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(stdout=diff)
    )
    chunk_validation._validate_chunked_claude_evidence(receipt, context)


@pytest.mark.parametrize("tamper", ["global_prompt", "source", "manifest"])
def test_validator_rejects_tampering_even_with_updated_evidence_hashes(
    monkeypatch, tmp_path: Path, tamper
):
    receipt, context, item, diff = _chunk_validation_fixture(tmp_path, _split_file_diff())
    top = json.loads(context.raw_output_bytes)
    if tamper == "global_prompt":
        item["prompt"] = item["prompt"].replace(b'"tests/module_test.py"', b'"invented_test.py"')
        item["execution"] = replace(
            item["execution"],
            reviewer_command=(*item["execution"].reviewer_command[:-1], item["prompt"].decode()),
        )
        top["chunks"][0]["prompt_sha256"] = sha256_bytes(item["prompt"])
    elif tamper == "source":
        item["source"] += b"+tampered\n"
        item["source_sha256"] = sha256_bytes(item["source"])
        top["chunks"][0]["source_sha256"] = item["source_sha256"]
    else:
        top["manifest"]["chunks"][0]["changed_paths"] = ["invented.py"]
        top["manifest_sha256"] = sha256_bytes(canonical_json(top["manifest"]))
        receipt["provenance"]["chunk_manifest_sha256"] = top["manifest_sha256"]
    receipt["provenance"]["chunk_evidence_manifest_sha256"] = sha256_bytes(
        chunk_evidence_manifest_bytes(top["chunks"])
    )
    context.raw_output_bytes = canonical_json(top)
    monkeypatch.setattr(
        chunk_validation.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(stdout=diff)
    )
    with pytest.raises(IndependentReviewProtocolError):
        chunk_validation._validate_chunked_claude_evidence(receipt, context)
