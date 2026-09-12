#!/usr/bin/env python3
"""启动并验证 engineering-independent Codex reviewer。

lifecycle: permanent
owner: engineering workflow governance

`run` 在 reviewed commit 的 detached worktree 中启动新的、ephemeral
``codex exec`` 子进程，强制 ``--sandbox read-only`` 和 JSON 输出；reviewer
不共享 Builder session，也不接收 Builder 的自证。receipt 与原始 Codex
输出必须位于 reviewed source tree 之外。

本模块只负责执行与 CLI：receipt 的证据读取与内部一致性证明在
``codex_review_receipt``，三态分类在 ``codex_review_classification``。

本模块实现的是 `ENGINEERING_INDEPENDENT_REVIEW`：fresh Codex
process/context、clean exact-head worktree、只读执行和可重算的 evidence
完整性检查。它不声称提供密码学 reviewer identity，也不抵抗同一 OS uid
的恶意 Builder；该 residual risk 由项目策略明确接受。
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_classification import (  # noqa: E402
    ReceiptClassification,
    classify_receipt,
    validate_receipt,
)
from scripts.devops.codex_review_contract import (  # noqa: E402
    _canonical_json,
    build_reviewer_command,
    review_challenge,
    reviewer_selectors_from_command,
    sha256_bytes,
    validate_review_result,
)
from scripts.devops.codex_review_output import (  # noqa: E402
    assert_successful_completion,
    parse_json_lines,
    reviewer_invocation_id,
)
from scripts.devops.codex_review_provenance import (  # noqa: E402
    ReviewReceiptError,
    observe_codex_cli_version,
    resolve_codex_binary,
)
from scripts.devops.codex_review_receipt import (  # noqa: E402
    CLI_VERSION_SOURCE_OBSERVED_STDOUT,
    EFFORT_SOURCE_CODEX_CONFIG_OVERRIDE,
    MODEL_SOURCE_CODEX_EXEC_FLAG,
    RECEIPT_SCHEMA_VERSION,
    REVIEW_OUTPUT_SCHEMA,
    THREAD_ID_RE,
    WRAPPER_NAME,
    _assert_contexts_separate,
    _assert_review_challenge,
    _codex_prompt,
    _parse_final_message,
    _require_external_path,
    _run_git,
    diff_sha256,
    exact_head,
    git_blob_sha256,
    sha256_file,
)
from scripts.devops.exact_head import (  # noqa: E402
    ExactHeadError,
    assert_exact_head,
    normalize_full_sha,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW,
    CONTRACT_SCHEMA_VERSION,
    REVIEW_ENGINE_CODEX,
    REVIEW_ROLE_INDEPENDENT,
    MissionScope,
    MissionScopeError,
    load_mission_scope_file,
    mission_scope_relative_path,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    mission_scope_sha256 as scope_file_sha256,
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_exact_review_scope(
    *, repo_root: Path, scope_file: Path, expected_head: str, mission_id: str
) -> tuple[MissionScope, str, str]:
    """Load a mission scope and prove its bytes are present at reviewed HEAD."""

    mission_scope_path = mission_scope_relative_path(scope_file, repo_root)
    mission_scope = load_mission_scope_file(
        scope_file, repo_root=repo_root, expected_mission_id=mission_id
    )
    mission_scope_hash = git_blob_sha256(repo_root, expected_head, mission_scope_path)
    if scope_file_sha256(scope_file) != mission_scope_hash:
        raise MissionScopeError("mission scope file bytes differ from the exact candidate HEAD")
    return mission_scope, mission_scope_path, mission_scope_hash


def _ensure_private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    current_mode = stat.S_IMODE(path.stat().st_mode)
    if current_mode & 0o077:
        raise ReviewReceiptError(f"evidence directory 必须是 owner-only (0700): {path}")


def _write_exclusive(path: Path, body: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ReviewReceiptError(f"拒绝覆盖已有 evidence 文件: {path}") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ReviewReceiptError(f"写入 evidence 失败: {path}: {exc}") from exc


def run_review(args: argparse.Namespace) -> Path:  # noqa: PLR0915
    """Run a fresh read-only Codex review and emit one external receipt."""

    repo_root = Path(args.repo_root).resolve()
    base_sha = normalize_full_sha(args.base_sha, role="base SHA")
    expected_head = normalize_full_sha(args.head_sha, role="review head SHA")
    actual_head = exact_head(repo_root, "HEAD")
    assert_exact_head(expected_head, actual_head, role="review head")
    if not (repo_root / ".git").exists() and not (repo_root / ".git").is_file():
        raise ReviewReceiptError(f"不是 Git worktree: {repo_root}")
    if not REVIEW_OUTPUT_SCHEMA.is_file():
        raise ReviewReceiptError(f"review output schema 不存在: {REVIEW_OUTPUT_SCHEMA}")

    try:
        mission_scope_file = Path(args.mission_scope_file).absolute()
        mission_scope, mission_scope_path, mission_scope_hash = _load_exact_review_scope(
            repo_root=repo_root,
            scope_file=mission_scope_file,
            expected_head=expected_head,
            mission_id=args.mission_id,
        )
    except (MissionScopeError, ReviewReceiptError, OSError) as exc:
        raise ReviewReceiptError(f"invalid exact-head mission scope: {exc}") from exc

    evidence_dir = _require_external_path(Path(args.evidence_dir), repo_root)
    _ensure_private_directory(evidence_dir)
    run_id = uuid.uuid4().hex
    worktree = evidence_dir / f"review-worktree-{expected_head[:12]}-{run_id[:8]}"
    worktree.mkdir(mode=0o700)
    worktree.rmdir()
    raw_path = evidence_dir / f"codex-review-output-{expected_head[:12]}-{run_id}.jsonl"
    stderr_path = evidence_dir / f"codex-review-stderr-{expected_head[:12]}-{run_id}.log"
    final_path = evidence_dir / f"codex-review-final-{expected_head[:12]}-{run_id}.json"

    _run_git(repo_root, ["worktree", "add", "--detach", str(worktree), expected_head])
    worktree_head = exact_head(worktree, "HEAD")
    assert_exact_head(expected_head, worktree_head, role="review worktree HEAD")
    if _run_git(worktree, ["status", "--porcelain", "--untracked-files=all"]):
        raise ReviewReceiptError("review detached worktree 创建后不是 clean")
    schema_relative_path = REVIEW_OUTPUT_SCHEMA.relative_to(ROOT).as_posix()
    review_output_schema = worktree / schema_relative_path
    if not review_output_schema.is_file():
        raise ReviewReceiptError(f"review commit 中缺少 output schema: {review_output_schema}")

    started_at = _now()
    challenge = review_challenge(
        mission_id=args.mission_id,
        base_sha=base_sha,
        head_sha=expected_head,
        mission_scope_sha256=mission_scope_hash,
    )
    codex_binary = resolve_codex_binary(args.codex_binary)
    command = build_reviewer_command(
        codex_binary=str(codex_binary),
        base_sha=base_sha,
        output_schema=review_output_schema,
        final_message_path=final_path,
    )
    # Model identity and reasoning effort are read back out of the argv that is
    # actually executed, and the CLI version is observed from the same resolved
    # executable: the receipt records the invocation, not a Builder declaration.
    review_model, review_reasoning_effort = reviewer_selectors_from_command(command)
    codex_cli_version = observe_codex_cli_version(codex_binary)
    prompt = _codex_prompt(
        mission_id=args.mission_id,
        base_sha=base_sha,
        head_sha=expected_head,
        mission_scope=mission_scope,
        mission_scope_path=mission_scope_path,
        mission_scope_sha256=mission_scope_hash,
    )
    env = os.environ.copy()
    env["CODEX_AGENT_ROLE"] = REVIEW_ROLE_INDEPENDENT
    env["CODEX_REVIEW_HEAD_SHA"] = expected_head
    env["NO_COLOR"] = "1"

    try:
        process = subprocess.run(
            command,
            cwd=worktree,
            input=prompt.encode("utf-8"),
            text=False,
            capture_output=True,
            env=env,
            check=False,
            timeout=args.timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewReceiptError(f"Codex independent reviewer 启动失败: {exc}") from exc
    finally:
        completed_at = _now()

    raw_bytes = (
        process.stdout if isinstance(process.stdout, bytes) else str(process.stdout).encode("utf-8")
    )
    stderr_bytes = (
        process.stderr if isinstance(process.stderr, bytes) else str(process.stderr).encode("utf-8")
    )
    _write_exclusive(raw_path, raw_bytes)
    _write_exclusive(stderr_path, stderr_bytes)
    if process.returncode != 0:
        raise ReviewReceiptError(
            f"Codex independent reviewer exit={process.returncode}; raw evidence={raw_path}"
        )
    if not final_path.is_file():
        raise ReviewReceiptError("Codex 没有产生 output-last-message；拒绝创建 receipt")
    final_path.chmod(0o600)
    final_text = final_path.read_text(encoding="utf-8")
    result_document = _parse_final_message(final_text)
    _assert_review_challenge(
        result_document,
        mission_id=args.mission_id,
        base_sha=base_sha,
        head_sha=expected_head,
        mission_scope_sha256=mission_scope_hash,
    )
    counts, blocking, review_result, findings = validate_review_result(result_document)
    events = parse_json_lines(raw_bytes)
    reviewer_id = reviewer_invocation_id(events, THREAD_ID_RE)
    assert_successful_completion(events, final_text)
    builder_context_id = args.builder_context_id or os.environ.get(
        "BUILDER_CODEX_CONTEXT", f"builder-process:{os.getppid()}"
    )
    _assert_contexts_separate(builder_context_id, reviewer_id)
    worktree_status = _run_git(worktree, ["status", "--porcelain", "--untracked-files=all"])
    if worktree_status:
        raise ReviewReceiptError("reviewer 改动了 detached worktree；拒绝 receipt")

    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "assurance_model": ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW,
        "hostile_same_uid_forge_resistance": False,
        "review_engine": REVIEW_ENGINE_CODEX,
        "review_role": REVIEW_ROLE_INDEPENDENT,
        "base_sha": base_sha,
        "reviewed_head_sha": expected_head,
        "review_challenge": challenge,
        "diff_sha256": diff_sha256(repo_root, base_sha, expected_head),
        "mission_id": args.mission_id,
        "mission_scope_path": mission_scope_path,
        "mission_scope_sha256": mission_scope_hash,
        "review_started_at": started_at,
        "review_completed_at": completed_at,
        "finding_counts_by_severity": counts,
        "blocking_findings": blocking,
        "review_result": review_result,
        "findings": findings,
        "reviewer_invocation_id": reviewer_id,
        "builder_context_id": builder_context_id,
        "reviewer_context_id": reviewer_id,
        "reviewer_context_separate_from_builder": True,
        "reviewer_read_only": True,
        "isolation": {
            "fresh_process": True,
            "ephemeral_session": True,
            "sandbox": "read-only",
            "detached_worktree": True,
            "worktree_head_sha": worktree_head,
            "worktree_path": str(worktree),
            "worktree_clean_before": True,
            "worktree_clean_after": not bool(worktree_status),
            "source_mutation_detected": bool(worktree_status),
        },
        "model_provenance": {
            "review_model": review_model,
            "review_reasoning_effort": review_reasoning_effort,
            "codex_cli_version": codex_cli_version,
            "model_source": MODEL_SOURCE_CODEX_EXEC_FLAG,
            "reasoning_effort_source": EFFORT_SOURCE_CODEX_CONFIG_OVERRIDE,
            "cli_version_source": CLI_VERSION_SOURCE_OBSERVED_STDOUT,
            "derived_from_recorded_command": True,
        },
        "provenance": {
            "writer": WRAPPER_NAME,
            "integrity_only": True,
            "wrapper_sha256": sha256_file(Path(__file__).resolve()),
            "command_sha256": sha256_bytes(_canonical_json(command)),
            "reviewer_command": list(command),
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "codex_binary": str(codex_binary),
            "codex_binary_sha256": sha256_file(codex_binary),
            "output_schema_path": str(review_output_schema),
            "output_schema_sha256": sha256_file(review_output_schema),
            "raw_output_path": str(raw_path),
            "raw_output_sha256": sha256_bytes(raw_bytes),
            "agent_message_sha256": sha256_bytes(final_text.encode("utf-8")),
            "codex_exit_code": process.returncode,
            "stderr_path": str(stderr_path),
            "final_message_path": str(final_path),
            "final_message_sha256": sha256_file(final_path),
        },
    }
    payload_sha = sha256_bytes(_canonical_json(receipt))
    receipt["integrity"] = {"receipt_payload_sha256": payload_sha}
    receipt_path = _require_external_path(
        Path(args.receipt_path)
        if args.receipt_path
        else evidence_dir / f"codex-review-receipt-{expected_head[:12]}-{run_id}.json",
        repo_root,
    )
    _write_exclusive(receipt_path, _canonical_json(receipt))
    return receipt_path


def build_parser() -> argparse.ArgumentParser:
    """Build the reviewer run/receipt-validation CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="启动新的 read-only Codex reviewer")
    run.add_argument("--repo-root", type=Path, default=ROOT)
    run.add_argument("--base-sha", required=True)
    run.add_argument("--head-sha", required=True)
    run.add_argument("--mission-id", required=True)
    run.add_argument("--mission-scope-file", required=True, type=Path)
    run.add_argument("--evidence-dir", required=True, type=Path)
    run.add_argument("--receipt-path", type=Path, default=None)
    run.add_argument("--builder-context-id", default=None)
    run.add_argument("--codex-binary", default="codex")
    run.add_argument("--timeout-seconds", type=int, default=1800)
    run.add_argument("--json", action="store_true")
    check = sub.add_parser("validate", help="验证一个外部 exact-head receipt")
    check.add_argument("--repo-root", type=Path, default=ROOT)
    check.add_argument("--receipt", required=True, type=Path)
    check.add_argument("--current-head", default=None)
    check.add_argument("--base-sha", default=None)
    check.add_argument("--mission-id", default=None)
    check.add_argument("--mission-scope-file", default=None, type=Path)
    check.add_argument("--json", action="store_true")
    classify = sub.add_parser(
        "classify", help="把 receipt 分类为 VALID_CURRENT / STALE_TOOLING / INVALID"
    )
    classify.add_argument("--repo-root", type=Path, default=ROOT)
    classify.add_argument("--receipt", required=True, type=Path)
    classify.add_argument("--current-head", default=None)
    classify.add_argument("--base-sha", default=None)
    classify.add_argument("--mission-id", default=None)
    classify.add_argument("--mission-scope-file", default=None, type=Path)
    classify.add_argument(
        "--historical-audit",
        action="store_true",
        help="把 receipt 当作历史证据解释，忽略 current-HEAD freshness 比较",
    )
    classify.add_argument("--json", action="store_true")
    return parser


