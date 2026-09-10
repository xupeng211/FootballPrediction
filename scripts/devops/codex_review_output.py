"""Codex JSONL completion parsing for the independent-review wrapper.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

import json
from typing import Any

from scripts.devops.codex_review_provenance import ReviewReceiptError


def parse_json_lines(raw: bytes) -> list[dict[str, Any]]:
    """Parse Codex JSONL without exposing its event contents."""

    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReviewReceiptError(f"Codex JSONL 第 {line_no} 行无效: {exc}") from exc
        if isinstance(value, dict):
            events.append(value)
    return events


def reviewer_invocation_id(events: list[dict[str, Any]], thread_id_re: Any) -> str:
    """Extract one Codex thread identity from its started event."""

    for event in events:
        if event.get("type") != "thread.started":
            continue
        candidate = event.get("thread_id") or event.get("threadId")
        if isinstance(candidate, str) and thread_id_re.fullmatch(candidate):
            return candidate
    raise ReviewReceiptError("Codex JSONL 缺少独立 thread.started invocation id")


def assert_successful_completion(events: list[dict[str, Any]], final_text: str) -> None:
    """Bind the saved final message to a completed Codex turn in raw JSONL."""

    if any(event.get("type") == "turn.failed" for event in events):
        raise ReviewReceiptError("Codex JSONL 包含 turn.failed；拒绝 review receipt")
    completed_turns = [
        index for index, event in enumerate(events) if event.get("type") == "turn.completed"
    ]
    if len(completed_turns) != 1:
        raise ReviewReceiptError("Codex JSONL 必须包含恰好一个 turn.completed")
    messages = [
        (index, event.get("item", {}).get("text"))
        for index, event in enumerate(events)
        if event.get("type") == "item.completed"
        and event.get("item", {}).get("type") == "agent_message"
    ]
    if not messages or not isinstance(messages[-1][1], str):
        raise ReviewReceiptError("Codex JSONL 必须包含 completed agent_message")
    final_index, final_message = messages[-1]
    if final_index > completed_turns[0] or final_message != final_text:
        raise ReviewReceiptError("Codex raw completed agent_message 与 final message 不一致")
