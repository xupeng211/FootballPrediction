"""Least-privilege Claude Code adapter for DeepSeek reviews.

The secret is read only when launching Claude and is never returned, logged,
or represented in an artifact. Generic receipt validation remains outside this
adapter so backend claims cannot validate themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from typing import Any

BACKEND_ID = "claude-code-deepseek"
PROVIDER_ID = "deepseek"
ENDPOINT = "https://api.deepseek.com/anthropic"
EXPECTED_HOST = "api.deepseek.com"
MODEL = "deepseek-flash"
SECRET_PATH = Path(
    "/home/xupeng/.local/share/footballprediction-reviewer-secrets/anthropic_auth_token"
)


class BackendInfrastructureError(RuntimeError):
    """Never interpret runtime/provider failure as a code-review verdict."""


@dataclass(frozen=True)
class ExecutionEvidence:
    command: tuple[str, ...]
    cli_version: str
    binary_sha256: str
    settings_sha256: str
    endpoint: str
    requested_model: str
    resolved_model: str
    session_id: str


def _secret(path: Path = SECRET_PATH) -> str:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BackendInfrastructureError("AUTH_FAILURE: secret source is not a regular file")
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
        raise BackendInfrastructureError("AUTH_FAILURE: secret source permissions are unsafe")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise BackendInfrastructureError("AUTH_FAILURE: secret source is empty")
    return value


def child_environment(secret: str) -> dict[str, str]:
    """Build the only environment visible to Claude; no user-global routing."""
    return {
        "HOME": "/nonexistent",
        # PATH is needed for the Claude launcher runtime only; no arbitrary
        # provider-routing or credential variables are inherited.
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "ANTHROPIC_AUTH_TOKEN": secret,
        "ANTHROPIC_BASE_URL": ENDPOINT,
        "CLAUDE_CODE_SIMPLE": "1",
    }


def run(
    *, prompt: str, cwd: Path, settings: Path, schema: Path, secret_path: Path = SECRET_PATH
) -> tuple[bytes, dict[str, Any], ExecutionEvidence]:
    binary_text = shutil.which("claude")
    if not binary_text:
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: claude unavailable")
    binary = Path(binary_text).resolve()
    secret = _secret(secret_path)
    command = (
        str(binary),
        "--bare",
        "--print",
        "--model",
        MODEL,
        "--settings",
        str(settings),
        "--strict-mcp-config",
        "--disallowed-tools",
        "Bash,Edit,Write,WebFetch,WebSearch",
        "--output-format",
        "json",
        "--json-schema",
        schema.read_text(encoding="utf-8"),
        prompt,
    )
    with tempfile.TemporaryDirectory(prefix="fp-claude-review-home-") as isolated_home:
        child_env = child_environment(secret)
        child_env["HOME"] = isolated_home
        try:
            output = subprocess.run(
                command, cwd=cwd, env=child_env, capture_output=True, check=False, timeout=180
            )
        finally:
            secret = ""
    if output.returncode:
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE")
    try:
        event = json.loads(output.stdout)
        result = event["structured_output"]
        usage = event["modelUsage"][MODEL]
        resolved = usage["canonicalModel"]
        session = event["session_id"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise BackendInfrastructureError("INVALID_STRUCTURED_OUTPUT") from exc
    if (
        event.get("is_error") is not False
        or resolved != MODEL
        or not isinstance(session, str)
        or not session
    ):
        raise BackendInfrastructureError("MODEL_MISMATCH")
    version = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    return (
        output.stdout,
        result,
        ExecutionEvidence(
            command,
            version,
            sha256(binary.read_bytes()).hexdigest(),
            sha256(settings.read_bytes()).hexdigest(),
            ENDPOINT,
            MODEL,
            resolved,
            session,
        ),
    )
