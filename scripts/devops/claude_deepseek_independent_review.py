#!/usr/bin/env python3
"""Run one exact-head, isolated Claude Code / DeepSeek generic review.

Lifecycle: permanent
Owner: engineering workflow governance

This is deliberately a separate entrypoint from the canonical Codex approval
runner.  It makes the registered DeepSeek backend explicitly selectable, but
does not replace or upgrade the Codex merge-approval path.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
SHA1_LENGTH = 40
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops import independent_review_receipt as receipts  # noqa: E402
from scripts.devops.independent_review_backends import claude_code_deepseek as backend  # noqa: E402
from scripts.devops.independent_review_protocol import (  # noqa: E402
    PROTOCOL_VERSION,
    canonical_json,
    sha256_bytes,
    validate_result,
)
from scripts.devops.deepseek_review_chunks import (  # noqa: E402
    MAX_CHUNK_DIFF_BYTES,
    aggregate,
    chunk_evidence_manifest_bytes,
    plan,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    MissionScopeError,
    load_mission_scope_file,
    mission_scope_relative_path,
)


class DeepSeekReviewError(RuntimeError):
    """The DeepSeek review cannot establish a trustworthy verdict."""


_SAFE_BACKEND_FAILURE_CODES = frozenset(
    {
        "AUTH_FAILURE",
        "CLI_RUNTIME_FAILURE",
        "CLI_RUNTIME_TIMEOUT",
        "INVALID_STRUCTURED_OUTPUT",
        "MODEL_MISMATCH",
        "SECRET_LEAKAGE_DETECTED",
    }
)
_SAFE_NONZERO_DETAILS = frozenset(
    {
        "AUTH_ERROR",
        "RATE_LIMIT",
        "USAGE_LIMIT",
        "REQUEST_TOO_LARGE",
        "CONTEXT_LIMIT",
        "INVALID_MODEL",
        "UNSUPPORTED_PARAMETER",
        "INVALID_SCHEMA",
        "STRUCTURED_OUTPUT_ERROR",
        "PROVIDER_5XX",
        "NETWORK_FAILURE",
        "TLS_FAILURE",
        "UNKNOWN_NONZERO_EXIT",
    }
)


def _safe_backend_failure_code(error: backend.BackendInfrastructureError) -> str:
    """Expose only a stable non-secret infrastructure classification."""

    parts = str(error).split(":", 2)
    code = parts[0]
    detail = parts[1].strip() if len(parts) > 1 else ""
    if code == "CLI_RUNTIME_FAILURE" and detail in _SAFE_NONZERO_DETAILS:
        return f"{code}:{detail}"
    return code if code in _SAFE_BACKEND_FAILURE_CODES else "CLI_RUNTIME_FAILURE"


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise DeepSeekReviewError("git evidence command failed")
    return result.stdout.decode().strip() if text else result.stdout


def _sha(root: Path, value: str) -> str:
    resolved = _git(root, "rev-parse", f"{value}^{{commit}}")
    if not isinstance(resolved, str) or len(resolved) != SHA1_LENGTH:
        raise DeepSeekReviewError("review SHA is invalid")
    return resolved


def _write(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical_prompt_bytes(prompt: str | bytes) -> bytes:
    """Bind receipt evidence to the exact prompt bytes sent by its path."""

    if isinstance(prompt, bytes):
        return prompt
    if isinstance(prompt, str):
        return prompt.encode()
    raise DeepSeekReviewError("review prompt has unsupported type")


def _chunk_prompt(*, chunk: object, source: bytes, manifest: object, scope_sha: str) -> str:
    return (
        "You are an independent read-only code reviewer. Return only the required generic JSON result. "
        "PASS only when P0/P1/P2 are absent.\n"
        f"Mission: {manifest.mission_id}\nBase: {manifest.base_sha}\nHead: {manifest.head_sha}\n"
        f"Scope SHA256: {scope_sha}\nFull diff SHA256: {manifest.full_diff_sha256}\n"
        f"Chunk manifest SHA256: {manifest.sha256}\nChunk: {chunk.index + 1}/{len(manifest.chunks)} "
        f"range={chunk.start}:{chunk.end} source_sha256={chunk.source_sha256}\n"
        f"Changed paths: {','.join(sorted({path for item in manifest.chunks for path in item.changed_paths}))}\n"
        f"Canonical chunk diff:\n{source.decode('utf-8', 'replace')}"
    )


def _run_chunked_review(
    *, diff: bytes, base: str, head: str, scope: object, scope_sha: str, worktree: Path
) -> tuple[bytes, dict, list[dict]]:
    manifest = plan(
        diff,
        base_sha=base,
        head_sha=head,
        mission_id=scope.mission_id,
        mission_scope_sha256=scope_sha,
    )
    values: list[dict] = []
    trusted: list[dict] = []
    for chunk in manifest.chunks:
        source = diff[chunk.start : chunk.end]
        prompt = _chunk_prompt(chunk=chunk, source=source, manifest=manifest, scope_sha=scope_sha)
        try:
            raw, result, execution = backend.run(prompt=prompt, cwd=worktree)
        except backend.BackendInfrastructureError as exc:
            raise DeepSeekReviewError(
                f"chunk {chunk.index} infrastructure failure [{_safe_backend_failure_code(exc)}]"
            ) from exc
        normalized = validate_result(result)
        execution_evidence = receipts.ClaudeDeepSeekExecutionEvidence(
            reviewer_command=execution.command,
            resolved_model=execution.resolved_model,
            claude_cli_version=execution.cli_version,
            claude_binary_sha256=execution.binary_sha256,
            settings_sha256=execution.settings_sha256,
            provider_endpoint=execution.endpoint,
            session_id=execution.session_id,
        )
        final = canonical_json(
            {
                "protocol_version": PROTOCOL_VERSION,
                "review_result": normalized["review_result"],
                "findings": normalized["findings"],
            }
        )
        values.append({"chunk_index": chunk.index, "result": json.loads(final)})
        trusted.append(
            {
                "index": chunk.index,
                "source": source,
                "source_sha256": chunk.source_sha256,
                "prompt": prompt.encode(),
                "raw": raw,
                "final": final,
                "execution": execution_evidence,
                "session_id": execution_evidence.session_id,
            }
        )
    normalized = aggregate(values, manifest)
    evidence = [
        {
            "index": item["index"],
            "source_sha256": item["source_sha256"],
            "prompt_sha256": sha256_bytes(item["prompt"]),
            "raw_sha256": sha256_bytes(item["raw"]),
            "final_sha256": sha256_bytes(item["final"]),
            "session_id": item["session_id"],
            "execution": {
                "reviewer_command": list(item["execution"].reviewer_command),
                "resolved_model": item["execution"].resolved_model,
                "claude_cli_version": item["execution"].claude_cli_version,
                "claude_binary_sha256": item["execution"].claude_binary_sha256,
                "settings_sha256": item["execution"].settings_sha256,
                "provider_endpoint": item["execution"].provider_endpoint,
                "session_id": item["execution"].session_id,
            },
        }
        for item in trusted
    ]
    return (
        canonical_json(
            {"manifest": manifest.payload(), "manifest_sha256": manifest.sha256, "chunks": evidence}
        ),
        normalized,
        trusted,
    )


def _run_review(args: argparse.Namespace) -> Path:
    """Create an external generic receipt for a new DeepSeek review session."""
    root = args.repo_root.resolve()
    base, head = _sha(root, args.base_sha), _sha(root, args.head_sha)
    if _sha(root, "HEAD") != head:
        raise DeepSeekReviewError("review head is not the current exact HEAD")
    scope_file = args.mission_scope_file.resolve()
    try:
        scope = load_mission_scope_file(
            scope_file, repo_root=root, expected_mission_id=args.mission_id
        )
        scope_path = mission_scope_relative_path(scope_file, root)
    except MissionScopeError as exc:
        raise DeepSeekReviewError("mission scope is invalid") from exc
    scope_bytes = _git(root, "show", f"{head}:{scope_path}", text=False)
    if not isinstance(scope_bytes, bytes) or sha256_bytes(scope_file.read_bytes()) != sha256_bytes(
        scope_bytes
    ):
        raise DeepSeekReviewError("mission scope is not bound to reviewed HEAD")
    evidence = args.evidence_dir.resolve()
    if root in evidence.parents or evidence == root:
        raise DeepSeekReviewError("evidence directory must be outside the repository")
    evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    if evidence.stat().st_mode & 0o077:
        raise DeepSeekReviewError("evidence directory must be owner-only")
    run_id = uuid.uuid4().hex
    worktree = evidence / f"claude-deepseek-worktree-{head[:12]}-{run_id}"
    _git(root, "worktree", "add", "--detach", str(worktree), head)
    if _sha(worktree, "HEAD") != head or _git(worktree, "status", "--porcelain"):
        raise DeepSeekReviewError("detached review worktree is not clean")
    diff = _git(root, "diff", "--binary", "--no-ext-diff", f"{base}...{head}", text=False)
    if not isinstance(diff, bytes):
        raise DeepSeekReviewError("diff evidence is invalid")
    prompt = (
        "You are an independent read-only code reviewer. Review the exact diff below. "
        "Return only the required generic JSON result. PASS only when P0/P1/P2 are absent; "
        "FAIL when a P0/P1/P2 exists. Findings require severity, title, and evidence.\n"
        f"Mission: {scope.mission_id}\nBase: {base}\nHead: {head}\n"
        f"Scope SHA256: {sha256_bytes(scope_bytes)}\nDiff:\n{diff.decode('utf-8', 'replace')}"
    )
    started = _now()
    chunked = len(diff) > MAX_CHUNK_DIFF_BYTES
    trusted_chunks: list[dict] = []
    if chunked:
        raw, normalized, trusted_chunks = _run_chunked_review(
            diff=diff,
            base=base,
            head=head,
            scope=scope,
            scope_sha=sha256_bytes(scope_bytes),
            worktree=worktree,
        )
        prompt = raw
        execution = trusted_chunks[0]["execution"]
    else:
        try:
            raw, result, execution = backend.run(prompt=prompt, cwd=worktree)
        except backend.BackendInfrastructureError as exc:
            raise DeepSeekReviewError(
                f"backend infrastructure failure [{_safe_backend_failure_code(exc)}]; no verdict"
            ) from exc
        normalized = validate_result(result)
        execution = receipts.ClaudeDeepSeekExecutionEvidence(
            reviewer_command=execution.command,
            resolved_model=execution.resolved_model,
            claude_cli_version=execution.cli_version,
            claude_binary_sha256=execution.binary_sha256,
            settings_sha256=execution.settings_sha256,
            provider_endpoint=execution.endpoint,
            session_id=execution.session_id,
        )
    completed = _now()
    final = canonical_json(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": normalized["review_result"],
            "findings": normalized["findings"],
        }
    )
    if _git(worktree, "status", "--porcelain"):
        raise DeepSeekReviewError("reviewer mutated detached worktree")
    raw_path = evidence / f"claude-deepseek-raw-{head[:12]}-{run_id}.json"
    final_path = evidence / f"claude-deepseek-final-{head[:12]}-{run_id}.json"
    if chunked:
        for item in trusted_chunks:
            index = item["index"]
            _write(
                evidence / f"claude-deepseek-chunk-prompt-{head[:12]}-{run_id}-{index}.txt",
                item["prompt"],
            )
            _write(
                evidence / f"claude-deepseek-chunk-raw-{head[:12]}-{run_id}-{index}.json",
                item["raw"],
            )
            _write(
                evidence / f"claude-deepseek-chunk-final-{head[:12]}-{run_id}-{index}.json",
                item["final"],
            )
    _write(raw_path, raw)
    _write(final_path, final)
    prompt_path = evidence / f"claude-deepseek-prompt-{head[:12]}-{run_id}.txt"
    if not chunked:
        _write(prompt_path, _canonical_prompt_bytes(prompt))
    receipt = {
        "protocol_version": PROTOCOL_VERSION,
        "receipt_version": "independent-review-receipt/v1",
        "review_run_id": run_id,
        "review_backend": backend.BACKEND_ID,
        "review_harness": "claude-code",
        "provider": backend.PROVIDER_ID,
        "requested_model": backend.MODEL,
        "resolved_model": execution.resolved_model,
        "base_sha": base,
        "head_sha": head,
        "diff_sha256": sha256_bytes(diff),
        "mission_id": args.mission_id,
        "mission_scope_path": scope_path,
        "mission_scope_sha256": sha256_bytes(scope_bytes),
        "review_prompt_sha256": sha256_bytes(_canonical_prompt_bytes(prompt)),
        "review_started_at": started,
        "review_completed_at": completed,
        "review_result": normalized["review_result"],
        "finding_counts_by_severity": normalized["finding_counts_by_severity"],
        "findings": normalized["findings"],
        "raw_output_sha256": sha256_bytes(raw),
        "final_result_sha256": sha256_bytes(final),
        "isolation": {
            "fresh_process": True,
            "fresh_context": True,
            "detached_worktree": True,
            "read_only": True,
            "worktree_head_sha": head,
            "worktree_clean_before": True,
            "worktree_clean_after": True,
        },
        "provenance": {
            "reviewer_command": list(execution.reviewer_command),
            "command_sha256": sha256_bytes(canonical_json(list(execution.reviewer_command))),
            "claude_cli_version": execution.claude_cli_version,
            "claude_binary_sha256": execution.claude_binary_sha256,
            "settings_sha256": execution.settings_sha256,
            "provider_endpoint": execution.provider_endpoint,
            "session_id": execution.session_id,
            **({"review_prompt_path": prompt_path.name} if not chunked else {}),
            **(
                {
                    "chunked_review": True,
                    "chunk_count": len(trusted_chunks),
                    "chunk_manifest_sha256": json.loads(raw)["manifest_sha256"],
                    "full_diff_sha256": sha256_bytes(diff),
                    "aggregate_result_sha256": sha256_bytes(final),
                    "chunk_evidence_manifest_sha256": sha256_bytes(
                        chunk_evidence_manifest_bytes(json.loads(raw)["chunks"])
                    ),
                }
                if chunked
                else {}
            ),
        },
    }
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    context = receipts.ReceiptEvidenceContext(
        repo_root=root,
        base_sha=base,
        head_sha=head,
        mission_scope_path=scope_path,
        prompt_bytes=_canonical_prompt_bytes(prompt),
        raw_output_bytes=raw,
        final_result_bytes=final,
        claude_deepseek_execution=None
        if chunked
        else receipts.ClaudeDeepSeekExecutionEvidence(
            reviewer_command=execution.reviewer_command,
            resolved_model=execution.resolved_model,
            claude_cli_version=execution.claude_cli_version,
            claude_binary_sha256=execution.claude_binary_sha256,
            settings_sha256=execution.settings_sha256,
            provider_endpoint=execution.provider_endpoint,
            session_id=execution.session_id,
        ),
        chunked_claude_evidence=tuple(trusted_chunks),
    )
    receipts.validate_receipt(
        receipt,
        registry=receipts.load_backend_registry(
            root / "docs/agentic/independent_review_backends.json"
        ),
        evidence_context=context,
    )
    receipt_path = evidence / f"claude-deepseek-receipt-{head[:12]}-{run_id}.json"
    _write(receipt_path, canonical_json(receipt))
    return receipt_path


def _cleanup_invocation(
    *,
    evidence: Path,
    repo_root: Path,
    before_dirs: set[Path],
    before_artifacts: set[Path],
    preserve_artifacts: bool,
) -> OSError | None:
    """Remove only worktrees/artifacts created by this review invocation."""
    cleanup_error: OSError | None = None
    created_worktrees = set(evidence.glob("claude-deepseek-worktree-*")).difference(before_dirs)
    for worktree in created_worktrees:
        try:
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
        except OSError:
            cleanup_error = OSError("temporary review worktree cleanup failed")
        else:
            if result.returncode:
                cleanup_error = OSError("temporary review worktree cleanup failed")
    if not preserve_artifacts or cleanup_error is not None:
        # A receipt is commit-last evidence. If any later lifecycle step
        # fails, remove only this invocation's artifacts so an incomplete run
        # cannot be mistaken for an approval.
        for artifact in set(evidence.glob("claude-deepseek-*")).difference(before_artifacts):
            if artifact.is_file():
                try:
                    artifact.unlink()
                except OSError:
                    cleanup_error = OSError("temporary review artifact cleanup failed")
    return cleanup_error


def run_review(args: argparse.Namespace) -> Path:
    """Run one review and always remove only this invocation's worktree."""
    evidence = args.evidence_dir.resolve()
    before_dirs = set(evidence.glob("claude-deepseek-worktree-*")) if evidence.exists() else set()
    before_artifacts = set(evidence.glob("claude-deepseek-*")) if evidence.exists() else set()
    completed = False
    try:
        receipt = _run_review(args)
        completed = True
    finally:
        cleanup_error = _cleanup_invocation(
            evidence=evidence,
            repo_root=args.repo_root.resolve(),
            before_dirs=before_dirs,
            before_artifacts=before_artifacts,
            preserve_artifacts=completed,
        )
        if cleanup_error is not None:
            raise DeepSeekReviewError("temporary review worktree cleanup failed") from cleanup_error
    return receipt


def main(argv: list[str] | None = None) -> int:
    """Parse one explicit DeepSeek review invocation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--mission-scope-file", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = run_review(args)
    except (DeepSeekReviewError, OSError, ValueError) as exc:
        print(f"DEEPSEEK_INDEPENDENT_REVIEW=NO_VERDICT: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"review_receipt": str(receipt), "status": "COMPLETE"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
