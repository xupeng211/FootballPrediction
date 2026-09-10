#!/usr/bin/env python3
"""Agentic Engineering Workflow V1 的动作分类与 merge-readiness gate。

lifecycle: permanent
owner: engineering workflow governance

`classify-finding` 暴露 Builder 的自主修复/升级边界；`merge-ready` 只读地
汇总 local preflight、PR exact-head/required CI、外部 Codex receipt、scope
和 protected-invariant evidence。它绝不执行 merge、push、commit 或清理。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_independent_review import (  # noqa: E402
    ReviewReceiptError,
    validate_receipt,
)
from scripts.devops.exact_head import (  # noqa: E402
    ExactHeadError,
    assert_exact_head,
    normalize_full_sha,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    CONTRACT_SCHEMA_VERSION,
    DECISION_AUTO_REMEDIATE,
    DECISION_ESCALATE,
    classify_failure,
    validate_mission_scope,
)
from scripts.ops.helpers.pr_authorization_matrix import parse_task_type  # noqa: E402
from scripts.ops.helpers.strict_review_evidence import validate_strict_review_evidence  # noqa: E402


@dataclass(frozen=True)
class GateCheck:
    """One merge-readiness predicate and its machine-readable status."""

    name: str
    status: str
    message: str


def _git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"JSON evidence 必须是 object: {path}")
    return value


def _status(value: str | None) -> str:
    return (value or "UNKNOWN").strip().upper()


def classify_command(args: argparse.Namespace) -> int:
    """Classify one current-mission finding for Builder remediation."""

    decision = classify_failure(args.category, in_current_mission=not args.out_of_scope)
    payload = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "category": args.category,
        "decision": decision,
        "builder_may_continue": decision == DECISION_AUTO_REMEDIATE,
        "execution_controller_required": decision == DECISION_ESCALATE,
    }
    print(
        json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"DECISION={decision}"
    )
    return 0


def _local_preflight_check(path: Path, base_sha: str, head_sha: str) -> GateCheck:
    try:
        value = _load_json(path)
        if value.get("verdict") != "PASS":
            return GateCheck(
                "local-required-checks", "FAIL", f"local preflight verdict={value.get('verdict')}"
            )
        assert_exact_head(base_sha, value.get("base_sha"), role="local preflight base")
        assert_exact_head(head_sha, value.get("current_head_sha"), role="local preflight HEAD")
    except (RuntimeError, TypeError, ExactHeadError) as exc:
        return GateCheck("local-required-checks", "FAIL", str(exc))
    return GateCheck("local-required-checks", "PASS", f"verified {path}")


def _remote_pr_check(
    pr_number: int,
    *,
    changed_paths: set[str],
    expected_head: str,
) -> tuple[GateCheck, dict[str, Any]]:
    try:
        from scripts.devops import pr_ready_check  # noqa: PLC0415

        result = pr_ready_check.evaluate(pr_number)
    except Exception as exc:  # unknown GitHub state must fail closed
        return GateCheck(
            "remote-required-ci", "UNKNOWN", f"pr-ready evidence unavailable: {exc}"
        ), {}
    failed = [finding for finding in result.findings if not finding.passed]
    evidence: dict[str, Any] = {
        "pr": pr_number,
        "verdict": result.verdict,
        "findings": [asdict(item) for item in result.findings],
        "head_sha": result.pr.head_sha,
    }
    if result.pr.head_sha != expected_head:
        return GateCheck(
            "remote-required-ci",
            "FAIL",
            f"PR head={result.pr.head_sha}; expected exact HEAD={expected_head}",
        ), evidence
    if failed:
        detail = "; ".join(f"{item.name}: {item.message}" for item in failed)
        return GateCheck("remote-required-ci", "FAIL", detail), evidence
    strict_errors = validate_strict_review_evidence(
        result.pr.body,
        result.pr.head_sha,
        changed_paths=changed_paths,
        task_type=parse_task_type(result.pr.body),
        allow_pending=False,
    )
    if strict_errors:
        evidence["verdict"] = "FAIL"
        evidence["strict_review_errors"] = strict_errors
        return GateCheck(
            "remote-required-ci",
            "FAIL",
            "final PR body review evidence invalid: " + "; ".join(strict_errors),
        ), evidence
    return GateCheck(
        "remote-required-ci", "PASS", f"PR #{pr_number} exact-head required checks green"
    ), evidence


def merge_ready_command(args: argparse.Namespace) -> int:
    """Evaluate merge readiness without performing any merge-side effect."""

    repo_root = Path(args.repo_root).resolve()
    checks: list[GateCheck] = []
    try:
        base_sha = normalize_full_sha(args.base_sha, role="base SHA")
        expected_head = normalize_full_sha(args.head_sha, role="expected PR HEAD")
        actual_head = normalize_full_sha(
            _git(["rev-parse", "HEAD"], repo_root), role="current HEAD"
        )
        assert_exact_head(expected_head, actual_head, role="current PR HEAD")
    except (RuntimeError, ExactHeadError) as exc:
        checks.append(GateCheck("exact-head", "FAIL", str(exc)))
        base_sha = args.base_sha
        expected_head = args.head_sha
        actual_head = None
    else:
        checks.append(GateCheck("exact-head", "PASS", actual_head))

    try:
        changed = {
            line.strip()
            for line in _git(
                ["diff", "--name-only", f"{base_sha}...{expected_head}"], repo_root
            ).splitlines()
            if line.strip()
        }
    except RuntimeError as exc:
        changed = set()
        checks.append(GateCheck("mission-scope", "UNKNOWN", str(exc)))
    scope_errors = validate_mission_scope(changed)
    if scope_errors:
        checks.append(GateCheck("mission-scope", "FAIL", "; ".join(scope_errors)))
    else:
        checks.append(
            GateCheck(
                "mission-scope",
                "PASS",
                "changed paths remain inside workflow infrastructure allowlist",
            )
        )

    checks.append(_local_preflight_check(Path(args.local_preflight_json), base_sha, expected_head))

    if args.pr is not None:
        remote_check, remote_evidence = _remote_pr_check(
            args.pr,
            changed_paths=changed,
            expected_head=expected_head,
        )
        checks.append(remote_check)
    else:
        remote_evidence = {}
        checks.append(
            GateCheck(
                "remote-required-ci",
                "UNKNOWN",
                "PR context is required; caller-supplied CI status is ignored",
            )
        )

    try:
        receipt = validate_receipt(
            Path(args.receipt),
            repo_root=repo_root,
            current_head=actual_head,
            expected_base=base_sha,
            expected_mission_id=args.mission_id,
        )
    except (ReviewReceiptError, ExactHeadError, OSError, ValueError) as exc:
        receipt = {}
        checks.append(GateCheck("independent-review", "FAIL", str(exc)))
    else:
        checks.append(
            GateCheck(
                "independent-review",
                "PASS" if receipt.get("review_result") == "PASS" else "FAIL",
                f"engine=codex head={receipt.get('reviewed_head_sha')} blocking={receipt.get('blocking_findings')}",
            )
        )

    protected = _status(args.protected_invariants)
    forbidden = _status(args.forbidden_side_effects)
    checks.append(
        GateCheck("protected-invariants", "PASS" if protected == "PASS" else protected, protected)
    )
    checks.append(
        GateCheck("forbidden-side-effects", "PASS" if forbidden == "NO" else forbidden, forbidden)
    )
    if args.pr is not None:
        checks.append(
            GateCheck(
                "required-pr-governance",
                "PASS" if remote_evidence.get("verdict") == "PASS" else "FAIL",
                "derived from pr-ready",
            )
        )
    else:
        checks.append(
            GateCheck(
                "required-pr-governance",
                "UNKNOWN",
                "PR context is required; caller-supplied governance status is ignored",
            )
        )

    ready = bool(checks) and all(check.status == "PASS" for check in checks)
    output: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "mission_id": args.mission_id,
        "mission_scope_valid": "YES"
        if next(
            (c for c in checks if c.name == "mission-scope"), GateCheck("", "UNKNOWN", "")
        ).status
        == "PASS"
        else "NO",
        "local_required_checks": next(
            (c.status for c in checks if c.name == "local-required-checks"), "UNKNOWN"
        ),
        "remote_required_ci_terminal_green": "YES"
        if next(
            (c for c in checks if c.name == "remote-required-ci"), GateCheck("", "UNKNOWN", "")
        ).status
        == "PASS"
        else "NO",
        "independent_review_present": "YES" if receipt else "NO",
        "independent_review_result": receipt.get("review_result", "UNKNOWN"),
        "reviewed_head_sha": receipt.get("reviewed_head_sha", "UNKNOWN"),
        "current_pr_head_sha": actual_head or "UNKNOWN",
        "blocking_findings": receipt.get("blocking_findings", "UNKNOWN"),
        "protected_invariants": protected,
        "forbidden_side_effects": forbidden,
        "required_pr_governance": "PASS"
        if next(
            (c for c in checks if c.name == "required-pr-governance"), GateCheck("", "UNKNOWN", "")
        ).status
        == "PASS"
        else "UNKNOWN",
        "checks": [asdict(check) for check in checks],
        "remote_evidence": remote_evidence,
        "merge_ready": "YES" if ready else "NO",
        "ready_for_execution_controller_merge_review": "YES" if ready else "NO",
        "self_merged": "NO",
    }
    print(
        json.dumps(output, ensure_ascii=False, indent=2)
        if args.json
        else "\n".join(
            [
                f"MERGE_READY={output['merge_ready']}",
                f"READY_FOR_EXECUTION_CONTROLLER_MERGE_REVIEW={output['ready_for_execution_controller_merge_review']}",
                *(f"[{check.status}] {check.name}: {check.message}" for check in checks),
            ]
        )
    )
    return 0 if ready else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the action-classification and merge-readiness CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    classify = sub.add_parser("classify-finding")
    classify.add_argument("--category", required=True)
    classify.add_argument("--out-of-scope", action="store_true")
    classify.add_argument("--json", action="store_true")
    gate = sub.add_parser("merge-ready")
    gate.add_argument("--repo-root", type=Path, default=ROOT)
    gate.add_argument("--base-sha", required=True)
    gate.add_argument("--head-sha", required=True)
    gate.add_argument("--mission-id", required=True)
    gate.add_argument("--local-preflight-json", required=True, type=Path)
    gate.add_argument("--receipt", required=True, type=Path)
    gate.add_argument("--pr", type=int, default=None)
    gate.add_argument("--remote-ci-status", default="UNKNOWN")
    gate.add_argument("--protected-invariants", default="UNKNOWN")
    gate.add_argument("--forbidden-side-effects", default="UNKNOWN")
    gate.add_argument("--required-pr-governance", default="UNKNOWN")
    gate.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one read-only Agentic Workflow V1 command."""

    args = build_parser().parse_args(argv)
    if args.command == "classify-finding":
        return classify_command(args)
    return merge_ready_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
