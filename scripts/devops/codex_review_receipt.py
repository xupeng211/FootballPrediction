#!/usr/bin/env python3
"""Receipt evidence for the engineering-independent Codex reviewer.

lifecycle: permanent
owner: engineering workflow governance

This module owns the toolchain-independent half of receipt validation: it
locates one external receipt, proves its evidence is internally consistent and
anchored to the exact reviewed Git object, and hands the raw facts to the
classification layer in ``codex_review_classification``.

No check here compares against the *currently installed* toolchain.  That is
deliberate: a later legitimate upgrade must never turn genuine historical
evidence into INVALID, while a receipt that contradicts the reviewed Git object
must fail.  Local hashes remain integrity evidence, not cryptographic reviewer
identity; the same-uid residual risk stays an explicitly accepted project
decision.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_contract import (  # noqa: E402
    _canonical_json,
    build_review_prompt,
    parse_final_message,
    parse_timestamp,
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
from scripts.devops.codex_review_provenance import ReviewReceiptError  # noqa: E402
from scripts.devops.exact_head import (  # noqa: E402
    ExactHeadError,
    assert_exact_head,
    normalize_full_sha,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW,
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

RECEIPT_SCHEMA_VERSION = "codex-independent-review-receipt/v2"
RECEIPT_SCHEMA_VERSION_V1 = "codex-independent-review-receipt/v1"
LEGACY_RECEIPT_SCHEMA_VERSIONS = frozenset({RECEIPT_SCHEMA_VERSION_V1})
KNOWN_RECEIPT_SCHEMA_VERSIONS = frozenset({RECEIPT_SCHEMA_VERSION, RECEIPT_SCHEMA_VERSION_V1})

MODEL_SOURCE_CODEX_EXEC_FLAG = "codex_exec_model_flag"
EFFORT_SOURCE_CODEX_CONFIG_OVERRIDE = "codex_config_override"
CLI_VERSION_SOURCE_OBSERVED_STDOUT = "observed_codex_version_stdout"

REVIEW_OUTPUT_SCHEMA = ROOT / "schemas" / "agentic" / "codex_review_result.schema.json"
WRAPPER_NAME = "scripts/devops/codex_independent_review.py"
THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{4,256}$")
_codex_prompt = build_review_prompt
_parse_final_message = parse_final_message
_parse_timestamp = parse_timestamp


class _EvidenceError(Exception):
    """Internal carrier for one classified evidence fault."""

    def __init__(self, code: str, detail: str, *, head_error: bool = False) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.head_error = head_error


@contextlib.contextmanager
def _fault(code: str, *, head_error: bool = False) -> Iterator[None]:
    """Attribute any fail-closed evidence error to one machine-readable code."""

    try:
        yield
    except _EvidenceError:
        raise
    except (ReviewReceiptError, ExactHeadError, MissionScopeError, OSError, ValueError) as exc:
        raise _EvidenceError(code, str(exc), head_error=head_error) from exc


def sha256_file(path: Path) -> str:
    """Return SHA-256 for one evidence file without exposing its content."""

    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 evidence 文件 {path}: {exc}") from exc


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


def _validate_private_file(path: Path, field: str) -> None:
    if not path.is_file():
        raise ReviewReceiptError(f"{field} 不存在: {path}")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ReviewReceiptError(f"{field} 必须是 owner-only 文件: {path}")


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


SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Reason codes that describe a target-binding mismatch rather than damaged
# evidence.  They still classify as INVALID for the current target, but the
# receipt itself is not labelled as tampered.
TARGET_BINDING_CODES = frozenset(
    {"WRONG_HEAD", "WRONG_BASE", "WRONG_DIFF", "WRONG_SCOPE", "MISSION_ID_MISMATCH"}
)
REQUIRED_REVIEWER_COMMAND_FLAGS = (
    "--sandbox",
    "--ignore-user-config",
    "--ephemeral",
    "--json",
    "--output-schema",
    "--output-last-message",
)

# Frozen v1 reviewer argv.  A v1 receipt never recorded the executed argv, so
# its ``command_sha256`` can only be re-verified against the exact invocation
# shape that v1 wrapper versions executed.  The literal effort argument is
# deliberately not built from the currently pinned policy: rebuilding it from
# today's selectors would make every genuine v1 receipt look tampered as soon as
# the pinned model or effort changes.
LEGACY_V1_EFFORT_ARGUMENT = 'model_reasoning_effort="medium"'


def build_legacy_v1_reviewer_command(
    *, codex_binary: str, output_schema: Path, final_message_path: Path
) -> list[str]:
    """Rebuild the frozen v1 reviewer invocation recorded by v1 receipts."""

    return [
        codex_binary,
        "exec",
        "-c",
        LEGACY_V1_EFFORT_ARGUMENT,
        "--sandbox",
        "read-only",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--output-schema",
        str(output_schema),
        "--output-last-message",
        str(final_message_path),
    ]


def _load_receipt_document(receipt_path: Path, repo_root: Path) -> tuple[dict[str, Any], list[str]]:
    """Read one external receipt, reporting permission faults as reason codes."""

    resolved = _require_external_path(receipt_path, repo_root, must_exist=True)
    permission_faults: list[str] = []
    if stat.S_IMODE(resolved.stat().st_mode) & 0o077:
        permission_faults.append("RECEIPT_PERMISSION_NOT_OWNER_ONLY")
    try:
        receipt = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _EvidenceError("RECEIPT_JSON_INVALID", f"receipt JSON 无效: {resolved}") from exc
    if not isinstance(receipt, dict):
        raise _EvidenceError("RECEIPT_JSON_INVALID", "receipt 必须是 JSON object")
    return receipt, permission_faults


def _declared_model_provenance(receipt: dict[str, Any]) -> dict[str, Any]:
    value = receipt.get("model_provenance")
    return value if isinstance(value, dict) else {}


def _verify_receipt_internals(  # noqa: C901, PLR0912, PLR0915
    receipt: dict[str, Any],
    *,
    repo_root: Path,
    current_head: str | None,
    expected_base: str | None,
    expected_mission_id: str | None,
    expected_mission_scope_file: Path | None,
    historical_audit: bool,
) -> dict[str, Any]:
    """Prove the toolchain-independent part of one receipt.

    Every check here is anchored either inside the receipt itself or inside the
    reviewed Git object (exact HEAD, blob bytes, `base...head` diff).  None of
    them compares against the *currently installed* toolchain, so a later
    legitimate upgrade cannot turn genuine historical evidence into INVALID.
    """

    schema_version = receipt.get("schema_version")
    if schema_version not in KNOWN_RECEIPT_SCHEMA_VERSIONS:
        raise _EvidenceError("RECEIPT_SCHEMA_UNKNOWN", "receipt schema_version 不匹配")
    legacy = schema_version in LEGACY_RECEIPT_SCHEMA_VERSIONS
    if receipt.get("assurance_model") != ASSURANCE_MODEL_ENGINEERING_INDEPENDENT_REVIEW:
        raise _EvidenceError(
            "ASSURANCE_MODEL_INVALID",
            "receipt assurance_model 必须为 engineering_independent_review",
        )
    if receipt.get("hostile_same_uid_forge_resistance") is not False:
        raise _EvidenceError(
            "SAME_UID_DISCLOSURE_INVALID",
            "receipt 必须明确记录 hostile same-uid forge resistance=NO",
        )
    if receipt.get("review_engine") != REVIEW_ENGINE_CODEX:
        raise _EvidenceError("REVIEW_ENGINE_INVALID", "receipt review_engine 必须为 codex")
    if receipt.get("review_role") != REVIEW_ROLE_INDEPENDENT:
        raise _EvidenceError(
            "REVIEW_ROLE_INVALID", "receipt review_role 必须为 independent_reviewer"
        )

    with _fault("WRONG_BASE", head_error=True):
        base_sha = normalize_full_sha(receipt.get("base_sha"), role="receipt base SHA")
        reviewed_head = normalize_full_sha(
            receipt.get("reviewed_head_sha"), role="receipt reviewed HEAD"
        )
    if not historical_audit:
        observed_head = current_head or exact_head(repo_root, "HEAD")
        with _fault("WRONG_HEAD", head_error=True):
            assert_exact_head(observed_head, reviewed_head, role="review HEAD")
    if expected_base is not None:
        with _fault("WRONG_BASE", head_error=True):
            assert_exact_head(expected_base, base_sha, role="review base")

    if not isinstance(receipt.get("mission_id"), str) or not receipt["mission_id"].strip():
        raise _EvidenceError("MISSION_ID_MISMATCH", "receipt mission_id 缺失")
    if expected_mission_id is not None and receipt.get("mission_id") != expected_mission_id:
        raise _EvidenceError("MISSION_ID_MISMATCH", "receipt mission_id 不匹配")

    with _fault("WRONG_SCOPE"):
        mission_scope, scope_relative_path, scope_commit_hash = _load_receipt_scope(
            repo_root=repo_root,
            receipt=receipt,
            expected_mission_scope_file=expected_mission_scope_file,
            reviewed_head=reviewed_head,
        )
    if receipt.get("mission_scope_sha256") != scope_commit_hash:
        raise _EvidenceError(
            "WRONG_SCOPE", "receipt mission_scope_sha256 与 reviewed exact HEAD 不匹配"
        )
    expected_challenge = review_challenge(
        mission_id=receipt["mission_id"],
        base_sha=base_sha,
        head_sha=reviewed_head,
        mission_scope_sha256=scope_commit_hash,
    )
    if receipt.get("review_challenge") != expected_challenge:
        raise _EvidenceError(
            "WRONG_SCOPE", "receipt review_challenge 与当前 mission/base/HEAD 不匹配"
        )
    if receipt.get("diff_sha256") != diff_sha256(repo_root, base_sha, reviewed_head):
        raise _EvidenceError("WRONG_DIFF", "receipt diff_sha256 与当前 base...HEAD 不匹配")

    with _fault("REVIEW_TIMESTAMP_INVALID"):
        started = _parse_timestamp(receipt.get("review_started_at"), "review_started_at")
        completed = _parse_timestamp(receipt.get("review_completed_at"), "review_completed_at")
    if completed < started:
        raise _EvidenceError(
            "REVIEW_TIMESTAMP_INVALID", "review_completed_at 早于 review_started_at"
        )

    if receipt.get("reviewer_read_only") is not True:
        raise _EvidenceError("ISOLATION_INVALID", "reviewer_read_only 必须为 true")
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
        raise _EvidenceError("ISOLATION_INVALID", "reviewer isolation provenance 不完整")
    if isolation.get("source_mutation_detected") is not False:
        raise _EvidenceError("ISOLATION_INVALID", "reviewer source mutation evidence 不是 false")
    if isolation.get("sandbox") != "read-only":
        raise _EvidenceError("ISOLATION_INVALID", "reviewer sandbox 必须为 read-only")

    with _fault("REVIEW_WORKTREE_INVALID"):
        worktree_path = _require_external_path(
            Path(str(isolation.get("worktree_path") or "")), repo_root
        )
    # A transient detached worktree may legitimately no longer exist when older
    # evidence is re-audited.  That is unverifiable history, not tampering: it
    # downgrades the receipt to STALE_TOOLING and can never reach VALID_CURRENT.
    # The canonical invocation also keeps ``--output-schema`` inside that
    # worktree, so the schema check below depends on this fact as well.
    worktree_available = worktree_path.is_dir() and not worktree_path.is_symlink()
    if worktree_available:
        with _fault("WORKTREE_HEAD_MISMATCH", head_error=True):
            assert_exact_head(
                reviewed_head, isolation.get("worktree_head_sha"), role="review worktree HEAD"
            )
        if not (worktree_path / ".git").exists():
            raise _EvidenceError("REVIEW_WORKTREE_INVALID", "review worktree 必须是 Git worktree")
        with _fault("WORKTREE_HEAD_MISMATCH", head_error=True):
            actual_worktree_head = exact_head(worktree_path, "HEAD")
            assert_exact_head(
                reviewed_head, actual_worktree_head, role="actual review worktree HEAD"
            )
        with _fault("REVIEW_WORKTREE_INVALID"):
            attached_branch = _run_git(
                worktree_path, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False
            )
        if attached_branch:
            raise _EvidenceError(
                "REVIEW_WORKTREE_INVALID", "review worktree 必须保持 detached HEAD"
            )
        with _fault("REVIEW_WORKTREE_INVALID"):
            worktree_status = _run_git(
                worktree_path, ["status", "--porcelain", "--untracked-files=all"]
            )
        if worktree_status:
            raise _EvidenceError("REVIEW_WORKTREE_DIRTY", "review worktree 当前不是 clean")

    reviewer_id = receipt.get("reviewer_invocation_id")
    if not isinstance(reviewer_id, str) or not THREAD_ID_RE.fullmatch(reviewer_id):
        raise _EvidenceError("CONTEXT_SEPARATION_INVALID", "reviewer_invocation_id 无效")
    builder_id = receipt.get("builder_context_id")
    if not isinstance(builder_id, str):
        raise _EvidenceError("CONTEXT_SEPARATION_INVALID", "builder_context_id 缺失")
    if receipt.get("reviewer_context_separate_from_builder") is not True:
        raise _EvidenceError(
            "CONTEXT_SEPARATION_INVALID", "reviewer_context_separate_from_builder 必须为 true"
        )
    with _fault("CONTEXT_SEPARATION_INVALID"):
        _assert_contexts_separate(builder_id, str(receipt.get("reviewer_context_id") or ""))
    if receipt.get("reviewer_context_id") != reviewer_id:
        raise _EvidenceError(
            "CONTEXT_SEPARATION_INVALID", "reviewer_context_id 与 invocation id 不一致"
        )

    provenance = receipt.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("writer") != WRAPPER_NAME:
        raise _EvidenceError("PROVENANCE_INVALID", "receipt provenance writer 缺失或不匹配")
    if provenance.get("integrity_only") is not True:
        raise _EvidenceError(
            "PROVENANCE_INVALID", "receipt 必须明确将本地 provenance 标记为 integrity_only"
        )
    recorded_wrapper_sha = provenance.get("wrapper_sha256")
    if not isinstance(recorded_wrapper_sha, str) or not SHA256_HEX_RE.fullmatch(
        recorded_wrapper_sha
    ):
        raise _EvidenceError(
            "WRAPPER_EVIDENCE_TAMPER", "receipt wrapper_sha256 不是有效的 SHA-256 evidence"
        )
    if not isinstance(provenance.get("command_sha256"), str) or not SHA256_HEX_RE.fullmatch(
        provenance["command_sha256"]
    ):
        raise _EvidenceError(
            "COMMAND_EVIDENCE_TAMPER", "receipt command_sha256 不是有效的 SHA-256 evidence"
        )
    # Git-anchored wrapper provenance: the recorded wrapper hash must be the
    # wrapper blob that actually exists at the reviewed commit.  That check is
    # independent of the currently installed wrapper, so it distinguishes a
    # legitimate later upgrade (STALE_TOOLING) from a rewritten hash (INVALID).
    try:
        anchored_wrapper_sha = git_blob_sha256(repo_root, reviewed_head, WRAPPER_NAME)
    except ReviewReceiptError:
        anchored_wrapper_sha = None
    if anchored_wrapper_sha is not None and recorded_wrapper_sha != anchored_wrapper_sha:
        raise _EvidenceError(
            "WRAPPER_EVIDENCE_TAMPER",
            "receipt wrapper_sha256 与 reviewed exact HEAD 中的 reviewer wrapper 不一致",
        )

    with _fault("OUTPUT_SCHEMA_INVALID"):
        schema_path = _require_external_path(
            Path(str(provenance.get("output_schema_path") or "")), repo_root
        )
    schema_relative_path = REVIEW_OUTPUT_SCHEMA.relative_to(ROOT).as_posix()
    with _fault("OUTPUT_SCHEMA_INVALID"):
        expected_schema_sha = git_blob_sha256(repo_root, reviewed_head, schema_relative_path)
    # The canonical invocation keeps ``--output-schema`` inside the transient
    # review worktree.  Removing that worktree is a legitimate cleanup, so the
    # historical schema is then verified against the blob stored in the reviewed
    # commit instead of the vanished file.  That is unverifiable local history,
    # not tampering: it forces STALE_TOOLING and can never reach VALID_CURRENT.
    # A schema that is missing for any other reason, or present but wrong, stays
    # a tamper fault.
    schema_file_available = schema_path.is_file() and not schema_path.is_symlink()
    schema_inside_removed_worktree = (
        not schema_file_available
        and not worktree_available
        and _path_is_inside(schema_path, worktree_path)
    )
    if schema_file_available:
        if provenance.get("output_schema_sha256") != sha256_file(schema_path):
            raise _EvidenceError("OUTPUT_SCHEMA_INVALID", "output schema sha256 不匹配")
    elif not schema_inside_removed_worktree:
        raise _EvidenceError("OUTPUT_SCHEMA_INVALID", "review output schema 不存在")
    if provenance.get("output_schema_sha256") != expected_schema_sha:
        raise _EvidenceError(
            "OUTPUT_SCHEMA_INVALID", "output schema 不是 reviewed exact HEAD 中的版本"
        )
    with _fault("EVIDENCE_PATH_INVALID"):
        raw_path = _require_external_path(
            Path(str(provenance.get("raw_output_path") or "")), repo_root
        )
        stderr_path = _require_external_path(
            Path(str(provenance.get("stderr_path") or "")), repo_root
        )
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
        raise _EvidenceError("RAW_OUTPUT_SHA256_MISMATCH", "raw output sha256 不匹配")
    if provenance.get("final_message_sha256") != sha256_file(final_path):
        raise _EvidenceError("FINAL_MESSAGE_SHA256_MISMATCH", "final message sha256 不匹配")

    codex_binary = provenance.get("codex_binary")
    if not isinstance(codex_binary, str) or not codex_binary.strip():
        raise _EvidenceError("BINARY_EVIDENCE_UNRESOLVABLE", "provenance codex_binary 缺失")
    try:
        codex_binary_path = Path(codex_binary).resolve(strict=True)
    except OSError as exc:
        raise _EvidenceError(
            "BINARY_EVIDENCE_UNRESOLVABLE", "provenance codex_binary path 无法解析"
        ) from exc
    if not codex_binary_path.is_file() or not os.access(codex_binary_path, os.X_OK):
        raise _EvidenceError(
            "BINARY_EVIDENCE_UNRESOLVABLE", "provenance codex_binary 不是 Codex CLI executable"
        )
    recorded_binary_sha = provenance.get("codex_binary_sha256")
    if not isinstance(recorded_binary_sha, str) or not SHA256_HEX_RE.fullmatch(recorded_binary_sha):
        raise _EvidenceError(
            "BINARY_EVIDENCE_UNRESOLVABLE",
            "receipt codex_binary_sha256 不是有效的 SHA-256 evidence",
        )

    recorded_command: list[str] | None = None
    review_model: str | None = None
    review_effort: str | None = None
    if legacy:
        if "reviewer_command" in provenance or "model_provenance" in receipt:
            raise _EvidenceError(
                "MODEL_PROVENANCE_INVALID", "v1 receipt 不得包含 v2 model provenance 字段"
            )
        # v1 receipts cannot record the executed argv, so their command hash is
        # re-derived from the frozen v1 invocation rebuilt out of the receipt's
        # own recorded paths.  The legacy internal-consistency check therefore
        # still holds: an arbitrary 64-hex command_sha256 is a tamper fault, not
        # legitimate historical drift.  It never makes a v1 receipt current.
        expected_legacy_command_sha = sha256_bytes(
            _canonical_json(
                build_legacy_v1_reviewer_command(
                    codex_binary=codex_binary,
                    output_schema=schema_path,
                    final_message_path=final_path,
                )
            )
        )
        if provenance.get("command_sha256") != expected_legacy_command_sha:
            raise _EvidenceError(
                "COMMAND_EVIDENCE_TAMPER",
                "command_sha256 与 v1 canonical reviewer invocation 不一致",
            )
    else:
        recorded_command = provenance.get("reviewer_command")
        if not isinstance(recorded_command, list) or not all(
            isinstance(part, str) and part for part in recorded_command
        ):
            raise _EvidenceError(
                "COMMAND_EVIDENCE_TAMPER", "receipt provenance.reviewer_command 缺失或无效"
            )
        if provenance.get("command_sha256") != sha256_bytes(_canonical_json(recorded_command)):
            raise _EvidenceError(
                "COMMAND_EVIDENCE_TAMPER",
                "command_sha256 与 receipt 自己记录的 reviewer invocation 不一致",
            )
        for required_flag in REQUIRED_REVIEWER_COMMAND_FLAGS:
            if required_flag not in recorded_command:
                raise _EvidenceError(
                    "REVIEWER_ISOLATION_MISSING",
                    f"recorded reviewer command 缺少 {required_flag}",
                )
        if recorded_command[recorded_command.index("--sandbox") + 1] != "read-only":
            raise _EvidenceError(
                "REVIEWER_ISOLATION_MISSING", "recorded reviewer command sandbox 不是 read-only"
            )
        try:
            review_model, review_effort = reviewer_selectors_from_command(recorded_command)
        except ReviewReceiptError as exc:
            raise _EvidenceError("REVIEWER_MODEL_NOT_PINNED", str(exc)) from exc
        model_declaration = receipt.get("model_provenance")
        if not isinstance(model_declaration, dict):
            raise _EvidenceError("MODEL_PROVENANCE_INVALID", "receipt model_provenance 缺失")
        if model_declaration.get("derived_from_recorded_command") is not True:
            raise _EvidenceError(
                "MODEL_PROVENANCE_INVALID", "model_provenance 必须声明由 recorded command 派生"
            )
        if model_declaration.get("model_source") != MODEL_SOURCE_CODEX_EXEC_FLAG:
            raise _EvidenceError("MODEL_PROVENANCE_INVALID", "model_provenance.model_source 无效")
        if model_declaration.get("reasoning_effort_source") != EFFORT_SOURCE_CODEX_CONFIG_OVERRIDE:
            raise _EvidenceError(
                "MODEL_PROVENANCE_INVALID", "model_provenance.reasoning_effort_source 无效"
            )
        if model_declaration.get("cli_version_source") != CLI_VERSION_SOURCE_OBSERVED_STDOUT:
            raise _EvidenceError(
                "MODEL_PROVENANCE_INVALID", "model_provenance.cli_version_source 无效"
            )
        if model_declaration.get("review_model") != review_model:
            raise _EvidenceError(
                "MODEL_FIELD_COMMAND_MISMATCH",
                "receipt review_model 与 recorded reviewer command 不一致",
            )
        if model_declaration.get("review_reasoning_effort") != review_effort:
            raise _EvidenceError(
                "REASONING_FIELD_COMMAND_MISMATCH",
                "receipt review_reasoning_effort 与 recorded reviewer command 不一致",
            )
        if (
            not isinstance(model_declaration.get("codex_cli_version"), str)
            or not str(model_declaration["codex_cli_version"]).strip()
        ):
            raise _EvidenceError("MODEL_PROVENANCE_INVALID", "receipt codex_cli_version 缺失")

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
        raise _EvidenceError(
            "PROMPT_SHA256_MISMATCH", "reviewer prompt provenance 与当前 target 不匹配"
        )

    with _fault("RAW_OUTPUT_COMPLETION_INVALID"):
        final_text = final_path.read_text(encoding="utf-8")
        events = parse_json_lines(raw_path.read_bytes())
    if reviewer_invocation_id(events, THREAD_ID_RE) != reviewer_id:
        raise _EvidenceError("INVOCATION_ID_MISMATCH", "raw output invocation id 与 receipt 不一致")
    with _fault("RAW_OUTPUT_COMPLETION_INVALID"):
        assert_successful_completion(events, final_text)
    if provenance.get("agent_message_sha256") != sha256_bytes(final_text.encode("utf-8")):
        raise _EvidenceError("AGENT_MESSAGE_SHA256_MISMATCH", "agent_message_sha256 不匹配")
    if provenance.get("codex_exit_code") != 0:
        raise _EvidenceError("CODEX_EXIT_CODE_NONZERO", "Codex exit code 不是 0")

    with _fault("FINDING_DERIVATION_MISMATCH"):
        result_document = _parse_final_message(final_text)
    with _fault("REVIEW_CHALLENGE_MISMATCH"):
        _assert_review_challenge(
            result_document,
            mission_id=receipt["mission_id"],
            base_sha=base_sha,
            head_sha=reviewed_head,
            mission_scope_sha256=scope_commit_hash,
        )
    with _fault("FINDING_DERIVATION_MISMATCH"):
        counts, blocking, review_result, findings = validate_review_result(result_document)
    if receipt.get("finding_counts_by_severity") != counts:
        raise _EvidenceError(
            "FINDING_DERIVATION_MISMATCH", "receipt finding counts 不是由 final message 派生的值"
        )
    if (
        receipt.get("blocking_findings") != blocking
        or receipt.get("review_result") != review_result
    ):
        raise _EvidenceError(
            "FINDING_DERIVATION_MISMATCH", "receipt result/blocking findings 不一致"
        )
    if receipt.get("findings") != findings:
        raise _EvidenceError(
            "FINDING_DERIVATION_MISMATCH", "receipt findings 与 final message 不一致"
        )

    unsigned = dict(receipt)
    integrity = unsigned.pop("integrity", None)
    if not isinstance(integrity, dict):
        raise _EvidenceError("RECEIPT_PAYLOAD_INTEGRITY_MISMATCH", "receipt integrity 缺失")
    if integrity.get("receipt_payload_sha256") != sha256_bytes(_canonical_json(unsigned)):
        raise _EvidenceError(
            "RECEIPT_PAYLOAD_INTEGRITY_MISMATCH", "receipt payload integrity 不匹配"
        )

    return {
        "legacy_schema": legacy,
        "base_sha": base_sha,
        "reviewed_head": reviewed_head,
        "schema_path": schema_path,
        "final_path": final_path,
        "schema_argument": str(provenance.get("output_schema_path")),
        "final_argument": str(provenance.get("final_message_path")),
        "codex_binary_path": codex_binary_path,
        "codex_binary_argument": codex_binary,
        "recorded_binary_sha256": recorded_binary_sha,
        "current_binary_sha256": sha256_file(codex_binary_path),
        "recorded_wrapper_sha256": recorded_wrapper_sha,
        "wrapper_anchored": anchored_wrapper_sha is not None,
        "recorded_command": recorded_command,
        "review_model": review_model,
        "review_effort": review_effort,
        "worktree_available": worktree_available,
        "schema_file_available": schema_file_available,
    }
