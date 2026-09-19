#!/usr/bin/env python3
"""Canonical Codex reviewer authentication and transport isolation.

Lifecycle: permanent
Owner: engineering workflow governance

This module is deliberately the only environment constructor for the canonical
reviewer lane.  Builder Codex continues to use its ordinary shell untouched.
"""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import subprocess
from typing import TYPE_CHECKING

from scripts.devops.codex_review_contract import REVIEW_MODEL_PINNED, REVIEW_REASONING_EFFORT_PINNED
from scripts.devops.codex_review_provenance import ReviewReceiptError

if TYPE_CHECKING:
    from collections.abc import Mapping

ISOLATION_POLICY_VERSION = "canonical-codex-auth-transport-isolation/v1"
CANONICAL_CODEX_HOME = (
    Path(pwd.getpwuid(os.getuid()).pw_dir) / ".footballprediction" / "canonical-codex-reviewer"
).resolve()
CANONICAL_CODEX_BINARY = Path("/usr/lib/chatgpt/resources/codex")
# This deliberately excludes the Builder's PATH.  The runner prepends the
# directory of its already-resolved absolute Codex executable immediately
# before exec, so node-based Codex installations retain their matching runtime
# without allowing a caller-supplied PATH entry to shadow the child command.
CANONICAL_EXEC_PATH = "/usr/local/bin:/usr/bin:/bin"

# Generic proxy variables are network transport settings, not model/provider
# selection.  CA transport settings remain available when they point at a
# system-owned, non-writable trust root; a Builder-controlled CA path is never
# copied into the canonical lane.  Everything else is intentionally excluded
# by the allowlist below, so a newly introduced Builder variable cannot drift
# into the official reviewer lane by omission from a denylist.
NETWORK_TRANSPORT_VARIABLES = frozenset(
    {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    }
)
CA_TRANSPORT_VARIABLES = frozenset(
    {
        "CODEX_CA_CERTIFICATE",
        "CURL_CA_BUNDLE",
        "GIT_SSL_CAINFO",
        "NODE_EXTRA_CA_CERTS",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
    }
)
CANONICAL_FIXED_ENVIRONMENT_NAMES = frozenset(
    {"CODEX_AGENT_ROLE", "CODEX_HOME", "HOME", "NO_COLOR", "PATH"}
)
CANONICAL_ALLOWED_ENVIRONMENT_NAMES = frozenset(
    set(NETWORK_TRANSPORT_VARIABLES) | set(CA_TRANSPORT_VARIABLES)
)


def _is_safe_ca_path(value: str, *, directory: bool) -> bool:
    """Return whether one CA path is a stable, system-owned trust root."""

    try:
        path = Path(value)
        metadata = path.stat()
    except (OSError, ValueError):
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    expected_type = path.is_dir() if directory else path.is_file()
    return (
        path.is_absolute()
        and not path.is_symlink()
        and metadata.st_uid == 0
        and not mode & (stat.S_IWGRP | stat.S_IWOTH)
        and expected_type
    )


def _is_safe_ca_transport_value(name: str, value: str) -> bool:
    """Allow only stable system trust roots into the canonical environment."""

    upper = name.upper()
    if upper not in CA_TRANSPORT_VARIABLES or not value:
        return False
    directory = upper == "SSL_CERT_DIR"
    values = value.split(os.pathsep) if directory else [value]
    return all(_is_safe_ca_path(item, directory=directory) for item in values)


def canonical_reviewer_environment(
    source: Mapping[str, str] | None = None, *, codex_binary: Path | None = None
) -> dict[str, str]:
    """Build the canonical child environment without mutating ``source``."""

    original = dict(os.environ if source is None else source)
    environment = {
        name: value for name, value in original.items() if name in NETWORK_TRANSPORT_VARIABLES
    }
    environment.update(
        {
            name: value
            for name, value in original.items()
            if _is_safe_ca_transport_value(name, value)
        }
    )
    environment["CODEX_HOME"] = str(CANONICAL_CODEX_HOME)
    environment["HOME"] = str(CANONICAL_CODEX_HOME.parent.parent)
    codex_bin_dir = "" if codex_binary is None else str(codex_binary.parent)
    environment["PATH"] = (
        f"{codex_bin_dir}{os.pathsep}{CANONICAL_EXEC_PATH}"
        if codex_bin_dir
        else CANONICAL_EXEC_PATH
    )
    environment["CODEX_AGENT_ROLE"] = "independent_reviewer"
    environment["NO_COLOR"] = "1"
    return environment


def _unexpected_environment_names(environment: Mapping[str, str]) -> set[str]:
    """Return names outside the explicit canonical environment allowlist."""

    allowed = CANONICAL_FIXED_ENVIRONMENT_NAMES | CANONICAL_ALLOWED_ENVIRONMENT_NAMES
    unexpected = set(environment) - allowed
    unsafe_ca = {
        name
        for name, value in environment.items()
        if name.upper() in CA_TRANSPORT_VARIABLES and not _is_safe_ca_transport_value(name, value)
    }
    return unexpected | unsafe_ca


def _is_custom_provider_name(name: str) -> bool:
    """Return whether ``name`` can select a custom model/provider lane."""

    upper = name.upper()
    return upper.startswith(("OPENAI_", "CLIPROXY", "CLI_PROXY"))


