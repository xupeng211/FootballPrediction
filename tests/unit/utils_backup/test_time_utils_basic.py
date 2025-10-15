"""时间工具基础测试"""

from datetime import datetime, timezone, timedelta
from src.utils.time_utils import TimeUtils, utc_now, parse_datetime


class TestTimeUtilsBasic:
    """时间工具基础测试"""

    def test_now_utc(self):
        """测试获取UTC时间"""
        result = TimeUtils.now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 使用固定时间戳
        timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(result, float)
        assert result == 1640995200.0

    def test_format_datetime(self):
        """测试格式化日期时间"""
        dt = datetime(2022, 1, 1, 12, 30, 45, tzinfo=timezone.utc)

        # 默认格式
        result = TimeUtils.format_datetime(dt)
        assert result == "2022-01-01 12:30:45"

        # 自定义格式
        result = TimeUtils.format_datetime(dt, "%Y/%m/%d")
        assert result == "2022/01/01"

    def test_parse_datetime(self):
        """测试解析日期时间字符串"""
        # 基本格式
        date_str = "2022-01-01 12:30:45"
        result = TimeUtils.parse_datetime(date_str)

        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_utc_now_function(self):
        """测试向后兼容函数"""
        result = utc_now()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_parse_datetime_function(self):
        """测试向后兼容解析函数"""
        # 标准格式
        result = parse_datetime("2022-01-01 12:30:45")
        assert isinstance(result, datetime)
        assert result.year == 2022

        # ISO格式
        result = parse_datetime("2022-01-01T12:30:45Z")
        assert isinstance(result, datetime)
        assert result.year == 2022

        # 日期格式
        result = parse_datetime("2022-01-01")
        assert isinstance(result, datetime)
        assert result.year == 2022

        # 无效格式
        result = parse_datetime("invalid")
        assert result is None

        # None输入
        result = parse_datetime(None)
        assert result is None
