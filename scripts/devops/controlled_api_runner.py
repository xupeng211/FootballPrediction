"""Direct API 请求形状的受控离线 Runner（AF_UNIX HTTP，绝不访问真实 Provider）。

lifecycle: permanent
不加载 API Key；没有 HTTPS/live 开关或 SDK；不跟随重定向、不自动重试、不执行模型工具。
生产出口与计费 admission 尚待独立补齐，不能用本模块冒充 qualified Reviewer。
"""

from __future__ import annotations

import argparse
from http import HTTPStatus
import http.client
import json
from pathlib import Path
import socket
import sqlite3
import stat

from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_policy import ControlError, validate_plan
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes, validate_result

MAX_RESPONSE_BYTES = 2_000_000


class UnixHTTP(http.client.HTTPConnection):
    """只建立一个 Unix-domain socket；连接数不是费用证明，实际 POST 槽才是。"""

    def __init__(self, path: Path, timeout: float):
        super().__init__("offline.invalid", timeout=timeout)
        self.socket_path = path

    def connect(self):
        """忽略环境代理/DNS，只访问显式 Unix socket。"""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.socket_path))


def _decode(raw: bytes) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ControlError("DUPLICATE_JSON_FIELD")
            value[key] = item
        return value

    return json.loads(raw, object_pairs_hook=unique)


def _openai_text(data: dict) -> str:
    """拒绝不完整或额外工具输出，只返回唯一审核文本。"""
    if data.get("status") != "completed":
        raise ControlError("INCOMPLETE_RESPONSE")
    output = data["output"]
    if any(item.get("type") not in {"reasoning", "message"} for item in output):
        raise ControlError("UNEXPECTED_TOOL_CALL")
    messages = [item for item in output if item.get("type") == "message"]
    if len(messages) != 1 or messages[0].get("status") != "completed":
        raise ControlError("INVALID_RESPONSE")
    content = messages[0]["content"]
    if len(content) != 1 or content[0].get("type") != "output_text":
        raise ControlError("INVALID_RESPONSE")
    return content[0]["text"]


def _result(raw: bytes, plan: dict) -> None:
    """验证 Provider envelope、总 Usage（含 reasoning）与现有结果合同；不授予资格。"""
    data = _decode(raw)
    policy = plan["policy"]
    if data.get("model") != policy["model"]:
        raise ControlError("MODEL_MISMATCH")
    usage = data.get("usage")
    if not isinstance(usage, dict):
        raise ControlError("USAGE_UNKNOWN")
    if policy["provider"] == "openai":
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        text = _openai_text(data)
    else:
        input_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
        choices = data["choices"]
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ControlError("INCOMPLETE_RESPONSE")
        message = choices[0]["message"]
        if message.get("tool_calls"):
            raise ControlError("UNEXPECTED_TOOL_CALL")
        text = message["content"]
    if (
        type(input_tokens) is not int
        or type(output_tokens) is not int
        or not 0 <= input_tokens <= policy["input_cap"]
        or not 0 <= output_tokens <= policy["output_cap"]
        or type(usage.get("total_tokens")) is not int
        or usage["total_tokens"] != input_tokens + output_tokens
    ):
        raise ControlError("USAGE_UNKNOWN_OR_EXCEEDS_RESERVATION")
    validate_result(_decode(text.encode()))


def _exchange(connection: UnixHTTP, plan: dict) -> bytes:
    """执行唯一 POST 并检查 HTTP 完整性，不实现任何重试。"""
    connection.request(
        "POST",
        plan["policy"]["path"],
        body=canonical_json(plan["body"]),
        headers={"Content-Type": "application/json", "Connection": "close"},
    )
    response = connection.getresponse()
    if response.status != HTTPStatus.OK:
        raise ControlError("HTTP_STATUS_REJECTED")
    expected_length = response.length
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if expected_length is not None and len(raw) < expected_length:
        raise http.client.IncompleteRead(raw, expected_length - len(raw))
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ControlError("RESPONSE_TOO_LARGE")
    return raw


def execute(
    budget: Budget, identity: str, slot: int, plan: dict, *, socket_path: Path, timeout: float = 5.0
) -> dict:
    """每次物理 POST 前先持久 claim；任一异常不退款、不补发、不产正式 Receipt。"""
    plan = validate_plan(plan)
    path = Path(socket_path).absolute()
    if path.is_symlink() or not stat.S_ISSOCK(path.stat().st_mode):
        raise ControlError("OFFLINE_SOCKET_REQUIRED")
    budget.claim(identity, slot, plan)
    raw = b""
    connection = UnixHTTP(path, timeout)
    try:
        raw = _exchange(connection, plan)
        _result(raw, plan)
    except BaseException as exc:
        # 不写入 str(exc)、raw stdout/stderr 或 Provider 原始响应。
        category = "RESPONSE_INVALID"
        if isinstance(exc, TimeoutError):
            category = "TIMEOUT"
        elif isinstance(exc, (OSError, http.client.HTTPException)):
            category = "TRANSPORT_FAILURE"
        budget.finish(
            identity, slot, complete=False, category=category, response_sha256=sha256_bytes(raw)
        )
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise ControlError(category) from None
    else:
        budget.finish(
            identity,
            slot,
            complete=True,
            category="VALID_OFFLINE_RESPONSE",
            response_sha256=sha256_bytes(raw),
        )
    finally:
        connection.close()
    return budget.evidence(identity)


def main() -> int:
    """内部离线入口；任务预算必须由 Controller 事先创建。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--slot", required=True, type=int)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--offline-socket", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = execute(
            Budget(args.state_root),
            args.task,
            args.slot,
            _decode(args.plan.read_bytes()),
            socket_path=args.offline_socket,
        )
    except (ControlError, OSError, ValueError, sqlite3.Error):
        print("CONTROLLED_API_EXECUTION_REJECTED")
        return 1
    print(canonical_json(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
