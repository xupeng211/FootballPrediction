"""
test_date_time_utils - 第10部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307010
包含项目: 5 个 (函数/类)
"""


import pytest
from unittest.mock import Mock, patch
import sys
import os
import datetime



class TestDateTimeUtilsPart10:

    """测试类"""


    def test_format_date(self):

        """测试格式化日期"""
        date_obj = datetime.date(2023, 12, 25)
        result = DateUtils.format_date(date_obj)
        assert result == "2023-12-25"

        # 测试自定义格式
        result = DateUtils.format_date(date_obj, "%d/%m/%Y")
        assert result == "25/12/2023"


    def test_add_days(self):

        """测试添加天数"""
        base_date = datetime.date(2023, 12, 25)

        # 添加正数天
        result = DateUtils.add_days(base_date, 5)
        expected = datetime.date(2023, 12, 30)
        assert result == expected

        # 添加负数天
        result = DateUtils.add_days(base_date, -5)
        expected = datetime.date(2023, 12, 20)
        assert result == expected

        # 添加零天
        result = DateUtils.add_days(base_date, 0)
        assert result == base_date


    def test_add_months(self):

        """测试添加月份"""
        base_date = datetime.date(2023, 12, 25)

        # 添加正数月
        result = DateUtils.add_months(base_date, 2)
        expected = datetime.date(2024, 2, 25)
        assert result == expected

        # 添加负数月
        result = DateUtils.add_months(base_date, -3)
        expected = datetime.date(2023, 9, 25)
        assert result == expected

        # 跨年测试
        result = DateUtils.add_months(base_date, 1)
        expected = datetime.date(2024, 1, 25)
        assert result == expected


    def test_days_between(self):

        """测试计算日期间隔"""
        start = datetime.date(2023, 12, 25)
        end = datetime.date(2023, 12, 30)

        result = DateUtils.days_between(start, end)
        assert result == 5

        # 反向日期
        result = DateUtils.days_between(end, start)
        assert result == 5

        # 相同日期
        result = DateUtils.days_between(start, start)
        assert result == 0


    def test_is_weekend(self):

        """测试周末检查"""
        # 周六
        saturday = datetime.date(2023, 12, 23)  # 2023-12-23是周六
        assert DateUtils.is_weekend(saturday) is True

        # 周日
        sunday = datetime.date(2023, 12, 24)  # 2023-12-24是周日
        assert DateUtils.is_weekend(sunday) is True

        # 周一
        monday = datetime.date(2023, 12, 25)  # 2023-12-25是周一
        assert DateUtils.is_weekend(monday) is False


