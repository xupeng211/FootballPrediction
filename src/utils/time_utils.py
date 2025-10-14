from typing import Any, Dict, List, Optional, Union
"""
足球预测系统时间处理工具模块

提供时间和日期处理相关的工具函数。
"""

from datetime import datetime, timezone


class TimeUtils:
    """时间处理工具类"""

    @staticmethod
    def now_utc() -> datetime:
        """获取当前UTC时间"""
        return datetime.now(timezone.utc)

    @staticmethod
    def timestamp_to_datetime(timestamp: float) -> datetime:
        """时间戳转datetime"""
        return datetime.fromtimestamp(timestamp, timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> float:
        """datetime转时间戳"""
        return dt.timestamp()

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间"""
        return dt.strftime(format_str)

    @staticmethod
    def parse_datetime(
        date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime:
        """解析日期时间字符串"""
        return datetime.strptime(date_str, format_str)


# 为了向后兼容，添加常用函数别名
def utc_now() -> datetime:
    """获取当前UTC时间（向后兼容性函数）"""
    return datetime.now(timezone.utc)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """解析日期时间字符串（向后兼容性函数）"""
    if date_str is None:
        return None  # type: ignore

    try:
        return datetime.strptime(date_str, format_str)
    except (ValueError, TypeError):
        # 尝试其他常见格式
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None  # type: ignore
