from typing import cast, Any, Optional, Union

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
