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
import time
from typing import Any

from scripts.devops.deepseek_review_chunks import MAX_CHUNK_PROMPT_BYTES
from scripts.devops.independent_review_backends.deepseek_transport import (
    SingleRequestTransport,
    TransportError,
)

BACKEND_ID = "claude-code-deepseek"
PROVIDER_ID = "deepseek"
ENDPOINT = "https://api.deepseek.com/anthropic"
EXPECTED_HOST = "api.deepseek.com"
MODEL = "deepseek-flash"
MIN_CLAUDE_VERSION = (2, 1, 276)
DEFAULT_REVIEW_TIMEOUT_SECONDS = 900
MIN_REVIEW_TIMEOUT_SECONDS = 30
MAX_REVIEW_TIMEOUT_SECONDS = 900
SECRET_PATH = Path(
    "/home/xupeng/.local/share/footballprediction-reviewer-secrets/anthropic_auth_token"
)
SECRET_FILE_MODE = 0o600
# ``claude`` is resolved from PATH only as a candidate.  Before any provider
# credential is read, the candidate must resolve inside this installation root
# and match the approved launcher digest.  This prevents a same-name PATH
# shim from receiving the secret while preserving the existing no-fallback
# behaviour when the controlled installation is unavailable or changed.
TRUSTED_CLAUDE_BINARY_ROOTS = (Path("/home/xupeng/.nvm/versions/node/v22.23.2"),)
TRUSTED_CLAUDE_BINARY_SHA256 = frozenset(
    {"5c4735937844e84f8a93306e841a5b0e12252909b07870f789b190468da147ab"}
)
# Never inherit the caller's PATH after credentials are injected.  The Claude
# launcher is approved above; its child may resolve only this fixed installation
# directory and root-owned system command directories.
CONTROLLED_CLAUDE_PATH = "/home/xupeng/.nvm/versions/node/v22.23.2/bin:/usr/bin:/bin"
# Kept as bytes owned by this adapter instead of accepting mutable user or
# project Claude settings.  The temporary file is hashed into provenance.
MAX_REVIEW_OUTPUT_TOKENS = 16384
MAX_REVIEW_CONTEXT_TOKENS = 64000
REVIEW_BUDGET_ENV = {
    "CLAUDE_CODE_MAX_RETRIES": "0",
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
    "CLAUDE_CODE_NO_MODEL_FALLBACK": "1",
    "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_AUTO_COMPACT": "1",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(MAX_REVIEW_OUTPUT_TOKENS),
    "CLAUDE_CODE_MAX_CONTEXT_TOKENS": str(MAX_REVIEW_CONTEXT_TOKENS),
}
DEDICATED_SETTINGS = (
    json.dumps(
        {
            "env": REVIEW_BUDGET_ENV,
            "permissions": {
                "allow": [],
                "deny": ["Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch"],
            },
        },
        separators=(",", ":"),
    ).encode()
    + b"\n"
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


_SAFE_NONZERO_CLASSES = (
    (b"rate limit", "RATE_LIMIT"),
    (b"usage limit", "USAGE_LIMIT"),
    (b"request too large", "REQUEST_TOO_LARGE"),
    (b"payload too large", "REQUEST_TOO_LARGE"),
    (b"context length", "CONTEXT_LIMIT"),
    (b"context window", "CONTEXT_LIMIT"),
    (b"invalid model", "INVALID_MODEL"),
    (b"unsupported parameter", "UNSUPPORTED_PARAMETER"),
    (b"json schema", "INVALID_SCHEMA"),
    (b"structured output", "STRUCTURED_OUTPUT_ERROR"),
    (b"authentication", "AUTH_ERROR"),
    (b"unauthorized", "AUTH_ERROR"),
    (b"tls", "TLS_FAILURE"),
    (b"network", "NETWORK_FAILURE"),
    (b"status 5", "PROVIDER_5XX"),
    (b"http 5", "PROVIDER_5XX"),
)


def _output_contains_secret(output: subprocess.CompletedProcess[bytes], secret: str) -> bool:
    """Reject direct credential reflection before any provider output persists."""
    marker = secret.encode("utf-8")
    return any(
        isinstance(value, bytes) and marker in value
        for value in (getattr(output, "stdout", None), getattr(output, "stderr", None))
    )


def _safe_nonzero_detail(output: subprocess.CompletedProcess[bytes], elapsed_seconds: int) -> str:
    """Classify only allowlisted provider markers; never surface raw output."""

    observed = b" ".join(
        value
        for value in (getattr(output, "stdout", b""), getattr(output, "stderr", b""))
        if isinstance(value, bytes)
    ).lower()
    category = next(
        (label for marker, label in _SAFE_NONZERO_CLASSES if marker in observed),
        "UNKNOWN_NONZERO_EXIT",
    )
    return (
        f"{category}: exit={output.returncode}; stdout_bytes={len(getattr(output, 'stdout', b'') or b'')}; "
        f"stderr_bytes={len(getattr(output, 'stderr', b'') or b'')}; elapsed_seconds={elapsed_seconds}"
    )


def _version_at_least(version: str) -> bool:
    """Require the reviewed Claude feature baseline without trusting defaults."""
    matched = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
    return bool(matched and tuple(map(int, matched.groups())) >= MIN_CLAUDE_VERSION)


def _validated_timeout(timeout_seconds: int) -> int:
    """Accept only the finite, backend-owned review timeout range."""
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or not MIN_REVIEW_TIMEOUT_SECONDS <= timeout_seconds <= MAX_REVIEW_TIMEOUT_SECONDS
    ):
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: invalid review timeout")
    return timeout_seconds


