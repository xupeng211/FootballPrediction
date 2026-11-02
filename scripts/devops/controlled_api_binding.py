"""候选通道的 Git object 绑定与离线资格清单；不生成正式 Receipt。

lifecycle: permanent
新通道的真实 Qualification/Registry 接入未获授权，不能迁移旧 CLI 资格。
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from scripts.devops.controlled_api_policy import PROFILES, ControlError, source_identity
from scripts.devops.exact_head import assert_exact_head, normalize_full_sha
from scripts.devops.independent_review_protocol import sha256_bytes
from scripts.ops.helpers.agent_workflow_contract import MissionScope, validate_mission_scope

if TYPE_CHECKING:
    from pathlib import Path

HTTPS_CHANNEL = "controlled-direct-api/https-candidate-v1"


def bind_source(project: Path, base: str, head: str, mission: str, scope_path: str) -> dict:
    """从 clean exact HEAD 的 Git blobs 读取 scope 和 canonical 三点 diff。"""
    base = normalize_full_sha(base, role="review base")
    head = normalize_full_sha(head, role="review head")
    if scope_path != f"docs/agentic/missions/{mission}.json":
        raise ControlError("INVALID_SCOPE_PATH")

    def git(*args: str) -> bytes:
        result = subprocess.run(["git", *args], cwd=project, capture_output=True, check=False)
        if result.returncode:
            raise ControlError("SOURCE_GIT_REJECTED")
        return result.stdout

    assert_exact_head(head, git("rev-parse", "HEAD").decode().strip(), role="review source")
    if git("status", "--porcelain=v1"):
        raise ControlError("SOURCE_DIRTY")
    git("merge-base", "--is-ancestor", base, head)
    tree = git("ls-tree", head, "--", scope_path).split(maxsplit=1)
    if not tree or tree[0] != b"100644":
        raise ControlError("REGULAR_SCOPE_BLOB_REQUIRED")
    scope = git("show", f"{head}:{scope_path}")
    contract = MissionScope.from_mapping(json.loads(scope))
    if contract.mission_id != mission or contract.workflow_class != "CRITICAL":
        raise ControlError("SOURCE_SCOPE_MISMATCH")
    changed = git("diff", "--name-only", "-z", f"{base}...{head}").decode().split("\0")
    if validate_mission_scope([path for path in changed if path], contract):
        raise ControlError("SOURCE_OUTSIDE_MISSION_SCOPE")
    source = {
        "repository": "xupeng211/FootballPrediction",
        "mission": mission,
        "base": base,
        "head": head,
        "diff_sha256": sha256_bytes(git("diff", "--binary", "--no-ext-diff", f"{base}...{head}")),
        "scope_sha256": sha256_bytes(scope),
    }
    source_identity(source)
    return source


def qualification_requirements(provider: str) -> dict:
    """准备独立身份，显式列出 admission 前置条件；绝不授予旧资格。"""
    if provider not in {"deepseek", "openai"}:
        raise ControlError("UNKNOWN_REVIEWER")
    return {
        "execution_identity": f"{HTTPS_CHANNEL}/{provider}",
        "provider": provider,
        "requested_model": PROFILES[provider].model,
        "qualification_scope": "EXACT_TOOLCHAIN_MODEL_PROMPT_AND_ISOLATION_RECIPE",
        "current_approval_eligible": False,
        "legacy_qualification_inheritance": False,
        "qualification_status": "NOT_RUN",
        "formal_receipt_supported": False,
        "required_before_live": [
            "provider_billing_bound_and_frozen_price",
            "exclusive_credential_and_egress_deployment",
            "owner_paid_execution_authorization",
            "independent_channel_qualification",
            "owner_approved_qualification_plan_and_acceptance_criteria",
            "approved_registry_and_receipt_contract_migration",
            "exact_source_binding_and_full_results",
            "formal_review_context_and_placeholder_validation",
            "independent_critical_review_of_bootstrap_candidate",
        ],
    }
