"""
简化版日期工具类
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class DateUtils:
    @staticmethod
    def now() -> datetime:
        """获取当前时间"""
        return datetime.utcnow()

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间"""
        if not isinstance(dt, datetime):
            return ""

        try:
            return dt.strftime(format_str)
        except ValueError:
            return ""

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """增加天数"""
        return dt + timedelta(days=days)

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """判断是否为周末"""
        return dt.weekday() >= 5  # 周六、周日