def canonical_codex_binary() -> Path:
    """Return the fixed official Codex executable for the canonical lane.

    This intentionally does not consult Builder-controlled PATH, CODEX_CLI_PATH
    or any caller argument.  The ChatGPT desktop installation owns this
    root-owned binary; absence or replacement is a fail-closed infrastructure
    error rather than a reason to use a development CLI installation.
    """

    try:
        binary = CANONICAL_CODEX_BINARY.resolve(strict=True)
        metadata = binary.stat()
    except OSError as exc:
        raise ReviewReceiptError("canonical official Codex CLI 不可用") from exc
    if (
        not binary.is_file()
        or not os.access(binary, os.X_OK)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ReviewReceiptError("canonical official Codex CLI 不安全")
    return binary


def _assert_private_regular_file(path: Path) -> None:
    try:
        metadata = path.stat()
    except OSError as exc:
        raise ReviewReceiptError("canonical Codex authentication file 不存在") from exc
    if not path.is_file() or path.is_symlink() or metadata.st_uid != os.getuid():
        raise ReviewReceiptError("canonical Codex authentication file 不安全")
    if stat.S_IMODE(metadata.st_mode) != stat.S_IRUSR | stat.S_IWUSR:
        raise ReviewReceiptError("canonical Codex authentication file 必须为 0600")


def _assert_private_home() -> None:
    try:
        metadata = CANONICAL_CODEX_HOME.stat()
    except OSError as exc:
        raise ReviewReceiptError("canonical CODEX_HOME 不存在") from exc
    if not CANONICAL_CODEX_HOME.is_dir() or CANONICAL_CODEX_HOME.is_symlink():
        raise ReviewReceiptError("canonical CODEX_HOME 必须是普通目录")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != stat.S_IRWXU:
        raise ReviewReceiptError("canonical CODEX_HOME 必须由当前 owner 以 0700 持有")
    _assert_private_regular_file(CANONICAL_CODEX_HOME / "auth.json")


def _assert_no_custom_provider_configuration() -> None:
    """Reject a dedicated config that could choose a custom transport/provider."""

    config = CANONICAL_CODEX_HOME / "config.toml"
    if not config.exists():
        return
    if config.is_symlink() or not config.is_file():
        raise ReviewReceiptError("canonical Codex config 不安全")
    text = config.read_text(encoding="utf-8")
    forbidden = ("model_providers", "provider", "base_url", "api_base")
    for line in text.splitlines():
        key = line.split("=", 1)[0].strip().lower()
        if any(token in key for token in forbidden):
            raise ReviewReceiptError("canonical Codex config 不得定义 custom provider/base URL")


def canonical_reviewer_preflight(*, codex_binary: Path, command: list[str]) -> dict[str, object]:
    """Prove the dedicated official-auth reviewer boundary before execution."""

    _assert_private_home()
    _assert_no_custom_provider_configuration()
    environment = canonical_reviewer_environment(codex_binary=codex_binary)
    leaked_names = _unexpected_environment_names(environment)
    if leaked_names:
        raise ReviewReceiptError("Builder auth/provider routing leaked into canonical environment")
    if environment.get("CODEX_HOME") != str(CANONICAL_CODEX_HOME):
        raise ReviewReceiptError("canonical CODEX_HOME 未被强制设置")
    if "--ignore-user-config" not in command:
        raise ReviewReceiptError("canonical reviewer 缺少 --ignore-user-config")
    if "-m" not in command or "-c" not in command:
        raise ReviewReceiptError("canonical reviewer 缺少 pinned model/reasoning")
    if command[command.index("-m") + 1] != REVIEW_MODEL_PINNED or (
        f'model_reasoning_effort="{REVIEW_REASONING_EFFORT_PINNED}"' not in command
    ):
        raise ReviewReceiptError("canonical reviewer model/reasoning pin 不匹配")
    try:
        status = subprocess.run(
            [str(codex_binary), "login", "status"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewReceiptError(f"canonical authentication status 无法检查: {exc}") from exc
    # Only the mode label is inspected; no account identifier or token is kept.
    if status.returncode != 0 or "Logged in using ChatGPT" not in (
        f"{status.stdout}\n{status.stderr}"
    ):
        raise ReviewReceiptError("canonical reviewer 未建立官方 ChatGPT authentication")
    custom_provider_leaks = any(_is_custom_provider_name(name) for name in environment)
    cliproxyapi_leaks = any(
        name.upper().startswith(("CLIPROXY", "CLI_PROXY")) for name in environment
    )
    builder_auth_leaks = any(
        name.upper() in {"CODEX_ACCESS_TOKEN", "CODEX_API_KEY"} or _is_custom_provider_name(name)
        for name in environment
    )
    return {
        "policy": ISOLATION_POLICY_VERSION,
        "canonical_codex_home_external": True,
        "canonical_codex_home_owner_only": True,
        "authentication_mode": "official_chatgpt_stored_state",
        "builder_auth_override_inherited": builder_auth_leaks,
        "custom_model_provider_inherited": custom_provider_leaks,
        "cliproxyapi_routing_inherited": cliproxyapi_leaks,
        "generic_network_proxy_preserved": any(
            name in environment for name in NETWORK_TRANSPORT_VARIABLES if "PROXY" in name.upper()
        ),
        "user_codex_config_ignored": True,
        "pinned_model_active": True,
        "pinned_reasoning_active": True,
    }
