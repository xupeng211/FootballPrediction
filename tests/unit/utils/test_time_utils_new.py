from datetime import datetime
"""
时间工具测试
Tests for Time Utils

测试src.utils.time_utils模块的功能
"""

import pytest

from src.utils.time_utils import TimeUtils, parse_datetime, utc_now


@pytest.mark.unit
class TestTimeUtils:
    """时间工具测试"""

    # ==================== now_utc测试 ====================

    def test_now_utc_returns_datetime(self):
        """测试：返回datetime对象"""
        _result = TimeUtils.now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_is_utc(self):
        """测试：返回UTC时间"""
        _result = TimeUtils.now_utc()
        assert _result.tzinfo == timezone.utc

    def test_now_utc_is_recent(self):
        """测试：时间是最近的"""
        before = datetime.now(timezone.utc)
        _result = TimeUtils.now_utc()
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    # ==================== timestamp_to_datetime测试 ====================

    def test_timestamp_to_datetime_valid(self):
        """测试：有效时间戳转换"""
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        _result = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc
        assert _result.year == 2021
        assert _result.month == 1
        assert _result.day == 1

    def test_timestamp_to_datetime_zero(self):
        """测试：时间戳为0"""
        _result = TimeUtils.timestamp_to_datetime(0.0)
        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc
        assert _result.year == 1970
        assert _result.month == 1

    def test_timestamp_to_datetime_negative(self):
        """测试：负时间戳"""
        timestamp = -86400.0  # 1969-12-31 00:00:00 UTC
        _result = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc
        assert _result.year == 1969
        assert _result.month == 12
        assert _result.day == 31

    def test_timestamp_to_datetime_with_microseconds(self):
        """测试：包含微秒的时间戳"""
        timestamp = 1609459200.123456
        _result = TimeUtils.timestamp_to_datetime(timestamp)
        assert _result.microsecond == 123456

    # ==================== datetime_to_timestamp测试 ====================

    def test_datetime_to_timestamp_utc(self):
        """测试：UTC时间转时间戳"""
        dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        _result = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(result, float)
        assert _result == 1609459200.0

    def test_datetime_to_timestamp_with_microseconds(self):
        """测试：包含微秒的时间转换"""
        dt = datetime(2021, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
        _result = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(result, float)
        assert _result == 1609459200.123456

    def test_datetime_to_timestamp_roundtrip(self):
        """测试：往返转换"""
        original_timestamp = 1609459200.123456
        dt = TimeUtils.timestamp_to_datetime(original_timestamp)
        result_timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert result_timestamp == original_timestamp

    # ==================== format_datetime测试 ====================

    def test_format_datetime_default(self):
        """测试：默认格式"""
        dt = datetime(2021, 1, 1, 12, 30, 45)
        _result = TimeUtils.format_datetime(dt)
        assert _result == "2021-01-01 12:30:45"

    def test_format_datetime_custom(self):
        """测试：自定义格式"""
        dt = datetime(2021, 1, 1, 12, 30, 45)
        _result = TimeUtils.format_datetime(dt, "%Y/%m/%d %H-%M-%S")
        assert _result == "2021/01/01 12-30-45"

    def test_format_datetime_iso_format(self):
        """测试：ISO格式"""
        dt = datetime(2021, 1, 1, 12, 30, 45)
        _result = TimeUtils.format_datetime(dt, "%Y-%m-%dT%H:%M:%S")
        assert _result == "2021-01-01T12:30:45"

    def test_format_datetime_with_microseconds(self):
        """测试：包含微秒"""
        dt = datetime(2021, 1, 1, 12, 30, 45, 123456)
        _result = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S.%f")
        assert _result == "2021-01-01 12:30:45.123456"

    def test_format_datetime_date_only(self):
        """测试：只有日期"""
        dt = datetime(2021, 1, 1, 12, 30, 45)
        _result = TimeUtils.format_datetime(dt, "%Y-%m-%d")
        assert _result == "2021-01-01"

    # ==================== parse_datetime测试 ====================

    def test_parse_datetime_default(self):
        """测试：默认格式解析"""
        date_str = "2021-01-01 12:30:45"
        _result = TimeUtils.parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.year == 2021
        assert _result.month == 1
        assert _result.day == 1
        assert _result.hour == 12
        assert _result.minute == 30
        assert _result.second == 45

    def test_parse_datetime_custom(self):
        """测试：自定义格式解析"""
        date_str = "2021/01/01 12-30-45"
        _result = TimeUtils.parse_datetime(date_str, "%Y/%m/%d %H-%M-%S")
        assert isinstance(result, datetime)
        assert _result.year == 2021
        assert _result.month == 1
        assert _result.day == 1

    def test_parse_datetime_date_only(self):
        """测试：只有日期"""
        date_str = "2021-01-01"
        _result = TimeUtils.parse_datetime(date_str, "%Y-%m-%d")
        assert isinstance(result, datetime)
        assert _result.hour == 0
        assert _result.minute == 0
        assert _result.second == 0

    # ==================== 向后兼容函数测试 ====================

    def test_utc_now_function(self):
        """测试：utc_now函数"""
        _result = utc_now()
        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc

    def test_utc_now_same_as_class_method(self):
        """测试：utc_now与类方法返回相同类型"""
        func_result = utc_now()
        class_result = TimeUtils.now_utc()
        assert type(func_result) is type(class_result)
        assert func_result.tzinfo == class_result.tzinfo

    def test_parse_datetime_function_default(self):
        """测试：parse_datetime函数默认格式"""
        date_str = "2021-01-01 12:30:45"
        _result = parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.year == 2021

    def test_parse_datetime_function_none(self):
        """测试：parse_datetime函数处理None"""
        _result = parse_datetime(None)
        assert _result is None

    def test_parse_datetime_function_iso_with_z(self):
        """测试：parse_datetime函数处理ISO格式带Z"""
        date_str = "2021-01-01T12:30:45Z"
        _result = parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.year == 2021
        assert _result.hour == 12

    def test_parse_datetime_function_iso_with_microseconds(self):
        """测试：parse_datetime函数处理ISO格式带微秒"""
        date_str = "2021-01-01T12:30:45.123456Z"
        _result = parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.microsecond == 123456

    def test_parse_datetime_function_iso_without_z(self):
        """测试：parse_datetime函数处理ISO格式不带Z"""
        date_str = "2021-01-01T12:30:45"
        _result = parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.year == 2021

    def test_parse_datetime_function_date_only(self):
        """测试：parse_datetime函数处理只有日期"""
        date_str = "2021-01-01"
        _result = parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert _result.hour == 0

    def test_parse_datetime_function_invalid(self):
        """测试：parse_datetime函数处理无效格式"""
        date_str = "not a date"
        _result = parse_datetime(date_str)
        assert _result is None

    def test_parse_datetime_function_invalid_type(self):
        """测试：parse_datetime函数处理无效类型"""
        # 实际实现会抛出TypeError而不是返回None
        try:
            parse_datetime(123)
            assert False, "应该抛出TypeError"
        except TypeError:
            pass  # 预期的错误

    # ==================== 组合测试 ====================

    def test_format_parse_roundtrip(self):
        """测试：格式化和解析往返"""
        original_dt = datetime(2021, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_datetime(original_dt)
        parsed = TimeUtils.parse_datetime(formatted)
        assert original_dt == parsed

    def test_multiple_formats(self):
        """测试：多种格式"""
        dt = datetime(2021, 1, 1, 12, 30, 45)

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H-%M-%S",
            "%Y%m%d_%H%M%S",
        ]

        for fmt in formats:
            formatted = TimeUtils.format_datetime(dt, fmt)
            parsed = TimeUtils.parse_datetime(formatted, fmt)
            assert dt == parsed

    # ==================== 边界条件测试 ====================

    def test_extreme_dates(self):
        """测试：极端日期"""
        # 最小日期（datetime在处理时会省略前导零）
        dt_min = datetime(1, 1, 1, 0, 0, 0)
        formatted = TimeUtils.format_datetime(dt_min, "%Y-%m-%d")
        assert "1-01-01" in formatted

        # 远未来日期
        dt_future = datetime(9999, 12, 31, 23, 59, 59)
        formatted = TimeUtils.format_datetime(dt_future)
        assert "9999-12-31" in formatted

    def test_leap_year(self):
        """测试：闰年"""
        dt = datetime(2020, 2, 29, 12, 0, 0)  # 闰年
        formatted = TimeUtils.format_datetime(dt)
        parsed = TimeUtils.parse_datetime(formatted)
        assert parsed.year == 2020
        assert parsed.month == 2
        assert parsed.day == 29

    def test_timezone_handling(self):
        """测试：时区处理"""
        # UTC时间
        utc_dt = datetime(2021, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(utc_dt)
        result_dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert result_dt.tzinfo == timezone.utc
