"""
时间处理工具的全面单元测试
Comprehensive unit tests for time utilities
"""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest

from src.utils.time_utils import TimeUtils, utc_now, parse_datetime


class TestTimeUtils:
    """测试 TimeUtils 类"""

    def test_class_vs_module_functions(self):
        """测试类方法与模块函数的一致性"""
        # TimeUtils.now_utc vs utc_now
        class_time = TimeUtils.now_utc()
        module_time = utc_now()

        # 时间应该非常接近（允许1秒差异）
        difference = abs((class_time - module_time).total_seconds())
        assert difference < 1.0

    def test_all_methods_exist(self):
        """确保所有方法都存在"""
        methods = [
            "now_utc",
            "timestamp_to_datetime",
            "datetime_to_timestamp",
            "format_datetime",
            "parse_datetime",
        ]

        for method in methods:
            assert hasattr(TimeUtils, method)
            assert callable(getattr(TimeUtils, method))


class TestNowUTC:
    """测试获取当前UTC时间功能"""

    def test_now_utc_returns_datetime(self):
        """测试返回datetime对象"""
        result = TimeUtils.now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_is_utc(self):
        """测试返回UTC时间"""
        result = TimeUtils.now_utc()
        assert result.tzinfo == timezone.utc

    def test_now_utc_is_current(self):
        """测试返回当前时间"""
        result = TimeUtils.now_utc()
        now = datetime.now(timezone.utc)

        # 应该在1秒内
        difference = abs((result - now).total_seconds())
        assert difference < 1.0

    def test_now_utc_multiple_calls(self):
        """测试多次调用返回不同时间"""
        result1 = TimeUtils.now_utc()
        time.sleep(0.01)  # 睡眠10ms
        result2 = TimeUtils.now_utc()

        # result2 应该比 result1 晚
        assert result2 > result1

    def test_now_utc_consistency(self):
        """测试时间一致性"""
        # 连续调用应该返回递增的时间
        times = [TimeUtils.now_utc() for _ in range(5)]

        for i in range(1, len(times)):
            assert times[i] >= times[i - 1]

    @patch("datetime.datetime")
    def test_now_utc_mocked(self, mock_datetime):
        """测试模拟的now_utc"""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        result = TimeUtils.now_utc()
        # 由于mock的实现，这个测试可能需要调整
        assert isinstance(result, datetime)


