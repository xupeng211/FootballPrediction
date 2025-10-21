from typing import Any, Dict
from datetime import datetime

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    return dt.strftime(format_str)

def format_currency(amount: float, currency: str = "USD") -> str:
    """格式化货币"""
    return f"{currency} {amount:,.2f}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """格式化百分比"""
    return f"{value:.{decimals}%}"

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