def _approved_claude_binary(binary_text: str) -> tuple[Path, str]:
    """Resolve and authenticate the Claude launcher before secret injection."""

    if not isinstance(binary_text, str) or not binary_text:
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: claude unavailable")
    candidate = Path(binary_text)
    try:
        binary = candidate.resolve(strict=True)
    except OSError as exc:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: Claude launcher cannot be resolved"
        ) from exc
    if not binary.is_file():
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: Claude launcher is not a file")
    try:
        trusted_roots = tuple(root.resolve(strict=True) for root in TRUSTED_CLAUDE_BINARY_ROOTS)
    except OSError as exc:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: trusted Claude launcher root cannot be resolved"
        ) from exc
    if not any(binary == root or root in binary.parents for root in trusted_roots):
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: Claude launcher is untrusted")
    try:
        info = binary.stat()
    except OSError as exc:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: Claude launcher metadata unavailable"
        ) from exc
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: Claude launcher permissions are unsafe"
        )
    try:
        digest = sha256(binary.read_bytes()).hexdigest()
    except OSError as exc:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: Claude launcher bytes unavailable"
        ) from exc
    if digest not in TRUSTED_CLAUDE_BINARY_SHA256:
        raise BackendInfrastructureError(
            "CLI_RUNTIME_FAILURE: Claude launcher identity is unapproved"
        )
    return binary, digest


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
    transport: dict[str, Any]
    transport_log: bytes


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


def child_environment(secret: str, *, endpoint: str) -> dict[str, str]:
    """Build the only environment visible to Claude; no user-global routing."""
    return {
        "HOME": "/nonexistent",
        # PATH is needed for the Claude launcher runtime only; no arbitrary
        # provider-routing or credential variables are inherited.
        "PATH": CONTROLLED_CLAUDE_PATH,
        "LANG": "C.UTF-8",
        # Claude Code 2.1.276 documents ANTHROPIC_API_KEY as the only
        # credential accepted by --bare.  Keep the Owner's token contract as
        # well because the DeepSeek Anthropic-compatible endpoint expects it;
        # both names exist only in this allowlisted child environment.
        "ANTHROPIC_API_KEY": secret,
        "ANTHROPIC_AUTH_TOKEN": secret,
        "ANTHROPIC_BASE_URL": endpoint,
        "CLAUDE_CODE_SIMPLE": "1",
        **REVIEW_BUDGET_ENV,
    }


