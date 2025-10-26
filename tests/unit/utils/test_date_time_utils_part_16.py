"""
test_date_time_utils - 第16部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307868
包含项目: 5 个 (函数/类)
"""


import pytest

from unittest.mock import Mock, patch

import sys

import os



class TestDateTimeUtilsPart16:

    """测试类"""


    def test_get_date_range_single_day(self):

        """测试单日范围"""
        start = datetime.date(2023, 12, 25)
        end = datetime.date(2023, 12, 25)

        result = DateRangeCalculator.get_date_range(start, end)
        expected = [datetime.date(2023, 12, 25)]
        assert result == expected


    def test_get_date_range_invalid(self):

        """测试无效范围"""
        start = datetime.date(2023, 12, 27)
        end = datetime.date(2023, 12, 25)

        result = DateRangeCalculator.get_date_range(start, end)
        assert result == []


    def test_get_business_days(self):

        """测试获取工作日"""
        start = datetime.date(2023, 12, 25)  # 周一
        end = datetime.date(2023, 12, 29)  # 周五

        result = DateRangeCalculator.get_business_days(start, end)
        # 应该包含5个工作日（周一到周五）
        assert len(result) == 5
        assert all(DateUtils.is_weekday(date) for date in result)


    def test_get_weekends(self):

        """测试获取周末"""
        start = datetime.date(2023, 12, 23)  # 周六
        end = datetime.date(2023, 12, 24)  # 周日

        result = DateRangeCalculator.get_weekends(start, end)
        expected = [
        datetime.date(2023, 12, 23),
        datetime.date(2023, 12, 24)
        ]
        assert result == expected


    def test_count_working_days(self):

        """测试计算工作日数量"""
        start = datetime.date(2023, 12, 25)  # 周一
        end = datetime.date(2023, 12, 29)  # 周五

        result = DateRangeCalculator.count_working_days(start, end)
        assert result == 5


