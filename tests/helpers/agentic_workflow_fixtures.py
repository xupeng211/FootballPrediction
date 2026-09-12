"""Fixtures for Agentic Workflow V1 receipt and PR-contract tests.

lifecycle: test-fixture
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING

from scripts.devops.codex_review_contract import (
    REVIEW_MODEL_FLAG,
    _canonical_json,
    build_reviewer_command,
    review_challenge,
    reviewer_selectors_from_command,
)
from scripts.devops.codex_review_provenance import observe_codex_cli_version
from scripts.devops.codex_review_receipt import (
    RECEIPT_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION_V1,
    WRAPPER_NAME,
    _codex_prompt,
    diff_sha256,
    git_blob_sha256,
    sha256_file,
)
from scripts.ops.helpers.agent_workflow_contract import (
    load_mission_scope_file,
    mission_scope_sha256,
)

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[2]


def _canonical_sha256(value: object) -> str:
    """Hash one canonical JSON document exactly like the receipt writer does."""

    return hashlib.sha256(_canonical_json(value)).hexdigest()


BASE_SHA = "1" * 40
MISSION_ID = "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1"
MISSION_SCOPE_PATH = "docs/agentic/missions/current.json"


def mission_scope_payload(*, mission_id: str = MISSION_ID) -> dict[str, object]:
    """Return a minimal explicit scope for synthetic receipt tests."""

    return {
        "schema_version": "agentic-mission-scope/v1",
        "mission_id": mission_id,
        "task_type": "workflow-governance",
        "workflow_class": "STRICT",
        "authorized_paths": ["Makefile"],
        "authorized_prefixes": [],
        "excluded_paths": [],
        "excluded_prefixes": [],
        "excluded_tokens": [],
        "protected_invariants": ["synthetic test repository only"],
        "forbidden_side_effects": ["no external side effects"],
    }


def body(
    *,
    mission_id: str = MISSION_ID,
    task_type: str = "workflow-governance",
    workflow_class: str = "STRICT",
    review_result: str = "PENDING",
    reviewed_sha: str = BASE_SHA,
    provider: str = "codex-independent-reviewer (pending)",
) -> str:
    return f"""## Summary

This is a bounded workflow infrastructure test change with no business runtime mutation.

## Scope

| Field | Value |
| --- | --- |
| Task type | {task_type} |
| Workflow class | {workflow_class} |
| Mission ID | {mission_id} |
| Mission scope contract | `{MISSION_SCOPE_PATH}` |
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