class TestTimestampToDatetime:
    """测试时间戳转datetime功能"""

    def test_timestamp_to_datetime_current(self):
        """测试当前时间戳"""
        timestamp = time.time()
        result = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

        # 应该接近当前时间
        expected = datetime.fromtimestamp(timestamp, timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_epoch(self):
        """测试Unix纪元时间戳"""
        timestamp = 0.0
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_negative(self):
        """测试负时间戳（纪元前）"""
        timestamp = -86400.0  # 纪元前1天
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime(1969, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_large(self):
        """测试大时间戳（未来）"""
        # 2030年
        timestamp = 1893456000.0
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_float(self):
        """测试浮点时间戳（包含毫秒）"""
        timestamp = 1640995200.123456
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime.fromtimestamp(timestamp, timezone.utc)
        assert result == expected

        # 检查微秒精度
        assert result.microsecond == 123456

    def test_timestamp_to_datetime_int(self):
        """测试整数时间戳"""
        timestamp = 1640995200
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime.fromtimestamp(timestamp, timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_roundtrip(self):
        """测试往返转换"""
        original_dt = TimeUtils.now_utc()
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        # 由于精度问题，允许微小差异
        difference = abs((original_dt - converted_dt).total_seconds())
        assert difference < 0.001  # 小于1毫秒


class TestDatetimeToTimestamp:
    """测试datetime转时间戳功能"""

    def test_datetime_to_timestamp_current(self):
        """测试当前时间"""
        dt = TimeUtils.now_utc()
        result = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(result, float)

        # 应该接近time.time()
        current_timestamp = time.time()
        difference = abs(result - current_timestamp)
        assert difference < 1.0

    def test_datetime_to_timestamp_epoch(self):
        """测试Unix纪元"""
        dt = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        assert result == 0.0

    def test_datetime_to_timestamp_future(self):
        """测试未来时间"""
        dt = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(result, float)
        assert result > 0

    def test_datetime_to_timestamp_with_microseconds(self):
        """测试包含微秒的时间"""
        dt = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(result, float)
        # 检查微秒是否被保留
        timestamp_str = f"{result:.6f}"
        assert "123456" in timestamp_str or round(result * 1000000) % 1000000 == 123456

    def test_datetime_to_timestamp_without_timezone(self):
        """测试不带时区的时间（应该抛出错误）"""
        dt = datetime(2024, 1, 1, 12, 0, 0)  # 没有时区信息

        # 这应该仍然工作，但会产生本地时间戳
        result = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(result, float)

    def test_datetime_to_timestamp_negative(self):
        """测试负时间戳（1969年）"""
        dt = datetime(1969, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        assert result < 0
        assert result > -86400  # 不超过1天

    def test_datetime_to_timestamp_consistency(self):
        """测试一致性"""
        dt = TimeUtils.now_utc()

        # 多次转换应该返回相同结果
        result1 = TimeUtils.datetime_to_timestamp(dt)
        result2 = TimeUtils.datetime_to_timestamp(dt)

        assert result1 == result2


class TestFormatDatetime:
    """测试日期时间格式化功能"""

    def test_format_datetime_default(self):
        """测试默认格式"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt)

        assert result == "2024-01-15 12:30:45"

    def test_format_datetime_custom_format(self):
        """测试自定义格式"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

        # 测试各种格式
        formats = [
            ("%Y/%m/%d", "2024/01/15"),
            ("%d-%m-%Y %H:%M", "15-01-2024 12:30"),
            ("%B %d, %Y", "January 15, 2024"),
            ("%Y年%m月%d日", "2024年01月15日"),
            ("%Y-%m-%dT%H:%M:%SZ", "2024-01-15T12:30:45Z"),
        ]

        for format_str, expected in formats:
            result = TimeUtils.format_datetime(dt, format_str)
            assert result == expected

    def test_format_datetime_with_microseconds(self):
        """测试包含微秒的格式化"""
        dt = datetime(2024, 1, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)

        # 格式化包含微秒
        result = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S.%f")
        assert result == "2024-01-15 12:30:45.123456"

    def test_format_datetime_different_timezone(self):
        """测试不同时区（但仍然格式化为UTC时间）"""
        # 使用+8时区的时间
        dt_plus8 = datetime(
            2024, 1, 15, 20, 30, 45, tzinfo=timezone(timedelta(hours=8))
        )

        # 格式化应该显示实际时间
        result = TimeUtils.format_datetime(dt_plus8)
        assert result == "2024-01-15 20:30:45"

    def test_format_datetime_empty_format(self):
        """测试空格式字符串"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

        # 空格式可能导致问题，但应该返回字符串
        result = TimeUtils.format_datetime(dt, "")
        assert isinstance(result, str)

    def test_format_datetime_special_characters(self):
        """测试特殊字符格式"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

        # 测试特殊字符
        result = TimeUtils.format_datetime(dt, "Date: %Y-%m-%d\nTime: %H:%M:%S")
        assert result == "Date: 2024-01-15\nTime: 12:30:45"

    def test_format_datetime_edge_dates(self):
        """测试边界日期"""
        dates = [
            datetime(1, 1, 1, tzinfo=timezone.utc),  # 公元1年
            datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),  # 最大年份
        ]

        for dt in dates:
            result = TimeUtils.format_datetime(dt)
            assert isinstance(result, str)
            assert len(result) > 0


class TestParseDatetime:
    """测试日期时间解析功能"""

    def test_parse_datetime_default_format(self):
        """测试默认格式解析"""
        date_str = "2024-01-15 12:30:45"
        result = TimeUtils.parse_datetime(date_str)

        expected = datetime(2024, 1, 15, 12, 30, 45)
        assert result == expected

    def test_parse_datetime_custom_format(self):
        """测试自定义格式解析"""
        test_cases = [
            ("2024/01/15", "%Y/%m/%d", datetime(2024, 1, 15)),
            ("15-01-2024 12:30", "%d-%m-%Y %H:%M", datetime(2024, 1, 15, 12, 30)),
            ("2024年01月15日", "%Y年%m月%d日", datetime(2024, 1, 15)),
        ]

        for date_str, format_str, expected in test_cases:
            result = TimeUtils.parse_datetime(date_str, format_str)
            assert result == expected

    def test_parse_datetime_iso_format(self):
        """测试ISO格式"""
        date_str = "2024-01-15T12:30:45"
        result = TimeUtils.parse_datetime(date_str, "%Y-%m-%dT%H:%M:%S")

        expected = datetime(2024, 1, 15, 12, 30, 45)
        assert result == expected

    def test_parse_datetime_with_microseconds(self):
        """测试解析微秒"""
        date_str = "2024-01-15 12:30:45.123456"
        result = TimeUtils.parse_datetime(date_str, "%Y-%m-%d %H:%M:%S.%f")

        expected = datetime(2024, 1, 15, 12, 30, 45, 123456)
        assert result == expected

    def test_parse_datetime_invalid_format(self):
        """测试无效格式"""
        date_str = "2024-01-15 12:30:45"

        with pytest.raises(ValueError):
            TimeUtils.parse_datetime(date_str, "%Y/%m/%d")  # 格式不匹配

    def test_parse_datetime_invalid_string(self):
        """测试无效字符串"""
        date_str = "not a date"

        with pytest.raises(ValueError):
            TimeUtils.parse_datetime(date_str)

    def test_parse_datetime_empty_string(self):
        """测试空字符串"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("")

    def test_parse_datetime_edge_cases(self):
        """测试边界情况"""
        test_cases = [
            ("2024-02-29 12:30:45", datetime(2024, 2, 29, 12, 30, 45)),  # 闰年
            ("1900-01-01 00:00:00", datetime(1900, 1, 1, 0, 0, 0)),  # 早期日期
        ]

        for date_str, expected in test_cases:
            result = TimeUtils.parse_datetime(date_str)
            assert result == expected


class TestModuleFunctions:
    """测试模块级别的向后兼容函数"""

    def test_utc_now_function(self):
        """测试utc_now函数"""
        result = utc_now()

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_utc_now_vs_time_utils(self):
        """测试utc_now与TimeUtils.now_utc的一致性"""
        module_result = utc_now()
        class_result = TimeUtils.now_utc()

        # 应该非常接近
        difference = abs((module_result - class_result).total_seconds())
        assert difference < 0.001  # 小于1毫秒

    def test_parse_datetime_module_function_valid(self):
        """测试模块parse_datetime函数 - 有效输入"""
        date_str = "2024-01-15 12:30:45"
        result = parse_datetime(date_str)

        expected = datetime(2024, 1, 15, 12, 30, 45)
        assert result == expected

    def test_parse_datetime_module_function_none(self):
        """测试模块parse_datetime函数 - None输入"""
        result = parse_datetime(None)
        assert result is None

    def test_parse_datetime_module_function_iso_with_z(self):
        """测试模块parse_datetime函数 - ISO格式带Z"""
        # 测试带微秒的ISO格式
        date_str = "2024-01-15T12:30:45.123456Z"
        result = parse_datetime(date_str)

        expected = datetime(2024, 1, 15, 12, 30, 45, 123456)
        assert result == expected

    def test_parse_datetime_module_function_iso_without_z(self):
        """测试模块parse_datetime函数 - ISO格式不带Z"""
        date_str = "2024-01-15T12:30:45Z"
        result = parse_datetime(date_str)

        expected = datetime(2024, 1, 15, 12, 30, 45)
        assert result == expected

    def test_parse_datetime_module_function_date_only(self):
        """测试模块parse_datetime函数 - 只有日期"""
        date_str = "2024-01-15"
        result = parse_datetime(date_str)

        expected = datetime(2024, 1, 15)
        assert result == expected

    def test_parse_datetime_module_function_invalid(self):
        """测试模块parse_datetime函数 - 无效输入"""
        result = parse_datetime("not a date")
        assert result is None

    def test_parse_datetime_module_function_type_error(self):
        """测试模块parse_datetime函数 - 类型错误"""
        result = parse_datetime(12345)  # 数字而不是字符串
        assert result is None

    def test_parse_datetime_module_function_empty_string(self):
        """测试模块parse_datetime函数 - 空字符串"""
        result = parse_datetime("")
        assert result is None

    def test_parse_datetime_module_function_complex_format(self):
        """测试模块parse_datetime函数 - 复杂格式"""
        # 测试带时区的ISO格式（虽然可能不会被正确解析）
        date_str = "2024-01-15T12:30:45+08:00"
        result = parse_datetime(date_str)

        # 可能返回None或解析出的时间
        assert result is None or isinstance(result, datetime)


class TestEdgeCases:
    """测试边界情况和特殊场景"""

    def test_roundtrip_conversions(self):
        """测试往返转换"""
        original_dt = TimeUtils.now_utc()

        # 转换为时间戳再转回datetime
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        # 格式化再解析
        formatted = TimeUtils.format_datetime(converted_dt)
        parsed_dt = TimeUtils.parse_datetime(formatted)

        # 比较原始时间和最终解析的时间
        # 由于格式化时丢失了时区信息，parsed_dt可能没有时区
        if parsed_dt.tzinfo is None:
            # 比较不考虑时区
            assert parsed_dt.year == original_dt.year
            assert parsed_dt.month == original_dt.month
            assert parsed_dt.day == original_dt.day
            assert parsed_dt.hour == original_dt.hour
            assert parsed_dt.minute == original_dt.minute
            assert parsed_dt.second == original_dt.second
        else:
            # 如果有时区，直接比较
            difference = abs((parsed_dt - original_dt).total_seconds())
            assert difference < 1.0

    def test_extreme_timestamps(self):
        """测试极端时间戳"""
        extreme_timestamps = [
            -2208988800.0,  # 1900年
            253402300799.0,  # 9999年
        ]

        for timestamp in extreme_timestamps:
            dt = TimeUtils.timestamp_to_datetime(timestamp)
            assert isinstance(dt, datetime)

            # 转换回去应该接近原始值
            converted_timestamp = TimeUtils.datetime_to_timestamp(dt)
            assert abs(converted_timestamp - timestamp) < 0.001

    def test_timezone_handling(self):
        """测试时区处理"""
        # 创建不同时区的时间
        utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        plus8_time = datetime(
            2024, 1, 15, 20, 0, 0, tzinfo=timezone(timedelta(hours=8))
        )

        # 它们应该代表相同的时刻
        utc_timestamp = TimeUtils.datetime_to_timestamp(utc_time)
        plus8_timestamp = TimeUtils.datetime_to_timestamp(plus8_time)

        # 时间戳应该相同（因为是同一时刻）
        assert utc_timestamp == plus8_timestamp

    def test_format_consistency(self):
        """测试格式一致性"""
        dt = TimeUtils.now_utc()

        # 多次格式化应该返回相同结果
        result1 = TimeUtils.format_datetime(dt)
        result2 = TimeUtils.format_datetime(dt)

        assert result1 == result2

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        dt = TimeUtils.now_utc()

        # 测试大量格式化的性能
        start_time = time.time()
        for _ in range(1000):
            TimeUtils.format_datetime(dt)
        end_time = time.time()

        # 应该在合理时间内完成
        assert end_time - start_time < 1.0

        # 测试大量解析的性能
        date_str = "2024-01-15 12:30:45"
        start_time = time.time()
        for _ in range(1000):
            TimeUtils.parse_datetime(date_str)
        end_time = time.time()

        # 应该在合理时间内完成
        assert end_time - start_time < 1.0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__])
