"""
日期时间工具模块 - 重写版本

提供核心的日期时间处理功能
"""

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, Optional, Union


class DateUtils:
    """日期时间工具类 - 简化版本"""

    # 常用格式定义
    DATETIME_FORMATS = {
        "default": "%Y-%m-%d %H:%M:%S",
        "date": "%Y-%m-%d",
        "time": "%H:%M:%S",
        "iso": "%Y-%m-%dT%H:%M:%S",
        "readable": "%Y年%m月%d日 %H:%M:%S",
        "short": "%m/%d %H:%M",
        "us": "%m/%d/%Y %I:%M %p",
    }

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
    def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> Optional[datetime]:
        """解析日期字符串"""
        if not isinstance(date_str, str):
            return None

        try:
            return datetime.strptime(date_str, format_str)
        except ValueError:
            return None

    @staticmethod
    def time_ago(dt: datetime) -> str:
        """计算相对时间"""
        if not isinstance(dt, datetime):
            return ""

        now = datetime.utcnow()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "刚刚"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)}分钟前"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() / 3600)}小时前"
        elif diff.days < 7:
            return f"{diff.days}天前"
        elif diff.days < 30:
            return f"{diff.days // 7}周前"
        else:
            return dt.strftime("%Y-%m-%d")

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """判断是否为周末"""
        if not isinstance(dt, datetime):
            return False
        return dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    @staticmethod
    def is_weekday(dt: datetime) -> bool:
        """判断是否为工作日"""
        return not DateUtils.is_weekend(dt)

    @staticmethod
    def get_age(birth_date: Union[datetime, date]) -> int:
        """计算年龄"""
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()

        today = date.today()
        age = today.year - birth_date.year

        # 检查是否还没到生日
        if today.month < birth_date.month or (
            today.month == birth_date.month and today.day < birth_date.day
        ):
            age -= 1

        return max(0, age)

    @staticmethod
    def get_month_range(year: int, month: int) -> tuple:
        """获取月份的开始和结束日期"""
        if month < 1 or month > 12:
            raise ValueError("无效的月份")

        start_date = datetime(year, month, 1)

        # 计算下个月的第一天，然后减去一天得到本月的最后一天
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        return start_date, end_date

    @staticmethod
    def get_days_in_month(year: int, month: int) -> int:
        """获取月份的天数"""
        start_date, end_date = DateUtils.get_month_range(year, month)
        return end_date.day

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """增加天数"""
        if not isinstance(dt, datetime):
            raise ValueError("无效的日期时间对象")
        return dt + timedelta(days=days)

    @staticmethod
    def add_months(dt: datetime, months: int) -> datetime:
        """增加月份"""
        if not isinstance(dt, datetime):
            raise ValueError("无效的日期时间对象")

        year = dt.year + (dt.month + months - 1) // 12
        month = (dt.month + months - 1) % 12 + 1
        day = min(dt.day, DateUtils.get_days_in_month(year, month))

        return datetime(year, month, day, dt.hour, dt.minute, dt.second)

    @staticmethod
    def get_timezone_aware(dt: datetime, timezone_offset: int = 0) -> datetime:
        """获取时区感知的日期时间（简化版本）"""
        if not isinstance(dt, datetime):
            raise ValueError("无效的日期时间对象")
        # 这里简化处理，实际项目中应该使用pytz等库
        return dt + timedelta(hours=timezone_offset)

    @staticmethod
    def get_holiday_info(dt: datetime) -> Dict[str, Any]:
        """获取节假日信息（简化版本）"""
        # 这里简化处理，实际项目中应该使用节假日库
        date_str = dt.strftime("%m-%d")
        holidays = {
            "01-01": "元旦",
            "05-01": "劳动节",
            "10-01": "国庆节",
        }
        holiday_name = holidays.get(date_str)

        return {
            "is_holiday": bool(holiday_name),
            "holiday_name": holiday_name or "",
            "is_weekend": DateUtils.is_weekend(dt),
        }

    @staticmethod
    def format_duration(start_time: datetime, end_time: datetime) -> str:
        """格式化两个时间之间的时长"""
        if not isinstance(start_time, datetime):
            return "无效时间"

        if end_time is None:
            end_time = datetime.utcnow()

        if not isinstance(end_time, datetime):
            return "无效时间"

        duration = end_time - start_time

        if duration.total_seconds() < 0:
            return "结束时间早于开始时间"

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"

    @staticmethod
    def get_business_days_count(start_date: date, end_date: date) -> int:
        """计算工作日数量"""
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            return 0

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        business_days = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # 0-4 表示周一到周五
                business_days += 1
            current_date += timedelta(days=1)

        return business_days


# 性能优化的日期处理函数
@lru_cache(maxsize=500)
def cached_format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """缓存的日期格式化函数"""
    return DateUtils.format_datetime(dt, format_str)


@lru_cache(maxsize=200)
def cached_time_ago(dt: datetime) -> str:
    """缓存的时间格式化函数"""
    return DateUtils.time_ago(dt)
