"""
test_date_time_utils - 第15部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307716
包含项目: 5 个 (函数/类)
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest


class TestDateTimeUtilsPart15:
    """测试类"""

    def test_get_utc_now(self):
        """测试获取UTC时间"""
        utc_now = TimeZoneUtils.get_utc_now()
        assert isinstance(utc_now, datetime.datetime)

        # 允许几秒的误差
        now = datetime.datetime.utcnow()
        assert abs((utc_now - now).total_seconds()) < 5

    def test_get_timezone_offset(self):
        """测试获取时区偏移"""
        assert TimeZoneUtils.get_timezone_offset("UTC") == 0
        assert TimeZoneUtils.get_timezone_offset("GMT") == 0
        assert TimeZoneUtils.get_timezone_offset("EST") == -5
        assert TimeZoneUtils.get_timezone_offset("JST") == 9

        # 测试未知时区
        assert TimeZoneUtils.get_timezone_offset("UNKNOWN") == 0

    def test_timezone_conversion(self):
        """测试时区转换（简化版本）"""
        dt = datetime.datetime(2023, 12, 25, 14, 30, 45)

        # 简化版本应该返回相同的时间
        result = TimeZoneUtils.to_utc(dt)
        assert result == dt

        result = TimeZoneUtils.from_utc(dt)
        assert result == dt

    """日期范围计算器测试"""

    def test_get_date_range(self):
        """测试获取日期范围"""
        start = datetime.date(2023, 12, 25)
        end = datetime.date(2023, 12, 27)

        result = DateRangeCalculator.get_date_range(start, end)
        expected = [
            datetime.date(2023, 12, 25),
            datetime.date(2023, 12, 26),
            datetime.date(2023, 12, 27),
        ]
        assert result == expected
