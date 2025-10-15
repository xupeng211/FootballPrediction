"""时间工具增强测试"""

import pytest
from datetime import datetime, timedelta, timezone
from src.utils.time_utils import TimeUtils


class TestTimeUtilsEnhanced:
    """时间工具增强测试"""

    def test_format_timestamp_with_datetime(self):
        """测试使用datetime格式化时间戳"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        formatted = TimeUtils.format_timestamp(dt)
        assert "2025-01-15T14:30:45" in formatted

    def test_format_timestamp_with_timezone(self):
        """测试时区时间戳格式化"""
        dt = datetime(2025, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_timestamp(dt)
        assert "2025-01-15T14:30:45" in formatted

    def test_format_timestamp_none(self):
        """测试None时间戳"""
        formatted = TimeUtils.format_timestamp(None)
        assert isinstance(formatted, str)
        assert "T" in formatted  # ISO格式

    def test_parse_iso_datetime(self):
        """测试解析ISO时间字符串"""
        iso_str = "2025-01-15T14:30:45"
        dt = TimeUtils.parse_iso_datetime(iso_str)
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_iso_datetime_with_timezone(self):
        """测试解析带时区的ISO时间"""
        iso_str = "2025-01-15T14:30:45Z"
        dt = TimeUtils.parse_iso_datetime(iso_str)
        assert dt is not None

    def test_add_days(self):
        """测试添加天数"""
        dt = datetime(2025, 1, 15)
        new_dt = TimeUtils.add_days(dt, 5)
        assert new_dt.day == 20
        assert new_dt.month == 1

    def test_add_days_negative(self):
        """测试减去天数"""
        dt = datetime(2025, 1, 15)
        new_dt = TimeUtils.add_days(dt, -5)
        assert new_dt.day == 10

    def test_add_hours(self):
        """测试添加小时"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        new_dt = TimeUtils.add_hours(dt, 2)
        assert new_dt.hour == 16

    def test_add_minutes(self):
        """测试添加分钟"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        new_dt = TimeUtils.add_minutes(dt, 30)
        assert new_dt.minute == 0
        assert new_dt.hour == 15

    def test_diff_in_days(self):
        """测试日期差（天）"""
        dt1 = datetime(2025, 1, 15)
        dt2 = datetime(2025, 1, 20)
        diff = TimeUtils.diff_in_days(dt2, dt1)
        assert diff == 5

    def test_diff_in_hours(self):
        """测试时间差（小时）"""
        dt1 = datetime(2025, 1, 15, 14, 0, 0)
        dt2 = datetime(2025, 1, 15, 18, 0, 0)
        diff = TimeUtils.diff_in_hours(dt2, dt1)
        assert diff == 4

    def test_diff_in_minutes(self):
        """测试时间差（分钟）"""
        dt1 = datetime(2025, 1, 15, 14, 0, 0)
        dt2 = datetime(2025, 1, 15, 14, 45, 0)
        diff = TimeUtils.diff_in_minutes(dt2, dt1)
        assert diff == 45

    def test_start_of_day(self):
        """测试一天的开始"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        start = TimeUtils.start_of_day(dt)
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

    def test_end_of_day(self):
        """测试一天的结束"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        end = TimeUtils.end_of_day(dt)
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

    def test_is_weekend(self):
        """测试是否是周末"""
        # 周六
        saturday = datetime(2025, 1, 18)  # 2025-01-18是周六
        assert TimeUtils.is_weekend(saturday) is True

        # 周日
        sunday = datetime(2025, 1, 19)
        assert TimeUtils.is_weekend(sunday) is True

        # 周一
        monday = datetime(2025, 1, 20)
        assert TimeUtils.is_weekend(monday) is False

    def test_format_duration(self):
        """测试持续时间格式化"""
        duration = timedelta(hours=2, minutes=30, seconds=45)
        formatted = TimeUtils.format_duration(duration)
        assert "2h" in formatted or "2 hour" in formatted
        assert "30m" in formatted or "30 min" in formatted

    def test_format_duration_seconds_only(self):
        """测试仅秒数的持续时间"""
        duration = timedelta(seconds=45)
        formatted = TimeUtils.format_duration(duration)
        assert "45s" in formatted or "45 sec" in formatted

    def test_parse_duration(self):
        """测试解析持续时间字符串"""
        duration_str = "2h30m"
        duration = TimeUtils.parse_duration(duration_str)
        assert duration.total_seconds() == 9000  # 2.5小时

    def test_get_age(self):
        """测试计算年龄"""
        birth_date = datetime(2000, 1, 15)
        now = datetime(2025, 1, 15)
        age = TimeUtils.get_age(birth_date, now)
        assert age == 25

    def test_format_relative_time(self):
        """测试相对时间格式"""
        now = datetime.now()
        past = now - timedelta(hours=2)
        formatted = TimeUtils.format_relative_time(past, now)
        assert "2 hours ago" in formatted or "2h ago" in formatted

    def test_format_relative_time_future(self):
        """测试未来相对时间"""
        now = datetime.now()
        future = now + timedelta(days=3)
        formatted = TimeUtils.format_relative_time(future, now)
        assert "in 3 days" in formatted or "3 days" in formatted

    def test_is_business_day(self):
        """测试是否是工作日"""
        # 周一到周五
        for day in [13, 14, 15, 16, 17]:  # 2025-01-13到17是周一到周五
            dt = datetime(2025, 1, day)
            assert TimeUtils.is_business_day(dt) is True

        # 周末
        for day in [18, 19]:  # 周六周日
            dt = datetime(2025, 1, day)
            assert TimeUtils.is_business_day(dt) is False

    def test_get_quarter(self):
        """测试获取季度"""
        q1 = datetime(2025, 1, 15)
        q2 = datetime(2025, 4, 15)
        q3 = datetime(2025, 7, 15)
        q4 = datetime(2025, 10, 15)

        assert TimeUtils.get_quarter(q1) == 1
        assert TimeUtils.get_quarter(q2) == 2
        assert TimeUtils.get_quarter(q3) == 3
        assert TimeUtils.get_quarter(q4) == 4

    def test_get_week_of_year(self):
        """测试获取年中第几周"""
        dt = datetime(2025, 1, 15)
        week = TimeUtils.get_week_of_year(dt)
        assert isinstance(week, int)
        assert 1 <= week <= 53

    def test_is_leap_year(self):
        """测试是否是闰年"""
        assert TimeUtils.is_leap_year(2020) is True
        assert TimeUtils.is_leap_year(2024) is True
        assert TimeUtils.is_leap_year(2025) is False
        assert TimeUtils.is_leap_year(2100) is False

    def test_days_in_month(self):
        """测试月份天数"""
        assert TimeUtils.days_in_month(2025, 1) == 31
        assert TimeUtils.days_in_month(2025, 2) == 28
        assert TimeUtils.days_in_month(2024, 2) == 29  # 闰年
        assert TimeUtils.days_in_month(2025, 4) == 30

    def test_timezone_conversion(self):
        """测试时区转换"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        # 简单的时区偏移
        utc_dt = TimeUtils.to_utc(dt)
        assert isinstance(utc_dt, datetime)

    def test_range_overlap(self):
        """测试时间范围重叠"""
        start1 = datetime(2025, 1, 1)
        end1 = datetime(2025, 1, 31)
        start2 = datetime(2025, 1, 15)
        end2 = datetime(2025, 2, 15)

        assert TimeUtils.ranges_overlap(start1, end1, start2, end2) is True

        # 不重叠
        start3 = datetime(2025, 2, 1)
        end3 = datetime(2025, 2, 28)
        assert TimeUtils.ranges_overlap(start1, end1, start3, end3) is False

    def test_merge_datetime_date_time(self):
        """测试合并日期和时间"""
        date_part = datetime(2025, 1, 15).date()
        time_part = datetime(2025, 1, 1, 14, 30, 45).time()
        merged = TimeUtils.merge_datetime(date_part, time_part)
        assert merged.year == 2025
        assert merged.month == 1
        assert merged.day == 15
        assert merged.hour == 14
        assert merged.minute == 30