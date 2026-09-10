"""Fixtures for Agentic Workflow V1 receipt and PR-contract tests.

lifecycle: test-fixture
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from scripts.devops.codex_independent_review import (
    _codex_prompt,
    build_reviewer_command,
    diff_sha256,
    review_challenge,
    sha256_file,
)
from scripts.devops.codex_review_provenance import codex_home

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "1" * 40
MISSION_ID = "FOOTBALLPREDICTION_AGENTIC_ENGINEERING_WORKFLOW_V1"


def body(
    *,
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
| Provider | {provider} |
| Reviewed full SHA | {reviewed_sha} |
| Result | {review_result} |
| Timestamp | 2026-09-10T00:00:00Z |
"""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, str, str]:
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


def write_valid_receipt(
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
    reviewer_id = "reviewer-1234"
    worktree = tmp_path / "review-worktree"
    worktree.mkdir(mode=0o700)
    prompt = _codex_prompt(mission_id=MISSION_ID, base_sha=base, head_sha=head)
    final_document = {
        "result": result,
        "review_challenge": review_challenge(mission_id=MISSION_ID, base_sha=base, head_sha=head),
        "findings": [finding] if finding else [],
    }
    final_text = json.dumps(final_document)
    session_path = codex_home() / "sessions" / "2026" / "09" / "10" / f"rollout-{reviewer_id}.jsonl"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "session_meta",
                        "payload": {
                            "id": reviewer_id,
                            "session_id": reviewer_id,
                            "cwd": str(worktree),
                            "source": "cli",
                            "cli_version": "0.153.4",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": prompt}],
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "item_completed",
                            "item": {
                                "type": "AgentMessage",
                                "phase": "final_answer",
                                "content": [{"type": "Text", "text": final_text}],
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                            "content": [{"type": "output_text", "text": final_text}],
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "task_complete",
                            "last_agent_message": final_text,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    session_path.chmod(0o600)
    session_index_path = codex_home() / "session_index.jsonl"
    session_index_path.write_text(
        json.dumps({"id": reviewer_id, "thread_name": "synthetic structural test"}) + "\n",
        encoding="utf-8",
    )
    session_index_path.chmod(0o600)
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
    codex_binary = Path(shutil.which("codex")).resolve()
    receipt: dict[str, object] = {
        "schema_version": "codex-independent-review-receipt/v1",
        "contract_schema_version": "agentic-engineering-workflow/v1",
        "review_engine": "codex",
        "review_role": "independent_reviewer",
        "base_sha": base,
        "reviewed_head_sha": head,
        "review_challenge": review_challenge(mission_id=MISSION_ID, base_sha=base, head_sha=head),
        "diff_sha256": diff_sha256(repo, base, head),
        "mission_id": MISSION_ID,
        "review_started_at": "2026-09-10T00:00:00Z",
        "review_completed_at": "2026-09-10T00:01:00Z",
        "finding_counts_by_severity": counts,
        "blocking_findings": sum(counts[key] for key in ("P0", "P1", "P2")),
        "review_result": result,
        "findings": normalized_findings,
        "reviewer_invocation_id": reviewer_id,
        "builder_context_id": "builder-5678",
        "reviewer_context_id": reviewer_id,
        "reviewer_read_only": True,
        "isolation": {
            "fresh_process": True,
            "persisted_session_artifact": True,
            "sandbox": "read-only",
            "detached_worktree": True,
            "worktree_head_sha": head,
            "worktree_path": str(worktree),
        },
        "provenance": {
            "writer": "scripts/devops/codex_independent_review.py",
            "wrapper_sha256": sha256_file(ROOT / "scripts/devops/codex_independent_review.py"),
            "command_sha256": "0" * 64,
            "codex_binary": str(codex_binary),
            "codex_binary_sha256": sha256_file(codex_binary),
            "codex_session_path": str(session_path),
            "codex_session_sha256": sha256_file(session_path),
            "codex_session_final_message_sha256": hashlib.sha256(final_text.encode()).hexdigest(),
            "codex_session_thread_id": reviewer_id,
            "codex_session_index_path": str(session_index_path),
            "codex_session_index_entry_sha256": hashlib.sha256(
                session_index_path.read_bytes().splitlines()[0]
            ).hexdigest(),
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
