#!/usr/bin/env python3
"""
时间工具测试
测试 src.utils.time_utils 模块的功能
"""


import pytest

from src.utils.time_utils import TimeUtils


@pytest.mark.unit
class TestTimeUtils:
    """时间工具测试"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        result = TimeUtils.now_utc()

        # 验证返回的是datetime对象
        assert isinstance(result, datetime)

        # 验证时区是UTC
        assert result.tzinfo == timezone.utc

        # 验证时间在合理范围内（最近几秒）
        now = datetime.now(timezone.utc)
        time_diff = abs((result - now).total_seconds())
        assert time_diff < 5  # 5秒内

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 测试已知时间戳
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)

        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_timestamp_to_datetime_current(self):
        """测试当前时间戳转换"""
        import time

        current_timestamp = time.time()
        result = TimeUtils.timestamp_to_datetime(current_timestamp)

        # 验证时区是UTC
        assert result.tzinfo == timezone.utc

        # 验证时间接近当前时间
        time_diff = abs((result.timestamp() - current_timestamp))
        assert time_diff < 1  # 1秒内

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        # 验证返回的是浮点数
        assert isinstance(result, float)

        # 验证时间戳正确
        expected_timestamp = 1609501845.0
        assert abs(result - expected_timestamp) < 1

    def test_datetime_to_timestamp_conversion_roundtrip(self):
        """测试datetime和timestamp转换的往返一致性"""
        original_dt = TimeUtils.now_utc()

        # 转换为时间戳再转回datetime
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        # 验证时间相同（允许微秒级差异）
        time_diff = abs((converted_dt - original_dt).total_seconds())
        assert time_diff < 0.001  # 1毫秒内

    def test_format_datetime_default(self):
        """测试默认格式的时间格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = TimeUtils.format_datetime(dt)

        assert result == "2024-01-15 14:30:45"

    def test_format_datetime_custom(self):
        """测试自定义格式的时间格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 测试不同格式
        assert TimeUtils.format_datetime(dt, "%Y/%m/%d") == "2024/01/15"
        assert TimeUtils.format_datetime(dt, "%H:%M:%S") == "14:30:45"
        assert TimeUtils.format_datetime(dt, "%d-%m-%Y %H:%M") == "15-01-2024 14:30"
        assert TimeUtils.format_datetime(dt, "%Y年%m月%d日") == "2024年01月15日"

    def test_parse_datetime_default(self):
        """测试默认格式的日期时间解析"""
        date_str = "2024-01-15 14:30:45"
        result = TimeUtils.parse_datetime(date_str)

        expected = datetime(2024, 1, 15, 14, 30, 45)
        assert result == expected

    def test_parse_datetime_custom(self):
        """测试自定义格式的日期时间解析"""
        # 测试不同格式
        assert TimeUtils.parse_datetime("2024/01/15", "%Y/%m/%d") == datetime(2024, 1, 15)
        assert TimeUtils.parse_datetime("14:30:45", "%H:%M:%S") == datetime(1900, 1, 1, 14, 30, 45)
        assert TimeUtils.parse_datetime("15-01-2024", "%d-%m-%Y") == datetime(2024, 1, 15)

    def test_format_parse_roundtrip(self):
        """测试格式化和解析的往返一致性"""
        original_dt = datetime(2024, 1, 15, 14, 30, 45, 123456)

        # 格式化再解析
        formatted = TimeUtils.format_datetime(original_dt, "%Y-%m-%d %H:%M:%S")
        parsed_dt = TimeUtils.parse_datetime(formatted, "%Y-%m-%d %H:%M:%S")

        # 比较到秒级（因为格式化丢失了微秒）
        assert parsed_dt.year == original_dt.year
        assert parsed_dt.month == original_dt.month
        assert parsed_dt.day == original_dt.day
        assert parsed_dt.hour == original_dt.hour
        assert parsed_dt.minute == original_dt.minute
        assert parsed_dt.second == original_dt.second

    def test_datetime_with_timezone(self):
        """测试带时区的datetime处理"""
        # 创建UTC时间
        utc_dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)

        # 转换为时间戳再转回
        timestamp = TimeUtils.datetime_to_timestamp(utc_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert converted_dt == utc_dt

    def test_edge_case_dates(self):
        """测试边界日期"""
        # 测试年份边界
        start_dt = datetime(2000, 1, 1, 0, 0, 0)
        end_dt = datetime(2099, 12, 31, 23, 59, 59)

        # 验证格式化
        assert TimeUtils.format_datetime(start_dt) == "2000-01-01 00:00:00"
        assert TimeUtils.format_datetime(end_dt) == "2099-12-31 23:59:59"

        # 验证解析
        parsed_start = TimeUtils.parse_datetime("2000-01-01 00:00:00")
        parsed_end = TimeUtils.parse_datetime("2099-12-31 23:59:59")

        assert parsed_start == start_dt
        assert parsed_end == end_dt
