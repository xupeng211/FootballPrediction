from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops.independent_review_backends import claude_code_deepseek as backend
from tests.unit.test_deepseek_transport import synthetic_transport_evidence


def _approve_test_binary(monkeypatch, binary: Path) -> None:
    """Keep backend tests explicit about the launcher identity they approve."""

    binary.chmod(0o755)
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (binary.parent,))
    monkeypatch.setattr(
        backend,
        "TRUSTED_CLAUDE_BINARY_SHA256",
        frozenset({sha256(binary.read_bytes()).hexdigest()}),
    )


def test_child_environment_is_allowlisted_and_has_no_competing_route():
    env = backend.child_environment("local-token", endpoint="http://127.0.0.1:1234/anthropic")
    assert env["PATH"] == backend.CONTROLLED_CLAUDE_PATH
    assert env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:1234/anthropic"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "local-token"
    assert env["ANTHROPIC_API_KEY"] == "local-token"
    assert "HTTPS_PROXY" not in env


def test_secret_source_rejects_symlink_and_unsafe_permissions(tmp_path: Path):
    target = tmp_path / "target"
    target.write_text("synthetic", encoding="utf-8")
    target.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(backend.BackendInfrastructureError):
        backend._secret(link)
    target.chmod(0o644)
    with pytest.raises(backend.BackendInfrastructureError):
        backend._secret(target)


def test_synthetic_secret_is_not_exported_to_parent():
    assert "synthetic-secret" not in os.environ.values()


def test_run_injects_synthetic_secret_only_into_claude_child(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(stdout="2.1.276 (Claude Code)\n")
        observed.update(kwargs)
        observed["env"] = dict(kwargs["env"])
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b'{"is_error":false,"session_id":"fresh-session","structured_output":'
                b'{"protocol_version":"INDEPENDENT_REVIEW_PROTOCOL_V1",'
                b'"review_result":"PASS","findings":[]},"modelUsage":'
                b'{"deepseek-flash":{"canonicalModel":"deepseek-flash"}}}'
            ),
        )

    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    raw, result, evidence = backend.run(
        prompt="review", cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl"
    )
    child_env = observed["env"]
    assert isinstance(child_env, dict)
    assert child_env["ANTHROPIC_AUTH_TOKEN"] == "local-token"
    assert child_env["ANTHROPIC_API_KEY"] == "local-token"
    assert child_env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:1234/anthropic"
    assert "HTTPS_PROXY" not in child_env
    assert "synthetic-secret" not in os.environ.values()
    assert "synthetic-secret" not in evidence.command
    assert b"synthetic-secret" not in raw
    assert result["review_result"] == "PASS"


def test_run_uses_explicit_bounded_timeout(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (Claude Code)\n")
        observed.update(kwargs)
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b'{"is_error":false,"session_id":"fresh-session","structured_output":'
                b'{"protocol_version":"INDEPENDENT_REVIEW_PROTOCOL_V1",'
                b'"review_result":"PASS","findings":[]},"modelUsage":'
                b'{"deepseek-flash":{"canonicalModel":"deepseek-flash"}}}'
            ),
        )

    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    backend.run(
        prompt="review",
        cwd=tmp_path,
        timeout_seconds=backend.MAX_REVIEW_TIMEOUT_SECONDS,
        attempt_path=tmp_path / "attempt.jsonl",
    )
    assert 0 < observed["timeout"] <= backend.MAX_REVIEW_TIMEOUT_SECONDS


