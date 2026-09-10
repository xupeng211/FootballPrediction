#!/usr/bin/env python3
"""Agentic Engineering Workflow V1 的本地 governance preflight。

lifecycle: permanent
owner: engineering workflow governance

该入口把本地 branch/diff 检查与远端 AI Workflow Gate 使用的同一套
metadata、authorization、lifecycle、growth-freeze 和 STRICT 分类合同串起来。
它只读 Git 和文件，不访问 GitHub、数据库、provider 或生产系统。
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ci.governance_growth_gate import check_local_worktree_growth  # noqa: E402
from scripts.devops.exact_head import is_full_sha  # noqa: E402
from scripts.ops.ai_workflow_gate import validate as validate_ai_workflow_gate  # noqa: E402
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    CONTRACT_SCHEMA_VERSION,
    MissionScope,
    MissionScopeError,
    contract_summary,
    load_mission_scope_file,
    mission_scope_relative_path,
    mission_scope_sha256,
    validate_mission_scope_reference,
)
from scripts.ops.helpers.git_change_helpers import (  # noqa: E402
    changed_paths,
    collect_changes,
    resolve_comparison_refs,
)


@dataclass(frozen=True)
class PreflightFinding:
    """One machine-readable local preflight finding."""

    check: str
    status: str
    message: str


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _git_blob_sha(commit_sha: str, relative_path: str) -> str:
    """Hash one scope file as stored in the candidate commit."""

    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise MissionScopeError(
            f"mission scope file is not tracked at exact head {commit_sha}: {relative_path}"
        )
    return hashlib.sha256(result.stdout).hexdigest()


def _assert_scope_file_matches_head(
    scope_hash: str, *, resolved_head: str, relative_path: str
) -> None:
    commit_hash = _git_blob_sha(resolved_head, relative_path)
    if commit_hash != scope_hash:
        raise MissionScopeError("mission scope file bytes differ from the exact candidate HEAD")


def _load_current_mission_scope(
    pr_body: str,
    mission_scope_file: Path | None,
    *,
    resolved_head: str,
    allow_uncommitted: bool,
) -> tuple[MissionScope | None, str | None, str | None, list[str]]:
    """Load and bind the explicit scope without ever falling back to allow-all."""

    if mission_scope_file is None:
        return (
            None,
            None,
            None,
            [
                "AGENT_WORKFLOW_SCOPE_INVALID: --mission-scope-file is required; "
                "missing scope never means allow-all."
            ],
        )
    try:
        scope_path = mission_scope_file.absolute()
        relative_path = mission_scope_relative_path(scope_path, ROOT)
        scope = load_mission_scope_file(scope_path, repo_root=ROOT)
        scope_hash = mission_scope_sha256(scope_path)
        if not allow_uncommitted:
            _assert_scope_file_matches_head(
                scope_hash, resolved_head=resolved_head, relative_path=relative_path
            )
        binding_errors = validate_mission_scope_reference(
            pr_body, mission_scope=scope, scope_path=relative_path
        )
    except (MissionScopeError, OSError) as exc:
        return None, None, None, [f"AGENT_WORKFLOW_SCOPE_INVALID: {exc}"]
    return scope, relative_path, scope_hash, binding_errors


def run_preflight(
    pr_body: str,
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
    require_review: bool = False,
    mission_scope_file: Path | None = None,
) -> dict[str, Any]:
    """Run the V1 local checks and return a stable JSON-compatible result."""

    findings: list[PreflightFinding] = []
    try:
        resolved_base, resolved_head = resolve_comparison_refs(base_ref, head_ref)
        changes = collect_changes(
            base_ref,
            head_ref,
            include_worktree=head_ref is None,
        )
        branch = _git(["branch", "--show-current"])
        current_head = _git(["rev-parse", "HEAD"])
    except (RuntimeError, OSError) as exc:
        findings.append(PreflightFinding("git-topology", "FAIL", str(exc)))
        return _result(findings, None, None, None, [], require_review, None, None, None)

    scope, scope_path, scope_hash, scope_errors = _load_current_mission_scope(
        pr_body,
        mission_scope_file,
        resolved_head=resolved_head,
        allow_uncommitted=head_ref is None,
    )
    findings.extend(
        PreflightFinding("mission-scope-contract", "FAIL", error) for error in scope_errors
    )
    if not scope_errors:
        findings.append(
            PreflightFinding(
                "mission-scope-contract",
                "PASS",
                f"mission={scope.mission_id}; path={scope_path}; sha256={scope_hash}",
            )
        )

    if not branch or branch in {"main", "master"}:
        findings.append(
            PreflightFinding(
                "feature-branch",
                "FAIL",
                f"当前 branch={branch or 'DETACHED'}；Builder 必须在 feature branch 工作。",
            )
        )
    else:
        findings.append(PreflightFinding("feature-branch", "PASS", f"branch={branch}"))

    if is_full_sha(current_head):
        findings.append(PreflightFinding("exact-current-head", "PASS", current_head))
    else:
        findings.append(PreflightFinding("exact-current-head", "FAIL", "HEAD 不是完整 40 位 SHA。"))

    changed = changed_paths(changes)
    local_growth_errors = check_local_worktree_growth(changes) if head_ref is None else []
    findings.extend(
        PreflightFinding("governance-growth-freeze", "FAIL", error) for error in local_growth_errors
    )
    if not local_growth_errors:
        findings.append(
            PreflightFinding("governance-growth-freeze", "PASS", "未发现新增冻结治理资产。")
        )

    # The shared gate has human-readable progress output.  Keep that output
    # visible on stderr so --json remains a parseable machine interface.
    with contextlib.redirect_stdout(sys.stderr):
        gate_errors = validate_ai_workflow_gate(
            pr_body,
            changes,
            block_matrix=True,
            enforce_strict_review=True,
            enforce_agent_workflow_contract=True,
            enforce_agent_workflow_scope=True,
            mission_scope=scope,
            allow_review_pending=not require_review,
            base_ref=resolved_base,
            head_ref=resolved_head,
        )
    findings.extend(
        PreflightFinding("shared-ai-workflow-gate", "FAIL", error) for error in gate_errors
    )
    if not gate_errors:
        findings.append(
            PreflightFinding(
                "shared-ai-workflow-gate",
                "PASS",
                "本地使用与远端相同的 AI Workflow Gate contract。",
            )
        )

    return _result(
        findings,
        resolved_base,
        resolved_head,
        branch,
        sorted(changed),
        require_review,
        scope,
        scope_path,
        scope_hash,
        current_head=current_head,
    )


def _result(
    findings: list[PreflightFinding],
    base_sha: str | None,
    head_sha: str | None,
    branch: str | None,
    changed_paths_value: list[str],
    require_review: bool,
    mission_scope: MissionScope | None,
    mission_scope_path: str | None,
    mission_scope_hash: str | None,
    *,
    current_head: str | None = None,
) -> dict[str, Any]:
    failed = [finding for finding in findings if finding.status == "FAIL"]
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "workflow": "agentic_engineering_workflow_v1",
        "verdict": "FAIL" if failed else "PASS",
        "require_review": require_review,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "current_head_sha": current_head or head_sha,
        "branch": branch,
        "changed_paths": changed_paths_value,
        "findings": [asdict(finding) for finding in findings],
        "contract": contract_summary(),
        "mission_scope": mission_scope.to_dict() if mission_scope else None,
        "mission_scope_path": mission_scope_path,
        "mission_scope_sha256": mission_scope_hash,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the local preflight CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body-file", required=True, type=Path)
    parser.add_argument(
        "--mission-scope-file",
        required=True,
        type=Path,
        help="当前 mission 的 tracked JSON scope contract；缺失时 fail closed",
    )
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--head-ref", default=None)
    parser.add_argument(
        "--require-review",
        action="store_true",
        help="最终 review 阶段使用；不允许 STRICT PENDING 状态",
    )
    parser.add_argument("--json", action="store_true", help="只输出 machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run local Agentic Workflow V1 preflight and return its exit status."""

    args = build_parser().parse_args(argv)
    try:
        body = args.pr_body_file.read_text(encoding="utf-8")
    except OSError as exc:
        result = _result(
            [PreflightFinding("pr-body", "FAIL", f"无法读取 PR body: {exc}")],
            None,
            None,
            None,
            [],
            args.require_review,
            None,
            None,
            None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = run_preflight(
        body,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        require_review=args.require_review,
        mission_scope_file=args.mission_scope_file,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"AGENT_PREFLIGHT={result['verdict']}")
        print(f"BASE_SHA={result.get('base_sha') or 'UNKNOWN'}")
        print(f"HEAD_SHA={result.get('current_head_sha') or 'UNKNOWN'}")
        print(f"CHANGED_PATHS={len(result['changed_paths'])}")
        for finding in result["findings"]:
            print(f"[{finding['status']}] {finding['check']}: {finding['message']}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
