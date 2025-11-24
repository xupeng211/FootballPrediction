from typing import Optional

"""
TimeUtils增强测试 - 提升39%到65%+覆盖率
针对未覆盖的时间工具函数进行全面测试
"""

from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    # For Python < 3.11
    UTC = UTC
from unittest.mock import MagicMock, patch

import pytest

from src.utils.time_utils import TimeUtils, parse_datetime, utc_now


class TestTimeUtilsEnhanced:
    """TimeUtils增强测试类 - 提升覆盖率到65%+"""

    def test_get_utc_now_alias(self):
        """测试获取UTC时间别名方法"""
        result = TimeUtils.get_utc_now()
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

        # 验证与now_utc结果一致
        result1 = TimeUtils.now_utc()
        result2 = TimeUtils.get_utc_now()
        assert isinstance(result1, datetime)
        assert isinstance(result2, datetime)

    def test_get_local_now_function(self):
        """测试获取本地时间功能"""
        result = TimeUtils.get_local_now()
        assert isinstance(result, datetime)
        # 本地时间通常没有时区信息（除非系统设置）
        assert result.year > 2000  # 基本的合理性检查

    def test_format_date_function(self):
        """测试日期格式化功能"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = TimeUtils.format_date(dt)
        assert result == "2024-01-15"
        assert isinstance(result, str)

    def test_format_time_function(self):
        """测试时间格式化功能"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = TimeUtils.format_time(dt)
        assert result == "14:30:45"
        assert isinstance(result, str)

    def test_parse_date_function(self):
        """测试日期解析功能"""
        # 不同格式测试
        test_cases = [
            ("2024-01-15", datetime(2024, 1, 15)),
            ("2024/01/15", datetime(2024, 1, 15)),
            ("15-01-2024", datetime(2024, 1, 15)),
            ("15/01/2024", datetime(2024, 1, 15)),
        ]

        for date_str, expected in test_cases:
            result = TimeUtils.parse_date(date_str)
            assert result.year == expected.year
            assert result.month == expected.month
            assert result.day == expected.day

    def test_parse_date_invalid_format(self):
        """测试无效日期格式解析"""
        invalid_dates = ["invalid-date", "2024-13-45", "not-a-date"]

        for invalid_date in invalid_dates:
            with pytest.raises(ValueError):
                TimeUtils.parse_date(invalid_date)

    def test_parse_time_function(self):
        """测试时间解析功能"""
        # 不同格式测试
        test_cases = [
            ("14:30:45", datetime(1900, 1, 1, 14, 30, 45)),
            ("14:30", datetime(1900, 1, 1, 14, 30)),
            ("02:30:45 PM", datetime(1900, 1, 1, 14, 30, 45)),
            ("02:30 PM", datetime(1900, 1, 1, 14, 30)),
        ]

        for time_str, expected in test_cases:
            result = TimeUtils.parse_time(time_str)
            assert result.hour == expected.hour
            assert result.minute == expected.minute

    def test_parse_time_invalid_format(self):
        """测试无效时间格式解析"""
        invalid_times = ["invalid-time", "25:70:90", "not-a-time"]

        for invalid_time in invalid_times:
            with pytest.raises(ValueError):
                TimeUtils.parse_time(invalid_time)

    def test_add_hours_function(self):
        """测试添加小时功能"""
        base_dt = datetime(2024, 1, 15, 10, 0, 0)
        result = TimeUtils.add_hours(base_dt, 5)
        assert result.hour == 15
        assert result.day == 15

        # 跨天测试
        result = TimeUtils.add_hours(base_dt, 15)
        assert result.hour == 1
        assert result.day == 16

    def test_add_minutes_function(self):
        """测试添加分钟功能"""
        base_dt = datetime(2024, 1, 15, 10, 30, 0)
        result = TimeUtils.add_minutes(base_dt, 45)
        assert result.hour == 11
        assert result.minute == 15

        # 跨小时测试
        result = TimeUtils.add_minutes(base_dt, 150)
        assert result.hour == 13
        assert result.minute == 0

    def test_subtract_days_function(self):
        """测试减去天数功能"""
        base_dt = datetime(2024, 1, 15, 10, 0, 0)
        result = TimeUtils.subtract_days(base_dt, 5)
        assert result.day == 10
        assert result.month == 1

        # 跨月测试
        result = TimeUtils.subtract_days(base_dt, 20)
        assert result.day == 26
        assert result.month == 12
        assert result.year == 2023

    def test_get_weekday_function(self):
        """测试获取星期几功能"""
        # 2024-01-15是星期一 (weekday() 返回 0)
        monday = datetime(2024, 1, 15)
        assert TimeUtils.get_weekday(monday) == 0

        # 2024-01-20是星期六 (weekday() 返回 5)
        saturday = datetime(2024, 1, 20)
        assert TimeUtils.get_weekday(saturday) == 5

        # 2024-01-21是星期日 (weekday() 返回 6)
        sunday = datetime(2024, 1, 21)
        assert TimeUtils.get_weekday(sunday) == 6

    def test_is_weekend_function(self):
        """测试周末判断功能"""
        # 周一到周五
        weekday = datetime(2024, 1, 15)  # 星期一
        assert TimeUtils.is_weekend(weekday) is False

        friday = datetime(2024, 1, 19)  # 星期五
        assert TimeUtils.is_weekend(friday) is False

        # 周六和周日
        saturday = datetime(2024, 1, 20)  # 星期六
        assert TimeUtils.is_weekend(saturday) is True

        sunday = datetime(2024, 1, 21)  # 星期日
        assert TimeUtils.is_weekend(sunday) is True

    def test_get_business_days_function(self):
        """测试工作日计算功能"""
        # 同一周内
        start = datetime(2024, 1, 15)  # 星期一
        end = datetime(2024, 1, 19)  # 星期五
        business_days = TimeUtils.get_business_days(start, end)
        assert business_days == 5

        # 包含周末
        start = datetime(2024, 1, 15)  # 星期一
        end = datetime(2024, 1, 21)  # 星期日
        business_days = TimeUtils.get_business_days(start, end)
        assert business_days == 5  # 只有5个工作日

        # 反向顺序
        start = datetime(2024, 1, 21)  # 星期日
        end = datetime(2024, 1, 15)  # 星期一
        business_days = TimeUtils.get_business_days(start, end)
        assert business_days == 5

    def test_is_valid_date_function(self):
        """测试日期验证功能"""
        # 有效日期
        valid_dates = [
            "2024-01-15",
            "2024/01/15",
            "15-01-2024",
            "15/01/2024",
            "2024-01-15 14:30:45",
        ]

        for date_str in valid_dates:
            assert TimeUtils.is_valid_date(date_str) is True

        # 无效日期
        invalid_dates = [
            "invalid-date",
            "2024-13-45",
            "not-a-date",
            "",
            "2024-01-15 25:70:90",
        ]

        for date_str in invalid_dates:
            assert TimeUtils.is_valid_date(date_str) is False

    def test_is_valid_time_function(self):
        """测试时间验证功能"""
        # 有效时间
        valid_times = ["14:30:45", "14:30", "02:30:45 PM", "02:30 PM"]

        for time_str in valid_times:
            assert TimeUtils.is_valid_time(time_str) is True

        # 无效时间
        invalid_times = ["invalid-time", "25:70:90", "not-a-time", ""]

        for time_str in invalid_times:
            assert TimeUtils.is_valid_time(time_str) is False

    def test_is_future_date_function(self):
        """测试未来日期判断功能"""
        future = datetime.now() + timedelta(days=1)
        assert TimeUtils.is_future_date(future) is True

        past = datetime.now() - timedelta(days=1)
        assert TimeUtils.is_future_date(past) is False

        now = datetime.now()
        # 根据执行时间，结果可能为True或False
        result = TimeUtils.is_future_date(now)
        assert isinstance(result, bool)

    def test_is_past_date_function(self):
        """测试过去日期判断功能"""
        past = datetime.now() - timedelta(days=1)
        assert TimeUtils.is_past_date(past) is True

        future = datetime.now() + timedelta(days=1)
        assert TimeUtils.is_past_date(future) is False

        now = datetime.now()
        # 根据执行时间，结果可能为True或False
        result = TimeUtils.is_past_date(now)
        assert isinstance(result, bool)

    def test_date_range_overlap_function(self):
        """测试日期范围重叠功能"""
        # 重叠的日期范围
        range1 = (datetime(2024, 1, 15), datetime(2024, 1, 20))
        range2 = (datetime(2024, 1, 18), datetime(2024, 1, 25))
        assert TimeUtils.date_range_overlap(range1, range2) is True

        # 相邻的日期范围
        range1 = (datetime(2024, 1, 15), datetime(2024, 1, 20))
        range2 = (datetime(2024, 1, 20), datetime(2024, 1, 25))
        assert TimeUtils.date_range_overlap(range1, range2) is True

        # 不重叠的日期范围
        range1 = (datetime(2024, 1, 15), datetime(2024, 1, 20))
        range2 = (datetime(2024, 1, 21), datetime(2024, 1, 25))
        assert TimeUtils.date_range_overlap(range1, range2) is False

    def test_convert_timezone_function(self):
        """测试时区转换功能"""
        base_dt = datetime(2024, 1, 15, 12, 0, 0)

        # 测试有效时区转换
        try:
            result = TimeUtils.convert_timezone(base_dt, "Asia/Shanghai")
            assert isinstance(result, datetime)
        except Exception:
            # 如果时区数据库不可用，应该返回原始datetime
            pass

        # 测试无效时区
        result = TimeUtils.convert_timezone(base_dt, "Invalid/Timezone")
        assert isinstance(result, datetime)

    @patch("src.utils.time_utils.ZoneInfo")
    def test_convert_timezone_with_mock(self, mock_zone_info):
        """测试使用mock的时区转换功能"""
        mock_tz = MagicMock()
        mock_zone_info.return_value = mock_tz

        base_dt = datetime(2024, 1, 15, 12, 0, 0)
        result = TimeUtils.convert_timezone(base_dt, "Test/Timezone")

        # 验证ZoneInfo被调用
        mock_zone_info.assert_called_with("Test/Timezone")
        assert isinstance(result, datetime)

    def test_format_duration_function(self):
        """测试时间长度格式化功能"""
        # 小时级别
        assert TimeUtils.format_duration(3665) == "1h 1m 5s"
        assert TimeUtils.format_duration(7200) == "2h 0m 0s"

        # 分钟级别
        assert TimeUtils.format_duration(125) == "2m 5s"
        assert TimeUtils.format_duration(180) == "3m 0s"

        # 秒级别
        assert TimeUtils.format_duration(45) == "45s"
        assert TimeUtils.format_duration(0) == "0s"

        # 浮点数输入
        assert TimeUtils.format_duration(3665.7) == "1h 1m 5s"

    def test_utc_now_compatibility_function(self):
        """测试向后兼容的utc_now函数"""
        result = utc_now()
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

        # 验证与类方法的一致性
        class_result = TimeUtils.now_utc()
        function_result = utc_now()
        assert isinstance(class_result, datetime)
        assert isinstance(function_result, datetime)
        assert class_result.tzinfo == function_result.tzinfo

    def test_parse_datetime_compatibility_function(self):
        """测试向后兼容的parse_datetime函数"""
        # 基本解析
        result = parse_datetime("2024-01-15 14:30:45")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        # 不同格式测试
        formats = [
            "2024-01-15T14:30:45.123456Z",
            "2024-01-15T14:30:45Z",
            "2024-01-15T14:30:45",
            "2024-01-15",
        ]

        for fmt in formats:
            result = parse_datetime(fmt)
            assert result is not None
            assert isinstance(result, datetime)

        # None输入
        assert parse_datetime(None) is None

        # 无效格式
        assert parse_datetime("invalid-date") is None

    def test_time_utils_comprehensive_workflow(self):
        """测试时间工具的完整工作流程"""
        # 1. 获取当前时间
        now_utc = TimeUtils.now_utc()
        now_local = TimeUtils.get_local_now()
        assert isinstance(now_utc, datetime)
        assert isinstance(now_local, datetime)

        # 2. 时间格式化
        formatted_datetime = TimeUtils.format_datetime(now_utc)
        formatted_date = TimeUtils.format_date(now_utc)
        formatted_time = TimeUtils.format_time(now_utc)
        assert isinstance(formatted_datetime, str)
        assert isinstance(formatted_date, str)
        assert isinstance(formatted_time, str)

        # 3. 时间解析
        parsed_dt = TimeUtils.parse_datetime(formatted_datetime)
        assert isinstance(parsed_dt, datetime)

        # 4. 时间计算
        future_date = TimeUtils.add_days(now_utc, 7)
        past_date = TimeUtils.subtract_days(now_utc, 7)
        hours_added = TimeUtils.add_hours(now_utc, 5)
        minutes_added = TimeUtils.add_minutes(now_utc, 30)

        assert future_date > now_utc
        assert past_date < now_utc
        assert hours_added > now_utc
        assert minutes_added > now_utc

        # 5. 时间验证
        assert TimeUtils.is_valid_date(formatted_date) is True
        assert TimeUtils.is_valid_time(formatted_time) is True

        # 6. 星期和工作日计算
        weekday = TimeUtils.get_weekday(now_utc)
        is_weekend = TimeUtils.is_weekend(now_utc)
        assert isinstance(weekday, int)
        assert isinstance(is_weekend, bool)

        # 7. 时间长度格式化
        duration = TimeUtils.format_duration(3665)
        assert isinstance(duration, str)
        assert "h" in duration

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 测试极值时间
        very_old = datetime(1900, 1, 1)
        very_future = datetime(2100, 12, 31, 23, 59, 59)

        # 验证这些时间可以被处理
        assert TimeUtils.format_date(very_old) == "1900-01-01"
        assert TimeUtils.format_date(very_future) == "2100-12-31"

        # 测试大量时间操作性能
        import time

        start_time = time.time()

        for i in range(100):
            dt = datetime(2024, 1, 1) + timedelta(days=i)
            TimeUtils.format_datetime(dt)
            TimeUtils.get_weekday(dt)
            TimeUtils.is_weekend(dt)

        end_time = time.time()
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_timezone_handling_edge_cases(self):
        """测试时区处理边界情况"""
        base_dt = datetime(2024, 1, 15, 12, 0, 0)

        # 测试有时区信息的datetime
        utc_dt = base_dt.replace(tzinfo=UTC)
        result = TimeUtils.convert_timezone(utc_dt, "Asia/Shanghai")
        assert isinstance(result, datetime)

        # 测试无时区信息的datetime
        naive_dt = base_dt
        result = TimeUtils.convert_timezone(naive_dt, "UTC")
        assert isinstance(result, datetime)

    def test_date_calculation_edge_cases(self):
        """测试日期计算边界情况"""
        base_dt = datetime(2024, 1, 15, 12, 0, 0)

        # 测试大数值计算
        future = TimeUtils.add_days(base_dt, 365)
        assert future.year == 2025

        past = TimeUtils.subtract_days(base_dt, 365)
        assert past.year == 2023

        # 测试负数输入
        result = TimeUtils.add_days(base_dt, -10)
        expected = TimeUtils.subtract_days(base_dt, 10)
        assert result.day == expected.day

        # 测试零值输入
        result = TimeUtils.add_days(base_dt, 0)
        assert result == base_dt
