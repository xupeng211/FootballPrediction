"""Least-privilege Claude Code adapter for DeepSeek reviews.

The secret is read only when launching Claude and is never returned, logged,
or represented in an artifact. Generic receipt validation remains outside this
adapter so backend claims cannot validate themselves.

Lifecycle: permanent
Owner: engineering workflow governance
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
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
MIN_CLAUDE_VERSION = (2, 1, 276)
SECRET_PATH = Path(
    "/home/xupeng/.local/share/footballprediction-reviewer-secrets/anthropic_auth_token"
)
SECRET_FILE_MODE = 0o600
# Kept as bytes owned by this adapter instead of accepting mutable user or
# project Claude settings.  The temporary file is hashed into provenance.
DEDICATED_SETTINGS = (
    b'{"permissions":{"allow":[],"deny":["Bash","Edit","Write","WebFetch","WebSearch"]}}\n'
)
# Claude Code 2.1.276 accepts this conservative subset of the generic result
# schema.  ``validate_result`` remains the protocol authority after execution;
# it accepts this strict subset without relaxing any generic rule.
CLAUDE_RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["protocol_version", "review_result", "findings"],
    "properties": {
        "protocol_version": {"const": "INDEPENDENT_REVIEW_PROTOCOL_V1"},
        "review_result": {"enum": ["PASS", "FAIL"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "title", "evidence"],
                "properties": {
                    "severity": {"enum": ["P0", "P1", "P2", "P3"]},
                    "title": {"type": "string", "minLength": 1},
                    "evidence": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}


class BackendInfrastructureError(RuntimeError):
    """Never interpret runtime/provider failure as a code-review verdict."""


def _version_at_least(version: str) -> bool:
    """Require the reviewed Claude feature baseline without trusting defaults."""
    matched = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
    return bool(matched and tuple(map(int, matched.groups())) >= MIN_CLAUDE_VERSION)


@dataclass(frozen=True)
class ExecutionEvidence:
    """Non-secret harness observations for a single Claude subprocess."""

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
    if stat.S_IMODE(info.st_mode) != SECRET_FILE_MODE or info.st_uid != os.getuid():
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
    *, prompt: str, cwd: Path, secret_path: Path = SECRET_PATH
) -> tuple[bytes, dict[str, Any], ExecutionEvidence]:
    """Run one isolated, schema-bound Claude/DeepSeek turn.

    The credential exists only in the child environment.  This function never
    returns stderr or that environment, so callers cannot accidentally persist
    either as review evidence.
    """
    binary_text = shutil.which("claude")
    if not binary_text:
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: claude unavailable")
    binary = Path(binary_text).resolve()
    version = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if not _version_at_least(version):
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: unsupported Claude version")
    secret = _secret(secret_path)
    if not cwd.is_dir():
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: isolated review inputs unavailable")
    schema_bytes = json.dumps(CLAUDE_RESULT_SCHEMA, separators=(",", ":")).encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="fp-claude-review-home-") as isolated_home:
        runtime = Path(isolated_home)
        settings = runtime / "settings.json"
        settings.write_bytes(DEDICATED_SETTINGS)
        child_env = child_environment(secret)
        child_env["HOME"] = isolated_home
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
            schema_bytes.decode("utf-8"),
            prompt,
        )
        try:
            output = subprocess.run(
                command, cwd=cwd, env=child_env, capture_output=True, check=False, timeout=180
            )
        finally:
            secret = ""
    if output.returncode:
        raise BackendInfrastructureError(f"CLI_RUNTIME_FAILURE: exit={output.returncode}")
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
    return (
        output.stdout,
        result,
        ExecutionEvidence(
            command,
            version,
            sha256(binary.read_bytes()).hexdigest(),
            sha256(DEDICATED_SETTINGS).hexdigest(),
            ENDPOINT,
            MODEL,
            resolved,
            session,
        ),
    )
