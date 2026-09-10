#!/usr/bin/env python3
"""Stable prompt, result and command contract for Codex independent review."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from scripts.devops.codex_review_provenance import ReviewReceiptError
from scripts.devops.exact_head import normalize_full_sha
from scripts.ops.helpers.agent_workflow_contract import (
    ALL_REVIEW_SEVERITIES,
    BLOCKING_REVIEW_SEVERITIES,
    REVIEW_RESULT_FAIL,
    REVIEW_RESULT_PASS,
    REVIEW_ROLE_INDEPENDENT,
    MissionScope,
    is_blocking_severity,
)

MIN_FENCED_JSON_LINES = 3
REVIEW_CHALLENGE_VERSION = "codex-independent-review-challenge/v2"


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return SHA-256 for one in-memory evidence byte string."""

    return hashlib.sha256(value).hexdigest()


def review_challenge(
    *, mission_id: str, base_sha: str, head_sha: str, mission_scope_sha256: str
) -> str:
    """Derive a target-specific challenge that prevents receipt rebinding."""

    return sha256_bytes(
        f"{REVIEW_CHALLENGE_VERSION}\n{mission_id}\n{base_sha}\n{head_sha}\n{mission_scope_sha256}\n".encode()
    )


def parse_timestamp(value: object, field: str) -> datetime:
    """Parse one timezone-aware RFC3339 timestamp from review evidence."""

    if not isinstance(value, str) or not value:
        raise ReviewReceiptError(f"{field} 缺少 RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewReceiptError(f"{field} 不是有效 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReviewReceiptError(f"{field} 必须包含 timezone")
    return parsed


def parse_final_message(text: str) -> dict[str, Any]:
    """Parse the reviewer's schema-constrained final JSON message."""

    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= MIN_FENCED_JSON_LINES:
            stripped = "\n".join(lines[1:-1]).strip()
    try:
        result = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ReviewReceiptError("Codex final message 必须是 schema 约束的 JSON 对象") from exc
    if not isinstance(result, dict):
        raise ReviewReceiptError("Codex final message 必须是 JSON object")
    return result


def validate_review_result(
    result: dict[str, Any],
) -> tuple[dict[str, int], int, str, list[dict[str, Any]]]:
    """Derive counts from reviewer findings; never trust caller-supplied counts."""

    raw_findings = result.get("findings")
    if not isinstance(raw_findings, list):
        raise ReviewReceiptError("review result.findings 必须是数组")
    normalized: list[dict[str, Any]] = []
    counts = Counter(dict.fromkeys(ALL_REVIEW_SEVERITIES, 0))
    for index, finding in enumerate(raw_findings):
        if not isinstance(finding, dict):
            raise ReviewReceiptError(f"finding[{index}] 必须是 object")
        severity = str(finding.get("severity") or "").upper()
        if severity not in ALL_REVIEW_SEVERITIES:
            raise ReviewReceiptError(f"finding[{index}] severity 必须为 P0/P1/P2/P3")
        title = str(finding.get("title") or "").strip()
        summary = str(finding.get("summary") or "").strip()
        if not title or not summary:
            raise ReviewReceiptError(f"finding[{index}] 缺少 title/summary")
        path = finding.get("path")
        if path is not None and not isinstance(path, str):
            raise ReviewReceiptError(f"finding[{index}].path 必须是字符串或 null")
        line = finding.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            raise ReviewReceiptError(f"finding[{index}].line 必须是正整数或 null")
        counts[severity] += 1
        normalized.append(
            {
                "severity": severity,
                "title": title,
                "path": path,
                "line": line,
                "summary": summary,
                "blocking": is_blocking_severity(severity),
            }
        )
    blocking = sum(counts[severity] for severity in BLOCKING_REVIEW_SEVERITIES)
    review_result = str(result.get("result") or "").upper()
    if review_result not in {REVIEW_RESULT_PASS, REVIEW_RESULT_FAIL}:
        raise ReviewReceiptError("review result.result 必须是 PASS 或 FAIL")
    if (review_result == REVIEW_RESULT_PASS) != (blocking == 0):
        raise ReviewReceiptError("review result 与 P0/P1/P2 blocking finding 数量不一致")
    return dict(counts), blocking, review_result, normalized


def build_review_prompt(
    *,
    mission_id: str,
    base_sha: str,
    head_sha: str,
    mission_scope: MissionScope,
    mission_scope_path: str,
    mission_scope_sha256: str,
) -> str:
    """Build the auditable exact-head prompt supplied to the fresh reviewer."""

    challenge = review_challenge(
        mission_id=mission_id,
        base_sha=base_sha,
        head_sha=head_sha,
        mission_scope_sha256=mission_scope_sha256,
    )
    scope_json = json.dumps(mission_scope.to_dict(), ensure_ascii=False, sort_keys=True)
    return f"""你是 FOOTBALLPREDICTION 的 {REVIEW_ROLE_INDEPENDENT}。

这是一次全新的 Codex reviewer invocation；你不能使用 Builder 的思路、私有草稿、自证或结论作为证据。
只审查 detached read-only worktree 中的真实代码、完整 diff、测试与仓库治理合同。

MISSION_ID={mission_id}
BASE_SHA={base_sha}
REVIEW_HEAD_SHA={head_sha}
MISSION_SCOPE_PATH={mission_scope_path}
MISSION_SCOPE_SHA256={mission_scope_sha256}
REVIEW_ENGINE=CODEX
REVIEW_ROLE=INDEPENDENT_REVIEWER
ASSURANCE_MODEL=ENGINEERING_INDEPENDENT_REVIEW
REVIEW_CHALLENGE={challenge}

当前 mission scope contract（这是本次审查必须使用的唯一授权范围）：
```json
{scope_json}
```

这是工程独立性 review，不是 cryptographic attestation：同一 OS uid 的恶意
Builder 理论上可能篡改本地 evidence，这个 residual risk 已由 Owner 接受。
不要把这个已接受的 same-uid 风险本身报告为 blocker；仍必须严格执行 fresh
context、exact HEAD、clean worktree、read-only 和 self-review 排除。

审查目标：
1. 先读取 AGENTS.md 的 Agentic Engineering Workflow V1 入口、docs/AGENT_WORKFLOW.md 的第 11 节，以及相关 governance source-of-truth；使用针对性 sed/rg，不要把整份长文档回显到上下文。
2. 用 `git diff --stat`、`git diff --name-only {base_sha}...{head_sha}` 和针对性 diff 检查所有本 mission 的变更；优先审查实现、schema、CI、测试和与其直接相关的文档，不要输出完整 diff。
3. 将上面给出的 mission scope contract 作为本次授权边界：每一个 changed path 必须命中 authorized paths/prefixes 且不命中 excluded paths/prefixes/tokens；排除项优先。只审查当前 mission 变更；Stage D、PR #1903、生产/provider/ledger 路径是保护边界。
4. P0=security/destructive/authorization/production corruption；P1=correctness/invariant/data-loss/provider-request risk；
   P2=significant robustness/recoverability/observability/governance defect；P3=non-blocking maintainability。
5. P0/P1/P2 阻塞 merge，P3 不阻塞。只报告当前 mission 内可以清楚归因的 finding；需要新 scope、产品要求、架构决定、Chief Engineer Gate、
   protected invariant 语义变化或授权边界变化时，按 blocking finding 报告。
6. 不修改任何文件，不写 Builder worktree，不 commit、不 push、不 merge、不调用 network/provider/DB/生产命令。

最终回复必须只包含下面 schema 形状的 JSON（不要 Markdown、不要隐藏推理、不要长篇过程日志）：
{{
  "result": "PASS" | "FAIL",
  "review_challenge": "{challenge}",
  "findings": [
    {{"severity":"P0|P1|P2|P3","title":"简短标题","path":"repo/path 或 null","line":1,"summary":"适合普通 code review 的可审计说明"}}
  ]
}}
没有 P0/P1/P2 时 result=PASS；存在任一 P0/P1/P2 时 result=FAIL。"""


def build_reviewer_command(
    *,
    codex_binary: str,
    base_sha: str,
    output_schema: Path,
    final_message_path: Path,
) -> list[str]:
    """Build the only supported isolated reviewer invocation."""

    normalize_full_sha(base_sha, role="review base SHA")
    return [
        codex_binary,
        "exec",
        "-c",
        'model_reasoning_effort="medium"',
        "--sandbox",
        "read-only",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--output-schema",
        str(output_schema),
        "--output-last-message",
        str(final_message_path),
    ]
