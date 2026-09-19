"""External DeepSeek receipt evidence consumption.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from scripts.devops.codex_review_verdict import (
    ReviewReceiptError,
    assert_owner_only_directory,
    assert_owner_only_file,
)
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes, validate_result
from scripts.devops.independent_review_receipt import (
    ClaudeDeepSeekExecutionEvidence,
    ReceiptEvidenceContext,
    load_backend_registry,
    receipt_payload_sha256,
    validate_receipt,
)
from scripts.devops.review_policy import BACKEND_DEEPSEEK, ReviewEvidence


def _assert_external_artifact(path: Path, *, repo_root: Path, kind: str) -> None:
    """Require evidence artifacts to live in a private external directory."""

    resolved = path.resolve()
    repository = repo_root.resolve()
    if resolved == repository or repository in resolved.parents:
        raise ValueError(f"{kind} must be outside repository worktree")
    try:
        assert_owner_only_directory(path.parent)
        assert_owner_only_file(path)
    except (OSError, ReviewReceiptError) as exc:
        raise ValueError(f"invalid {kind} metadata: {path}: {exc}") from exc


def _assert_run_id(run_id: Any) -> str:
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{1,64}", run_id):
        raise ValueError("run id")
    return run_id


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"JSON evidence 必须是 object: {path}")
    return value


def _deepseek_receipt_evidence(  # noqa: C901, PLR0912
    path: Path,
    *,
    repo_root: Path,
    expected_base: str,
    expected_head: str,
    expected_mission_id: str,
    expected_scope_hash: str,
) -> ReviewEvidence:
    """Read commit-last DeepSeek evidence or return one untrusted NO_VERDICT."""

    try:
        _assert_external_artifact(path, repo_root=repo_root, kind="receipt")
        value = _load_json(path)
        registry = load_backend_registry(
            repo_root / "docs/agentic/independent_review_backends.json"
        )
        backend = registry.get(value.get("review_backend"))
        if backend is None or value.get("review_backend") != BACKEND_DEEPSEEK:
            raise ValueError("backend identity")
        if (
            backend["status"] != "active"
            or value.get("requested_model") not in backend["allowed_requested_models"]
        ):
            raise ValueError("backend registry")
        integrity = value.get("integrity")
        if not isinstance(integrity, dict) or integrity.get(
            "receipt_payload_sha256"
        ) != receipt_payload_sha256(value):
            raise ValueError("receipt integrity")
        result = validate_result(
            {
                "protocol_version": value.get("protocol_version"),
                "review_result": value.get("review_result"),
                "findings": value.get("findings"),
            }
        )
        if value.get("finding_counts_by_severity") != result["finding_counts_by_severity"]:
            raise ValueError("finding counts")
        if value.get("base_sha") != expected_base or value.get("head_sha") != expected_head:
            raise ValueError("head binding")
        if (
            value.get("mission_id") != expected_mission_id
            or value.get("mission_scope_sha256") != expected_scope_hash
        ):
            raise ValueError("mission binding")
        expected_diff = sha256_bytes(
            subprocess.run(
                ["git", "diff", "--binary", "--no-ext-diff", f"{expected_base}...{expected_head}"],
                cwd=repo_root,
                capture_output=True,
                check=True,
            ).stdout
        )
        if value.get("diff_sha256") != expected_diff:
            raise ValueError("diff binding")
        provenance = value.get("provenance")
        if not isinstance(provenance, dict) or any(
            (
                not isinstance(provenance.get(field), list)
                or not provenance[field]
                or not all(isinstance(part, str) for part in provenance[field])
            )
            if field == "reviewer_command"
            else (not isinstance(provenance.get(field), str) or not provenance[field])
            for field in backend["required_provenance_fields"]
        ):
            raise ValueError("provenance")
        if value.get("resolved_model") != value.get("requested_model"):
            raise ValueError("model fallback")
        # Commit-last output files are named from the immutable receipt run id.
        run_id = _assert_run_id(value.get("review_run_id"))
        raw = path.parent / f"claude-deepseek-raw-{expected_head[:12]}-{run_id}.json"
        final = path.parent / f"claude-deepseek-final-{expected_head[:12]}-{run_id}.json"
        _assert_external_artifact(raw, repo_root=repo_root, kind="raw artifact")
        _assert_external_artifact(final, repo_root=repo_root, kind="final artifact")
        raw_bytes, final_bytes = raw.read_bytes(), final.read_bytes()
        if value.get("raw_output_sha256") != sha256_bytes(raw_bytes) or value.get(
            "final_result_sha256"
        ) != sha256_bytes(final_bytes):
            raise ValueError("raw/final binding")
        if final_bytes != canonical_json(
            {
                "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                "review_result": result["review_result"],
                "findings": result["findings"],
            }
        ):
            raise ValueError("final result")
        chunked_evidence: tuple[dict[str, Any], ...] = ()
        one_shot_execution = None
        if provenance.get("chunked_review") is True:
            top = json.loads(raw_bytes)
            chunks = top.get("chunks") if isinstance(top, dict) else None
            manifest = top.get("manifest") if isinstance(top, dict) else None
            descriptors = manifest.get("chunks") if isinstance(manifest, dict) else None
            if not isinstance(chunks, list) or not isinstance(descriptors, list):
                raise ValueError("chunk evidence manifest")
            diff_bytes = subprocess.run(
                ["git", "diff", "--binary", "--no-ext-diff", f"{expected_base}...{expected_head}"],
                cwd=repo_root,
                capture_output=True,
                check=True,
            ).stdout
            loaded: list[dict[str, Any]] = []
            if len(chunks) != len(descriptors):
                raise ValueError("chunk count")
            for index, entry in enumerate(chunks):
                descriptor = descriptors[index]
                execution = entry.get("execution") if isinstance(entry, dict) else None
                if not isinstance(descriptor, dict) or not isinstance(execution, dict):
                    raise ValueError("chunk descriptor/execution")
                start, end = descriptor.get("start"), descriptor.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    raise ValueError("chunk range")
                prompt_path = path.parent / (
                    f"claude-deepseek-chunk-prompt-{expected_head[:12]}-{run_id}-{index}.txt"
                )
                chunk_raw_path = path.parent / (
                    f"claude-deepseek-chunk-raw-{expected_head[:12]}-{run_id}-{index}.json"
                )
                chunk_final_path = path.parent / (
                    f"claude-deepseek-chunk-final-{expected_head[:12]}-{run_id}-{index}.json"
                )
                _assert_external_artifact(prompt_path, repo_root=repo_root, kind="chunk prompt")
                _assert_external_artifact(
                    chunk_raw_path, repo_root=repo_root, kind="chunk raw artifact"
                )
                _assert_external_artifact(
                    chunk_final_path, repo_root=repo_root, kind="chunk final artifact"
                )
                command = execution.get("reviewer_command")
                if not isinstance(command, list) or not all(
                    isinstance(part, str) for part in command
                ):
                    raise ValueError("chunk command")
                chunk_execution = ClaudeDeepSeekExecutionEvidence(
                    reviewer_command=tuple(command),
                    resolved_model=execution.get("resolved_model"),
                    claude_cli_version=execution.get("claude_cli_version"),
                    claude_binary_sha256=execution.get("claude_binary_sha256"),
                    settings_sha256=execution.get("settings_sha256"),
                    provider_endpoint=execution.get("provider_endpoint"),
                    session_id=execution.get("session_id"),
                )
                prompt_bytes = prompt_path.read_bytes()
                chunk_raw_bytes = chunk_raw_path.read_bytes()
                chunk_final_bytes = chunk_final_path.read_bytes()
                if (
                    entry.get("index") != index
                    or entry.get("source_sha256") != descriptor.get("source_sha256")
                    or entry.get("prompt_sha256") != sha256_bytes(prompt_bytes)
                    or entry.get("raw_sha256") != sha256_bytes(chunk_raw_bytes)
                    or entry.get("final_sha256") != sha256_bytes(chunk_final_bytes)
                    or entry.get("session_id") != chunk_execution.session_id
                ):
                    raise ValueError("chunk artifact binding")
                loaded.append(
                    {
                        "index": index,
                        "source": diff_bytes[start:end],
                        "source_sha256": descriptor.get("source_sha256"),
                        "prompt": prompt_bytes,
                        "raw": chunk_raw_bytes,
                        "final": chunk_final_bytes,
                        "execution": chunk_execution,
                        "session_id": chunk_execution.session_id,
                    }
                )
            chunked_evidence = tuple(loaded)
        else:
            prompt_name = value.get("review_prompt_path")
            if not isinstance(prompt_name, str) or Path(prompt_name).name != prompt_name:
                raise ValueError("review prompt path")
            prompt_path = path.parent / prompt_name
            _assert_external_artifact(prompt_path, repo_root=repo_root, kind="review prompt")
            prompt_bytes = prompt_path.read_bytes()
            command = provenance.get("reviewer_command")
            if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
                raise ValueError("reviewer command")
            one_shot_execution = ClaudeDeepSeekExecutionEvidence(
                reviewer_command=tuple(command),
                resolved_model=value.get("resolved_model"),
                claude_cli_version=provenance.get("claude_cli_version"),
                claude_binary_sha256=provenance.get("claude_binary_sha256"),
                settings_sha256=provenance.get("settings_sha256"),
                provider_endpoint=provenance.get("provider_endpoint"),
                session_id=provenance.get("session_id"),
            )
        validate_receipt(
            value,
            registry=registry,
            evidence_context=ReceiptEvidenceContext(
                repo_root=repo_root,
                base_sha=expected_base,
                head_sha=expected_head,
                mission_scope_path=value.get("mission_scope_path"),
                prompt_bytes=raw_bytes if chunked_evidence else prompt_bytes,
                raw_output_bytes=raw_bytes,
                final_result_bytes=final_bytes,
                claude_deepseek_execution=one_shot_execution,
                chunked_claude_evidence=chunked_evidence,
            ),
        )
        return ReviewEvidence(
            BACKEND_DEEPSEEK,
            True,
            result["review_result"],
            expected_base,
            expected_head,
            expected_diff,
            expected_mission_id,
            expected_scope_hash,
            result["finding_counts_by_severity"],
        )
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        return ReviewEvidence(
            BACKEND_DEEPSEEK,
            False,
            "NO_VERDICT",
            "",
            "",
            "",
            "",
            "",
            {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
            True,
        )
