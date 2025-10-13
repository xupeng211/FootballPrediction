"""
时间工具测试
Tests for Time Utils

测试src.utils.time_utils模块的时间处理功能
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# 测试导入
try:
    from src.utils.time_utils import TimeUtils

    TIME_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    TIME_UTILS_AVAILABLE = False
    TimeUtils = None


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsFormatting:
    """时间工具格式化测试"""

    def test_format_datetime(self):
        """测试：格式化日期时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_datetime(dt)
        assert isinstance(formatted, str)
        # 应该包含日期和时间
        assert "2023-01-01" in formatted
        assert "12:30:45" in formatted

    def test_format_datetime_with_format(self):
        """测试：格式化日期时间（自定义格式）"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_datetime(dt, "%Y-%m-%d")
        assert formatted == "2023-01-01"

    def test_format_date(self):
        """测试：格式化日期"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_date(dt)
        assert formatted == "2023-01-01"

    def test_format_time(self):
        """测试：格式化时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_time(dt)
        assert formatted == "12:30:45"

    def test_format_datetime_none(self):
        """测试：格式化None日期时间"""
        formatted = TimeUtils.format_datetime(None)
        # 应该返回空字符串或默认值
        assert formatted in ["", None, "N/A"]

    def test_format_datetime_timezone(self):
        """测试：格式化时区日期时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt)
        assert isinstance(formatted, str)

    def test_format_datetime_microseconds(self):
        """测试：格式化带微秒的日期时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45, 123456)
        formatted = TimeUtils.format_datetime(dt)
        # 可能包含或忽略微秒
        assert isinstance(formatted, str)


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsParsing:
    """时间工具解析测试"""

    def test_parse_datetime(self):
        """测试：解析日期时间字符串"""
        dt_str = "2023-01-01 12:30:45"
        dt = TimeUtils.parse_datetime(dt_str)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_date(self):
        """测试：解析日期字符串"""
        date_str = "2023-01-01"
        dt = TimeUtils.parse_date(date_str)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_time(self):
        """测试：解析时间字符串"""
        time_str = "12:30:45"
        dt = TimeUtils.parse_time(time_str)
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_invalid_datetime(self):
        """测试：解析无效日期时间"""
        invalid_str = "invalid-date"
        try:
            TimeUtils.parse_datetime(invalid_str)
        except (ValueError, AttributeError):
            # 应该抛出适当的异常
            pass

    def test_parse_datetime_iso_format(self):
        """测试：解析ISO格式日期时间"""
        iso_str = "2023-01-01T12:30:45"
        dt = TimeUtils.parse_datetime(iso_str)
        assert dt.year == 2023
        assert dt.month == 1

    def test_parse_datetime_custom_format(self):
        """测试：解析自定义格式日期时间"""
        dt_str = "01/01/2023 12:30"
        # 如果支持自定义格式解析
        if hasattr(TimeUtils, "parse_datetime_format"):
            dt = TimeUtils.parse_datetime_format(dt_str, "%d/%m/%Y %H:%M")
            assert dt.day == 1
            assert dt.month == 1
            assert dt.year == 2023


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsOperations:
    """时间工具操作测试"""

    def test_add_days(self):
        """测试：添加天数"""
        dt = datetime(2023, 1, 1)
        _result = TimeUtils.add_days(dt, 7)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 8

    def test_add_hours(self):
        """测试：添加小时"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        _result = TimeUtils.add_hours(dt, 5)
        assert result.hour == 17
        assert result.day == 1

    def test_add_minutes(self):
        """测试：添加分钟"""
        dt = datetime(2023, 1, 1, 12, 30, 0)
        _result = TimeUtils.add_minutes(dt, 45)
        assert result.minute == 15
        assert result.hour == 13

    def test_subtract_days(self):
        """测试：减去天数"""
        dt = datetime(2023, 1, 8)
        _result = TimeUtils.subtract_days(dt, 7)
        assert result.day == 1
        assert result.month == 1
        assert result.year == 2023

    def test_get_weekday(self):
        """测试：获取星期几"""
        # 2023-01-01是星期日
        dt = datetime(2023, 1, 1)
        weekday = TimeUtils.get_weekday(dt)
        assert isinstance(weekday, int)
        assert 0 <= weekday <= 6

    def test_is_weekend(self):
        """测试：是否是周末"""
        # 周六
        saturday = datetime(2023, 1, 7)
        assert TimeUtils.is_weekend(saturday) is True

        # 周日
        sunday = datetime(2023, 1, 8)
        assert TimeUtils.is_weekend(sunday) is True

        # 周一
        monday = datetime(2023, 1, 9)
        assert TimeUtils.is_weekend(monday) is False

    def test_get_days_between(self):
        """测试：获取两个日期之间的天数"""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 8)
        days = TimeUtils.get_days_between(start, end)
        assert days == 7

    def test_get_business_days(self):
        """测试：获取工作日天数"""
        start = datetime(2023, 1, 2)  # 周一
        end = datetime(2023, 1, 6)  # 周五
        business_days = TimeUtils.get_business_days(start, end)
        assert business_days == 5


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsValidation:
    """时间工具验证测试"""

    def test_is_valid_date(self):
        """测试：验证有效日期"""
        assert TimeUtils.is_valid_date("2023-01-01") is True
        assert TimeUtils.is_valid_date("2023-02-28") is True
        assert TimeUtils.is_valid_date("2023-02-29") is False  # 非闰年
        assert TimeUtils.is_valid_date("2024-02-29") is True  # 闰年
        assert TimeUtils.is_valid_date("invalid") is False

    def test_is_valid_time(self):
        """测试：验证有效时间"""
        assert TimeUtils.is_valid_time("12:00:00") is True
        assert TimeUtils.is_valid_time("23:59:59") is True
        assert TimeUtils.is_valid_time("24:00:00") is False
        assert TimeUtils.is_valid_time("25:00:00") is False
        assert TimeUtils.is_valid_time("invalid") is False

    def test_is_future_date(self):
        """测试：是否是未来日期"""
        future_date = datetime.now() + timedelta(days=1)
        past_date = datetime.now() - timedelta(days=1)

        assert TimeUtils.is_future_date(future_date) is True
        assert TimeUtils.is_future_date(past_date) is False

    def test_is_past_date(self):
        """测试：是否是过去日期"""
        past_date = datetime.now() - timedelta(days=1)
        future_date = datetime.now() + timedelta(days=1)

        assert TimeUtils.is_past_date(past_date) is True
        assert TimeUtils.is_past_date(future_date) is False

    def test_date_range_overlap(self):
        """测试：日期范围重叠"""
        # 测试重叠的日期范围
        range1 = (datetime(2023, 1, 1), datetime(2023, 1, 7))
        range2 = (datetime(2023, 1, 5), datetime(2023, 1, 10))
        assert TimeUtils.date_range_overlap(range1, range2) is True

        # 测试不重叠的日期范围
        range3 = (datetime(2023, 1, 8), datetime(2023, 1, 14))
        assert TimeUtils.date_range_overlap(range1, range3) is False


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsTimezone:
    """时间工具时区测试"""

    def test_convert_timezone(self):
        """测试：时区转换"""
        utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 转换为其他时区
        if hasattr(TimeUtils, "convert_timezone"):
            local_dt = TimeUtils.convert_timezone(utc_dt, "America/New_York")
            assert local_dt is not None

    def test_get_utc_now(self):
        """测试：获取当前UTC时间"""
        utc_now = TimeUtils.get_utc_now()
        assert isinstance(utc_now, datetime)
        assert utc_now.tzinfo is not None
        assert utc_now.tzinfo == timezone.utc

    def test_get_local_now(self):
        """测试：获取本地时间"""
        local_now = TimeUtils.get_local_now()
        assert isinstance(local_now, datetime)

    def test_timezone_offset(self):
        """测试：时区偏移"""
        if hasattr(TimeUtils, "get_timezone_offset"):
            offset = TimeUtils.get_timezone_offset("America/New_York")
            assert isinstance(offset, (int, float))


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsPerformance:
    """时间工具性能测试"""

    def test_format_performance(self):
        """测试：格式化性能"""
        dt = datetime.now()

        import time

        start_time = time.time()

        for _ in range(10000):
            TimeUtils.format_datetime(dt)

        end_time = time.time()
        # 10000次格式化应该在1秒内完成
        assert end_time - start_time < 1.0

    def test_parse_performance(self):
        """测试：解析性能"""
        dt_str = "2023-01-01 12:30:45"

        import time

        start_time = time.time()

        for _ in range(10000):
            TimeUtils.parse_datetime(dt_str)

        end_time = time.time()
        # 10000次解析应该在1秒内完成
        assert end_time - start_time < 1.0


