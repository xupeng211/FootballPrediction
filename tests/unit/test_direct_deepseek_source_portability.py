"""显式冻结 Harness 测试来源：缺失或漂移必须拒绝，不静默跳过。"""

import pytest

from tests.unit.test_direct_deepseek_bound import git


def test_explicit_harness_source_missing_fails_instead_of_skip(monkeypatch):
    from tests.helpers.direct_harness_source import harness_source  # noqa: PLC0415

    monkeypatch.delenv("CMH_OFFLINE_HARNESS_ROOT", raising=False)
    with pytest.raises(pytest.UsageError, match="must name the frozen"):
        harness_source()


def test_unapproved_harness_head_fails_closed(tmp_path, monkeypatch):
    from tests.helpers.direct_harness_source import harness_source  # noqa: PLC0415

    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "commit", "--allow-empty", "-qm", "TEST_ONLY unapproved source")
    monkeypatch.setenv("CMH_OFFLINE_HARNESS_ROOT", str(tmp_path))
    with pytest.raises(pytest.UsageError, match="HEAD mismatch"):
        harness_source()
