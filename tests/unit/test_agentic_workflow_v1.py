"""Agentic Engineering Workflow V1 的机器合同和 merge gate 测试。

lifecycle: test-fixture
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.ci.governance_growth_gate import check_local_worktree_growth
from scripts.devops import agent_workflow
from scripts.devops.codex_independent_review import (
    REVIEW_OUTPUT_SCHEMA,
    ReviewReceiptError,
    _assert_contexts_separate,
    build_reviewer_command,
    diff_sha256,
    sha256_file,
    validate_receipt,
    validate_review_result,
)
from scripts.devops.exact_head import ExactHeadError
from scripts.ops.helpers.agent_workflow_contract import (
    DECISION_AUTO_REMEDIATE,
    DECISION_ESCALATE,
    classify_failure,
    validate_mission_scope,
    validate_pr_metadata,
)
from scripts.ops.helpers.garbage_prevention_checks import check_report_lifecycle_required
from scripts.ops.helpers.git_change_helpers import Change
from scripts.ops.helpers.governance_p1_checks import check_script_lifecycle_requirement

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "1" * 40


def _body(*, task_type: str = "workflow-governance", workflow_class: str = "STRICT") -> str:
    return f"""## Summary

This is a bounded workflow infrastructure test change with no business runtime mutation.

## Scope

| Field | Value |
| --- | --- |
| Task type | {task_type} |
| Workflow class | {workflow_class} |
| Changed paths | scripts/devops/agent_workflow.py; tests/unit/test_agentic_workflow_v1.py |
| Runtime behavior changed | no |
| Business progress | Durable workflow governance only. |

## Documentation Impact

| Field | Value |
| --- | --- |
| Capability changed? | yes |
| Milestone changed? | no |
| Canonical entrypoint changed? | no |
| Current blocker changed? | no |
| Data/model/authorization contract changed? | yes |
| Repository structure/authority navigation changed? | yes |
| Project vision / target-state changed? | no |
| Source-of-truth docs updated | yes |
| Updated authoritative docs | AGENTS.md; docs/AGENT_WORKFLOW.md; docs/CAPABILITY_INDEX.md |
| If not updated, explicit reason | The relevant workflow and capability authorities are updated in this mission. |

## Tests

pytest verifies the bounded workflow contract and gate behavior.

## Risk

No live fetch, provider request, database write, raw write, training, prediction, migration, scheduler, or production mutation.

## Rollback

Revert this infrastructure change; business runtime files are outside the mission allowlist.

## Dangerous File Authorization

The exact workflow files and tests listed in Scope are authorized for this governance mission; no production path is authorized.

## PR Authorization Matrix

