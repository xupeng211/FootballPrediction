"""
test_date_time_utils - 第12部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307341
包含项目: 5 个 (函数/类)
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest


class TestDateTimeUtilsPart12:
    """测试类"""

    def test_parse_time(self):
        """测试解析时间字符串"""
        result = TimeUtils.parse_time("14:30:45")
        expected = datetime.time(14, 30, 45)
        assert result == expected

        # 测试自定义格式
        result = TimeUtils.parse_time("2:30 PM", "%I:%M %p")
        expected = datetime.time(14, 30, 0)
        assert result == expected

    def test_format_time(self):
        """测试格式化时间"""
        time_obj = datetime.time(14, 30, 45)
        result = TimeUtils.format_time(time_obj)
        assert result == "14:30:45"

        # 测试自定义格式
        result = TimeUtils.format_time(time_obj, "%I:%M %p")
        assert result == "02:30 PM"

    def test_add_hours(self):
        """测试添加小时"""
        base_time = datetime.time(14, 30, 0)

        result = TimeUtils.add_hours(base_time, 2)
        expected = datetime.time(16, 30, 0)
        assert result == expected

        # 跨日测试
        result = TimeUtils.add_hours(base_time, 12)
        expected = datetime.time(2, 30, 0)
        assert result == expected

    def test_add_minutes(self):
        """测试添加分钟"""
        base_time = datetime.time(14, 30, 0)

        result = TimeUtils.add_minutes(base_time, 30)
        expected = datetime.time(15, 0, 0)
        assert result == expected

        # 跨小时测试
        result = TimeUtils.add_minutes(base_time, 45)
        expected = datetime.time(15, 15, 0)
        assert result == expected
