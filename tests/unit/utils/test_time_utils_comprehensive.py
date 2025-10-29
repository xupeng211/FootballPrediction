from datetime import datetime
"""
时间工具模块完整测试
"""

import pytest

# from src.utils.time_utils import TimeUtils, utc_now, parse_datetime


@pytest.mark.unit
class TestTimeUtils:
    """时间工具类测试"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        _result = TimeUtils.now_utc()

        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc
        # 确保时间在合理范围内（前后5秒）
        now = datetime.now(timezone.utc)
        assert abs((result - now).total_seconds()) < 5

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 使用固定时间戳
        timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
        _result = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(result, datetime)
        assert _result.tzinfo == timezone.utc
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 1
        assert _result.hour == 0
        assert _result.minute == 0
        assert _result.second == 0

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2022, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        _result = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(result, float)
        assert _result == 1641038400.0  # 2022-01-01 12:00:00 UTC

    def test_datetime_conversion_roundtrip(self):
        """测试datetime和时间戳相互转换"""
        original_dt = TimeUtils.now_utc()

        # 转换为时间戳再转回datetime
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        # 比较时间戳（忽略微秒差异）
        assert abs((original_dt - converted_dt).total_seconds()) < 1

    def test_format_datetime_default(self):
        """测试格式化日期时间（默认格式）"""
        dt = datetime(2022, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        _result = TimeUtils.format_datetime(dt)

        assert _result == "2022-01-15 14:30:45"

    def test_format_datetime_custom(self):
        """测试格式化日期时间（自定义格式）"""
        dt = datetime(2022, 1, 15, 14, 30, 45, tzinfo=timezone.utc)

        # 测试不同格式
        assert TimeUtils.format_datetime(dt, "%Y-%m-%d") == "2022-01-15"
        assert TimeUtils.format_datetime(dt, "%d/%m/%Y") == "15/01/2022"
        assert TimeUtils.format_datetime(dt, "%H:%M:%S") == "14:30:45"
        assert TimeUtils.format_datetime(dt, "%Y%m%d_%H%M%S") == "20220115_143045"

    def test_parse_datetime_default(self):
        """测试解析日期时间字符串（默认格式）"""
        date_str = "2022-01-15 14:30:45"
        _result = TimeUtils.parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 14
        assert _result.minute == 30
        assert _result.second == 45

    def test_parse_datetime_custom(self):
        """测试解析日期时间字符串（自定义格式）"""
        # 测试不同格式
        assert TimeUtils.parse_datetime("2022-01-15", "%Y-%m-%d") == datetime(2022, 1, 15)
        assert TimeUtils.parse_datetime("15/01/2022", "%d/%m/%Y") == datetime(2022, 1, 15)
        assert TimeUtils.parse_datetime("20220115", "%Y%m%d") == datetime(2022, 1, 15)

    def test_parse_datetime_invalid(self):
        """测试解析无效的日期时间字符串"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("invalid-date-string")

    def test_utc_now_function(self):
        """测试向后兼容的utc_now函数"""
        result1 = utc_now()
        _result2 = TimeUtils.now_utc()

        assert isinstance(result1, datetime)
        assert isinstance(result2, datetime)
        assert result1.tzinfo == timezone.utc
        assert result2.tzinfo == timezone.utc
        # 时间应该很接近
        assert abs((result1 - result2).total_seconds()) < 1

    def test_parse_datetime_function_default_format(self):
        """测试向后兼容的parse_datetime函数 - 默认格式"""
        date_str = "2022-01-15 14:30:45"
        _result = parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 14
        assert _result.minute == 30
        assert _result.second == 45

    def test_parse_datetime_function_iso_format(self):
        """测试向后兼容的parse_datetime函数 - ISO格式"""
        # 测试ISO 8601格式
        date_str = "2022-01-15T14:30:45.123Z"
        _result = parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 14
        assert _result.minute == 30
        assert _result.second == 45
        assert _result.microsecond == 123000

    def test_parse_datetime_function_iso_no_fraction(self):
        """测试向后兼容的parse_datetime函数 - ISO无小数部分"""
        date_str = "2022-01-15T14:30:45Z"
        _result = parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 14
        assert _result.minute == 30
        assert _result.second == 45

    def test_parse_datetime_function_iso_no_timezone(self):
        """测试向后兼容的parse_datetime函数 - ISO无时区"""
        date_str = "2022-01-15T14:30:45"
        _result = parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 14
        assert _result.minute == 30
        assert _result.second == 45

    def test_parse_datetime_function_date_only(self):
        """测试向后兼容的parse_datetime函数 - 仅日期"""
        date_str = "2022-01-15"
        _result = parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15
        assert _result.hour == 0
        assert _result.minute == 0
        assert _result.second == 0

    def test_parse_datetime_function_none(self):
        """测试向后兼容的parse_datetime函数 - None输入"""
        _result = parse_datetime(None)
        assert _result is None

    def test_parse_datetime_function_invalid(self):
        """测试向后兼容的parse_datetime函数 - 无效输入"""
        # 完全无效的字符串
        _result = parse_datetime("not-a-date")
        assert _result is None

        # 部分有效但格式不对
        _result = parse_datetime("2022-13-45")  # 无效的月份和日期
        assert _result is None

        _result = parse_datetime("")  # 空字符串
        assert _result is None

    def test_parse_datetime_function_custom_format(self):
        """测试向后兼容的parse_datetime函数 - 自定义格式"""
        date_str = "15/01/2022"
        _result = parse_datetime(date_str, "%d/%m/%Y")

        assert isinstance(result, datetime)
        assert _result.year == 2022
        assert _result.month == 1
        assert _result.day == 15

    def test_parse_datetime_function_wrong_custom_format(self):
        """测试向后兼容的parse_datetime函数 - 错误的自定义格式"""
        # 使用错误的格式，但应该能尝试其他格式
        _result = parse_datetime("2022-01-15", "%d/%m/%Y")
        assert _result is not None
        assert _result == datetime(2022, 1, 15)

    def test_time_edge_cases(self):
        """测试时间边界情况"""
        # 测试闰年
        dt = TimeUtils.parse_datetime("2020-02-29", "%Y-%m-%d")
        assert dt.year == 2020
        assert dt.month == 2
        assert dt.day == 29

        # 测试年末
        dt = TimeUtils.parse_datetime("2022-12-31 23:59:59")
        assert dt.month == 12
        assert dt.day == 31
        assert dt.hour == 23
        assert dt.minute == 59
        assert dt.second == 59

    def test_format_and_parse_roundtrip(self):
        """测试格式化和解析的往返转换"""
        # 使用固定时间避免时区问题
        original_dt = datetime(2022, 1, 15, 14, 30, 45, tzinfo=timezone.utc)

        # 格式化
        formatted = TimeUtils.format_datetime(original_dt)

        # 解析
        parsed_dt = TimeUtils.parse_datetime(formatted)

        # 比较
        assert original_dt.replace(tzinfo=None) == parsed_dt

    def test_multiple_formats_parsing(self):
        """测试多种格式的解析能力"""
        formats = [
            "2022-01-15 14:30:45",
            "2022-01-15T14:30:45.123Z",
            "2022-01-15T14:30:45Z",
            "2022-01-15T14:30:45",
            "2022-01-15",
        ]

        for date_str in formats:
            _result = parse_datetime(date_str)
            assert isinstance(result, datetime)
            assert _result.year == 2022
            assert _result.month == 1
            assert _result.day == 15
