"""Least-privilege Claude Code adapter for DeepSeek reviews.

The secret is read only when launching Claude and is never returned, logged,
or represented in an artifact. Generic receipt validation remains outside this
adapter so backend claims cannot validate themselves.

Lifecycle: permanent
Owner: engineering workflow governance
"""

from __future__ import annotations

import base64
from contextlib import nullcontext, suppress
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

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
DEDICATED_SETTINGS = b'{"permissions":{"allow":[],"deny":["Bash","Edit","Write","Read","Glob","Grep","WebFetch","WebSearch"]}}\n'
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
_OUTPUT_TOKEN_LIMIT_MESSAGE = re.compile(
    r"(?:API Error: )?Claude's response exceeded the [1-9][0-9]* output token maximum\. "
    r"To configure this behavior, set the CLAUDE_CODE_MAX_OUTPUT_TOKENS environment variable\."
)
_CLIENT_EFFORT_LEVELS = frozenset({"low", "medium", "high", "xhigh", "max"})
_SESSION_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_MAX_EFFORT_TRACE_BYTES = 8 * 1024 * 1024
_MAX_EFFORT_TRACE_LINES = 4096
_PRIVATE_FILE_MODE = 0o600


def _output_contains_secret(output: subprocess.CompletedProcess[bytes], secret: str) -> bool:
    """Reject direct credential reflection before any provider output persists."""
    marker = secret.encode("utf-8")
    return any(
        isinstance(value, bytes) and marker in value
        for value in (getattr(output, "stdout", None), getattr(output, "stderr", None))
    )


def _json_record(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


def _client_reported_output_limit(stdout: bytes) -> bool:
    event = _json_record(stdout)
    if event.get("type") != "result" or event.get("is_error") is not True:
        return False
    if event.get("subtype") == "error_during_execution":
        errors = event.get("errors")
    elif event.get("subtype") == "success":
        errors = [event.get("result")]
    else:
        return False
    return isinstance(errors, list) and any(
        isinstance(error, str) and _OUTPUT_TOKEN_LIMIT_MESSAGE.fullmatch(error) for error in errors
    )


def _safe_nonzero_detail(output: subprocess.CompletedProcess[bytes], elapsed_seconds: int) -> str:
    """Classify only allowlisted provider markers; never surface raw output."""

    observed = b" ".join(
        value
        for value in (getattr(output, "stdout", b""), getattr(output, "stderr", b""))
        if isinstance(value, bytes)
    ).lower()
    category = (
        "OUTPUT_TOKEN_LIMIT"
        if _client_reported_output_limit(getattr(output, "stdout", b""))
        else next(
            (label for marker, label in _SAFE_NONZERO_CLASSES if marker in observed),
            "UNKNOWN_NONZERO_EXIT",
        )
    )
    return (
        f"{category}: exit={output.returncode}; stdout_bytes={len(getattr(output, 'stdout', b'') or b'')}; "
        f"stderr_bytes={len(getattr(output, 'stderr', b'') or b'')}; elapsed_seconds={elapsed_seconds}"
    )


def _read_private_trace(path: Path) -> bytes:
    if path.resolve(strict=True) != path:
        raise ValueError("trace must be a direct file in the isolated home")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != _PRIVATE_FILE_MODE
            or info.st_nlink != 1
            or not 0 < info.st_size <= _MAX_EFFORT_TRACE_BYTES
        ):
            raise ValueError("trace is not a private bounded file")
        raw = stream.read(info.st_size + 1)
        if len(raw) != info.st_size or os.fstat(stream.fileno()).st_mtime_ns != info.st_mtime_ns:
            raise ValueError("trace changed during observation")
        if raw.count(b"\n") >= _MAX_EFFORT_TRACE_LINES:
            raise ValueError("trace has too many records")
        return raw


def _observed_trace_row(row: dict[str, Any], session: str, cwd: str) -> bool:
    return row.get("sessionId") == session and row.get("cwd") == cwd


def _trace_effort_levels(
    rows: list[dict[str, Any]], session: str, directory: str, *, strict: bool = False
) -> set[str]:
    efforts = set()
    for row in rows:
        if (
            strict
            and row.get("type") == "assistant"
            and (
                not isinstance(row.get("isApiErrorMessage", False), bool)
                or (
                    row.get("perTurnEffort") is not None
                    and row.get("effort") is not None
                    and row["perTurnEffort"] != row["effort"]
                )
            )
        ):
            raise ValueError("conflicting client turn metadata")
        if row.get("type") != "assistant" or row.get("isApiErrorMessage"):
            continue
        message = row.get("message")
        if isinstance(message, dict) and message.get("model") == "<synthetic>":
            continue
        value = row.get("perTurnEffort")
        if value is None:
            value = row.get("effort")
        if (
            not _observed_trace_row(row, session, directory)
            or not isinstance(message, dict)
            or message.get("model") != MODEL
            or not isinstance(value, str)
            or value not in _CLIENT_EFFORT_LEVELS
        ):
            raise ValueError("client turn lacks bound effort metadata")
        efforts.add(value)
    return efforts


