from typing import Optional

"""
DateUtils基础测试 - 针对性覆盖129行潜力代码
快速提升整体覆盖率冲刺7.5%目标
"""

from datetime import date, datetime, timedelta

import pytest

from src.utils.date_utils import DateUtils


class TestDateUtilsBasic:
    """DateUtils基础测试类 - 高效覆盖核心功能"""

    def test_format_datetime_basic(self):
        """测试基本日期时间格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        formatted = DateUtils.format_datetime(dt)
        assert formatted == "2024-01-15 14:30:45"
        assert isinstance(formatted, str)

    def test_format_datetime_custom_format(self):
        """测试自定义格式日期时间格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 测试不同格式
        assert DateUtils.format_datetime(dt, "%Y年%m月%d日") == "2024年01月15日"
        assert DateUtils.format_datetime(dt, "%m/%d/%Y") == "01/15/2024"
        assert DateUtils.format_datetime(dt, "%H:%M") == "14:30"

    def test_format_datetime_invalid_input(self):
        """测试无效输入格式化"""
        invalid_inputs = [None, "2024-01-15", 123, [], {}]

        for invalid_input in invalid_inputs:
            result = DateUtils.format_datetime(invalid_input)
            assert result == ""

    def test_parse_datetime_basic(self):
        """测试基本日期时间解析"""
        # 测试标准格式
        dt = DateUtils.parse_datetime("2024-01-15 14:30:45")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_datetime_custom_format(self):
        """测试自定义格式日期时间解析"""
        # 测试不同格式
        dt1 = DateUtils.parse_datetime("2024年01月15日", "%Y年%m月%d日")
        assert dt1 is not None
        assert dt1.year == 2024

        dt2 = DateUtils.parse_datetime("01/15/2024", "%m/%d/%Y")
        assert dt2 is not None
        assert dt2.month == 1

    def test_parse_datetime_invalid_input(self):
        """测试无效输入解析"""
        invalid_inputs = [None, 123, [], {}, "invalid date"]

        for invalid_input in invalid_inputs:
            result = DateUtils.parse_datetime(invalid_input)
            assert result is None

    def test_parse_datetime_empty_string(self):
        """测试空字符串解析"""
        result = DateUtils.parse_datetime("")
        assert result is None

    def test_add_days_basic(self):
        """测试基本天数添加"""
        base_date = datetime(2024, 1, 15)

        # 添加正数天
        result = DateUtils.add_days(base_date, 5)
        assert result.day == 20
        assert result.month == 1

        # 添加负数天
        result = DateUtils.add_days(base_date, -3)
        assert result.day == 12

    def test_add_days_month_boundary(self):
        """测试月份边界天数添加"""
        base_date = datetime(2024, 1, 30)

        # 跨月
        result = DateUtils.add_days(base_date, 2)
        assert result.day == 1
        assert result.month == 2

    def test_add_days_invalid_input(self):
        """测试无效输入天数添加（期望抛出ValueError）"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                DateUtils.add_days(invalid_input, 5)

    def test_get_weekday_basic(self):
        """测试基本星期几获取"""
        # 2024-01-15是星期一
        dt = datetime(2024, 1, 15)
        weekday = DateUtils.get_weekday(dt)
        assert weekday == 1  # 星期一

        # 2024-01-20是星期六
        saturday = datetime(2024, 1, 20)
        weekday_saturday = DateUtils.get_weekday(saturday)
        assert weekday_saturday == 6  # 星期六

    def test_get_weekday_invalid_input(self):
        """测试无效输入星期几获取"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.get_weekday(invalid_input)
            assert result is None

    def test_is_weekend_basic(self):
        """测试周末判断"""
        # 星期六
        saturday = datetime(2024, 1, 20)
        assert DateUtils.is_weekend(saturday) is True

        # 星期日
        sunday = datetime(2024, 1, 21)
        assert DateUtils.is_weekend(sunday) is True

        # 星期一
        monday = datetime(2024, 1, 22)
        assert DateUtils.is_weekend(monday) is False

    def test_is_weekend_invalid_input(self):
        """测试无效输入周末判断"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.is_weekend(invalid_input)
            assert result is False

    def test_get_month_start_basic(self):
        """测试获取月份开始日期"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        month_start = DateUtils.get_month_start(dt)

        assert month_start.day == 1
        assert month_start.month == 1
        assert month_start.year == 2024
        assert month_start.hour == 0
        assert month_start.minute == 0
        assert month_start.second == 0

    def test_get_month_start_different_months(self):
        """测试不同月份的开始日期"""
        months = [datetime(2024, i, 15) for i in range(1, 13)]

        for dt in months:
            start = DateUtils.get_month_start(dt)
            assert start.day == 1
            assert start.month == dt.month
            assert start.year == dt.year

    def test_get_month_start_invalid_input(self):
        """测试无效输入获取月份开始日期"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.get_month_start(invalid_input)
            assert result is None

    def test_get_month_end_basic(self):
        """测试获取月份结束日期"""
        # 31天的月份
        dt = datetime(2024, 1, 15)
        month_end = DateUtils.get_month_end(dt)
        assert month_end.day == 31
        assert month_end.month == 1
        assert month_end.year == 2024

        # 30天的月份
        dt2 = datetime(2024, 4, 15)
        month_end2 = DateUtils.get_month_end(dt2)
        assert month_end2.day == 30
        assert month_end2.month == 4

    def test_get_month_end_february(self):
        """测试二月份结束日期"""
        # 闰年 (2024年是闰年，2月有29天)
        dt = datetime(2024, 2, 15)
        month_end = DateUtils.get_month_end(dt)
        assert month_end.day == 29

    def test_get_month_end_invalid_input(self):
        """测试无效输入获取月份结束日期"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.get_month_end(invalid_input)
            assert result is None

    def test_days_between_basic(self):
        """测试日期间天数计算"""
        dt1 = datetime(2024, 1, 15)
        dt2 = datetime(2024, 1, 20)

        days = DateUtils.days_between(dt1, dt2)
        assert days == 5

    def test_days_between_negative(self):
        """测试反向日期天数计算"""
        dt1 = datetime(2024, 1, 20)
        dt2 = datetime(2024, 1, 15)

        days = DateUtils.days_between(dt1, dt2)
        assert days == -5

    def test_days_between_same_day(self):
        """测试同一天天数计算"""
        dt = datetime(2024, 1, 15)

        days = DateUtils.days_between(dt, dt)
        assert days == 0

    def test_days_between_invalid_input(self):
        """测试无效输入天数计算"""
        invalid_inputs = [None, "2024-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.days_between(invalid_input, datetime(2024, 1, 20))
            assert result is None

    def test_get_age_basic(self):
        """测试年龄计算"""
        birth_date = date(1990, 1, 15)
        current_date = date(2024, 1, 14)

        age = DateUtils.get_age(birth_date, current_date)
        assert age == 33

    def test_get_age_birthday_today(self):
        """测试生日当天年龄计算"""
        birth_date = date(1990, 1, 15)
        current_date = date(2024, 1, 15)

        age = DateUtils.get_age(birth_date, current_date)
        assert age == 34

    def test_get_age_invalid_input(self):
        """测试无效输入年龄计算"""
        invalid_inputs = [None, "1990-01-15", 123, []]

        for invalid_input in invalid_inputs:
            result = DateUtils.get_age(invalid_input, date(2024, 1, 15))
            assert result is None

    def test_is_leap_year_basic(self):
        """测试闰年判断"""
        # 闰年
        assert DateUtils.is_leap_year(2024) is True
        assert DateUtils.is_leap_year(2000) is True

        # 非闰年
        assert DateUtils.is_leap_year(2023) is False
        assert DateUtils.is_leap_year(1900) is False

    def test_is_leap_year_invalid_input(self):
        """测试无效输入闰年判断"""
        invalid_inputs = [None, "2024", 2024.5, [], {}]

        for invalid_input in invalid_inputs:
            result = DateUtils.is_leap_year(invalid_input)
            assert result is False

    def test_format_duration_basic(self):
        """测试时间长度格式化"""
        # 测试秒
        duration = DateUtils.format_duration(45)
        assert "45秒" in duration

        # 测试分钟
        duration = DateUtils.format_duration(125)
        assert "2分" in duration

        # 测试小时
        duration = DateUtils.format_duration(3665)
        assert "1小时" in duration

    def test_format_duration_invalid_input(self):
        """测试无效输入时间长度格式化"""
        invalid_inputs = [None, "invalid", [], {}]

        for invalid_input in invalid_inputs:
            result = DateUtils.format_duration(invalid_input)
            assert result == "0秒"

    def test_date_utils_workflow(self):
        """测试完整的日期工具工作流程"""
        # 1. 创建日期时间
        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 2. 格式化日期时间
        formatted = DateUtils.format_datetime(dt)
        assert formatted == "2024-01-15 14:30:45"

        # 3. 解析日期时间
        parsed = DateUtils.parse_datetime(formatted)
        assert parsed is not None
        assert parsed.year == 2024

        # 4. 日期计算
        future_date = DateUtils.add_days(dt, 10)
        days_between = DateUtils.days_between(dt, future_date)
        assert days_between == 10

        # 5. 获取月份边界
        month_start = DateUtils.get_month_start(dt)
        month_end = DateUtils.get_month_end(dt)
        assert month_start.day == 1
        assert month_end.day == 31

        # 6. 星期判断
        weekday = DateUtils.get_weekday(dt)
        is_weekend = DateUtils.is_weekend(dt)
        assert isinstance(weekday, int)
        assert isinstance(is_weekend, bool)

    def test_edge_cases_and_performance(self):
        """测试边界情况和性能"""
        # 测试极早日期
        early_date = datetime(1900, 1, 1)
        formatted = DateUtils.format_datetime(early_date)
        assert isinstance(formatted, str)

        # 测试未来日期
        future_date = datetime(2100, 12, 31, 23, 59, 59)
        formatted = DateUtils.format_datetime(future_date)
        assert isinstance(formatted, str)

        # 测试大量操作性能
        import time

        start_time = time.time()

        for i in range(100):
            dt = datetime(2024, 1, 1) + timedelta(days=i)
            DateUtils.format_datetime(dt)
            DateUtils.get_weekday(dt)
            DateUtils.is_weekend(dt)

        end_time = time.time()
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成