from datetime import datetime
"""
test_date_time_utils - 第13部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307483
包含项目: 5 个 (函数/类)
"""


class TestDateTimeUtilsPart13:
    """测试类"""

    def test_time_to_seconds(self):
        """测试时间转秒数"""
        time_obj = datetime.time(14, 30, 45)
        result = TimeUtils.time_to_seconds(time_obj)
        expected = 14 * 3600 + 30 * 60 + 45
        assert result == expected

    def test_seconds_to_time(self):
        """测试秒数转时间"""
        seconds = 14 * 3600 + 30 * 60 + 45
        result = TimeUtils.seconds_to_time(seconds)
        expected = datetime.time(14, 30, 45)
        assert result == expected

    def test_time_conversion_roundtrip(self):
        """测试时间转换往返"""
        original_time = datetime.time(23, 59, 59)
        seconds = TimeUtils.time_to_seconds(original_time)
        converted_time = TimeUtils.seconds_to_time(seconds)
        assert original_time == converted_time

    """日期时间解析器测试"""

    def test_parse_datetime(self):
        """测试解析日期时间字符串"""
        result = DateTimeParser.parse_datetime("2023-12-25 14:30:45")
        expected = datetime.datetime(2023, 12, 25, 14, 30, 45)
        assert result == expected