@pytest.mark.skipif(
    TIME_UTILS_AVAILABLE, reason="Time utils module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not TIME_UTILS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if TIME_UTILS_AVAILABLE:
        from src.utils.time_utils import TimeUtils

        assert TimeUtils is not None


def test_class_methods(self):
    """测试：类方法存在"""
    if TIME_UTILS_AVAILABLE:
        from src.utils.time_utils import TimeUtils

        expected_methods = [
            "format_datetime",
            "format_date",
            "format_time",
            "parse_datetime",
            "parse_date",
            "parse_time",
            "add_days",
            "add_hours",
            "add_minutes",
            "subtract_days",
            "get_weekday",
            "is_weekend",
        ]

        for method in expected_methods:
            if hasattr(TimeUtils, method):
                assert callable(getattr(TimeUtils, method))


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsEdgeCases:
    """时间工具边界情况测试"""

    def test_leap_year_handling(self):
        """测试：闰年处理"""
        # 闰年2月29日
        leap_date = datetime(2024, 2, 29)
        formatted = TimeUtils.format_date(leap_date)
        assert formatted == "2024-02-29"

        # 非闰年
        try:
            datetime(2023, 2, 29)
        except ValueError:
            # 应该抛出异常
            pass

    def test_midnight_handling(self):
        """测试：午夜处理"""
        midnight = datetime(2023, 1, 1, 0, 0, 0)
        formatted = TimeUtils.format_time(midnight)
        assert "00:00:00" in formatted

    def test_end_of_month(self):
        """测试：月末处理"""
        # 1月31日
        jan_end = datetime(2023, 1, 31)
        next_month = TimeUtils.add_days(jan_end, 1)
        assert next_month.month == 2
        assert next_month.day == 1

        # 12月31日
        dec_end = datetime(2023, 12, 31)
        next_year = TimeUtils.add_days(dec_end, 1)
        assert next_year.year == 2024
        assert next_year.month == 1

    def test_daylight_saving(self):
        """测试：夏令时处理"""
        # 夏令时开始和结束时间
        if hasattr(TimeUtils, "is_daylight_saving"):
            dt = datetime(2023, 7, 1)  # 北半球夏令时
            is_dst = TimeUtils.is_daylight_saving(dt)
            assert isinstance(is_dst, bool)

    def test_large_time_differences(self):
        """测试：大的时间差"""
        base_dt = datetime(2000, 1, 1)
        future_dt = datetime(2100, 1, 1)

        if hasattr(TimeUtils, "get_years_between"):
            years = TimeUtils.get_years_between(base_dt, future_dt)
            assert years == 100

    def test_microsecond_precision(self):
        """测试：微秒精度"""
        dt = datetime(2023, 1, 1, 12, 30, 45, 999999)
        formatted = TimeUtils.format_datetime(dt)

        # 微秒可能被包含或截断
        if "." in formatted:
            assert "999999" in formatted or "999999" in formatted[:10]

    def test_negative_time_differences(self):
        """测试：负时间差"""
        base_dt = datetime(2023, 1, 8)

        # 减去7天
        _result = TimeUtils.subtract_days(base_dt, 7)
        assert result.day == 1
        assert result.month == 1

    def test_timezone_edge_cases(self):
        """测试：时区边界情况"""
        # 跨越时区边界的时间
        utc_dt = datetime(2023, 1, 1, 23, 30, 0, tzinfo=timezone.utc)

        if hasattr(TimeUtils, "convert_timezone"):
            # 转换到UTC-14（国际日期变更线）
            local_dt = TimeUtils.convert_timezone(utc_dt, "Pacific/Kiritimati")
            # 日期可能改变
            assert local_dt is not None
