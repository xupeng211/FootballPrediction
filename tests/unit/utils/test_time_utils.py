"""时间处理工具模块测试"""

import pytest
from datetime import datetime, timezone, timedelta

from src.utils.time_utils import TimeUtils


class TestTimeUtils:
    """测试时间处理工具类"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        now = TimeUtils.now_utc()

        # 验证返回的是datetime对象
        assert isinstance(now, datetime)

        # 验证时区是UTC
        assert now.tzinfo == timezone.utc

        # 验证时间是最近的（1秒内）
        now2 = TimeUtils.now_utc()
        assert abs((now2 - now).total_seconds()) < 1

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        # 创建一个已知的时间戳
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        timestamp = dt.timestamp()

        # 转换回datetime
        result = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0

    def test_timestamp_to_datetime_float(self):
        """测试带小数的时间戳转换"""
        # 测试精确到毫秒的时间戳
        dt = datetime(2025, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        timestamp = dt.timestamp()

        result = TimeUtils.timestamp_to_datetime(timestamp)

        # 验证微秒部分
        assert result.microsecond == 123456

    def test_timestamp_to_datetime_zero(self):
        """测试零时间戳转换"""
        result = TimeUtils.timestamp_to_datetime(0.0)

        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == timezone.utc

    def test_timestamp_to_datetime_negative(self):
        """测试负时间戳转换"""
        # 1970年之前的时间
        result = TimeUtils.timestamp_to_datetime(-86400.0)  # 1969年12月31日

        assert result.year == 1969
        assert result.month == 12
        assert result.day == 31

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        assert timestamp > 0

        # 验证可以反向转换
        converted_back = TimeUtils.timestamp_to_datetime(timestamp)
        assert converted_back.year == 2025
        assert converted_back.month == 1
        assert converted_back.day == 15

    def test_datetime_to_timestamp_with_microseconds(self):
        """测试带微秒的datetime转时间戳"""
        dt = datetime(2025, 1, 15, 10, 30, 0, 500000, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        # 验证时间戳包含小数部分
        assert timestamp != int(timestamp)

        # 验证可以精确转换回来
        converted_back = TimeUtils.timestamp_to_datetime(timestamp)
        assert abs(converted_back.microsecond - 500000) < 1000  # 允许小误差

    def test_datetime_to_timestamp_without_timezone(self):
        """测试不带时区的datetime转时间戳"""
        # 创建不带时区的datetime
        dt = datetime(2025, 1, 15, 10, 30, 0)

        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        # 没有时区的datetime会被当作本地时间处理

    def test_format_datetime_default(self):
        """测试默认格式化datetime"""
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt)

        assert formatted == "2025-01-15 10:30:45"

    def test_format_datetime_custom_format(self):
        """测试自定义格式化datetime"""
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        # 测试不同格式
        assert TimeUtils.format_datetime(dt, "%Y/%m/%d") == "2025/01/15"
        assert TimeUtils.format_datetime(dt, "%d-%m-%Y %H:%M") == "15-01-2025 10:30"
        assert TimeUtils.format_datetime(dt, "%B %d, %Y") == "January 15, 2025"
        assert TimeUtils.format_datetime(dt, "%Y年%m月%d日") == "2025年01月15日"

    def test_format_datetime_edge_cases(self):
        """测试边界情况的格式化"""
        # 测试午夜时间
        midnight = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert TimeUtils.format_datetime(midnight) == "2025-01-01 00:00:00"

        # 测试年末时间
        year_end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert TimeUtils.format_datetime(year_end) == "2025-12-31 23:59:59"

    def test_parse_datetime_default(self):
        """测试默认格式解析datetime"""
        dt = TimeUtils.parse_datetime("2025-01-15 10:30:45")

        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_datetime_custom_format(self):
        """测试自定义格式解析datetime"""
        dt = TimeUtils.parse_datetime("15/01/2025", "%d/%m/%Y")
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_edge_cases(self):
        """测试边界情况的datetime解析"""
        # 测试不同的日期格式
        assert TimeUtils.parse_datetime("2025-01-01", "%Y-%m-%d").day == 1
        assert TimeUtils.parse_datetime("2025-12-31", "%Y-%m-%d").month == 12

        # 测试时间部分
        dt = TimeUtils.parse_datetime("2025-01-15 23:59:59")
        assert dt.hour == 23
        assert dt.minute == 59
        assert dt.second == 59

    def test_parse_datetime_invalid_format(self):
        """测试无效格式的datetime解析"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("invalid date")

        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2025-01-15", "%Y/%m/%d")  # 格式不匹配

    def test_round_trip_conversion(self):
        """测试往返转换"""
        # datetime -> timestamp -> datetime
        original_dt = TimeUtils.now_utc()
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        # 转换后的时间应该接近原始时间（可能有微秒差异）
        assert abs((converted_dt - original_dt).total_seconds()) < 0.001

    def test_string_datetime_conversion(self):
        """测试字符串和datetime转换"""
        # datetime -> string -> datetime
        original_dt = TimeUtils.now_utc()
        formatted = TimeUtils.format_datetime(original_dt)
        parsed_dt = TimeUtils.parse_datetime(formatted)

        # 比较年月日时分秒（忽略微秒和时区）
        assert parsed_dt.year == original_dt.year
        assert parsed_dt.month == original_dt.month
        assert parsed_dt.day == original_dt.day
        assert parsed_dt.hour == original_dt.hour
        assert parsed_dt.minute == original_dt.minute
        assert parsed_dt.second == original_dt.second

    def test_leap_year_handling(self):
        """测试闰年处理"""
        # 测试闰年2月29日
        leap_date = TimeUtils.parse_datetime("2024-02-29 00:00:00")
        assert leap_date.year == 2024
        assert leap_date.month == 2
        assert leap_date.day == 29

        # 非闰年应该报错
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("2023-02-29 00:00:00")

    def test_time_arithmetic(self):
        """测试时间运算"""
        # 获取当前时间
        now = TimeUtils.now_utc()

        # 加1小时
        later = now + timedelta(hours=1)
        timestamp_later = TimeUtils.datetime_to_timestamp(later)

        # 验证时间差
        assert timestamp_later > TimeUtils.datetime_to_timestamp(now)
        assert timestamp_later - TimeUtils.datetime_to_timestamp(now) > 3600 - 1  # 允许小误差

    def test_timezone_handling(self):
        """测试时区处理"""
        # 创建不同时区的时间
        utc_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(utc_time)

        # 转换回UTC时间应该相同
        converted_utc = TimeUtils.timestamp_to_datetime(timestamp)
        assert converted_utc.hour == 10

    def test_large_timestamp_values(self):
        """测试大的时间戳值"""
        # 2038年问题测试（32位时间戳溢出）
        future_dt = datetime(2040, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        future_timestamp = TimeUtils.datetime_to_timestamp(future_dt)

        assert future_timestamp > 2147483647  # 超过32位有符号整数最大值

        # 验证可以转换回来
        converted_dt = TimeUtils.timestamp_to_datetime(future_timestamp)
        assert converted_dt.year == 2040

    def test_precise_timestamp(self):
        """测试精确时间戳"""
        # 连续获取两个时间戳
        ts1 = TimeUtils.datetime_to_timestamp(TimeUtils.now_utc())
        ts2 = TimeUtils.datetime_to_timestamp(TimeUtils.now_utc())

        # 第二个应该大于第一个
        assert ts2 > ts1

        # 差异应该很小
        assert ts2 - ts1 < 1  # 小于1秒