"""Direct JSON 请求、费用与响应的确定性处理；不发送 HTTP 或写入状态。

lifecycle: permanent
owner: engineering workflow governance
"""

# backend 参数保留原模块的动态策略、异常类型与可替换符号；原公开入口仍在原模块。
# ruff: noqa: TRY300, TRY301
from __future__ import annotations

from typing import Any


def payload(
    backend, prompt: str, max_output: int, *, qualification=False, synthesis=False
) -> bytes:
    """冻结全部实际发送字段；正文 bytes 限制不充当 token 计数。"""
    if (
        type(max_output) is not int
        or not 1 <= max_output <= backend.POLICY["max_output"]
        or max_output > backend.POLICY["server_output_limit"]
    ):
        raise backend.DirectError("OUTPUT_CAPACITY")
    if not isinstance(prompt, str) or len(prompt.encode()) > backend.MAX_PROMPT_BYTES:
        raise backend.DirectError("PROMPT_BYTE_CAPACITY")
    # 完整正文限制是条件性费用估算的前提，不是 Provider 计费 Token 保证。
    body = backend.canonical_json(
        {
            "model": backend.MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": backend.QUALIFICATION_SYSTEM
                    if qualification
                    else backend.SYNTHESIS_SYSTEM
                    if synthesis
                    else backend.SYSTEM,
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_output,
            "thinking": {"type": "disabled"},
            "reasoning_effort": "none",
            "stream": False,
            "response_format": {"type": "json_object"},
        }
    )

    if len(body) > backend.MAX_PROMPT_BYTES:
        raise backend.DirectError("REQUEST_BODY_CAPACITY")
    return body


def request_cost(backend, body: bytes, snapshot=None) -> int:
    """按局部 Tokenizer 条件估算和实际 max_tokens 计算整数费用预留。

    40,003 来自审计的全正文包络，不是 bytes/token 等式；每次预留全部输出。
    价格取报价的 peak cache miss，逐请求向上取整到 micro 原币。
    模型容量、事后 usage 检查和资源合同仍使用 context_capacity。
    """
    value = backend.json.loads(body)
    if value.get("method") == "GET":
        if (
            set(value) != {"method", "endpoint", "kind"}
            or value["endpoint"] not in backend.CONTROL_URLS
            or value["kind"] not in {"price", "models", "balance_start", "balance_end"}
            or value["endpoint"]
            != (
                backend.price_url(snapshot["currency"] if snapshot else "USD")
                if value["kind"] == "price"
                else "https://api.deepseek.com/models"
                if value["kind"] == "models"
                else "https://api.deepseek.com/user/balance"
            )
        ):
            raise backend.DirectError("CONTROL_REQUEST_POLICY")
        return 0
    if backend.sha256_bytes(backend.canonical_json(backend.POLICY)) != backend.POLICY_SHA:
        raise backend.DirectError("POLICY_CHANGED")
    try:
        if body != backend.payload(
            value["messages"][1]["content"],
            value["max_tokens"],
            qualification=value["messages"][0]["content"] == backend.QUALIFICATION_SYSTEM,
            synthesis=value["messages"][0]["content"] == backend.SYNTHESIS_SYSTEM,
        ):
            raise backend.DirectError("REQUEST_FORMAT")
    except (KeyError, IndexError, TypeError):
        raise backend.DirectError("REQUEST_FORMAT") from None
    if (
        value.get("model") != backend.MODEL
        or value.get("thinking") != {"type": "disabled"}
        or value.get("reasoning_effort") != "none"
        or value.get("stream") is not False
        or type(value.get("max_tokens")) is not int
        or not 1 <= value["max_tokens"] <= backend.POLICY["max_output"]
    ):
        raise backend.DirectError("REQUEST_POLICY")
    numerator = backend.POLICY["budget_estimated_input_tokens"] * (
        snapshot["rates_micro_per_million"]["peak:input_cache_miss"]
        if snapshot
        else backend.POLICY["input_micro_usd_per_million"]
    ) + value["max_tokens"] * (
        snapshot["rates_micro_per_million"]["peak:output"]
        if snapshot
        else backend.POLICY["output_micro_usd_per_million"]
    )
    return (numerator + 999_999) // 1_000_000


def decode(backend, raw: bytes, body: bytes) -> dict[str, Any]:  # noqa: C901
    """只接受完整正常结束；usage 校验是事后检测，不冒充 Provider 硬保证。"""
    try:
        descriptor = backend.json.loads(body)
        if descriptor.get("method") == "GET":
            if descriptor["kind"] == "price":
                return {"price_sha256": backend.sha256_bytes(raw)}
            response = backend.json.loads(raw)
            if descriptor["kind"] == "models":
                if backend.MODEL not in [item["id"] for item in response["data"]]:
                    raise ValueError
            else:
                if response["is_available"] is not True:
                    raise ValueError
                for balance in response["balance_infos"]:
                    backend.balance_amount(response, balance["currency"])
                if not response["balance_infos"]:
                    raise ValueError
            return response
        response = backend.json.loads(raw)
        (choice,) = response["choices"]
        message = choice["message"]
        usage = response["usage"]
        prompt, completion = usage["prompt_tokens"], usage["completion_tokens"]
        if (
            response["model"] != backend.MODEL
            or not isinstance(response["id"], str)
            or not response["id"]
            or choice["finish_reason"] != "stop"
            or message.get("role") != "assistant"
            or message.get("tool_calls")
            or message.get("reasoning_content")
            or any(type(x) is not int or x < 0 for x in (prompt, completion))
            # 估算前提不成立时停止后续派发；事后检测不保证已发生的扣费。
            or prompt > backend.POLICY["budget_estimated_input_tokens"]
            or prompt > backend.POLICY["context_capacity"]
            or completion > backend.json.loads(body)["max_tokens"]
            or prompt + completion > backend.POLICY["context_capacity"]
            or usage["total_tokens"] != prompt + completion
            or usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0) != 0
        ):
            raise ValueError
        hit, miss = usage["prompt_cache_hit_tokens"], usage["prompt_cache_miss_tokens"]
        if any(type(x) is not int or x < 0 for x in (hit, miss)) or hit + miss != prompt:
            raise ValueError
        result = backend.json.loads(message["content"])
        if descriptor["messages"][0]["content"] not in {
            backend.QUALIFICATION_SYSTEM,
            backend.SYNTHESIS_SYSTEM,
        }:
            backend.validate_result(result)
        return result
    except Exception:
        raise backend.DirectError("INVALID_PROVIDER_RESPONSE") from None
