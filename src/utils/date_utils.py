"""日期时间工具模块 - 重写版本.

提供核心的日期时间处理功能
"""

from datetime import date, datetime as dt_datetime, timedelta
from functools import lru_cache
from typing import Any, Optional, Union


class DateUtils:
    """日期时间工具类 - 简化版本."""

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
    def format_dt_datetime(dt: dt_datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间."""
        if not isinstance(dt, dt_datetime):
            return ""

        try:
            return dt.strftime(format_str)
        except ValueError:
            return ""

    @staticmethod
    def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> Optional[dt_datetime]:
        """解析日期字符串."""
        if not isinstance(date_str, str):
            return None

        try:
            return datetime.strptime(date_str, format_str)
        except ValueError:
            return None

    @staticmethod
    def parse_dt_datetime(
        datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> Optional[dt_datetime]:
        """解析日期时间字符串."""
        if not isinstance(datetime_str, str):
            return None

        try:
            return datetime.strptime(datetime_str, format_str)
        except ValueError:
            return None

    @staticmethod
    def time_ago(dt: dt_datetime) -> str:
        """计算相对时间."""
        if not isinstance(dt, dt_datetime):
            return ""

        now = dt_datetime.utcnow()
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
    def is_weekend(dt: dt_datetime) -> bool:
        """判断是否为周末."""
        if not isinstance(dt, dt_datetime):
            return False
        return dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    @staticmethod
    def get_weekday(dt: dt_datetime) -> int:
        """获取星期几 (1=Monday, 7=Sunday)."""
        if not isinstance(dt, dt_datetime):
            return None
        # Python的weekday()是0=Monday, 转换为1=Monday
        return dt.weekday() + 1

    @staticmethod
    def is_weekday(dt: dt_datetime) -> bool:
        """判断是否为工作日."""
        return not DateUtils.is_weekend(dt)

    @staticmethod
    def get_age(
        birth_date: Union[dt_datetime, date], current_date: Optional[Union[dt_datetime, date]] = None
    ) -> Optional[int]:
        """计算年龄."""
        # 验证输入参数
        if birth_date is None or not isinstance(birth_date, (dt_datetime, date)):
            return None

        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()

        if current_date is None:
            today = date.today()
        else:
            if not isinstance(current_date, (dt_datetime, date)):
                return None
            if isinstance(current_date, datetime):
                today = current_date.date()
            else:
                today = current_date

        age = today.year - birth_date.year

        # 检查是否还没到生日
        if today.month < birth_date.month or (
            today.month == birth_date.month and today.day < birth_date.day
        ):
            age -= 1

        return max(0, age)

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """判断是否为闰年."""
        if not isinstance(year, int):
            return False

        # 闰年规则：
        # 1. 能被4整除但不能被100整除，或者
        # 2. 能被400整除
        if year % 4 != 0:
            return False
        elif year % 100 != 0:
            return True
        else:
            return year % 400 == 0

    @staticmethod
    def get_month_range(year: int, month: int) -> tuple:
        """获取月份的开始和结束日期."""
        if month < 1 or month > 12:
            raise ValueError("无效的月份")

        start_date = dt_datetime(year, month, 1)

        # 计算下个月的第一天，然后减去一天得到本月的最后一天
        if month == 12:
            end_date = dt_datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = dt_datetime(year, month + 1, 1) - timedelta(days=1)

        return start_date, end_date

    @staticmethod
    def get_days_in_month(year: int, month: int) -> int:
        """获取月份的天数."""
        start_date, end_date = DateUtils.get_month_range(year, month)
        return end_date.day

    @staticmethod
    def add_days(dt: dt_datetime, days: int) -> Optional[dt_datetime]:
        """增加天数."""
        if not isinstance(dt, dt_datetime):
            raise ValueError("Invalid datetime object")
        if not isinstance(days, int):
            return None
        return dt + timedelta(days=days)

    @staticmethod
    def add_months(dt: dt_datetime, months: int) -> datetime:
        """增加月份."""
        if not isinstance(dt, dt_datetime):
            raise ValueError("无效的日期时间对象")

        year = dt.year + (dt.month + months - 1) // 12
        month = (dt.month + months - 1) % 12 + 1
        day = min(dt.day, DateUtils.get_days_in_month(year, month))

        return dt_datetime(year, month, day, dt.hour, dt.minute, dt.second)

    @staticmethod
    def get_timezone_aware(dt: dt_datetime, timezone_offset: int = 0) -> datetime:
        """获取时区感知的日期时间（简化版本）."""
        if not isinstance(dt, dt_datetime):
            raise ValueError("无效的日期时间对象")
        # 这里简化处理，实际项目中应该使用pytz等库
        return dt + timedelta(hours=timezone_offset)

    @staticmethod
    def get_holiday_info(dt: dt_datetime) -> dict[str, Any]:
        """获取节假日信息（简化版本）."""
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
    def get_month_start(dt: dt_datetime) -> Optional[dt_datetime]:
        """获取月份开始日期."""
        if not isinstance(dt, (dt_datetime, date)):
            return None
        if isinstance(dt, date):
            dt = dt_datetime(dt.year, dt.month, dt.day)
        return dt_datetime(dt.year, dt.month, 1)

    @staticmethod
    def get_month_end(dt: dt_datetime) -> Optional[dt_datetime]:
        """获取月份结束日期."""
        if not isinstance(dt, (dt_datetime, date)):
            return None
        if isinstance(dt, date):
            dt = dt_datetime(dt.year, dt.month, dt.day)
        if dt.month == 12:
            return dt_datetime(dt.year + 1, 1, 1) - timedelta(days=1)
        else:
            return dt_datetime(dt.year, dt.month + 1, 1) - timedelta(days=1)

    @staticmethod
    def days_between(dt1: dt_datetime, dt2: dt_datetime) -> Optional[int]:
        """计算两个日期之间的天数."""
        if not isinstance(dt1, (dt_datetime, date)) or not isinstance(
            dt2, (dt_datetime, date)
        ):
            return None
        if isinstance(dt1, date):
            dt1 = dt_datetime(dt1.year, dt1.month, dt1.day)
        if isinstance(dt2, date):
            dt2 = dt_datetime(dt2.year, dt2.month, dt2.day)
        return (dt2 - dt1).days

    @staticmethod
    def format_duration(seconds: int) -> str:
        """格式化时间长度为人类可读格式."""
        if not isinstance(seconds, (int, float)):
            return "0秒"

        try:
            seconds = int(seconds)
            if seconds < 0:
                seconds = abs(seconds)

            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60

            parts = []
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分")
            if remaining_seconds > 0 or not parts:
                parts.append(f"{remaining_seconds}秒")

            return " ".join(parts)
        except Exception:
            return "0秒"

    @staticmethod
    def format_duration_between(start: dt_datetime, end: dt_datetime) -> str:
        """格式化两个时间点之间的时长."""
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            return "0秒"

        try:
            duration_seconds = int((end - start).total_seconds())
            return DateUtils.format_duration(duration_seconds)
        except Exception:
            return "0秒"


# 缓存版本的函数
@lru_cache(maxsize=128)
def cached_format_dt_datetime(dt: dt_datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """缓存版本的日期格式化."""
    return DateUtils.format_dt_datetime(dt, format_str)


@lru_cache(maxsize=256)
def cached_time_ago(dt: dt_datetime, reference: Optional[datetime] = None) -> str:
    """缓存版本的时间差格式化."""
    return DateUtils.time_ago(dt)
