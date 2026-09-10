#!/usr/bin/env python3
"""启动并验证 engineering-independent Codex reviewer。

lifecycle: permanent
owner: engineering workflow governance

`run` 在 reviewed commit 的 detached worktree 中启动新的、ephemeral
``codex exec`` 子进程，强制 ``--sandbox read-only`` 和 JSON 输出；reviewer
不共享 Builder session，也不接收 Builder 的自证。receipt 与原始 Codex
输出必须位于 reviewed source tree 之外。

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
import re
import stat
import subprocess
import sys
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_contract import (  # noqa: E402
    _canonical_json,
    build_review_prompt,
    build_reviewer_command,
    parse_final_message,
    parse_timestamp,
    review_challenge,
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
    resolve_codex_binary,
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

RECEIPT_SCHEMA_VERSION = "codex-independent-review-receipt/v1"
REVIEW_OUTPUT_SCHEMA = ROOT / "schemas" / "agentic" / "codex_review_result.schema.json"
WRAPPER_NAME = "scripts/devops/codex_independent_review.py"
THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{4,256}$")
_codex_prompt = build_review_prompt
_parse_final_message = parse_final_message
_parse_timestamp = parse_timestamp


def sha256_file(path: Path) -> str:
    """Return SHA-256 for one evidence file without exposing its content."""

    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 evidence 文件 {path}: {exc}") from exc


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _run_git(repo_root: Path, args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise ReviewReceiptError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def exact_head(repo_root: Path, ref: str) -> str:
    """Resolve one repository ref and require its complete 40-hex SHA."""

    return normalize_full_sha(_run_git(repo_root, ["rev-parse", f"{ref}^{{commit}}"]), role=ref)


def diff_sha256(repo_root: Path, base_sha: str, head_sha: str) -> str:
    """Hash the complete binary-safe base...head diff without persisting it."""

    result = subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", f"{base_sha}...{head_sha}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReviewReceiptError(result.stderr.decode("utf-8", errors="replace").strip())
    return sha256_bytes(result.stdout)


def git_blob_sha256(repo_root: Path, commit_sha: str, relative_path: str) -> str:
    """Hash one file as stored in an exact commit, not from a dirty worktree."""

    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{relative_path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReviewReceiptError(
            result.stderr.decode("utf-8", errors="replace").strip()
            or f"review commit 中缺少 output schema: {relative_path}"
        )
    return sha256_bytes(result.stdout)


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


def _path_is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _require_external_path(path: Path, repo_root: Path, *, must_exist: bool = False) -> Path:
    if not path.is_absolute():
        raise ReviewReceiptError(f"evidence path 必须是绝对路径: {path}")
    resolved = path.resolve(strict=False)
    if _path_is_inside(resolved, repo_root):
        raise ReviewReceiptError(f"evidence path 不得位于 reviewed source tree: {resolved}")
    if must_exist and not resolved.is_file():
        raise ReviewReceiptError(f"evidence 文件不存在: {resolved}")
    return resolved


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


def _assert_contexts_separate(builder_context_id: str, reviewer_context_id: str) -> None:
    if not builder_context_id.strip() or not reviewer_context_id.strip():
        raise ReviewReceiptError("Builder/reviewer context identity 不能为空")
    if builder_context_id == reviewer_context_id:
        raise ReviewReceiptError(
            "Builder 与 reviewer context 相同，拒绝把 self-review 算作 independent"
        )
    if reviewer_context_id.casefold() in {"builder", "builder-codex", "same-session"}:
        raise ReviewReceiptError("reviewer context 使用了 Builder/self-review identity")


def _assert_review_challenge(
    result: dict[str, Any],
    *,
    mission_id: str,
    base_sha: str,
    head_sha: str,
    mission_scope_sha256: str,
) -> None:
    expected = review_challenge(
        mission_id=mission_id,
        base_sha=base_sha,
        head_sha=head_sha,
        mission_scope_sha256=mission_scope_sha256,
    )
    if result.get("review_challenge") != expected:
        raise ReviewReceiptError("review challenge 与当前 mission/base/HEAD 不匹配")


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
        "provenance": {
            "writer": WRAPPER_NAME,
            "integrity_only": True,
            "wrapper_sha256": sha256_file(Path(__file__).resolve()),
            "command_sha256": sha256_bytes(_canonical_json(command)),
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


def _validate_private_file(path: Path, field: str) -> None:
    if not path.is_file():
        raise ReviewReceiptError(f"{field} 不存在: {path}")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ReviewReceiptError(f"{field} 必须是 owner-only 文件: {path}")


def _validate_regular_file(path: Path, field: str) -> None:
    """Validate an auditable file without treating mode as trust authority."""

    if not path.is_file() or path.is_symlink():
        raise ReviewReceiptError(f"{field} 必须是 regular file: {path}")


def _load_receipt_scope(
    *,
    repo_root: Path,
    receipt: dict[str, Any],
    expected_mission_scope_file: Path | None,
    reviewed_head: str,
) -> tuple[MissionScope, str, str]:
    """Load and exact-head-bind the scope named by a receipt."""

    scope_path_value = receipt.get("mission_scope_path")
    if not isinstance(scope_path_value, str) or not scope_path_value.strip():
        raise ReviewReceiptError("receipt mission_scope_path 缺失")
    scope_path = repo_root / scope_path_value
    scope_relative_path = mission_scope_relative_path(scope_path, repo_root)
    if scope_relative_path != scope_path_value:
        raise MissionScopeError("receipt mission_scope_path 必须是规范 repository-relative path")
    if expected_mission_scope_file is not None:
        expected_scope_relative = mission_scope_relative_path(
            expected_mission_scope_file, repo_root
        )
        if expected_scope_relative != scope_relative_path:
            raise MissionScopeError("receipt mission scope path 与当前 mission scope 不匹配")
    mission_scope = load_mission_scope_file(
        scope_path,
        repo_root=repo_root,
        expected_mission_id=receipt["mission_id"],
    )
    scope_commit_hash = git_blob_sha256(repo_root, reviewed_head, scope_relative_path)
    if scope_file_sha256(scope_path) != scope_commit_hash:
        raise MissionScopeError("mission scope file bytes differ from reviewed exact HEAD")
    return mission_scope, scope_relative_path, scope_commit_hash


def validate_receipt(  # noqa: C901, PLR0912, PLR0915
    receipt_path: Path,
    *,
    repo_root: Path,
    current_head: str | None = None,
    expected_base: str | None = None,
    expected_mission_id: str | None = None,
    expected_mission_scope_file: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed validation for one external, exact-head receipt."""

    receipt_path = _require_external_path(receipt_path, repo_root, must_exist=True)
    _validate_private_file(receipt_path, "receipt")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewReceiptError(f"receipt JSON 无效: {receipt_path}") from exc
    if not isinstance(receipt, dict):
        raise ReviewReceiptError("receipt 必须是 JSON object")
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ReviewReceiptError("receipt schema_version 不匹配")
    if receipt.get("assurance_model") != ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW:
        raise ReviewReceiptError("receipt assurance_model 必须为 engineering_independent_review")
    if receipt.get("hostile_same_uid_forge_resistance") is not False:
        raise ReviewReceiptError("receipt 必须明确记录 hostile same-uid forge resistance=NO")
    if receipt.get("review_engine") != REVIEW_ENGINE_CODEX:
        raise ReviewReceiptError("receipt review_engine 必须为 codex")
    if receipt.get("review_role") != REVIEW_ROLE_INDEPENDENT:
        raise ReviewReceiptError("receipt review_role 必须为 independent_reviewer")
    base_sha = normalize_full_sha(receipt.get("base_sha"), role="receipt base SHA")
    reviewed_head = normalize_full_sha(
        receipt.get("reviewed_head_sha"), role="receipt reviewed HEAD"
    )
    observed_head = current_head or exact_head(repo_root, "HEAD")
    assert_exact_head(observed_head, reviewed_head, role="review HEAD")
    if expected_base is not None:
        assert_exact_head(expected_base, base_sha, role="review base")
    if expected_mission_id is not None and receipt.get("mission_id") != expected_mission_id:
        raise ReviewReceiptError("receipt mission_id 不匹配")
    if not isinstance(receipt.get("mission_id"), str) or not receipt["mission_id"].strip():
        raise ReviewReceiptError("receipt mission_id 缺失")
    try:
        mission_scope, scope_relative_path, scope_commit_hash = _load_receipt_scope(
            repo_root=repo_root,
            receipt=receipt,
            expected_mission_scope_file=expected_mission_scope_file,
            reviewed_head=reviewed_head,
        )
    except (MissionScopeError, ReviewReceiptError, OSError) as exc:
        raise ReviewReceiptError(f"receipt mission scope invalid: {exc}") from exc
    if receipt.get("mission_scope_sha256") != scope_commit_hash:
        raise ReviewReceiptError("receipt mission_scope_sha256 与 reviewed exact HEAD 不匹配")
    expected_challenge = review_challenge(
        mission_id=receipt["mission_id"],
        base_sha=base_sha,
        head_sha=reviewed_head,
        mission_scope_sha256=scope_commit_hash,
    )
    if receipt.get("review_challenge") != expected_challenge:
        raise ReviewReceiptError("receipt review_challenge 与当前 mission/base/HEAD 不匹配")
    if receipt.get("diff_sha256") != diff_sha256(repo_root, base_sha, reviewed_head):
        raise ReviewReceiptError("receipt diff_sha256 与当前 base...HEAD 不匹配")

    started = _parse_timestamp(receipt.get("review_started_at"), "review_started_at")
    completed = _parse_timestamp(receipt.get("review_completed_at"), "review_completed_at")
    if completed < started:
        raise ReviewReceiptError("review_completed_at 早于 review_started_at")

    if receipt.get("reviewer_read_only") is not True:
        raise ReviewReceiptError("reviewer_read_only 必须为 true")
    isolation = receipt.get("isolation")
    if not isinstance(isolation, dict) or any(
        isolation.get(field) is not True
        for field in (
            "fresh_process",
            "ephemeral_session",
            "detached_worktree",
            "worktree_clean_before",
            "worktree_clean_after",
        )
    ):
        raise ReviewReceiptError("reviewer isolation provenance 不完整")
    if isolation.get("source_mutation_detected") is not False:
        raise ReviewReceiptError("reviewer source mutation evidence 不是 false")
    if isolation.get("sandbox") != "read-only":
        raise ReviewReceiptError("reviewer sandbox 必须为 read-only")
    worktree_path = _require_external_path(
        Path(str(isolation.get("worktree_path") or "")), repo_root
    )
    if not worktree_path.is_dir() or worktree_path.is_symlink():
        raise ReviewReceiptError("review worktree path 必须是 external regular directory")
    assert_exact_head(
        reviewed_head, isolation.get("worktree_head_sha"), role="review worktree HEAD"
    )
    if not (worktree_path / ".git").exists():
        raise ReviewReceiptError("review worktree 必须是 Git worktree")
    actual_worktree_head = exact_head(worktree_path, "HEAD")
    assert_exact_head(reviewed_head, actual_worktree_head, role="actual review worktree HEAD")
    attached_branch = _run_git(
        worktree_path, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False
    )
    if attached_branch:
        raise ReviewReceiptError("review worktree 必须保持 detached HEAD")
    if _run_git(worktree_path, ["status", "--porcelain", "--untracked-files=all"]):
        raise ReviewReceiptError("review worktree 当前不是 clean")

    reviewer_id = receipt.get("reviewer_invocation_id")
    builder_id = receipt.get("builder_context_id")
    if not isinstance(reviewer_id, str) or not THREAD_ID_RE.fullmatch(reviewer_id):
        raise ReviewReceiptError("reviewer_invocation_id 无效")
    if not isinstance(builder_id, str):
        raise ReviewReceiptError("builder_context_id 缺失")
    if receipt.get("reviewer_context_separate_from_builder") is not True:
        raise ReviewReceiptError("reviewer_context_separate_from_builder 必须为 true")
    _assert_contexts_separate(builder_id, str(receipt.get("reviewer_context_id") or ""))
    if receipt.get("reviewer_context_id") != reviewer_id:
        raise ReviewReceiptError("reviewer_context_id 与 invocation id 不一致")

    provenance = receipt.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("writer") != WRAPPER_NAME:
        raise ReviewReceiptError("receipt provenance writer 缺失或不匹配")
    if provenance.get("integrity_only") is not True:
        raise ReviewReceiptError("receipt 必须明确将本地 provenance 标记为 integrity_only")
    if provenance.get("wrapper_sha256") != sha256_file(Path(__file__).resolve()):
        raise ReviewReceiptError("receipt wrapper_sha256 与当前 reviewer wrapper 不匹配")
    schema_path = _require_external_path(
        Path(str(provenance.get("output_schema_path") or "")), repo_root
    )
    _validate_regular_file(schema_path, "review output schema")
    schema_relative_path = REVIEW_OUTPUT_SCHEMA.relative_to(ROOT).as_posix()
    expected_schema_sha = git_blob_sha256(repo_root, reviewed_head, schema_relative_path)
    if provenance.get("output_schema_sha256") != sha256_file(schema_path):
        raise ReviewReceiptError("output schema sha256 不匹配")
    if provenance.get("output_schema_sha256") != expected_schema_sha:
        raise ReviewReceiptError("output schema 不是 reviewed exact HEAD 中的版本")
    raw_path = _require_external_path(Path(str(provenance.get("raw_output_path") or "")), repo_root)
    stderr_path = _require_external_path(Path(str(provenance.get("stderr_path") or "")), repo_root)
    final_path = _require_external_path(
        Path(str(provenance.get("final_message_path") or "")), repo_root
    )
    for path, field in (
        (raw_path, "raw output"),
        (stderr_path, "stderr"),
        (final_path, "final message"),
    ):
        _validate_private_file(path, field)
    if provenance.get("raw_output_sha256") != sha256_file(raw_path):
        raise ReviewReceiptError("raw output sha256 不匹配")
    if provenance.get("final_message_sha256") != sha256_file(final_path):
        raise ReviewReceiptError("final message sha256 不匹配")
    codex_binary = provenance.get("codex_binary")
    if not isinstance(codex_binary, str) or not codex_binary.strip():
        raise ReviewReceiptError("provenance codex_binary 缺失")
    try:
        codex_binary_path = Path(codex_binary).resolve(strict=True)
    except OSError as exc:
        raise ReviewReceiptError("provenance codex_binary path 无法解析") from exc
    if not codex_binary_path.is_file() or not os.access(codex_binary_path, os.X_OK):
        raise ReviewReceiptError("provenance codex_binary 不是 Codex CLI executable")
    if provenance.get("codex_binary_sha256") != sha256_file(codex_binary_path):
        raise ReviewReceiptError("Codex CLI executable sha256 不匹配")
    expected_command_sha = sha256_bytes(
        _canonical_json(
            build_reviewer_command(
                codex_binary=codex_binary,
                base_sha=base_sha,
                output_schema=schema_path,
                final_message_path=final_path,
            )
        )
    )
    if provenance.get("command_sha256") != expected_command_sha:
        raise ReviewReceiptError("reviewer command provenance 不匹配")
    expected_prompt_sha = sha256_bytes(
        _codex_prompt(
            mission_id=receipt["mission_id"],
            base_sha=base_sha,
            head_sha=reviewed_head,
            mission_scope=mission_scope,
            mission_scope_path=scope_relative_path,
            mission_scope_sha256=scope_commit_hash,
        ).encode("utf-8")
    )
    if provenance.get("prompt_sha256") != expected_prompt_sha:
        raise ReviewReceiptError("reviewer prompt provenance 与当前 target 不匹配")
    final_text = final_path.read_text(encoding="utf-8")
    events = parse_json_lines(raw_path.read_bytes())
    if reviewer_invocation_id(events, THREAD_ID_RE) != reviewer_id:
        raise ReviewReceiptError("raw output invocation id 与 receipt 不一致")
    assert_successful_completion(events, final_text)
    if provenance.get("agent_message_sha256") != sha256_bytes(final_text.encode("utf-8")):
        raise ReviewReceiptError("agent_message_sha256 不匹配")
    if provenance.get("codex_exit_code") != 0:
        raise ReviewReceiptError("Codex exit code 不是 0")
    result_document = _parse_final_message(final_text)
    _assert_review_challenge(
        result_document,
        mission_id=receipt["mission_id"],
        base_sha=base_sha,
        head_sha=reviewed_head,
        mission_scope_sha256=scope_commit_hash,
    )
    counts, blocking, review_result, findings = validate_review_result(result_document)
    if receipt.get("finding_counts_by_severity") != counts:
        raise ReviewReceiptError("receipt finding counts 不是由 final message 派生的值")
    if (
        receipt.get("blocking_findings") != blocking
        or receipt.get("review_result") != review_result
    ):
        raise ReviewReceiptError("receipt result/blocking findings 不一致")
    if receipt.get("findings") != findings:
        raise ReviewReceiptError("receipt findings 与 final message 不一致")

    unsigned = dict(receipt)
    integrity = unsigned.pop("integrity", None)
    if not isinstance(integrity, dict):
        raise ReviewReceiptError("receipt integrity 缺失")
    if integrity.get("receipt_payload_sha256") != sha256_bytes(_canonical_json(unsigned)):
        raise ReviewReceiptError("receipt payload integrity 不匹配")
    return receipt


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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested reviewer subcommand and return its exit status."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            receipt_path = run_review(args)
            receipt = None
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