def _observe_client_effort(
    home: Path, prompt: str, cwd: Path, reported_session: object, *, strict: bool = False
) -> dict[str, Any]:
    projects = home / ".claude" / "projects"
    if projects.resolve(strict=True) != projects:
        raise ValueError("trace directory changed")
    traces = projects.glob("*/*.jsonl")
    trace = next(traces, None)
    if trace is None or next(traces, None) is not None or not _SESSION_ID.fullmatch(trace.stem):
        raise ValueError("unique client session trace required")
    session = trace.stem
    if reported_session is not None and reported_session != session:
        raise ValueError("trace does not match the CLI session")
    raw = _read_private_trace(trace)
    rows = [_json_record(line) for line in raw.splitlines()]
    if not all(rows):
        raise ValueError("incomplete client trace")
    directory = str(cwd)
    first_user = next(row for row in rows if row.get("type") == "user" and not row.get("isMeta"))
    if (
        not _observed_trace_row(first_user, session, directory)
        or not isinstance(first_user.get("message"), dict)
        or first_user["message"].get("content") != prompt
    ):
        raise ValueError("trace does not match the submitted prompt")
    if strict and any(row.get("type") == "assistant" for row in rows[: rows.index(first_user)]):
        raise ValueError("client response precedes submitted prompt")
    efforts = _trace_effort_levels(rows, session, directory, strict=strict)
    return {
        "observed_client_effort": next(iter(efforts))
        if len(efforts) == 1
        else ("MIXED" if efforts else "UNKNOWN"),
        "session_id": session,
        "trace_sha256": sha256(raw).hexdigest(),
    }


def _record_client_effort(
    home: Path | None, *, prompt: str, cwd: Path, stdout: bytes = b""
) -> None:
    if home is None:
        return
    observation: dict[str, Any] = {"observed_client_effort": "UNKNOWN"}
    with suppress(OSError, RuntimeError, ValueError, StopIteration):
        observation = _observe_client_effort(
            home, prompt, cwd, _json_record(stdout).get("session_id")
        )
    observation.update(
        schema="claude-client-effort-observation/v1",
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
    )
    # This optional record is private diagnostics. It cannot affect the receipt or verdict.
    with (
        suppress(OSError),
        os.fdopen(
            os.open(
                home / "client-effort.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                _PRIVATE_FILE_MODE,
            ),
            "w",
        ) as stream,
    ):
        json.dump(observation, stream, sort_keys=True)
        stream.write("\n")


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
        "PATH": CONTROLLED_CLAUDE_PATH,
        "LANG": "C.UTF-8",
        # Claude Code 2.1.276 documents ANTHROPIC_API_KEY as the only
        # credential accepted by --bare.  Keep the Owner's token contract as
        # well because the DeepSeek Anthropic-compatible endpoint expects it;
        # both names exist only in this allowlisted child environment.
        "ANTHROPIC_API_KEY": secret,
        "ANTHROPIC_AUTH_TOKEN": secret,
        "ANTHROPIC_BASE_URL": ENDPOINT,
        "CLAUDE_CODE_SIMPLE": "1",
    }


