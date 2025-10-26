"""
test_date_time_utils - 第18部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.308227
包含项目: 5 个 (函数/类)
"""


import pytest

from unittest.mock import Mock, patch

import sys

import os



class TestDateTimeUtilsPart18:

    """测试类"""


    def test_get_next_working_day(self):

        """测试获取下一个工作日"""
        # 周五的下个工作日是周一
        friday = datetime.date(2023, 12, 22)
        result = WorkingDayCalculator.get_next_working_day(friday)
        expected = datetime.date(2023, 12, 25)
        assert result == expected

        # 周三的下个工作日是周四
        wednesday = datetime.date(2023, 12, 27)
        result = WorkingDayCalculator.get_next_working_day(wednesday)
        expected = datetime.date(2023, 12, 28)
        assert result == expected


    def test_get_previous_working_day(self):

        """测试获取上一个工作日"""
        # 周一的上个工作日是周五
        monday = datetime.date(2023, 12, 25)
        result = WorkingDayCalculator.get_previous_working_day(monday)
        expected = datetime.date(2023, 12, 22)
        assert result == expected


    def test_working_day_with_holidays(self):

        """测试工作日计算（排除假期）"""
        start = datetime.date(2023, 12, 22)  # 周五
        holidays = [datetime.date(2023, 12, 25)]  # 周一为假期

        result = WorkingDayCalculator.get_next_working_day(start, holidays)
        expected = datetime.date(2023, 12, 26)  # 周二（跳过周一假期）
        assert result == expected




    """日期时间工具集成测试"""


    def test_date_time_combination(self):

        """测试日期时间组合"""
        if IMPORT_SUCCESS:
            date_obj = datetime.date(2023, 12, 25)
            time_obj = datetime.time(14, 30, 45)

            # 组合日期和时间
            combined = datetime.datetime.combine(date_obj, time_obj)
            assert combined == datetime.datetime(2023, 12, 25, 14, 30, 45)


