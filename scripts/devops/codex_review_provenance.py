#!/usr/bin/env python3
"""Codex CLI execution provenance helpers for the independent-review wrapper.

lifecycle: permanent
owner: engineering workflow governance

This module accepts persisted session/index evidence only when it is produced
under the Codex-owned session root and matches one exact reviewer target.
It never writes the reviewed source tree or any review receipt.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from typing import Any


class ReviewReceiptError(ValueError):
    """Raised when independent-review provenance cannot be trusted."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def codex_home() -> Path:
    """Resolve the Codex CLI home used for its persisted session evidence."""

    configured = os.environ.get("CODEX_HOME")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (Path.home() / ".codex").resolve()
    )


def codex_sessions_root() -> Path:
    """Return the Codex-owned persisted-session directory."""

    return codex_home() / "sessions"


def codex_session_index_path() -> Path:
    """Return the Codex-owned session index path."""

    return codex_home() / "session_index.jsonl"


def resolve_codex_binary(value: str) -> Path:
    """Resolve the installed Codex executable; arbitrary paths are rejected."""

    if value != "codex":
        raise ReviewReceiptError("reviewer executable 只允许使用 PATH 中的 codex CLI")
    resolved = shutil.which("codex")
    if not resolved:
        raise ReviewReceiptError("PATH 中找不到 Codex CLI executable")
    executable = Path(resolved).resolve(strict=True)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ReviewReceiptError(f"Codex CLI executable 无效: {executable}")
    return executable


def find_codex_session_artifact(reviewer_id: str) -> Path:
    """Find the unique persisted Codex rollout for one reviewer thread."""

    root = codex_sessions_root()
    try:
        candidates = sorted(
            path
            for path in root.rglob(f"*{reviewer_id}.jsonl")
            if path.is_file() and not path.is_symlink()
        )
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 Codex session evidence: {root}: {exc}") from exc
    if len(candidates) != 1:
        raise ReviewReceiptError(
            f"Codex persisted session evidence 必须唯一: thread={reviewer_id}, count={len(candidates)}"
        )
    return candidates[0].resolve()


def _validate_codex_session_file(path: Path, field: str) -> bytes:
    """Read a Codex-owned session file without accepting writable/symlink evidence."""

    if not path.is_file() or path.is_symlink():
        raise ReviewReceiptError(f"{field} 必须是 regular file: {path}")
    file_stat = path.stat()
    if stat.S_IMODE(file_stat.st_mode) & 0o022:
        raise ReviewReceiptError(f"{field} 不得由 group/other 写入: {path}")
    if hasattr(os, "getuid") and file_stat.st_uid != os.getuid():
        raise ReviewReceiptError(f"{field} owner 不是当前 Codex 用户: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 {field}: {path}: {exc}") from exc


def validate_codex_session_evidence(  # noqa: C901, PLR0912, PLR0915
    *,
    session_path: Path,
    reviewer_id: str,
    worktree: Path,
    mission_id: str,
    base_sha: str,
    head_sha: str,
    challenge: str,
) -> tuple[str, str, Path, str]:
    """Verify Codex-generated persisted session/index evidence for one target."""

    session_root = codex_sessions_root().resolve()
    try:
        session_path = session_path.resolve(strict=True)
        session_path.relative_to(session_root)
    except (OSError, ValueError) as exc:
        raise ReviewReceiptError(
            "Codex session evidence 必须位于 Codex-owned sessions root"
        ) from exc
    if not session_path.name.endswith(f"-{reviewer_id}.jsonl"):
        raise ReviewReceiptError("Codex session evidence filename 与 reviewer invocation 不一致")
    session_bytes = _validate_codex_session_file(session_path, "Codex session evidence")
    metadata: list[dict[str, Any]] = []
    has_user_prompt = False
    for line_no, line in enumerate(session_bytes.decode("utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            envelope = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReviewReceiptError(f"Codex session evidence 第 {line_no} 行无效") from exc
        if not isinstance(envelope, dict):
            continue
        if envelope.get("type") == "session_meta" and isinstance(envelope.get("payload"), dict):
            metadata.append(envelope["payload"])
        payload = envelope.get("payload")
        if (
            isinstance(payload, dict)
            and payload.get("type") == "message"
            and payload.get("role") == "user"
        ):
            has_user_prompt = True
    if len(metadata) != 1:
        raise ReviewReceiptError("Codex session evidence 必须包含唯一 session_meta")
    session_meta = metadata[0]
    if session_meta.get("id") != reviewer_id or session_meta.get("session_id") != reviewer_id:
        raise ReviewReceiptError("Codex session_meta identity 与 reviewer invocation 不一致")
    if session_meta.get("source") != "cli" or not str(session_meta.get("cli_version") or ""):
        raise ReviewReceiptError("Codex session_meta 缺少 CLI provenance")
    try:
        session_cwd = Path(str(session_meta.get("cwd") or "")).resolve(strict=True)
        expected_cwd = worktree.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ReviewReceiptError("Codex session_meta cwd 无法解析") from exc
    if session_cwd != expected_cwd:
        raise ReviewReceiptError("Codex session_meta cwd 不是 reviewed detached worktree")
    markers = (
        f"MISSION_ID={mission_id}",
        f"BASE_SHA={base_sha}",
        f"REVIEW_HEAD_SHA={head_sha}",
        f"REVIEW_CHALLENGE={challenge}",
    )
    if not all(marker.encode() in session_bytes for marker in markers):
        raise ReviewReceiptError("Codex persisted session 未包含本次 exact target prompt")
    if not has_user_prompt:
        raise ReviewReceiptError("Codex persisted session 缺少 user prompt evidence")

    index_path = codex_session_index_path().resolve(strict=True)
    index_bytes = _validate_codex_session_file(index_path, "Codex session index")
    matching_index_lines: list[str] = []
    for line in index_bytes.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReviewReceiptError("Codex session index 包含无效 JSONL") from exc
        if isinstance(value, dict) and value.get("id") == reviewer_id:
            matching_index_lines.append(line)
    if not matching_index_lines:
        raise ReviewReceiptError("Codex session index 缺少 reviewer invocation")
    index_line = matching_index_lines[-1]
    return (
        _sha256_bytes(session_bytes),
        _sha256_bytes(index_line.encode()),
        index_path,
        index_line,
    )