def reviewer_command(binary: Path, settings: Path, prompt: str) -> tuple[str, ...]:
    """构建正式审核的完整固定命令，独立消费者也按此核对。"""
    schema_bytes = json.dumps(CLAUDE_RESULT_SCHEMA, separators=(",", ":")).encode("utf-8")
    return (
        str(binary),
        "--bare",
        "--restricted",
        "--print",
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


def _write_settings(settings: Path, *, private: bool) -> None:
    if not private:
        settings.write_bytes(DEDICATED_SETTINGS)
        return
    with os.fdopen(os.open(settings, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
        stream.write(DEDICATED_SETTINGS)


def _review_secret(path: Path, supervised_chunk) -> str:
    if supervised_chunk is not None:
        from scripts.devops.deepseek_low_effort import verified_capture  # noqa: PLC0415

        pilot, _ = supervised_chunk
        verified_capture(pilot, pilot.target()["base"])
    return _secret(path)


def run(
    *,
    prompt: str,
    cwd: Path,
    secret_path: Path = SECRET_PATH,
    timeout_seconds: int = DEFAULT_REVIEW_TIMEOUT_SECONDS,
    retain_home_parent: Path | None = None,
    supervised_chunk=None,
) -> tuple[bytes, dict[str, Any], ExecutionEvidence]:
    """Run one isolated, schema-bound Claude/DeepSeek turn.

    The credential exists only in the child environment.  This function never
    returns stderr or that environment, so callers cannot accidentally persist
    either as review evidence.
    """
    timeout = _validated_timeout(timeout_seconds)
    binary_text = shutil.which("claude")
    binary, binary_sha256 = _approved_claude_binary(binary_text or "")
    version = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if not _version_at_least(version):
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: unsupported Claude version")
    secret = _review_secret(secret_path, supervised_chunk)
    if not cwd.is_dir():
        raise BackendInfrastructureError("CLI_RUNTIME_FAILURE: isolated review inputs unavailable")
    # The retained Controller mode owns this private home until the entire
    # review tree is confirmed stopped; it may contain untrusted runtime data.
    home_context = (
        nullcontext(tempfile.mkdtemp(prefix="fp-claude-review-home-", dir=retain_home_parent))
        if retain_home_parent is not None
        else tempfile.TemporaryDirectory(prefix="fp-claude-review-home-")
    )
    with home_context as isolated_home:
        runtime = Path(isolated_home)
        diagnostics_home = runtime if retain_home_parent is not None else None
        settings = runtime / "settings.json"
        _write_settings(settings, private=supervised_chunk is not None)
        child_env = child_environment(secret)
        child_env["HOME"] = isolated_home
        command = reviewer_command(binary, settings, prompt)
        started = time.monotonic()
        try:
            if supervised_chunk is None:
                output = subprocess.run(
                    command,
                    cwd=cwd,
                    env=child_env,
                    capture_output=True,
                    check=False,
                    timeout=timeout,
                )
            else:
                pilot, index = supervised_chunk
                output = pilot.run_client(index, command, cwd, child_env, timeout)
        except subprocess.TimeoutExpired as exc:
            # subprocess.run kills and reaps its direct child before raising.
            # Never expose captured stdout/stderr: either may contain model text.
            _record_client_effort(diagnostics_home, prompt=prompt, cwd=cwd)
            raise BackendInfrastructureError("CLI_RUNTIME_TIMEOUT: no review verdict") from exc
        else:
            if _output_contains_secret(output, secret):
                raise BackendInfrastructureError("SECRET_LEAKAGE_DETECTED")
            _record_client_effort(diagnostics_home, prompt=prompt, cwd=cwd, stdout=output.stdout)
        finally:
            child_env.clear()
            secret = ""
    if output.returncode or _client_reported_output_limit(output.stdout):
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
        ),
    )


def _capture_supervised_client(command: list[str], binary_sha: str) -> None:
    """在受监管进程内先过滤凭据，再向私有 transcript 输出原始响应及有限观测。"""
    token = os.environ["ANTHROPIC_API_KEY"]
    if (
        not token
        or token != os.environ["ANTHROPIC_AUTH_TOKEN"]
        or os.environ["ANTHROPIC_BASE_URL"] != ENDPOINT
    ):
        raise ValueError("invalid supervised client environment")
    binary = Path(command[0])
    home = Path(os.environ["HOME"])
    settings = home / "settings.json"
    if (
        binary.resolve(strict=True) != binary
        or sha256(binary.read_bytes()).hexdigest() != binary_sha
        or command != list(reviewer_command(binary, settings, command[-1]))
        or home.resolve(strict=True) != home
        or settings.resolve(strict=True) != settings
        or settings.read_bytes() != DEDICATED_SETTINGS
    ):
        raise ValueError("supervised client inputs changed")
    # 启动器已在注入凭据前验证。此子进程仅使用隔离环境，不读取磁盘凭据。
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
        proc = Path("/proc") / str(child.pid)
        fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        cwd = str((proc / "cwd").readlink())
        # 只导出该子进程实际环境中的一个无敏感策略键。
        environ = (proc / "environ").read_bytes().split(b"\0")
        if b"ANTHROPIC_BASE_URL=" + ENDPOINT.encode() not in environ:
            raise ValueError("client environment unavailable")
        effort = [
            item.split(b"=", 1)[1].decode()
            for item in environ
            if item.startswith(b"CLAUDE_CODE_EFFORT_LEVEL=")
        ]
        if effort not in ([], ["low"]) or int(fields[1]) != os.getpid():
            raise ValueError("client identity mismatch")
        stdout, stderr = child.communicate()
        completed = subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
    if _output_contains_secret(completed, token):
        raise ValueError("client credential reflection")
    result = {
        "pid": child.pid,
        "parent_pid": os.getpid(),
        "parent_starttime": int(Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19]),
        "starttime": int(fields[19]),
        "cwd": cwd,
        "effort_request": effort,
        "returncode": completed.returncode,
        "stdout": base64.b64encode(stdout).decode() if completed.returncode == 0 else "",
        "error_class": _safe_nonzero_detail(completed, 0) if completed.returncode else "",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    if sys.argv[1:2] != ["--capture-supervised"]:
        sys.exit("unsupported invocation")
    try:
        _capture_supervised_client(sys.argv[3:], sys.argv[2])
    except Exception:
        # stderr 由监护器保留，不输出原始异常、环境或客户端内容。
        sys.exit("supervised client evidence unavailable")
