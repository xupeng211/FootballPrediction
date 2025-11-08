"""
Data formatters
"""

import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format_str)


def format_json(data: Any, indent: int | None = None) -> str:
    """Format data as JSON string"""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    # 使用Decimal进行精确的四舍五入
    decimal_amount = Decimal(str(amount))
    rounded_amount = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rounded_amount:.2f} {currency}"


def format_percentage(value: float, decimals: int = 2, as_decimal: bool = False) -> str:
    """Format as percentage

    Args:
        value: 数值（如果是小数形式如0.1234，格式化为"0.12%"；如果是百分比形式如12.34，格式化为"12.34%"）
        decimals: 小数位数
        as_decimal: 如果为True且输入是小数形式，转换为百分比并返回；如果为False，保持原始格式并添加%

    Returns:
        格式化后的百分比字符串
    """
    # 使用Decimal进行精确的四舍五入
    decimal_value = Decimal(str(value))

    # 如果是百分比形式（>=1），直接格式化
    if decimal_value >= 1:
        rounded_value = decimal_value.quantize(
            Decimal(f"0.{'0' * (decimals - 1)}1"), rounding=ROUND_HALF_UP
        )
        return f"{rounded_value:.{decimals}f}%"

    # 如果是小数形式（< 1），根据as_decimal参数决定转换方式
    if as_decimal:
        # 转换为百分比形式
        percentage_value = decimal_value * 100
        rounded_percentage = percentage_value.quantize(
            Decimal(f"0.{'0' * (decimals - 1)}1"), rounding=ROUND_HALF_UP
        )
        return f"{rounded_percentage:.{decimals}f}%"
    else:
        # 保持小数格式但添加%
        rounded_value = decimal_value.quantize(
            Decimal(f"0.{'0' * (decimals - 1)}1"), rounding=ROUND_HALF_UP
        )
        return f"{rounded_value:.{decimals}f}%"