| Authorized paths | scripts/devops/**; scripts/ops/helpers/**; scripts/ci/**; docs/**; tests/**; AGENTS.md; Makefile; .github/**; schemas/agentic/** |
| --- | --- |

## Strict Review Evidence

| Field | Value |
| --- | --- |
| Version | 1 |
| Task type | STRICT |
| Provider | codex-independent-reviewer (pending) |
| Reviewed full SHA | {BASE_SHA} |
| Result | PENDING |
| Timestamp | 2026-09-10T00:00:00Z |
"""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _make_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "review-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Agent Workflow Test")
    (repo / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    schema_path = repo / "schemas" / "agentic" / "codex_review_result.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text('{"type":"object"}\n', encoding="utf-8")
    _git(repo, "add", "Makefile", "schemas/agentic/codex_review_result.schema.json")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "Makefile").write_text("all:\n\t@echo workflow\n", encoding="utf-8")
    _git(repo, "add", "Makefile")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, base, head


def _write_valid_receipt(
    tmp_path: Path,
    repo: Path,
    base: str,
    head: str,
    *,
    result: str = "PASS",
    finding: dict[str, object] | None = None,
) -> Path:
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    raw = evidence / "raw.jsonl"
    final = evidence / "final.json"
    stderr = evidence / "stderr.log"
    final_document = {"result": result, "findings": [finding] if finding else []}
    final_text = json.dumps(final_document) + "\n"
    final.write_text(final_text, encoding="utf-8")
    raw.write_text(
        "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "reviewer-1234"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-progress-1",
                            "type": "agent_message",
                            "text": "检查中",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-progress-2",
                            "type": "agent_message",
                            "text": "即将输出结果",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"id": "item-1", "type": "agent_message", "text": final_text},
                    }
                ),
                json.dumps({"type": "turn.completed"}),
                "",
            ]
        ),
        encoding="utf-8",
    )
    stderr.write_text("", encoding="utf-8")
    for path in (raw, final, stderr):
        path.chmod(0o600)
    schema_path = (
        tmp_path / "review-worktree" / "schemas" / "agentic" / "codex_review_result.schema.json"
    )
    schema_path.parent.mkdir(parents=True)
    schema_source = repo / "schemas" / "agentic" / "codex_review_result.schema.json"
    schema_path.write_bytes(schema_source.read_bytes())
    schema_path.chmod(0o600)
    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    normalized_findings: list[dict[str, object]] = []
    if finding:
        severity = str(finding["severity"])
        counts[severity] += 1
        normalized_findings.append(
            {
                "severity": severity,
                "title": finding["title"],
                "path": finding.get("path"),
                "line": finding.get("line"),
                "summary": finding["summary"],
                "blocking": severity in {"P0", "P1", "P2"},
            }
        )
    receipt: dict[str, object] = {
        "schema_version": "codex-independent-review-receipt/v1",
        "contract_schema_version": "agentic-engineering-workflow/v1",
        "review_engine": "codex",
        "review_role": "independent_reviewer",
        "base_sha": base,
        "reviewed_head_sha": head,
        "diff_sha256": diff_sha256(repo, base, head),
        "mission_id": "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
        "review_started_at": "2026-09-10T00:00:00Z",
        "review_completed_at": "2026-09-10T00:01:00Z",
        "finding_counts_by_severity": counts,
        "blocking_findings": sum(counts[key] for key in ("P0", "P1", "P2")),
        "review_result": result,
        "findings": normalized_findings,
        "reviewer_invocation_id": "reviewer-1234",
        "builder_context_id": "builder-5678",
        "reviewer_context_id": "reviewer-1234",
        "reviewer_read_only": True,
        "isolation": {
            "fresh_process": True,
            "ephemeral_session": True,
            "sandbox": "read-only",
            "detached_worktree": True,
            "worktree_head_sha": head,
        },
        "provenance": {
            "writer": "scripts/devops/codex_independent_review.py",
            "wrapper_sha256": sha256_file(ROOT / "scripts/devops/codex_independent_review.py"),
            "command_sha256": "0" * 64,
            "codex_binary": "codex",
            "output_schema_path": str(schema_path),
            "output_schema_sha256": sha256_file(schema_path),
            "raw_output_path": str(raw),
            "raw_output_sha256": sha256_file(raw),
            "agent_message_sha256": sha256_file(final),
            "codex_exit_code": 0,
            "stderr_path": str(stderr),
            "final_message_path": str(final),
            "final_message_sha256": sha256_file(final),
        },
    }
    command = build_reviewer_command(
        codex_binary="codex",
        base_sha=base,
        output_schema=schema_path,
        final_message_path=final,
    )
    receipt["provenance"]["command_sha256"] = hashlib.sha256(
        (
            json.dumps(command, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
    ).hexdigest()
    receipt["integrity"] = {
        "receipt_payload_sha256": hashlib.sha256(
            (
                json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode()
        ).hexdigest()
    }
    path = evidence / "receipt.json"
    path.write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)
    return path


def test_agent_entry_points_to_canonical_workflow():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/AGENT_WORKFLOW.md" in text
    assert "make agent-preflight" in text
    assert "make agent-merge-ready" in text


def test_in_scope_ci_failure_is_auto_remediated():
    assert classify_failure("ci") == DECISION_AUTO_REMEDIATE
    assert classify_failure("reviewer_narrow_defect") == DECISION_AUTO_REMEDIATE


def test_out_of_scope_architecture_change_escalates():
    assert classify_failure("architecture_decision") == DECISION_ESCALATE
    assert classify_failure("lint", in_current_mission=False) == DECISION_ESCALATE


def test_builder_cannot_count_self_review_as_independent():
    with pytest.raises(ReviewReceiptError):
        _assert_contexts_separate("same-session", "same-session")


def test_review_receipt_binds_exact_head(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    assert (
        validate_receipt(
            receipt,
            repo_root=repo,
            current_head=head,
            expected_base=base,
            expected_mission_id="FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
        )["reviewed_head_sha"]
        == head
    )


def test_stale_review_receipt_is_rejected(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    (repo / "Makefile").write_text("all:\n\t@echo newer\n", encoding="utf-8")
    _git(repo, "add", "Makefile")
    _git(repo, "commit", "-qm", "new builder commit")
    new_head = _git(repo, "rev-parse", "HEAD")
    with pytest.raises((ReviewReceiptError, ExactHeadError)):
        validate_receipt(receipt, repo_root=repo, current_head=new_head, expected_base=base)


def test_blocking_finding_rejects_merge_ready(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        result="FAIL",
        finding={
            "severity": "P1",
            "title": "defect",
            "path": "Makefile",
            "line": 1,
            "summary": "blocking",
        },
    )
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {"verdict": "PASS", "base_sha": base, "head_sha": head, "current_head_sha": head}
        ),
        encoding="utf-8",
    )
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--remote-ci-status",
            "GREEN",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--required-pr-governance",
            "PASS",
        ]
    )
    assert agent_workflow.merge_ready_command(args) == 1


def test_unknown_review_state_rejects_merge_ready():
    with pytest.raises(ReviewReceiptError):
        validate_review_result({"result": "UNKNOWN", "findings": []})


def test_missing_review_rejects_merge_ready(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {"verdict": "PASS", "base_sha": base, "head_sha": head, "current_head_sha": head}
        ),
        encoding="utf-8",
    )
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(tmp_path / "missing.json"),
            "--remote-ci-status",
            "GREEN",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--required-pr-governance",
            "PASS",
        ]
    )
    assert agent_workflow.merge_ready_command(args) == 1


def test_final_clean_review_can_reach_merge_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {"verdict": "PASS", "base_sha": base, "head_sha": head, "current_head_sha": head}
        ),
        encoding="utf-8",
    )
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--pr",
            "1",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--required-pr-governance",
            "PASS",
        ]
    )
    monkeypatch.setattr(
        agent_workflow,
        "_remote_pr_check",
        lambda pr_number, *, expected_head, **_kwargs: (
            agent_workflow.GateCheck("remote-required-ci", "PASS", "mock exact-head CI"),
            {"pr": pr_number, "verdict": "PASS", "head_sha": expected_head},
        ),
    )
    assert agent_workflow.merge_ready_command(args) == 0


@pytest.mark.parametrize("forbidden_status", ["PASS", "UNKNOWN"])
def test_non_no_forbidden_side_effect_status_rejects_merge_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forbidden_status: str,
):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {"verdict": "PASS", "base_sha": base, "head_sha": head, "current_head_sha": head}
        ),
        encoding="utf-8",
    )
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--pr",
            "1",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            forbidden_status,
        ]
    )
    monkeypatch.setattr(
        agent_workflow,
        "_remote_pr_check",
        lambda _pr_number, *, expected_head, **_kwargs: (
            agent_workflow.GateCheck("remote-required-ci", "PASS", "mock exact-head CI"),
            {"verdict": "PASS", "head_sha": expected_head},
        ),
    )
    assert agent_workflow.merge_ready_command(args) == 1


def test_invalid_task_type_caught_locally():
    errors = validate_pr_metadata(
        _body(task_type="not-a-task"), ["scripts/devops/agent_workflow.py"]
    )
    assert any("TASK_TYPE_INVALID" in error for error in errors)


def test_invalid_workflow_class_caught_locally():
    errors = validate_pr_metadata(
        _body(workflow_class="MAYBE"), ["scripts/devops/agent_workflow.py"]
    )
    assert any("CLASS_INVALID" in error for error in errors)


def test_invalid_documentation_impact_caught_locally():
    body = _body().replace("| Capability changed? | yes |", "| Capability changed? | maybe |")
    errors = validate_pr_metadata(body, ["scripts/devops/agent_workflow.py"])
    assert any("DOCUMENTATION_IMPACT_INVALID" in error for error in errors)


def test_global_metadata_contract_does_not_apply_mission_scope_allowlist():
    assert validate_pr_metadata(_body(), ["src/application.js"]) == []
    assert validate_pr_metadata(_body(), ["src/application.js"], enforce_mission_scope=True)


def test_merge_ready_without_pr_context_fails_closed(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {"verdict": "PASS", "base_sha": base, "head_sha": head, "current_head_sha": head}
        ),
        encoding="utf-8",
    )
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1",
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--remote-ci-status",
            "GREEN",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--required-pr-governance",
            "PASS",
        ]
    )
    assert agent_workflow.merge_ready_command(args) == 1


def test_local_preflight_rejects_pass_for_different_scanned_head(tmp_path: Path):
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps(
            {
                "verdict": "PASS",
                "base_sha": "1" * 40,
                "head_sha": "2" * 40,
                "current_head_sha": "3" * 40,
            }
        ),
        encoding="utf-8",
    )
    check = agent_workflow._local_preflight_check(local, "1" * 40, "3" * 40)
    assert check.status == "FAIL"
    assert "scanned HEAD" in check.message


def test_remote_merge_check_rejects_pending_pr_review_evidence(
    monkeypatch: pytest.MonkeyPatch,
):
    head = "2" * 40
    fake_result = SimpleNamespace(
        findings=[],
        verdict="PASS",
        pr=SimpleNamespace(head_sha=head, body=_body()),
    )
    monkeypatch.setattr("scripts.devops.pr_ready_check.evaluate", lambda _pr_number: fake_result)
    check, evidence = agent_workflow._remote_pr_check(
        1904,
        changed_paths={"scripts/devops/agent_workflow.py"},
        expected_head=head,
    )
    assert check.status == "FAIL"
    assert "final PR body review evidence invalid" in check.message
    assert evidence["verdict"] == "FAIL"


def test_missing_report_lifecycle_caught_locally():
    errors = check_report_lifecycle_required({"docs/_reports/new.md"}, _body())
    assert errors
    assert "Report lifecycle required" in errors[0]


def test_missing_script_lifecycle_caught_locally():
    errors = check_script_lifecycle_requirement({"scripts/devops/new_checker.py"}, _body())
    assert errors
    assert "Script lifecycle missing" in errors[0]


def test_report_growth_freeze_caught_locally():
    errors = check_local_worktree_growth([Change("A", "docs/_reports/new.md")])
    assert errors
    assert "GOV-GROWTH-REPORT" in errors[0]


def test_local_and_remote_use_same_contract_source():
    preflight = (ROOT / "scripts/devops/agent_workflow_preflight.py").read_text(encoding="utf-8")
    gate = (ROOT / "scripts/ops/ai_workflow_gate.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/production-gate.yml").read_text(encoding="utf-8")
    assert "validate_ai_workflow_gate" in preflight
    assert "validate_pr_metadata" in gate
    assert "--enforce-agent-workflow-contract" in workflow


def test_reviewer_invocation_is_read_only():
    command = build_reviewer_command(
        codex_binary="codex",
        base_sha=BASE_SHA,
        output_schema=REVIEW_OUTPUT_SCHEMA,
        final_message_path=Path("/tmp/final.json"),
    )
    assert "--sandbox" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in command
    assert "--output-schema" in command
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


def test_reviewer_run_uses_separate_codex_context():
    command = build_reviewer_command(
        codex_binary="codex",
        base_sha=BASE_SHA,
        output_schema=REVIEW_OUTPUT_SCHEMA,
        final_message_path=Path("/tmp/final.json"),
    )
    assert command[:2] == ["codex", "exec"]
    assert "review" not in command
    assert "-" not in command
    with pytest.raises(ReviewReceiptError):
        _assert_contexts_separate("reviewer-1234", "reviewer-1234")


def test_new_builder_commit_invalidates_previous_review(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    assert receipt.is_file()
    (repo / "Makefile").write_text("all:\n\t@echo changed-again\n", encoding="utf-8")
    _git(repo, "add", "Makefile")
    _git(repo, "commit", "-qm", "second builder commit")
    with pytest.raises((ReviewReceiptError, ExactHeadError)):
        validate_receipt(receipt, repo_root=repo, expected_base=base)


def test_merge_ready_command_has_no_merge_operation():
    source = inspect.getsource(agent_workflow)
    assert "gh pr merge" not in source
    assert "git merge" not in source


def test_protected_stage_d_path_is_out_of_scope():
    errors = validate_mission_scope(["scripts/ops/stage_d_cycle.js"])
    assert errors
    assert "SCOPE_ESCALATE" in errors[0]


@pytest.mark.parametrize(
    "path",
    [
        "scripts/ops/helpers/db_write_guard.js",
        "scripts/ops/helpers/python_db_write_guard.py",
        "scripts/ops/helpers/python_db_write_enforcement_check.py",
    ],
)
def test_production_db_write_guard_paths_are_out_of_scope(path: str):
    errors = validate_mission_scope([path])
    assert errors
    assert "SCOPE_ESCALATE" in errors[0]
