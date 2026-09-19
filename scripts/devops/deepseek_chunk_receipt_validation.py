"""Chunked DeepSeek receipt validation helpers.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from scripts.devops.deepseek_review_chunks import (
    ChunkReviewError,
    build_chunk_prompt,
    chunk_evidence_manifest_bytes,
    plan,
    validate_manifest,
)
from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    IndependentReviewProtocolError,
    sha256_bytes,
    validate_result,
    validate_sha,
)

_ENDPOINT = "https://api.deepseek.com/anthropic"
_MODEL = "deepseek-flash"
_MINIMUM_VERSION = (2, 1, 276)
_RESTRICTED_TOOLS = frozenset(
    {"Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch"}
)


def _validate_chunked_claude_evidence(  # noqa: C901, PLR0912, PLR0915
    receipt: dict[str, Any], context: Any
) -> None:
    """Validate harness-held chunks, not a receipt's self-consistent summary."""

    provenance = receipt["provenance"]
    chunks = context.chunked_claude_evidence
    if not chunks or provenance.get("chunk_count") != len(chunks):
        raise IndependentReviewProtocolError("chunk evidence is incomplete")
    try:
        top_evidence = json.loads(context.raw_output_bytes)
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--binary",
                "--no-ext-diff",
                f"{context.base_sha}...{context.head_sha}",
            ],
            cwd=context.repo_root,
            capture_output=True,
            check=True,
        ).stdout
        manifest = plan(
            diff,
            base_sha=context.base_sha,
            head_sha=context.head_sha,
            mission_id=receipt["mission_id"],
            mission_scope_sha256=receipt["mission_scope_sha256"],
        )
        if (
            top_evidence.get("manifest") != manifest.payload()
            or top_evidence.get("manifest_sha256") != manifest.sha256
            or provenance.get("chunk_manifest_sha256") != manifest.sha256
            or provenance.get("full_diff_sha256") != sha256_bytes(diff)
        ):
            raise ChunkReviewError("chunk manifest binding mismatch")  # noqa: TRY301
        validate_manifest(manifest, diff)
        top_chunks = top_evidence.get("chunks")
        if (
            not isinstance(top_chunks, list)
            or len(chunks) != len(manifest.chunks)
            or len(top_chunks) != len(manifest.chunks)
        ):
            raise ChunkReviewError("chunk evidence coverage is incomplete")  # noqa: TRY301
    except (
        ChunkReviewError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        raise IndependentReviewProtocolError("chunk manifest/coverage evidence is invalid") from exc
    if len({item.get("session_id") for item in chunks}) != len(chunks):
        raise IndependentReviewProtocolError("chunk session reuse is forbidden")
    evidence_payload: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    for index, item in enumerate(chunks):
        if item.get("index") != index or not all(
            hasattr(item.get("execution"), field)
            for field in (
                "reviewer_command",
                "resolved_model",
                "claude_cli_version",
                "claude_binary_sha256",
                "settings_sha256",
                "provider_endpoint",
                "session_id",
            )
        ):
            raise IndependentReviewProtocolError("chunk execution evidence is malformed")
        execution = item["execution"]
        raw, prompt, final = item.get("raw"), item.get("prompt"), item.get("final")
        if not all(isinstance(value, bytes) for value in (raw, prompt, final)):
            raise IndependentReviewProtocolError("chunk bytes are unavailable")
        try:
            event, result = json.loads(raw), json.loads(final)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentReviewProtocolError("chunk raw/final evidence is invalid") from exc
        normalized = validate_result(result)
        if (
            event.get("is_error") is not False
            or event.get("session_id") != execution.session_id
            or event.get("structured_output") != result
        ):
            raise IndependentReviewProtocolError(
                "chunk completion does not match execution evidence"
            )
        if execution.provider_endpoint != _ENDPOINT or execution.resolved_model != _MODEL:
            raise IndependentReviewProtocolError("chunk provider/model is not approved")
        version = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", execution.claude_cli_version)
        command = list(execution.reviewer_command)
        if (
            not version
            or tuple(map(int, version.groups())) < _MINIMUM_VERSION
            or not execution.reviewer_command
            or "--bare" not in command
            or "--print" not in command
            or command.count("--model") != 1
            or command[command.index("--model") + 1 : command.index("--model") + 2] != [_MODEL]
            or command.count("--settings") != 1
            or not command[command.index("--settings") + 1 : command.index("--settings") + 2]
            or "--strict-mcp-config" not in command
            or "--restricted" not in command
            or command.count("--tools") != 1
            or command[command.index("--tools") + 1 : command.index("--tools") + 2] != [""]
            or command.count("--disallowed-tools") != 1
            or not _RESTRICTED_TOOLS.issubset(
                set(command[command.index("--disallowed-tools") + 1].split(","))
            )
            or command.count("--output-format") != 1
            or command[command.index("--output-format") + 1 : command.index("--output-format") + 2]
            != ["json"]
            or command.count("--json-schema") != 1
            or not command[command.index("--json-schema") + 1 : command.index("--json-schema") + 2]
            or any(part in {"--resume", "--continue"} for part in command)
        ):
            raise IndependentReviewProtocolError(
                "chunk Claude command is not canonical isolated DeepSeek"
            )
        for digest in (execution.claude_binary_sha256, execution.settings_sha256):
            validate_sha(digest, name="trusted chunk Claude provenance digest", length=64)
        source = item.get("source")
        descriptor = manifest.chunks[index]
        if (
            not isinstance(source, bytes)
            or source != diff[descriptor.start : descriptor.end]
            or sha256_bytes(source) != item.get("source_sha256")
            or item.get("source_sha256") != descriptor.source_sha256
        ):
            raise IndependentReviewProtocolError("chunk source evidence is invalid")
        expected_prompt = build_chunk_prompt(
            chunk=descriptor,
            source=source,
            manifest=manifest,
            scope_sha=receipt["mission_scope_sha256"],
        ).encode()
        if prompt != expected_prompt or not command or command[-1].encode() != prompt:
            raise IndependentReviewProtocolError(
                "chunk prompt is not bound to the canonical source"
            )
        evidence_payload.append(
            {
                "index": index,
                "source_sha256": item["source_sha256"],
                "prompt_sha256": sha256_bytes(prompt),
                "raw_sha256": sha256_bytes(raw),
                "final_sha256": sha256_bytes(final),
                "session_id": execution.session_id,
            }
        )
        all_findings.extend(normalized["findings"])
    if provenance.get("chunk_evidence_manifest_sha256") != sha256_bytes(
        chunk_evidence_manifest_bytes(evidence_payload)
    ):
        raise IndependentReviewProtocolError("chunk evidence manifest hash mismatch")
    expected = validate_result(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": "FAIL"
            if any(item["severity"] in {"P0", "P1", "P2"} for item in all_findings)
            else "PASS",
            "findings": all_findings,
        }
    )
    if (
        expected["review_result"] != receipt["review_result"]
        or expected["findings"] != receipt["findings"]
        or provenance.get("aggregate_result_sha256") != sha256_bytes(context.final_result_bytes)
        or receipt["final_result_sha256"] != sha256_bytes(context.final_result_bytes)
    ):
        raise IndependentReviewProtocolError("chunk aggregate does not match trusted results")