def test_timeout_is_no_verdict_and_does_not_leak_secret_or_prompt(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")

    def fake_run(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (Claude Code)\n")
        raise backend.subprocess.TimeoutExpired(command, 30, output=b"synthetic-secret")

    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    with pytest.raises(backend.BackendInfrastructureError) as raised:
        backend.run(
            prompt="private prompt",
            cwd=tmp_path,
            timeout_seconds=30,
            attempt_path=tmp_path / "attempt.jsonl",
        )
    assert str(raised.value) == "CLI_RUNTIME_TIMEOUT: no review verdict"
    assert "synthetic-secret" not in str(raised.value)
    assert "private prompt" not in str(raised.value)


def test_run_rejects_secret_reflection_before_raw_output_can_persist(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")

    def fake_run(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (Claude Code)\n")
        return SimpleNamespace(returncode=0, stdout=b"synthetic-secret", stderr=b"")

    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    with pytest.raises(backend.BackendInfrastructureError, match="SECRET_LEAKAGE_DETECTED"):
        backend.run(prompt="review", cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl")


@pytest.mark.parametrize("timeout", [True, 29, 901, "900"])
def test_run_rejects_invalid_timeout_before_cli_execution(timeout):
    with pytest.raises(backend.BackendInfrastructureError, match="invalid review timeout"):
        backend._validated_timeout(timeout)


def test_run_rejects_malformed_provider_output_as_infrastructure(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")
    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")

    def fake_run(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (Claude Code)\n")
        return SimpleNamespace(returncode=0, stdout=b"not-json")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    with pytest.raises(backend.BackendInfrastructureError, match="INVALID_STRUCTURED_OUTPUT"):
        backend.run(prompt="review", cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl")


def test_nonzero_diagnostic_is_allowlisted_and_does_not_reflect_output():
    output = SimpleNamespace(
        returncode=1, stdout=b"request too large private prompt", stderr=b"secret"
    )
    detail = backend._safe_nonzero_detail(output, 12)
    assert detail.startswith("REQUEST_TOO_LARGE: exit=1;")
    assert "private prompt" not in detail
    assert "secret" not in detail


def test_path_selected_launcher_outside_trusted_root_is_rejected_before_secret(
    monkeypatch, tmp_path
):
    binary = tmp_path / "claude"
    binary.write_bytes(b"path shim")
    trusted = tmp_path / "approved-root"
    trusted.mkdir()
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (trusted,))
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "_secret", lambda _path: pytest.fail("secret was read"))
    with pytest.raises(backend.BackendInfrastructureError, match="launcher is untrusted"):
        backend.run(prompt="review", cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl")


def test_unapproved_launcher_digest_is_rejected_before_secret(monkeypatch, tmp_path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"unexpected cli")
    binary.chmod(0o755)
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (tmp_path,))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_SHA256", frozenset())
    monkeypatch.setattr(backend, "_secret", lambda _path: pytest.fail("secret was read"))
    with pytest.raises(backend.BackendInfrastructureError, match="identity is unapproved"):
        backend.run(prompt="review", cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl")


def test_unavailable_trusted_launcher_root_is_typed_infrastructure_failure(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")
    binary.chmod(0o755)
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (tmp_path / "missing",))
    with pytest.raises(
        backend.BackendInfrastructureError, match="trusted Claude launcher root cannot be resolved"
    ):
        backend._approved_claude_binary(str(binary))


def test_budget_recipe_is_fixed_and_hash_bound_in_dedicated_settings():
    env = backend.child_environment("synthetic", endpoint="http://127.0.0.1:1234/anthropic")
    assert env["CLAUDE_CODE_MAX_RETRIES"] == "0"
    assert env["CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK"] == "1"
    assert env["CLAUDE_CODE_NO_MODEL_FALLBACK"] == "1"
    assert env["DISABLE_AUTO_COMPACT"] == "1"
    assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "16384"
    assert json.loads(backend.DEDICATED_SETTINGS)["env"] == backend.REVIEW_BUDGET_ENV


def test_oversize_prompt_fails_before_binary_or_secret_resolution(monkeypatch, tmp_path):
    def forbidden(*_args):
        raise AssertionError("preflight must precede credential or launcher access")

    monkeypatch.setattr(backend, "_secret", forbidden)
    monkeypatch.setattr(backend.shutil, "which", forbidden)
    with pytest.raises(backend.BackendInfrastructureError, match="PROMPT_BUDGET_EXCEEDED"):
        backend.run(prompt="x" * 56001, cwd=tmp_path, attempt_path=tmp_path / "attempt.jsonl")


@pytest.fixture(autouse=True)
def synthetic_gateway(monkeypatch):
    """Adapter tests isolate CLI logic; actual gateway requests have separate tests."""

    class Gateway:
        cli_token = "local-token"
        cli_endpoint = "http://127.0.0.1:1234/anthropic"

        def __init__(self, *, secret, prompt, timeout, attempt_path):
            assert secret == "synthetic-secret"
            assert timeout > 0
            self.metadata, log = synthetic_transport_evidence(prompt.encode())
            attempt_path.write_bytes(log)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def evidence(self):
            return self.metadata

    monkeypatch.setattr(backend, "SingleRequestTransport", Gateway)
