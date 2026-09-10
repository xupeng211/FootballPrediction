#!/usr/bin/env python3
"""Codex CLI helpers for the engineering-independent review workflow.

lifecycle: permanent
owner: engineering workflow governance

The project assurance tier is intentionally based on fresh process/context
separation and exact-head review. This module therefore resolves the Codex
CLI used by the reviewer without making ownership or filesystem immutability a
cryptographic trust claim. Local evidence hashes are integrity checks only.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil


class ReviewReceiptError(ValueError):
    """Raised when independent-review execution evidence is incomplete."""


def resolve_codex_binary(value: str) -> Path:
    """Resolve the installed Codex CLI used for a fresh reviewer invocation.

    The selected assurance model permits the user's existing authenticated
    local Codex installation. We still require a regular executable and record
    its content hash in the receipt for audit/integrity comparison. That hash
    does not attest to reviewer identity or resist a same-UID actor.
    """

    if value != "codex":
        raise ReviewReceiptError("reviewer executable 只允许使用 PATH 中的 codex CLI")
    candidates: list[Path] = []
    configured = os.environ.get("CODEX_CLI_PATH")
    if configured:
        candidates.append(Path(configured))
    resolved = shutil.which("codex")
    if resolved:
        candidates.append(Path(resolved))
    # Keep the system installation as a useful fallback when PATH is minimal.
    candidates.append(Path("/usr/lib/chatgpt/resources/codex"))
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            executable = candidate.resolve(strict=True)
        except OSError:
            continue
        if executable in seen:
            continue
        seen.add(executable)
        if executable.is_file() and os.access(executable, os.X_OK):
            return executable
    raise ReviewReceiptError("没有找到可执行的 Codex CLI")
