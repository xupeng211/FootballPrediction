"""Canonical Codex reviewer auth/transport boundary regression tests.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from scripts.devops import codex_reviewer_isolation as isolation
from scripts.devops.codex_review_contract import build_reviewer_command
from scripts.devops.codex_review_provenance import ReviewReceiptError


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "canonical-reviewer"
    home.mkdir(mode=0o700)
    auth = home / "auth.json"
    auth.write_text("test fixture only", encoding="utf-8")
    auth.chmod(0o600)
    return home


def _command(tmp_path: Path) -> list[str]:
    return build_reviewer_command(
        codex_binary="/test/codex",
        base_sha="1" * 40,
        output_schema=tmp_path / "schema.json",
        final_message_path=tmp_path / "final.json",
    )


def test_builder_provider_and_auth_overrides_are_scrubbed_but_network_proxy_survives(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(isolation, "CANONICAL_CODEX_HOME", home)
    source = {
        "PATH": "/builder-controlled-shadow:/usr/bin",
        "HTTP_PROXY": "http://127.0.0.1:7897",
        "HTTPS_PROXY": "http://127.0.0.1:7897",
        "ALL_PROXY": "socks5://127.0.0.1:7897",
        "CODEX_CA_CERTIFICATE": "/builder-controlled-ca.pem",
        "SSL_CERT_FILE": "/builder-controlled-cert.pem",
        "SSL_CERT_DIR": "/builder-controlled-certs",
        "OPENAI_BASE_URL": "http://builder-proxy.invalid",
        "OPENAI_API_KEY": "not-to-be-copied",
        "CODEX_API_KEY": "not-to-be-copied",
        "CODEX_ACCESS_TOKEN": "not-to-be-copied",
        "CODEX_HOME": "/arbitrary-builder-home",
        "CLIPROXYAPI_BASE_URL": "http://builder-proxy.invalid",
    }
    environment = isolation.canonical_reviewer_environment(source)
    assert environment["PATH"] == isolation.CANONICAL_EXEC_PATH
    assert "/builder-controlled-shadow" not in environment["PATH"]
    assert source["CODEX_HOME"] == "/arbitrary-builder-home"  # Builder env unchanged.
    assert environment["CODEX_HOME"] == str(home)
    assert all(
        name not in environment
        for name in source
        if name.startswith(("OPENAI_", "CLIPROXY", "CODEX_")) and name != "CODEX_HOME"
    )
    assert environment["HTTP_PROXY"] == source["HTTP_PROXY"]
    assert environment["HTTPS_PROXY"] == source["HTTPS_PROXY"]
    assert environment["ALL_PROXY"] == source["ALL_PROXY"]
    assert all(
        name not in environment
        for name in ("CODEX_CA_CERTIFICATE", "SSL_CERT_FILE", "SSL_CERT_DIR")
    )


def test_preflight_rejects_missing_or_insecure_dedicated_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(isolation, "CANONICAL_CODEX_HOME", home)
    monkeypatch.setattr(
        isolation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="Logged in using ChatGPT", stderr=""
        ),
    )
    (home / "auth.json").unlink()
    with pytest.raises(ReviewReceiptError, match="authentication file"):
        isolation.canonical_reviewer_preflight(
            codex_binary=Path("/test/codex"), command=_command(tmp_path)
        )
    (home / "auth.json").write_text("fixture", encoding="utf-8")
    (home / "auth.json").chmod(0o644)
    with pytest.raises(ReviewReceiptError, match="0600"):
        isolation.canonical_reviewer_preflight(
            codex_binary=Path("/test/codex"), command=_command(tmp_path)
        )
    (home / "auth.json").chmod(0o600)
    home.chmod(0o755)
    with pytest.raises(ReviewReceiptError, match="0700"):
        isolation.canonical_reviewer_preflight(
            codex_binary=Path("/test/codex"), command=_command(tmp_path)
        )


def test_valid_official_auth_preflight_uses_fixed_home_and_preserves_proxy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(isolation, "CANONICAL_CODEX_HOME", home)
    monkeypatch.setenv("CODEX_HOME", "/caller-cannot-substitute")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://builder-proxy.invalid")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7897")
    seen: dict[str, str] = {}

    def status(_args, **kwargs):
        seen.update(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout="Logged in using ChatGPT", stderr="")

    monkeypatch.setattr(isolation.subprocess, "run", status)
    facts = isolation.canonical_reviewer_preflight(
        codex_binary=Path("/test/codex"), command=_command(tmp_path)
    )
    assert facts["authentication_mode"] == "official_chatgpt_stored_state"
    assert facts["generic_network_proxy_preserved"] is True
    assert seen["CODEX_HOME"] == str(home)
    assert "OPENAI_BASE_URL" not in seen
    assert "--ignore-user-config" in _command(tmp_path)


def test_preflight_rejects_non_chatgpt_auth_or_custom_provider_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(isolation, "CANONICAL_CODEX_HOME", home)
    monkeypatch.setattr(
        isolation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="Logged in using API key", stderr=""
        ),
    )
    with pytest.raises(ReviewReceiptError, match="官方 ChatGPT"):
        isolation.canonical_reviewer_preflight(
            codex_binary=Path("/test/codex"), command=_command(tmp_path)
        )
    (home / "config.toml").write_text("model_providers = {}\n", encoding="utf-8")
    with pytest.raises(ReviewReceiptError, match="custom provider"):
        isolation.canonical_reviewer_preflight(
            codex_binary=Path("/test/codex"), command=_command(tmp_path)
        )


def test_fixed_canonical_binary_rejects_group_writable_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RootOwnedGroupWritableBinary:
        def resolve(self, *, strict: bool) -> _RootOwnedGroupWritableBinary:
            assert strict is True
            return self

        def stat(self) -> SimpleNamespace:
            return SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o775)

        def is_file(self) -> bool:
            return True

        def __fspath__(self) -> str:
            return "/usr/bin/true"

    monkeypatch.setattr(isolation, "CANONICAL_CODEX_BINARY", _RootOwnedGroupWritableBinary())
    with pytest.raises(ReviewReceiptError, match="不安全"):
        isolation.canonical_codex_binary()
