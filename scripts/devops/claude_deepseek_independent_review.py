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
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    MissionScopeError,
    load_mission_scope_file,
    mission_scope_relative_path,
)


class DeepSeekReviewError(RuntimeError):
    """The DeepSeek review cannot establish a trustworthy verdict."""


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


def run_review(args: argparse.Namespace) -> Path:
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
    try:
        raw, result, execution = backend.run(prompt=prompt, cwd=worktree)
    except backend.BackendInfrastructureError as exc:
        raise DeepSeekReviewError("backend infrastructure failure; no verdict") from exc
    completed = _now()
    normalized = validate_result(result)
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
    _write(raw_path, raw)
    _write(final_path, final)
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
        "review_prompt_sha256": sha256_bytes(prompt.encode()),
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
            "reviewer_command": list(execution.command),
            "command_sha256": sha256_bytes(canonical_json(list(execution.command))),
            "claude_cli_version": execution.cli_version,
            "claude_binary_sha256": execution.binary_sha256,
            "settings_sha256": execution.settings_sha256,
            "provider_endpoint": execution.endpoint,
            "session_id": execution.session_id,
        },
    }
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    context = receipts.ReceiptEvidenceContext(
        repo_root=root,
        base_sha=base,
        head_sha=head,
        mission_scope_path=scope_path,
        prompt_bytes=prompt.encode(),
        raw_output_bytes=raw,
        final_result_bytes=final,
        claude_deepseek_execution=receipts.ClaudeDeepSeekExecutionEvidence(
            reviewer_command=execution.command,
            resolved_model=execution.resolved_model,
            claude_cli_version=execution.cli_version,
            claude_binary_sha256=execution.binary_sha256,
            settings_sha256=execution.settings_sha256,
            provider_endpoint=execution.endpoint,
            session_id=execution.session_id,
        ),
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
