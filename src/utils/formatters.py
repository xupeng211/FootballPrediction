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


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format as percentage"""
    # 使用Decimal进行精确的四舍五入
    decimal_value = Decimal(str(value))
    rounded_value = decimal_value.quantize(
        Decimal(f"0.{'0' * (decimals - 1)}1"), rounding=ROUND_HALF_UP
    )
    return f"{rounded_value:.{decimals}f}%"
