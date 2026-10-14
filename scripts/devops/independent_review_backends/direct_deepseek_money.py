"""Direct 原币金额与余额校验；纯确定性计算，不读取凭据或发送请求。

lifecycle: permanent
owner: engineering workflow governance
"""

# 金额事务沿用原 Backend 的异常校验结构，不改变失败语义。
# ruff: noqa: TRY301
from __future__ import annotations

from decimal import Decimal
import re


class DirectError(RuntimeError):
    """仅返回固定安全分类，不包含请求正文、Key 或 Provider 错误正文。"""


def currency(manifest):
    """旧非Standalone合同保持USD；其他币种必须显式绑定。"""
    value = manifest.get("standalone", {}).get("currency", "USD")
    if value not in {"USD", "CNY"}:
        raise DirectError("CURRENCY_POLICY")
    return value


def money_key(kind, unit):
    """原币micro字段名；USD兼容，CNY不借用USD字段。"""
    if unit not in {"USD", "CNY"}:
        raise DirectError("CURRENCY_POLICY")
    return kind + "_micro_" + unit.lower()


def money_amount(value):
    """金额精确到micro原币；不允许NaN、负数、隐式舍入或汇率。"""
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,6})?", value):
            raise ValueError
        amount = Decimal(value) * 1_000_000
        if not amount.is_finite() or not 0 <= amount <= 2**63 - 1:
            raise ValueError
        return int(amount)
    except Exception:
        raise DirectError("MONEY_VALUE") from None


def balance_amount(response, unit):
    """选取唯一同币种余额，保留赠额/充值分项的一致性。"""
    try:
        if unit not in {"USD", "CNY"} or response["is_available"] is not True:
            raise ValueError
        infos = response["balance_infos"]
        if not infos or any(b["currency"] not in {"USD", "CNY"} for b in infos):
            raise ValueError
        if len({b["currency"] for b in infos}) != len(infos):
            raise ValueError
        for b in infos:
            total = money_amount(b["total_balance"])
            if ("granted_balance" in b or "topped_up_balance" in b) and (
                money_amount(b["granted_balance"]) + money_amount(b["topped_up_balance"]) != total
            ):
                raise ValueError
        (selected,) = [b for b in infos if b["currency"] == unit]
        return money_amount(selected["total_balance"])
    except Exception:
        raise DirectError("BALANCE_CURRENCY_OR_VALUE") from None
