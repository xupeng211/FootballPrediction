from datetime import datetime, timezone
import pytest
from src.utils.time_utils import TimeUtils

"""
测试时间处理工具模块
"""


class TestTimeUtils:
    """测试TimeUtils类"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        now = TimeUtils.now_utc()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc
        # 检查时间差在合理范围内（1秒内）
        diff = abs((datetime.now(timezone.utc) - now).total_seconds())
        assert diff < 1.0

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 使用已知时间戳
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1

    def test_timestamp_to_datetime_current(self):
        """测试当前时间戳转换"""
        timestamp = datetime.now(timezone.utc).timestamp()
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc
        # 检查转换后的时间戳相同
        assert abs(dt.timestamp() - timestamp) < 0.001

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(timestamp, float)
        assert timestamp == 1609459200.0

    def test_datetime_to_timestamp_naive(self):
        """测试无时区datetime转时间戳"""
        # 注意：这可能会在系统中使用本地时区
        dt = datetime(2021, 1, 1, 0, 0, 0)
        timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(timestamp, float)

    def test_format_datetime_default(self):
        """测试默认格式化datetime"""
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2021-01-01 12:30:45"

    def test_format_datetime_custom(self):
        """测试自定义格式化datetime"""
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt, "%Y/%m/%d")
        assert formatted == "2021/01/01"

    def test_format_datetime_iso(self):
        """测试ISO格式化"""
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt, "%Y-%m-%dT%H:%M:%SZ")
        assert formatted == "2021-01-01T12:30:45Z"

    def test_parse_datetime_default(self):
        """测试默认格式解析datetime"""
        date_str = "2021-01-01 12:30:45"
        dt = TimeUtils.parse_datetime(date_str)
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_datetime_custom(self):
        """测试自定义格式解析datetime"""
        date_str = "2021/01/01"
        dt = TimeUtils.parse_datetime(date_str, "%Y/%m/%d")
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_datetime_iso(self):
        """测试解析ISO格式"""
        date_str = "2021-01-01T12:30:45Z"
        dt = TimeUtils.parse_datetime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_round_trip_timestamp(self):
        """测试时间戳往返转换"""
        original_timestamp = 1609459200.0
        dt = TimeUtils.timestamp_to_datetime(original_timestamp)
        new_timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert abs(original_timestamp - new_timestamp) < 0.001

    def test_round_trip_format(self):
        """测试格式化往返转换"""
        original_dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(original_dt)
        parsed = TimeUtils.parse_datetime(formatted)
        # 注意：parse_datetime返回的是naive datetime（无时区）
        assert parsed.year == original_dt.year
        assert parsed.month == original_dt.month
        assert parsed.day == original_dt.day
        assert parsed.hour == original_dt.hour
        assert parsed.minute == original_dt.minute
        assert parsed.second == original_dt.second

    def test_parse_invalid_format(self):
        """测试解析无效格式"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("invalid-date")

    def test_parse_mismatched_format(self):
        """测试格式不匹配"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2021/01/01", "%Y-%m-%d")

    def test_timestamp_edge_cases(self):
        """测试时间戳边界情况"""
        # Unix纪元时间
        timestamp = 0.0
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert dt.year == 1970
        assert dt.month == 1

    def test_negative_timestamp(self):
        """测试负时间戳（1970年之前）"""
        timestamp = -86400.0  # 1969-12-31
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert dt.year == 1969
        assert dt.month == 12
        assert dt.day == 31
