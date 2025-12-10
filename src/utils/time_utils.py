"""足球预测系统时间处理工具模块.

提供时间和日期处理相关的工具函数.
"""

from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    # For Python < 3.11
    UTC = timezone.utc

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # For Python < 3.9
    from backports.zoneinfo import ZoneInfo


class TimeUtils:
    """类文档字符串."""

    pass  # 添加pass语句
    """时间处理工具类"""

    @staticmethod
    def now_utc() -> datetime:
        """获取当前UTC时间."""
        return datetime.now(UTC)

    @staticmethod
    def get_utc_now() -> datetime:
        """获取当前UTC时间（别名方法）."""
        return datetime.now(UTC)

    @staticmethod
    def get_local_now() -> datetime:
        """获取当前本地时间."""
        return datetime.now()

    @staticmethod
    def timestamp_to_datetime(timestamp: float) -> datetime:
        """时间戳转datetime."""
        return datetime.fromtimestamp(timestamp, UTC)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> float:
        """datetime转时间戳."""
        return dt.timestamp()

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间."""
        return dt.strftime(format_str)

    @staticmethod
    def format_date(dt: datetime) -> str:
        """格式化日期."""
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def format_time(dt: datetime) -> str:
        """格式化时间."""
        return dt.strftime("%H:%M:%S")

    @staticmethod
    def parse_datetime(
        date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime:
        """解析日期时间字符串."""
        return datetime.strptime(date_str, format_str)

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """解析日期字符串."""
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_str}")

    @staticmethod
    def parse_time(time_str: str) -> datetime:
        """解析时间字符串."""
        formats = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse time: {time_str}")

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """添加天数."""
        return dt + timedelta(days=days)

    @staticmethod
    def add_hours(dt: datetime, hours: int) -> datetime:
        """添加小时."""
        return dt + timedelta(hours=hours)

    @staticmethod
    def add_minutes(dt: datetime, minutes: int) -> datetime:
        """添加分钟."""
        return dt + timedelta(minutes=minutes)

    @staticmethod
    def subtract_days(dt: datetime, days: int) -> datetime:
        """减去天数."""
        return dt - timedelta(days=days)

    @staticmethod
    def get_weekday(dt: datetime) -> int:
        """获取星期几 (0=周一, 6=周日)."""
        return dt.weekday()

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """是否是周末."""
        return dt.weekday() >= 5  # 5=周六, 6=周日

    @staticmethod
    def get_days_between(start: datetime, end: datetime) -> int:
        """获取两个日期之间的天数."""
        return abs((end - start).days)

    @staticmethod
    def get_business_days(start: datetime, end: datetime) -> int:
        """获取工作日天数."""
        days = abs((end - start).days)
        business_days = 0
        current = min(start, end)

        for _i in range(days + 1):
            if current.weekday() < 5:  # 周一到周五
                business_days += 1
            current += timedelta(days=1)

        return business_days

    @staticmethod
    def is_valid_date(date_str: str) -> bool:
        """验证日期字符串是否有效."""
        try:
            # 尝试解析常见的日期格式
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S",
            ]
            for fmt in formats:
                try:
                    datetime.strptime(date_str, fmt)
                    return True
                except ValueError:
                    continue
            return False
        except (ValueError, typeError):
            return False

    @staticmethod
    def is_valid_time(time_str: str) -> bool:
        """验证时间字符串是否有效."""
        try:
            # 尝试解析常见的时间格式
            formats = [
                "%H:%M:%S",
                "%H:%M",
                "%I:%M:%S %p",  # 12小时制
                "%I:%M %p",
            ]
            for fmt in formats:
                try:
                    datetime.strptime(time_str, fmt)
                    return True
                except ValueError:
                    continue
            return False
        except (ValueError, typeError):
            return False

    @staticmethod
    def is_future_date(dt: datetime) -> bool:
        """是否是未来日期."""
        return dt > datetime.now()

    @staticmethod
    def is_past_date(dt: datetime) -> bool:
        """是否是过去日期."""
        return dt < datetime.now()

    @staticmethod
    def date_range_overlap(range1: tuple, range2: tuple) -> bool:
        """检查两个日期范围是否有重叠."""
        start1, end1 = range1
        start2, end2 = range2
        return not (end1 < start2 or end2 < start1)

    @staticmethod
    def convert_timezone(dt: datetime, tz_name: str) -> datetime | None:
        """转换时区."""
        try:
            from_tz = UTC
            to_tz = ZoneInfo(tz_name)

            # 检查to_tz是否为有效的tzinfo对象（排除mock对象）
            if not hasattr(to_tz, "utcoffset") or not callable(to_tz.utcoffset):
                return dt

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=from_tz)
            return dt.astimezone(to_tz)
        except (ImportError, ValueError, KeyError, typeError, AttributeError):
            # 如果时区不可用或类型无效,返回原始datetime
            return dt

    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化时间长度."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# 为了向后兼容,添加常用函数别名
def utc_now() -> datetime:
    """获取当前UTC时间（向后兼容性函数）."""
    return datetime.now(UTC)


def parse_datetime(
    date_str: str | None, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> datetime | None:
    """解析日期时间字符串（向后兼容性函数）."""
    if date_str is None:
        return None

    try:
        return datetime.strptime(date_str, format_str)
    except (ValueError, typeError):
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
        return None


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间."""
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_duration(seconds: float) -> str:
    """格式化时间间隔."""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def parse_iso_datetime(date_str: str) -> datetime | None:
    """解析ISO格式日期时间."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return parse_datetime(date_str)


def calculate_duration(start_time: datetime, end_time: datetime) -> timedelta:
    """计算时间差."""
    return end_time - start_time


def get_current_timestamp() -> float:
    """获取当前时间戳."""
    import time

    return time.time()


def is_valid_datetime_format(
    date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> bool:
    """验证日期时间格式是否有效."""
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False
