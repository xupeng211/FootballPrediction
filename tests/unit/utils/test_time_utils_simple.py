"""
测试时间工具函数
"""

import pytest

from src.utils.time_utils import TimeUtils, parse_datetime, utc_now


@pytest.mark.unit
class TestTimeUtils:
    """测试时间工具函数"""

    def test_time_utils_now_utc(self):
        """测试获取当前UTC时间"""
        now = TimeUtils.now_utc()
        assert now.tzinfo is not None
        assert now.year >= 2025

    def test_time_utils_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        timestamp = 1705000000.0
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert dt.tzinfo is not None
        assert dt.year == 2024

    def test_time_utils_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2025, 1, 11, 12, 0, 0)
        timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_time_utils_format_datetime(self):
        """测试格式化日期时间"""
        dt = datetime(2025, 1, 11, 20, 30, 45)
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2025-01-11 20:30:45"

    def test_time_utils_parse_datetime(self):
        """测试解析日期时间字符串"""
        dt_str = "2025-01-11 20:30:45"
        dt = TimeUtils.parse_datetime(dt_str)
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 11

    def test_utc_now_function(self):
        """测试utc_now函数"""
        now = utc_now()
        assert now.tzinfo is not None

    def test_parse_datetime_function(self):
        """测试parse_datetime函数"""
        dt_str = "2025-01-11 20:30:45"
        dt = parse_datetime(dt_str)
        assert dt.year == 2025

    def test_parse_datetime_none(self):
        """测试解析None返回None"""
        dt = parse_datetime(None)
        assert dt is None