def _print_classification(classification: ReceiptClassification) -> None:
    print(f"RECEIPT_CLASSIFICATION={classification.classification}")
    print(f"RECEIPT_INTEGRITY={classification.integrity}")
    print(f"REASON_CODES={','.join(classification.reason_codes) or 'NONE'}")
    print(
        f"CURRENT_APPROVAL_ELIGIBLE={'YES' if classification.current_approval_eligible else 'NO'}"
    )

    print(f"DETAIL={classification.detail}")


def main(argv: list[str] | None = None) -> int:
    """Run the requested reviewer subcommand and return its exit status."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            receipt_path = run_review(args)
            receipt = None
        elif args.command == "classify":
            classification = classify_receipt(
                args.receipt,
                repo_root=Path(args.repo_root).resolve(),
                current_head=args.current_head,
                expected_base=args.base_sha,
                expected_mission_id=args.mission_id,
                expected_mission_scope_file=args.mission_scope_file,
                historical_audit=args.historical_audit,
            )
            receipt_path = args.receipt
            receipt = classification.receipt
            _print_classification(classification)
            if args.json:
                print(
                    json.dumps(
                        {
                            "review_receipt": str(receipt_path),
                            "classification": classification.to_dict(),
                        },
                        ensure_ascii=False,
                    )
                )
            # A classification query is informational: STALE_TOOLING and
            # INVALID are reported, never converted into a passing exit status.
            return 0
        else:
            receipt_path = args.receipt
            receipt = validate_receipt(
                args.receipt,
                repo_root=Path(args.repo_root).resolve(),
                current_head=args.current_head,
                expected_base=args.base_sha,
                expected_mission_id=args.mission_id,
                expected_mission_scope_file=args.mission_scope_file,
            )
    except (ReviewReceiptError, ExactHeadError, OSError, ValueError) as exc:
        print(f"INDEPENDENT_REVIEW_RECEIPT=FAIL: {exc}", file=sys.stderr)
        return 1
    if args.command == "run":
        print(
            json.dumps({"review_receipt": str(receipt_path), "status": "PASS"}, ensure_ascii=False)
        )
    else:
        print(
            json.dumps(
                {"review_receipt": str(receipt_path), "status": "PASS", "receipt": receipt},
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
