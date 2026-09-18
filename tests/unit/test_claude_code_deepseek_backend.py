from pathlib import Path
import os

import pytest

from scripts.devops.independent_review_backends import claude_code_deepseek as backend


def test_child_environment_is_allowlisted_and_has_no_competing_route():
    env = backend.child_environment("synthetic-secret")
    assert env["ANTHROPIC_BASE_URL"] == backend.ENDPOINT
    assert env["ANTHROPIC_AUTH_TOKEN"] == "synthetic-secret"
    assert "HTTPS_PROXY" not in env and "ANTHROPIC_API_KEY" not in env


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