def run(  # noqa: C901, PLR0912, PLR0915
    *,
    prompt: str,
    cwd: Path,
    secret_path: Path = SECRET_PATH,
    timeout_seconds: int = DEFAULT_REVIEW_TIMEOUT_SECONDS,
    attempt_path: Path,
) -> tuple[bytes, dict[str, Any], ExecutionEvidence]:
    """Run one isolated, schema-bound Claude/DeepSeek turn.

    The provider credential exists only in the bounded transport process.  This function never
    returns stderr or that environment, so callers cannot accidentally persist
    either as review evidence.
    """
    if len(prompt.encode("utf-8")) > MAX_CHUNK_PROMPT_BYTES:
        raise BackendInfrastructureError("PROMPT_BUDGET_EXCEEDED: no provider attempt")
    timeout = _validated_timeout(timeout_seconds)
    deadline = time.monotonic() + timeout
    binary_text = shutil.which("claude")
    binary, binary_sha256 = _approved_claude_binary(binary_text or "")
    try:
        version = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, check=False, timeout=10
        ).stdout.strip()
    except subprocess.TimeoutExpired as exc:
        raise BackendInfrastructureError("CLI_RUNTIME_TIMEOUT: version probe timed out") from exc
    if not _version_at_least(version):
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: unsupported Claude version")
    secret = _secret(secret_path)
    if not cwd.is_dir():
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: isolated review inputs unavailable")
    schema_bytes = json.dumps(CLAUDE_RESULT_SCHEMA, separators=(",", ":")).encode("utf-8")
    remaining = int(deadline - time.monotonic())
    if remaining <= 0:
        raise BackendInfrastructureError("CLI_RUNTIME_TIMEOUT: startup budget exhausted")
    with (
        SingleRequestTransport(
            secret=secret, prompt=prompt, timeout=remaining, attempt_path=attempt_path
        ) as transport,
        tempfile.TemporaryDirectory(prefix="fp-claude-review-home-") as isolated_home,
    ):
        runtime = Path(isolated_home)
        settings = runtime / "settings.json"
        settings.write_bytes(DEDICATED_SETTINGS)
        child_env = child_environment(transport.cli_token, endpoint=transport.cli_endpoint)
        child_env["HOME"] = isolated_home
        command = (
            str(binary),
            "--bare",
            "--restricted",
            "--print",
            "--max-turns",
            "1",
            "--model",
            MODEL,
            "--settings",
            str(settings),
            "--strict-mcp-config",
            "--tools",
            "",
            "--disallowed-tools",
            "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch",
            "--output-format",
            "json",
            "--json-schema",
            schema_bytes.decode("utf-8"),
            prompt,
        )
        started = time.monotonic()
        try:
            output = subprocess.run(
                command,
                cwd=cwd,
                env=child_env,
                capture_output=True,
                check=False,
                timeout=max(0.1, deadline - time.monotonic()),
            )
        except subprocess.TimeoutExpired as exc:
            # subprocess.run kills and reaps its direct child before raising.
            # Never expose captured stdout/stderr: either may contain model text.
            raise BackendInfrastructureError("CLI_RUNTIME_TIMEOUT: no review verdict") from exc
        else:
            if _output_contains_secret(output, secret):
                raise BackendInfrastructureError("SECRET_LEAKAGE_DETECTED")
        finally:
            child_env.clear()
            secret = ""
        try:
            transport_evidence = transport.evidence()
            transport_log = attempt_path.read_bytes()
        except TransportError as exc:
            raise BackendInfrastructureError("TRANSPORT_BOUND_FAILURE: no review verdict") from exc
    if output.returncode:
        raise BackendInfrastructureError(
            f"CLI_RUNTIME_FAILURE: {_safe_nonzero_detail(output, int(time.monotonic() - started))}"
        )
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
            binary_sha256,
            sha256(DEDICATED_SETTINGS).hexdigest(),
            ENDPOINT,
            MODEL,
            resolved,
            session,
            transport_evidence,
            transport_log,
        ),
    )
