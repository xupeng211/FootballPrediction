"""
时间工具测试（完整版）
Tests for Time Utils (Comprehensive)

测试时间处理工具类的各种功能，包括：
- UTC时间获取
- 时间戳转换
- 日期时间格式化
- 日期时间解析
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.utils.time_utils import TimeUtils, utc_now, parse_datetime


class TestTimeUtils:
    """测试时间处理工具类"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        now = TimeUtils.now_utc()

        # 验证类型
        assert isinstance(now, datetime)

        # 验证时区
        assert now.tzinfo == UTC

        # 验证时间合理（不能是太久以前或未来）
        utc_now = datetime.now(UTC)
        assert abs((now - utc_now).total_seconds()) < 1.0

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 测试当前时间戳
        current_timestamp = time.time()
        dt = TimeUtils.timestamp_to_datetime(current_timestamp)

        assert isinstance(dt, datetime)
        assert dt.tzinfo == UTC
        assert abs(dt.timestamp() - current_timestamp) < 0.001

        # 测试历史时间戳
        historical_timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(historical_timestamp)

        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert dt == expected

        # 测试负时间戳（1970年之前）
        negative_timestamp = -86400  # 1969-12-31 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(negative_timestamp)

        expected = datetime(1969, 12, 31, 0, 0, 0, tzinfo=UTC)
        assert dt == expected

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        # 测试当前时间
        dt = datetime.now(UTC)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        assert abs(timestamp - time.time()) < 1.0

        # 测试已知时间
        known_dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=UTC)
        timestamp = TimeUtils.datetime_to_timestamp(known_dt)

        expected = 1609459200.0
        assert timestamp == expected

        # 测试带微秒的时间
        dt_with_microseconds = datetime(2021, 1, 1, 0, 0, 0, 500000, tzinfo=UTC)
        timestamp = TimeUtils.datetime_to_timestamp(dt_with_microseconds)

        assert timestamp == 1609459200.5

    def test_format_datetime_default(self):
        """测试默认格式格式化"""
        dt = datetime(2023, 6, 15, 14, 30, 45, tzinfo=UTC)
        formatted = TimeUtils.format_datetime(dt)

        assert formatted == "2023-06-15 14:30:45"

    def test_format_datetime_custom_format(self):
        """测试自定义格式格式化"""
        dt = datetime(2023, 6, 15, 14, 30, 45, tzinfo=UTC)

        # 测试不同格式
        assert TimeUtils.format_datetime(dt, "%Y-%m-%d") == "2023-06-15"
        assert TimeUtils.format_datetime(dt, "%H:%M:%S") == "14:30:45"
        assert TimeUtils.format_datetime(dt, "%Y/%m/%d %H:%M") == "2023/06/15 14:30"
        assert TimeUtils.format_datetime(dt, "%d-%m-%Y") == "15-06-2023"
        assert TimeUtils.format_datetime(dt, "%B %d, %Y") == "June 15, 2023"

    def test_format_datetime_with_microseconds(self):
        """测试格式化带微秒的时间"""
        dt = datetime(2023, 6, 15, 14, 30, 45, 123456, tzinfo=UTC)

        # 包含微秒
        formatted = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S.%f")
        assert formatted == "2023-06-15 14:30:45.123456"

        # 不包含微秒
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2023-06-15 14:30:45"

    def test_format_datetime_timezone(self):
        """测试格式化时区时间"""
        dt = datetime(2023, 6, 15, 14, 30, 45, tzinfo=UTC)
        formatted = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S %Z")

        # UTC时区应该显示
        assert "2023-06-15 14:30:45" in formatted

    def test_parse_datetime_default_format(self):
        """测试解析默认格式时间字符串"""
        date_str = "2023-06-15 14:30:45"
        dt = TimeUtils.parse_datetime(date_str)

        expected = datetime(2023, 6, 15, 14, 30, 45)
        assert dt == expected

    def test_parse_datetime_custom_format(self):
        """测试解析自定义格式时间字符串"""
        # 不同格式
        assert TimeUtils.parse_datetime("2023-06-15", "%Y-%m-%d") == datetime(2023, 6, 15)
        assert TimeUtils.parse_datetime("14:30:45", "%H:%M:%S") == datetime(1900, 1, 1, 14, 30, 45)
        assert TimeUtils.parse_datetime("2023/06/15 14:30", "%Y/%m/%d %H:%M") == datetime(2023, 6, 15, 14, 30)
        assert TimeUtils.parse_datetime("15-06-2023", "%d-%m-%Y") == datetime(2023, 6, 15)

    def test_parse_datetime_invalid(self):
        """测试解析无效时间字符串"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("invalid date")

        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2023-13-15 14:30:45")  # 无效月份

        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2023-06-15 25:30:45")  # 无效小时

    def test_parse_datetime_edge_cases(self):
        """测试边界情况"""
        # 闰年
        dt = TimeUtils.parse_datetime("2020-02-29", "%Y-%m-%d")
        assert dt == datetime(2020, 2, 29)

        # 非闰年（2月29日无效）
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2021-02-29", "%Y-%m-%d")

    def test_timestamp_conversion_roundtrip(self):
        """测试时间戳转换往返"""
        original_timestamp = time.time()

        # 时间戳 -> datetime -> 时间戳
        dt = TimeUtils.timestamp_to_datetime(original_timestamp)
        new_timestamp = TimeUtils.datetime_to_timestamp(dt)

        # 应该接近原始值
        assert abs(original_timestamp - new_timestamp) < 0.001

    def test_datetime_parsing_roundtrip(self):
        """测试datetime解析往返"""
        original_dt = datetime(2023, 6, 15, 14, 30, 45, 123456)

        # datetime -> 字符串 -> datetime
        formatted = TimeUtils.format_datetime(original_dt, "%Y-%m-%d %H:%M:%S.%f")
        parsed_dt = TimeUtils.parse_datetime(formatted, "%Y-%m-%d %H:%M:%S.%f")

        assert original_dt == parsed_dt

    def test_time_operations(self):
        """测试时间操作相关功能"""
        # 获取当前时间
        now = TimeUtils.now_utc()

        # 测试时间戳转换
        timestamp = TimeUtils.datetime_to_timestamp(now)
        dt_from_timestamp = TimeUtils.timestamp_to_datetime(timestamp)

        # 应该非常接近
        assert abs((now - dt_from_timestamp).total_seconds()) < 0.001

    def test_performance(self):
        """测试性能"""
        import time

        # 测试大量操作的性能
        start_time = time.time()

        for i in range(1000):
            dt = TimeUtils.now_utc()
            formatted = TimeUtils.format_datetime(dt)
            parsed = TimeUtils.parse_datetime(formatted)
            timestamp = TimeUtils.datetime_to_timestamp(parsed)
            TimeUtils.timestamp_to_datetime(timestamp)

        elapsed = time.time() - start_time
        assert elapsed < 2.0  # 应该在2秒内完成1000次操作

    def test_class_methods_are_static(self):
        """测试类方法是静态方法"""
        # 应该能够直接调用，不需要实例化
        assert hasattr(TimeUtils, 'now_utc')
        assert hasattr(TimeUtils, 'timestamp_to_datetime')
        assert hasattr(TimeUtils, 'datetime_to_timestamp')
        assert hasattr(TimeUtils, 'format_datetime')
        assert hasattr(TimeUtils, 'parse_datetime')

    def test_edge_cases(self):
        """测试边界情况"""
        # Unix时间戳开始时间
        epoch_timestamp = 0.0
        dt = TimeUtils.timestamp_to_datetime(epoch_timestamp)
        assert dt == datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)

        # 最大时间戳（2038年问题，32位）
        max_32bit_timestamp = 2147483647.0
        dt = TimeUtils.timestamp_to_datetime(max_32bit_timestamp)
        assert dt.year == 2038

        # 测试最小日期
        min_dt = datetime(1, 1, 1, tzinfo=UTC)
        timestamp = TimeUtils.datetime_to_timestamp(min_dt)
        assert timestamp < 0

        # 测试未来日期
        future_dt = datetime(2100, 1, 1, 0, 0, 0, tzinfo=UTC)
        timestamp = TimeUtils.datetime_to_timestamp(future_dt)
        assert timestamp >= 4102444800.0  # 2100年的时间戳

    def test_with_mock_time(self):
        """测试使用模拟时间"""
        # 由于datetime是immutable的，我们直接验证timestamp转换功能
        fixed_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)
        fixed_timestamp = 1686830400.0

        # 测试timestamp转换
        dt_from_timestamp = TimeUtils.timestamp_to_datetime(fixed_timestamp)
        assert dt_from_timestamp == fixed_time

        # 测试datetime转timestamp
        timestamp_from_dt = TimeUtils.datetime_to_timestamp(fixed_time)
        assert timestamp_from_dt == fixed_timestamp

    def test_format_special_dates(self):
        """测试格式化特殊日期"""
        # 新年
        new_year = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert TimeUtils.format_datetime(new_year, "%A, %B %d, %Y") == "Monday, January 01, 2024"

        # 闰日
        leap_day = datetime(2024, 2, 29, 12, 0, 0, tzinfo=UTC)
        assert TimeUtils.format_datetime(leap_day, "%Y-%m-%d is day %j of the year") == "2024-02-29 is day 060 of the year"

        # 月末
        month_end = datetime(2023, 1, 31, 23, 59, 59, tzinfo=UTC)
        assert TimeUtils.format_datetime(month_end, "%Y-%m-%d %H:%M:%S") == "2023-01-31 23:59:59"

    def test_parse_special_formats(self):
        """测试解析特殊格式"""
        # ISO格式（需要自定义格式）
        iso_date = "2023-06-15T14:30:45"
        dt = TimeUtils.parse_datetime(iso_date.replace("T", " "))
        assert dt == datetime(2023, 6, 15, 14, 30, 45)

        # RFC 2822格式（简化版）
        rfc_date = "Thu, 15 Jun 2023 14:30:45 GMT"
        dt = TimeUtils.parse_datetime(rfc_date, "%a, %d %b %Y %H:%M:%S %Z")
        assert dt.year == 2023
        assert dt.month == 6
        assert dt.day == 15

    def test_timezone_handling(self):
        """测试时区处理"""
        # 所有操作都应该在UTC时区
        dt = TimeUtils.now_utc()
        assert dt.tzinfo == UTC

        timestamp = TimeUtils.datetime_to_timestamp(dt)
        dt2 = TimeUtils.timestamp_to_datetime(timestamp)
        assert dt2.tzinfo == UTC

        # 比较时区一致性
        assert dt == dt2


class TestBackwardCompatibility:
    """测试向后兼容性函数"""

    def test_utc_now_function(self):
        """测试utc_now函数"""
        now = utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo == UTC

    def test_parse_datetime_function_valid(self):
        """测试parse_datetime函数 - 有效输入"""
        # 默认格式
        dt = parse_datetime("2023-06-15 14:30:45")
        assert dt == datetime(2023, 6, 15, 14, 30, 45)

        # None输入
        assert parse_datetime(None) is None

        # 尝试其他格式
        dt = parse_datetime("2023-06-15T14:30:45.123Z")
        assert dt == datetime(2023, 6, 15, 14, 30, 45, 123000)

    def test_parse_datetime_function_multiple_formats(self):
        """测试parse_datetime函数 - 多种格式"""
        test_cases = [
            ("2023-06-15T14:30:45.123Z", datetime(2023, 6, 15, 14, 30, 45, 123000)),
            ("2023-06-15T14:30:45Z", datetime(2023, 6, 15, 14, 30, 45)),
            ("2023-06-15T14:30:45", datetime(2023, 6, 15, 14, 30, 45)),
            ("2023-06-15", datetime(2023, 6, 15)),
            ("2023-06-15 14:30:45", datetime(2023, 6, 15, 14, 30, 45)),
        ]

        for date_str, expected in test_cases:
            dt = parse_datetime(date_str)
            assert dt == expected, f"Failed to parse {date_str}"

    def test_parse_datetime_function_invalid(self):
        """测试parse_datetime函数 - 无效输入"""
        invalid_cases = [
            "not a date",
            "2023-13-15",  # 无效月份
            "2023-02-30",  # 无效日期
            "invalid format",
            "12345",
            ""
        ]

        for date_str in invalid_cases:
            dt = parse_datetime(date_str)
            assert dt is None, f"Should return None for {date_str}"

    def test_parse_datetime_function_with_custom_format(self):
        """测试parse_datetime函数 - 自定义格式"""
        dt = parse_datetime("15/06/2023", "%d/%m/%Y")
        assert dt == datetime(2023, 6, 15)

    def test_parse_datetime_function_type_error(self):
        """测试parse_datetime函数 - 类型错误"""
        # 非字符串输入会抛出TypeError
        with pytest.raises(TypeError):
            parse_datetime(123)

        # 对于列表和字典会抛出TypeError
        with pytest.raises(TypeError):
            parse_datetime([])

        with pytest.raises(TypeError):
            parse_datetime({})
