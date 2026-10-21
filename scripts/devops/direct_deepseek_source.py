"""Direct 冻结来源与资格合同加载；只读复用原 exact-HEAD 校验。

lifecycle: permanent
owner: engineering workflow governance
"""

# 资格模块只从已绑定的冻结 Harness 加载，沿用原局部导入。
# ruff: noqa: PLC0415
from __future__ import annotations

import json
from pathlib import Path
import sys

from scripts.devops.claude_deepseek_independent_review import _git, _sha
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import sha256_bytes

STANDALONE_MARKER = "STANDALONE_DIRECT_V1="


def standalone_config(scope):
    """Scope 只声明候选合同；运行时 Exact-HEAD/授权在提交后绑定，避免自引用。"""
    records = [s for s in scope.protected_invariants if s.startswith(STANDALONE_MARKER)]
    if not records:
        return None
    if len(records) != 1 or scope.workflow_class != "CRITICAL":
        raise backend.DirectError("STANDALONE_SCOPE")
    value = json.loads(records[0][len(STANDALONE_MARKER) :])
    if (
        set(value)
        != {
            "version",
            "football_base",
            "football_ancestor",
            "harness_root",
            "harness_base",
            "harness_head",
            "harness_tree",
            "harness_origin",
            "harness_paths",
        }
        or value["version"] != 1
    ):
        raise backend.DirectError("STANDALONE_SCOPE")
    return value


def source_binding(root, base, head, *, origin):
    """真实 Git 来源、tree、完整 diff 和每路径 blob/mode，而非伴随 hash 提示。"""
    if (
        _git(root, "config", "--get", "remote.origin.url").strip() != origin
        or _sha(root, "HEAD") != head
        or _git(root, "status", "--porcelain")
    ):
        raise backend.DirectError("SOURCE_IDENTITY")
    if _git(root, "merge-base", base, head).strip() != base:
        raise backend.DirectError("SOURCE_LINEAGE")
    diff = _git(root, "diff", "--binary", "--no-ext-diff", f"{base}...{head}", text=False)
    paths = _git(root, "diff", "--name-only", f"{base}...{head}").splitlines()
    return {
        "origin": origin,
        "base": base,
        "head": head,
        "tree": _git(root, "rev-parse", f"{head}^{{tree}}").strip(),
        "diff_sha256": sha256_bytes(diff),
        "diff_bytes": len(diff),
        "files": {p: _git(root, "ls-tree", head, "--", p).strip() for p in paths},
    }, diff


def companion_source(scope):
    """由冻结 scope 验证 Harness，只读传递完整应审 diff。"""
    config = standalone_config(scope)
    if config is None:
        return None
    root = Path(config["harness_root"])
    binding, diff = source_binding(
        root, config["harness_base"], config["harness_head"], origin=config["harness_origin"]
    )
    if binding["tree"] != config["harness_tree"] or sorted(binding["files"]) != sorted(
        config["harness_paths"]
    ):
        raise backend.DirectError("COMPANION_SOURCE")
    return binding, diff


def qualification_contract(scope):
    """复用冻结 Harness 的纯语义资格合同；绝不调用其旧 CLI qualify_live。"""
    config = standalone_config(scope)
    companion_source(scope)
    root = Path(config["harness_root"])
    sys.dont_write_bytecode = True
    source = str(root / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from harness import model_qualification as qualification
    from harness import reviewer_v2_contract as contract

    if (
        Path(qualification.__file__).resolve() != root / "src/harness/model_qualification.py"
        or Path(contract.__file__).resolve() != root / "src/harness/reviewer_v2_contract.py"
    ):
        raise backend.DirectError("QUALIFICATION_RUNTIME")
    return qualification, contract
