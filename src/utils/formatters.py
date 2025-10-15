from typing import Any, Dict, List, Optional, Union

"""
Data formatters
"""

import json
from datetime import datetime


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format_str)


def format_json(data: Any, indent: Optional[int] = 2) -> str:
    """Format data as JSON string"""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    return f"{amount:.2f} {currency}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format as percentage"""
    return f"{value:.{decimals}f}%"
