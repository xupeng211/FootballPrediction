import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.devops.independent_review_backends import claude_code_deepseek as backend


def test_child_environment_is_allowlisted_and_has_no_competing_route():
    env = backend.child_environment("synthetic-secret")
    assert env["ANTHROPIC_BASE_URL"] == backend.ENDPOINT
    assert env["ANTHROPIC_AUTH_TOKEN"] == "synthetic-secret"
    assert "HTTPS_PROXY" not in env
    assert "ANTHROPIC_API_KEY" not in env


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
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b'{"is_error":false,"session_id":"fresh-session","structured_output":'
                b'{"protocol_version":"INDEPENDENT_REVIEW_PROTOCOL_V1",'
                b'"review_result":"PASS","findings":[]},"modelUsage":'
                b'{"deepseek-flash":{"canonicalModel":"deepseek-flash"}}}'
            ),
        )

    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    raw, result, evidence = backend.run(prompt="review", cwd=tmp_path)
    child_env = observed["env"]
    assert isinstance(child_env, dict)
    assert child_env["ANTHROPIC_AUTH_TOKEN"] == "synthetic-secret"
    assert child_env["ANTHROPIC_BASE_URL"] == backend.ENDPOINT
    assert "HTTPS_PROXY" not in child_env
    assert "synthetic-secret" not in os.environ.values()
    assert "synthetic-secret" not in evidence.command
    assert b"synthetic-secret" not in raw
    assert result["review_result"] == "PASS"


def test_run_rejects_malformed_provider_output_as_infrastructure(monkeypatch, tmp_path: Path):
    binary = tmp_path / "claude"
    binary.write_bytes(b"synthetic cli")
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "_secret", lambda _path: "synthetic-secret")

    def fake_run(command, **_kwargs):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (Claude Code)\n")
        return SimpleNamespace(returncode=0, stdout=b"not-json")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    with pytest.raises(backend.BackendInfrastructureError, match="INVALID_STRUCTURED_OUTPUT"):
        backend.run(prompt="review", cwd=tmp_path)
