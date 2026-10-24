from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops.independent_review_backends import claude_code_deepseek as backend


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
    env = backend.child_environment("synthetic-secret")
    assert env["PATH"] == backend.CONTROLLED_CLAUDE_PATH
    assert env["ANTHROPIC_BASE_URL"] == backend.ENDPOINT
    assert env["ANTHROPIC_AUTH_TOKEN"] == "synthetic-secret"
    assert env["ANTHROPIC_API_KEY"] == "synthetic-secret"
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
    raw, result, evidence = backend.run(prompt="review", cwd=tmp_path)
    child_env = observed["env"]
    assert isinstance(child_env, dict)
    assert child_env["ANTHROPIC_AUTH_TOKEN"] == "synthetic-secret"
    assert child_env["ANTHROPIC_API_KEY"] == "synthetic-secret"
    assert child_env["ANTHROPIC_BASE_URL"] == backend.ENDPOINT
    assert "HTTPS_PROXY" not in child_env
    assert "synthetic-secret" not in os.environ.values()
    assert "synthetic-secret" not in evidence.command
    assert b"synthetic-secret" not in raw
    assert result["review_result"] == "PASS"
    status, digest = backend.validate_process_digest(evidence.process_digest)
    assert status == "VALID"
    assert digest["returncode"] == 0
    assert digest["stdout_bytes"] == len(raw)
    assert digest["stderr_bytes"] is None


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
    backend.run(prompt="review", cwd=tmp_path, timeout_seconds=backend.MAX_REVIEW_TIMEOUT_SECONDS)
    assert observed["timeout"] == backend.MAX_REVIEW_TIMEOUT_SECONDS


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
        backend.run(prompt="private prompt", cwd=tmp_path, timeout_seconds=30)
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
        backend.run(prompt="review", cwd=tmp_path)


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
        backend.run(prompt="review", cwd=tmp_path)


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
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (trusted,))
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "_secret", lambda _path: pytest.fail("secret was read"))
    with pytest.raises(backend.BackendInfrastructureError, match="launcher is untrusted"):
        backend.run(prompt="review", cwd=tmp_path)


def test_unapproved_launcher_digest_is_rejected_before_secret(monkeypatch, tmp_path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"unexpected cli")
    binary.chmod(0o755)
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (tmp_path,))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_SHA256", frozenset())
    monkeypatch.setattr(backend, "_secret", lambda _path: pytest.fail("secret was read"))
    with pytest.raises(backend.BackendInfrastructureError, match="identity is unapproved"):
        backend.run(prompt="review", cwd=tmp_path)


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


def _safe_digest(code=7):
    """A synthetic observation, never a real reviewer receipt."""
    return {
        "returncode": code,
        "signal": -code if code < 0 else None,
        "timeout": False,
        "timeout_seconds": 900,
        "stdout_bytes": 3,
        "stderr_bytes": 5,
        "count_scope": "complete",
        "elapsed_seconds": 2.5,
        "started_at": "2026-10-21T12:00:00Z",
        "completed_at": "2026-10-21T12:00:02.500000Z",
        "cli_version": "2.1.278",
        "binary_sha256": "d" * 64,
        "settings_sha256": "e" * 64,
    }


@pytest.mark.parametrize("scenario", ["nonzero", "signal", "timeout", "incomplete"])
def test_failure_carries_safe_process_metadata(monkeypatch, tmp_path, scenario):
    binary = tmp_path / "claude"
    binary.write_bytes(b"fake cli")
    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    ticks = iter([10.0, 12.5])
    monkeypatch.setattr(backend.time, "monotonic", lambda: next(ticks))
    code = {"nonzero": 7, "signal": -15, "incomplete": 0}.get(scenario)

    def invoke(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(stdout="2.1.278 (Claude Code)")
        if scenario == "timeout":
            raise backend.subprocess.TimeoutExpired(command, 900, output=b"{", stderr=None)
        return SimpleNamespace(returncode=code, stdout=b"{", stderr=b"private")

    monkeypatch.setattr(backend.subprocess, "run", invoke)
    with pytest.raises(backend.BackendInfrastructureError) as raised:
        backend.run(prompt="private prompt", cwd=tmp_path)
    error = raised.value
    assert error.process_digest_status == "VALID"
    digest = error.process_digest
    assert digest["returncode"] == code
    assert digest["signal"] == (15 if scenario == "signal" else None)
    assert digest["elapsed_seconds"] == _safe_digest()["elapsed_seconds"]
    assert digest["stdout_bytes"] == 1
    assert digest["stderr_bytes"] == (None if scenario == "timeout" else 7)
    assert digest["timeout"] is (scenario == "timeout")
    assert digest["count_scope"] == ("partial_observed" if scenario == "timeout" else "complete")
    assert digest["cli_version"] == "2.1.278"
    assert backend.validate_process_digest(None) == ("MISSING", None)
    for invalid in (
        {},
        {**digest, "extra": "Authorization: secret"},
        {**digest, "stdout_bytes": True},
        {**digest, "elapsed_seconds": float("nan")},
        {**digest, "elapsed_seconds": 10**400},
        {**digest, "stdout_bytes": -1},
        {**digest, "started_at": "secret"},
    ):
        assert backend.validate_process_digest(invalid) == ("INVALID", None)
    positive = _safe_digest(137)
    assert backend.validate_process_digest(positive)[0] == "VALID"
    assert positive["signal"] is None
    absent = {**digest, "stdout_bytes": None}
    assert backend.validate_process_digest(absent)[1]["stdout_bytes"] is None
    assert "private" not in str(error)


@pytest.mark.parametrize("echo_secret", [True, False])
def test_sensitive_error_stream_never_exported(monkeypatch, tmp_path, echo_secret):
    binary = tmp_path / "claude"
    binary.write_bytes(b"fake cli")
    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    sensitive = b"Authorization: Bearer other-token; config=password"
    stderr = sensitive + (b" synthetic-secret" if echo_secret else b"")

    def invoke(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(stdout="2.1.278 (Claude Code)")
        return SimpleNamespace(returncode=7, stdout=b"partial private response", stderr=stderr)

    monkeypatch.setattr(backend.subprocess, "run", invoke)
    with pytest.raises(backend.BackendInfrastructureError) as raised:
        backend.run(prompt="private prompt", cwd=tmp_path)
    serialized = str(raised.value) + json.dumps(vars(raised.value))
    for marker in (
        "synthetic-secret",
        "Authorization",
        "other-token",
        "password",
        "private response",
        "private prompt",
    ):
        assert marker not in serialized
    assert raised.value.process_digest["returncode"] == _safe_digest()["returncode"]
    assert raised.value.process_digest["stderr_bytes"] == len(stderr)
    if echo_secret:
        assert str(raised.value) == "SECRET_LEAKAGE_DETECTED"