Revert this infrastructure change; business runtime files are outside the explicit mission scope.

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
| Provider | {provider} |
| Reviewed full SHA | {reviewed_sha} |
| Result | {review_result} |
| Timestamp | 2026-09-10T00:00:00Z |
"""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path, *, wrapper_content: str | None = None) -> tuple[Path, str, str]:
    """Build a synthetic repo that also carries the real reviewer wrapper.

    The wrapper is committed at base and left untouched at head, so the exact
    `base...head` diff stays limited to `Makefile` while the receipt can still
    be git-anchored to a real wrapper blob.  ``wrapper_content`` substitutes an
    older wrapper, which models a legitimate later tooling upgrade.
    """

    repo = tmp_path / "review-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Agent Workflow Test")
    (repo / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    schema_path = repo / "schemas" / "agentic" / "codex_review_result.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text('{"type":"object"}\n', encoding="utf-8")
    scope_path = repo / MISSION_SCOPE_PATH
    scope_path.parent.mkdir(parents=True)
    scope_path.write_text(
        json.dumps(mission_scope_payload(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    wrapper_path = repo / WRAPPER_NAME
    wrapper_path.parent.mkdir(parents=True)
    wrapper_path.write_text(
        wrapper_content
        if wrapper_content is not None
        else (ROOT / WRAPPER_NAME).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        "Makefile",
        "schemas/agentic/codex_review_result.schema.json",
        MISSION_SCOPE_PATH,
        WRAPPER_NAME,
    )
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "Makefile").write_text("all:\n\t@echo workflow\n", encoding="utf-8")
    _git(repo, "add", "Makefile")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, base, head


def _apply_overrides(document: dict[str, object], overrides: dict[str, object]) -> None:
    """Merge one level of test overrides into a receipt before it is sealed."""

    for key, value in overrides.items():
        current = document.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            current.update(value)
        else:
            document[key] = value


def write_valid_receipt(
    tmp_path: Path,
    repo: Path,
    base: str,
    head: str,
    *,
    mission_id: str = MISSION_ID,
    result: str = "PASS",
    finding: dict[str, object] | None = None,
    legacy_schema: bool = False,
    overrides: dict[str, object] | None = None,
    command_transform: Callable[[list[str]], list[str]] | None = None,
) -> Path:
    """Write one sealed receipt.

    ``command_transform`` rewrites the recorded reviewer argv before it is
    hashed and sealed, so a test can build a receipt whose argv stays
    hash-consistent with itself while contradicting the rest of the evidence.
    """
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    raw = evidence / "raw.jsonl"
    final = evidence / "final.json"
    stderr = evidence / "stderr.log"
    reviewer_id = "reviewer-1234"
    worktree = tmp_path / "review-worktree"
    _git(repo, "worktree", "add", "--detach", str(worktree), head)
    scope_path = repo / MISSION_SCOPE_PATH
    mission_scope = load_mission_scope_file(
        scope_path, repo_root=repo, expected_mission_id=mission_id
    )
    scope_hash = mission_scope_sha256(scope_path)
    prompt = _codex_prompt(
        mission_id=mission_id,
        base_sha=base,
        head_sha=head,
        mission_scope=mission_scope,
        mission_scope_path=MISSION_SCOPE_PATH,
        mission_scope_sha256=scope_hash,
    )
    final_document = {
        "result": result,
        "review_challenge": review_challenge(
            mission_id=mission_id,
            base_sha=base,
            head_sha=head,
            mission_scope_sha256=scope_hash,
        ),
        "findings": [finding] if finding else [],
    }
    final_text = json.dumps(final_document)
    final.write_text(final_text, encoding="utf-8")
    raw.write_text(
        "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": reviewer_id}),
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
    schema_path = worktree / "schemas" / "agentic" / "codex_review_result.schema.json"
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
    codex_binary = Path(shutil.which("codex")).resolve()
    receipt: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA_VERSION_V1 if legacy_schema else RECEIPT_SCHEMA_VERSION,
        "contract_schema_version": "agentic-engineering-workflow/v1",
        "assurance_model": "engineering_independent_review",
        "hostile_same_uid_forge_resistance": False,
        "review_engine": "codex",
        "review_role": "independent_reviewer",
        "base_sha": base,
        "reviewed_head_sha": head,
        "review_challenge": review_challenge(
            mission_id=mission_id,
            base_sha=base,
            head_sha=head,
            mission_scope_sha256=scope_hash,
        ),
        "diff_sha256": diff_sha256(repo, base, head),
        "mission_id": mission_id,
        "mission_scope_path": MISSION_SCOPE_PATH,
        "mission_scope_sha256": scope_hash,
        "review_started_at": "2026-09-10T00:00:00Z",
        "review_completed_at": "2026-09-10T00:01:00Z",
        "finding_counts_by_severity": counts,
        "blocking_findings": sum(counts[key] for key in ("P0", "P1", "P2")),
        "review_result": result,
        "findings": normalized_findings,
        "reviewer_invocation_id": reviewer_id,
        "builder_context_id": "builder-5678",
        "reviewer_context_id": reviewer_id,
        "reviewer_context_separate_from_builder": True,
        "reviewer_read_only": True,
        "isolation": {
            "fresh_process": True,
            "ephemeral_session": True,
            "sandbox": "read-only",
            "detached_worktree": True,
            "worktree_head_sha": head,
            "worktree_path": str(worktree),
            "worktree_clean_before": True,
            "worktree_clean_after": True,
            "source_mutation_detected": False,
        },
        "provenance": {
            "writer": WRAPPER_NAME,
            "integrity_only": True,
            "wrapper_sha256": git_blob_sha256(repo, head, WRAPPER_NAME),
            "command_sha256": "0" * 64,
            "codex_binary": str(codex_binary),
            "codex_binary_sha256": sha256_file(codex_binary),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
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
        codex_binary=str(codex_binary),
        base_sha=base,
        output_schema=schema_path,
        final_message_path=final,
    )
    if command_transform is not None:
        command = command_transform(list(command))
    if legacy_schema:
        # Historical v1 receipts predate explicit model pinning: their recorded
        # command carried no model selector and no model_provenance block.
        legacy_command = list(command)
        model_index = legacy_command.index(REVIEW_MODEL_FLAG)
        del legacy_command[model_index : model_index + 2]
        receipt["provenance"]["command_sha256"] = _canonical_sha256(legacy_command)
    else:
        receipt["provenance"]["reviewer_command"] = list(command)
        receipt["provenance"]["command_sha256"] = _canonical_sha256(command)
        review_model, review_effort = reviewer_selectors_from_command(command)
        receipt["model_provenance"] = {
            "review_model": review_model,
            "review_reasoning_effort": review_effort,
            "codex_cli_version": observe_codex_cli_version(codex_binary),
            "model_source": "codex_exec_model_flag",
            "reasoning_effort_source": "codex_config_override",
            "cli_version_source": "observed_codex_version_stdout",
            "derived_from_recorded_command": True,
        }
    if overrides:
        _apply_overrides(receipt, overrides)
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
