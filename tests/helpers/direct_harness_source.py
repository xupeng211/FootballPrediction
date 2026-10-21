"""显式冻结 Harness 来源与临时 Git companion；不产生 Provider 证据。

lifecycle: test-fixture
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

HEAD = "ea507645cc143b883927fbb67b164cc85d4503a5"
DIFF_SHA256 = "311f336d73c3a353d4f3f17c3111d4e7d33c914ca2e2bb43279e491f65841b25"
QUALIFICATION_SHA256 = {
    "model_qualification.py": "a304da276ee3fd47d4356c5075797b46bdfd4e98667586ff790b0d6f812c8d5f",
    "reviewer_v2_contract.py": "57a0a4f419897d091825041aea7ae4ff418ec05dcaace44aab2e88cfbb28cf6d",
}


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(root), *args])


def harness_source():
    """来源缺失/漂移明确失败；H1/H2 交付后必须重新冻结此测试依赖。"""
    value = os.environ.get("CMH_OFFLINE_HARNESS_ROOT")
    if not value:
        raise pytest.UsageError(
            "CMH_OFFLINE_HARNESS_ROOT must name the frozen offline Harness source"
        )
    root = Path(value).resolve()
    if git(root, "rev-parse", "HEAD").decode().strip() != HEAD:
        raise pytest.UsageError("offline Harness HEAD mismatch")
    patch = git(root, "diff", "--binary", "HEAD")
    if hashlib.sha256(patch).hexdigest() != DIFF_SHA256:
        raise pytest.UsageError("offline Harness task-budget patch mismatch")
    for name, expected in QUALIFICATION_SHA256.items():
        if hashlib.sha256((root / "src/harness" / name).read_bytes()).hexdigest() != expected:
            raise pytest.UsageError("offline Harness qualification source mismatch: " + name)
    return root


@pytest.fixture(scope="session")
def portable_harness(tmp_path_factory):
    """真实 Git base/head/tree/diff；仅 companion 改动是声明的合成测试输入。"""
    source = harness_source()
    root = tmp_path_factory.getbasetemp() / "offline-harness-companion"
    if root.exists():
        return _companion_config(root)
    root.mkdir()
    shutil.copytree(source / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    git(root, "init", "-q")
    git(root, "config", "user.name", "Offline Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "remote.origin.url", "git@github.com:xupeng211/codex-mission-harness.git")
    git(root, "add", "src")
    git(root, "commit", "-qm", "TEST_ONLY frozen qualification source")
    (root / "companion.py").write_text("# TEST_ONLY reviewed companion source\n" * 24)
    git(root, "add", "companion.py")
    git(root, "commit", "-qm", "TEST_ONLY companion review target")
    return _companion_config(root)


def _companion_config(root):
    return {
        "version": 1,
        "harness_root": str(root),
        "harness_base": git(root, "rev-parse", "HEAD^").decode().strip(),
        "harness_head": git(root, "rev-parse", "HEAD").decode().strip(),
        "harness_tree": git(root, "rev-parse", "HEAD^{tree}").decode().strip(),
        "harness_origin": "git@github.com:xupeng211/codex-mission-harness.git",
        "harness_paths": ["companion.py"],
    }
