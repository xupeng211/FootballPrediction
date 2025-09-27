"""
Auto-generated tests for src.utils.time_utils module
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from src.utils.time_utils import TimeUtils


class TestTimeUtils:
    """测试时间处理工具类"""

    # Now UTC tests
    def test_now_utc_basic(self):
        """测试基本UTC时间获取"""
        result = TimeUtils.now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    @patch('src.utils.time_utils.datetime')
    def test_now_utc_mocked(self, mock_datetime):
        """测试模拟UTC时间获取"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        result = TimeUtils.now_utc()
        assert result == fixed_time
        mock_datetime.now.assert_called_once_with(timezone.utc)

    # Timestamp to datetime tests
    def test_timestamp_to_datetime_basic(self):
        """测试基本时间戳转换"""
        timestamp = 1672574400.0  # 2023-01-01 12:00:00 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_timestamp_to_datetime_zero(self):
        """测试零时间戳"""
        timestamp = 0.0  # 1970-01-01 00:00:00 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)
        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0

    def test_timestamp_to_datetime_negative(self):
        """测试负时间戳"""
        timestamp = -86400.0  # 1969-12-31 00:00:00 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)
        assert result.year == 1969
        assert result.month == 12
        assert result.day == 31

    @pytest.mark.parametrize("timestamp,expected_year,expected_month,expected_day", [
        (0.0, 1970, 1, 1),
        (86400.0, 1970, 1, 2),
        (1672574400.0, 2023, 1, 1),
        (1893456000.0, 2030, 1, 1),
    ])
    def test_timestamp_to_datetime_parametrized(self, timestamp, expected_year, expected_month, expected_day):
        """测试时间戳转换参数化"""
        result = TimeUtils.timestamp_to_datetime(timestamp)
        assert result.year == expected_year
        assert result.month == expected_month
        assert result.day == expected_day
        assert result.tzinfo == timezone.utc

    # Datetime to timestamp tests
    def test_datetime_to_timestamp_basic(self):
        """测试基本datetime转时间戳"""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(result, float)
        assert result == 1672574400.0

    def test_datetime_to_timestamp_epoch(self):
        """测试纪元时间"""
        dt = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)
        assert result == 0.0

    def test_datetime_to_timestamp_without_timezone(self):
        """测试不带时区的datetime"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(result, float)
        # 应该是本地时间对应的时间戳

    @pytest.mark.parametrize("year,month,day,hour,expected_timestamp", [
        (1970, 1, 1, 0, 0.0),
        (1970, 1, 2, 0, 86400.0),
        (2023, 1, 1, 12, 1672574400.0),
    ])
    def test_datetime_to_timestamp_parametrized(self, year, month, day, hour, expected_timestamp):
        """测试datetime转时间戳参数化"""
        dt = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)
        assert abs(result - expected_timestamp) < 0.001  # 允许微小误差

    # Format datetime tests
    def test_format_datetime_basic(self):
        """测试基本datetime格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt)
        assert result == "2023-01-01 12:30:45"

    def test_format_datetime_custom_format(self):
        """测试自定义格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt, "%Y/%m/%d %H-%M-%S")
        assert result == "2023/01/01 12-30-45"

    def test_format_datetime_date_only(self):
        """测试仅日期格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt, "%Y-%m-%d")
        assert result == "2023-01-01"

    def test_format_datetime_time_only(self):
        """测试仅时间格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt, "%H:%M:%S")
        assert result == "12:30:45"

    def test_format_datetime_iso_format(self):
        """测试ISO格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt, "%Y-%m-%dT%H:%M:%S")
        assert result == "2023-01-01T12:30:45"

    @pytest.mark.parametrize("format_str,expected", [
        ("%Y-%m-%d %H:%M:%S", "2023-01-01 12:30:45"),
        ("%Y/%m/%d %H:%M:%S", "2023/01/01 12:30:45"),
        ("%d-%m-%Y %H:%M", "01-01-2023 12:30"),
        ("%Y年%m月%d日 %H时%M分%S秒", "2023年01月01日 12时30分45秒"),
    ])
    def test_format_datetime_parametrized(self, format_str, expected):
        """测试datetime格式化参数化"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.format_datetime(dt, format_str)
        assert result == expected

    # Parse datetime tests
    def test_parse_datetime_basic(self):
        """测试基本datetime解析"""
        date_str = "2023-01-01 12:30:45"
        result = TimeUtils.parse_datetime(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_parse_datetime_custom_format(self):
        """测试自定义格式解析"""
        date_str = "2023/01/01 12-30-45"
        result = TimeUtils.parse_datetime(date_str, "%Y/%m/%d %H-%M-%S")
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_parse_datetime_date_only(self):
        """测试仅日期解析"""
        date_str = "2023-01-01"
        result = TimeUtils.parse_datetime(date_str, "%Y-%m-%d")
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_datetime_invalid_format(self):
        """测试无效格式解析"""
        date_str = "invalid-date"
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime(date_str)

    def test_parse_datetime_empty_string(self):
        """测试空字符串解析"""
        date_str = ""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime(date_str)

    @pytest.mark.parametrize("date_str,format_str,expected_year,expected_month", [
        ("2023-01-01 12:30:45", "%Y-%m-%d %H:%M:%S", 2023, 1),
        ("2023/12/31 23:59:59", "%Y/%m/%d %H:%M:%S", 2023, 12),
        ("01-01-2023", "%d-%m-%Y", 2023, 1),
        ("2023年01月01日", "%Y年%m月%d日", 2023, 1),
    ])
    def test_parse_datetime_parametrized(self, date_str, format_str, expected_year, expected_month):
        """测试datetime解析参数化"""
        result = TimeUtils.parse_datetime(date_str, format_str)
        assert result.year == expected_year
        assert result.month == expected_month

    # Round-trip conversion tests
    def test_timestamp_conversion_round_trip(self):
        """测试时间戳转换往返"""
        original_timestamp = 1672574400.0

        # timestamp -> datetime -> timestamp
        dt = TimeUtils.timestamp_to_datetime(original_timestamp)
        converted_back = TimeUtils.datetime_to_timestamp(dt)

        assert abs(converted_back - original_timestamp) < 0.001

    def test_string_conversion_round_trip(self):
        """测试字符串转换往返"""
        original_dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        format_str = "%Y-%m-%d %H:%M:%S"

        # datetime -> string -> datetime
        string_representation = TimeUtils.format_datetime(original_dt, format_str)
        parsed_back = TimeUtils.parse_datetime(string_representation, format_str)

        # 时区信息可能会丢失，比较日期时间部分
        assert parsed_back.year == original_dt.year
        assert parsed_back.month == original_dt.month
        assert parsed_back.day == original_dt.day
        assert parsed_back.hour == original_dt.hour
        assert parsed_back.minute == original_dt.minute
        assert parsed_back.second == original_dt.second

    # Integration tests
    def test_time_processing_workflow(self):
        """测试时间处理工作流"""
        # 获取当前时间
        now = TimeUtils.now_utc()
        assert isinstance(now, datetime)

        # 转换为时间戳
        timestamp = TimeUtils.datetime_to_timestamp(now)
        assert isinstance(timestamp, float)

        # 从时间戳转回datetime
        dt_from_timestamp = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(dt_from_timestamp, datetime)

        # 格式化为字符串
        formatted = TimeUtils.format_datetime(dt_from_timestamp)
        assert isinstance(formatted, str)

        # 从字符串解析
        parsed_dt = TimeUtils.parse_datetime(formatted)
        assert isinstance(parsed_dt, datetime)

        # 验证往返一致性（忽略时区差异）
        assert abs((parsed_dt - dt_from_timestamp.replace(tzinfo=None)).total_seconds()) < 1

    def test_time_zone_consistency(self):
        """测试时区一致性"""
        # 测试UTC时间的处理
        utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 格式化
        formatted = TimeUtils.format_datetime(utc_time)
        parsed = TimeUtils.parse_datetime(formatted)

        # 转换为时间戳再转回
        timestamp = TimeUtils.datetime_to_timestamp(utc_time)
        back_to_dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert back_to_dt.tzinfo == timezone.utc

    def test_edge_case_dates(self):
        """测试边界日期"""
        # 测试闰年
        leap_year_dt = datetime(2020, 2, 29, 12, 0, 0, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(leap_year_dt)
        assert "02-29" in formatted

        parsed_leap = TimeUtils.parse_datetime(formatted)
        assert parsed_leap.year == 2020
        assert parsed_leap.month == 2
        assert parsed_leap.day == 29

        # 测试月末
        month_end_dt = datetime(2023, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(month_end_dt)
        back_to_dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert back_to_dt.day == 31

    def test_performance_considerations(self):
        """测试性能考虑"""
        # 测试多次时间操作
        for _ in range(100):
            now = TimeUtils.now_utc()
            timestamp = TimeUtils.datetime_to_timestamp(now)
            dt = TimeUtils.timestamp_to_datetime(timestamp)
            formatted = TimeUtils.format_datetime(dt)
            parsed = TimeUtils.parse_datetime(formatted)

        # 验证操作的正确性
        assert isinstance(parsed, datetime)

    def test_different_timezone_handling(self):
        """测试不同时区处理"""
        # 创建不同时区的时间
        utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 转换为时间戳应该得到相同的值
        utc_timestamp = TimeUtils.datetime_to_timestamp(utc_time)

        # 从时间戳转回应该保持UTC时区
        converted_utc = TimeUtils.timestamp_to_datetime(utc_timestamp)
        assert converted_utc.tzinfo == timezone.utc