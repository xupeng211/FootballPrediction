"""
test_date_time_utils - 第9部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.306895
包含项目: 5 个 (函数/类)
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest


class TestDateTimeUtilsPart9:
    """测试类"""

    def test_today(self):
        """测试获取今天日期"""
        today = DateUtils.today()
        assert isinstance(today, datetime.date)
        assert today == datetime.date.today()

    def test_now(self):
        """测试获取当前时间"""
        now = DateUtils.now()
        assert isinstance(now, datetime.datetime)
        # 允许几秒的误差
        assert abs((now - datetime.datetime.now()).total_seconds()) < 5

    def test_parse_date(self):
        """测试解析日期字符串"""
        result = DateUtils.parse_date("2023-12-25")
        expected = datetime.date(2023, 12, 25)
        assert result == expected

        # 测试自定义格式
        result = DateUtils.parse_date("25/12/2023", "%d/%m/%Y")
        expected = datetime.date(2023, 12, 25)
        assert result == expected
