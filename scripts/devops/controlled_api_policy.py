"""受控 Direct API 离线候选的固定请求与条件性价格策略。

lifecycle: permanent
不提供 live admission；价格快照不是供应商锁价保证，也不是既有 Reviewer 资格。
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes, validate_sha

CHANNEL = "controlled-direct-api/offline-v1"
PRICE_STATUS = "CONDITIONAL_SNAPSHOT_NOT_PROVIDER_GUARANTEE"
MAX_MISSION_LENGTH = 128
SOURCE_FIELDS = {"repository", "mission", "base", "head", "diff_sha256", "scope_sha256"}


class ControlError(ValueError):
    """仅含安全错误码，不嵌入请求、响应、异常或凭据。"""


def positive_int(value: object) -> int:
    """拒绝 bool、浮点、负数及 SQLite 不支持的整型。"""
    if type(value) is not int or not 0 < value < 2**60:
        raise ControlError("INVALID_POSITIVE_INTEGER")
    return value


def source_identity(source: dict) -> str:
    """由完整候选身份生成稳定任务键；重新启动不能换 run id 重获预算。"""
    if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
        raise ControlError("INVALID_SOURCE_BINDING")
    if source["repository"] != "xupeng211/FootballPrediction":
        raise ControlError("INVALID_REPOSITORY")
    if (
        not isinstance(source["mission"], str)
        or not 1 <= len(source["mission"]) <= MAX_MISSION_LENGTH
    ):
        raise ControlError("INVALID_MISSION")
    for name in ("base", "head", "diff_sha256", "scope_sha256"):
        value = source[name]
        if validate_sha(value, name=name, length=40 if name in {"base", "head"} else 64) != value:
            raise ControlError("NONCANONICAL_SOURCE")
    # 同候选不能通过新 mission/scope/run 名称分割预算；首次入账仍冻结全部字段。
    return sha256_bytes(
        canonical_json({key: source[key] for key in ("repository", "base", "head", "diff_sha256")})
    )


@dataclass(frozen=True)
class Profile:
    """费用单位：USD 的十亿分之一；费率是保守快照，不是金额硬帽证明。"""

    model: str
    path: str
    context: int
    output_limit: int
    input_nano_usd: int
    output_nano_usd: int
    source_url: str


PROFILES = {
    # 全窗口输入预留；OpenAI 纳入长上下文 2x、cache write 1.25x、输出 1.5x。
    "openai": Profile(
        "gpt-5.6-terra",
        "/v1/responses",
        1_050_000,
        128_000,
        5_000,
        18_000,
        "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
    ),
    "deepseek": Profile(
        "deepseek-flash",
        "/chat/completions",
        1_048_576,
        393_216,
        300,
        1_200,
        "https://api-docs.deepseek.com/quick_start/pricing",
    ),
}


def prepare(provider: str, prompt: str, max_output: int) -> dict:
    """只构造文本、无工具、非流式请求；不估算 tokenizer 或依赖 Usage 退款。"""
    if provider not in PROFILES:
        raise ControlError("UNKNOWN_MODEL_OR_PRICE")
    profile = PROFILES[provider]
    positive_int(max_output)
    if max_output > profile.output_limit or not isinstance(prompt, str) or not prompt.strip():
        raise ControlError("INVALID_REQUEST")
    # 限制本地内存；真正的计费输入预留用整个 context，覆盖 framing/tokenizer 差异。
    if len(prompt.encode()) > profile.context:
        raise ControlError("INPUT_TOO_LARGE")
    if provider == "openai":
        body = {
            "model": profile.model,
            "input": prompt,
            "max_output_tokens": max_output,
            "reasoning": {"effort": "medium"},
            "service_tier": "default",
            "truncation": "disabled",
            "store": False,
            "stream": False,
        }
    else:
        body = {
            "model": profile.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output,
            "thinking": {"type": "enabled"},
            "stream": False,
        }
    policy = {
        "channel": CHANNEL,
        "price_status": PRICE_STATUS,
        "provider": provider,
        "model": profile.model,
        "path": profile.path,
        "input_cap": profile.context,
        "output_cap": max_output,
        "input_nano_usd": profile.input_nano_usd,
        "output_nano_usd": profile.output_nano_usd,
        "source_url": profile.source_url,
    }
    return {
        "body": body,
        "policy": policy,
        "request_sha256": sha256_bytes(canonical_json(body)),
        "policy_sha256": sha256_bytes(canonical_json(policy)),
        "reserve_tokens": profile.context + max_output,
        "reserve_nano_usd": profile.context * profile.input_nano_usd
        + max_output * profile.output_nano_usd,
    }


def validate_plan(plan: dict) -> dict:
    """从固定策略重算，不信任调用者提供的费用、模型、请求字段或摘要。"""
    try:
        provider = plan["policy"]["provider"]
        body = plan["body"]
        prompt = body["input"] if provider == "openai" else body["messages"][0]["content"]
        expected = prepare(provider, prompt, plan["policy"]["output_cap"])
        if canonical_json(plan) == canonical_json(expected):
            return expected
    except (KeyError, TypeError, IndexError, ValueError):
        pass
    raise ControlError("INVALID_REQUEST_PLAN")
