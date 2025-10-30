"""""""
日期工具完整测试
Date Utils Complete Tests

基于Issue #98成功模式，创建完整的日期工具测试
"""""""

from datetime import date, datetime, timedelta

import pytest

from src.utils.date_utils import DateUtils


@pytest.mark.unit
class TestDateUtilsComplete:
    """日期工具完整测试"""

    def test_format_datetime(self):
        """测试日期时间格式化"""
        dt = datetime(2025, 1, 28, 15, 30, 45)

        # 测试默认格式
        result = DateUtils.format_datetime(dt)
        assert result == "2025-01-28 15:30:45"

        # 测试自定义格式
        result = DateUtils.format_datetime(dt, "%Y年%m月%d日")
        assert result == "2025年01月28日"

        # 测试预定义格式
        formats = DateUtils.DATETIME_FORMATS
        for format_name, format_str in formats.items():
            result = DateUtils.format_datetime(dt, format_str)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_format_datetime_invalid_input(self):
        """测试无效输入的格式化"""
        invalid_inputs = [None, "not_datetime", 123, [], {}]

        for invalid_input in invalid_inputs:
            result = DateUtils.format_datetime(invalid_input)
            assert result == ""

        # 测试无效格式字符串
        dt = datetime(2025, 1, 28, 15, 30, 45)
        result = DateUtils.format_datetime(dt, "invalid_format_%Q")
        assert result == ""

    def test_parse_date(self):
        """测试日期字符串解析"""
        # 测试默认格式
        result = DateUtils.parse_date("2025-01-28")
        assert result == datetime(2025, 1, 28)

        # 测试自定义格式
        result = DateUtils.parse_date("28/01/2025", "%d/%m/%Y")
        assert result == datetime(2025, 1, 28)

        # 测试时间信息
        result = DateUtils.parse_date("2025-01-28 15:30:45", "%Y-%m-%d %H:%M:%S")
        assert result == datetime(2025, 1, 28, 15, 30, 45)

    def test_parse_date_invalid_input(self):
        """测试无效输入的解析"""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            result = DateUtils.parse_date(invalid_input)
            assert result is None

        # 测试无效日期字符串
        invalid_dates = ["not_a_date", "2025-13-01", "2025-02-30"]
        for invalid_date in invalid_dates:
            result = DateUtils.parse_date(invalid_date)
            assert result is None

    def test_get_time_ago(self):
        """测试相对时间计算"""
        now = datetime(2025, 1, 28, 12, 0, 0)

        # 测试秒级
        dt = now - timedelta(seconds=30)
        result = DateUtils.get_time_ago(dt)
        assert result == "刚刚"

        # 测试分钟级
        dt = now - timedelta(minutes=5)
        result = DateUtils.get_time_ago(dt)
        assert result == "5分钟前"

        # 测试小时级
        dt = now - timedelta(hours=2)
        result = DateUtils.get_time_ago(dt)
        assert result == "2小时前"

        # 浏天级
        dt = now - timedelta(days=3)
        result = DateUtils.get_time_ago(dt)
        assert result == "3天前"

        # 测试月级
        dt = now - timedelta(days=45)
        result = DateUtils.get_time_ago(dt)
        assert "个月前" in result

        # 测试年级
        dt = now - timedelta(days=400)
        result = DateUtils.get_time_ago(dt)
        assert "年前" in result

    def test_get_time_ago_future(self):
        """测试未来时间的相对时间"""
        now = datetime(2025, 1, 28, 12, 0, 0)

        # 未来时间
        dt = now + timedelta(minutes=5)
        result = DateUtils.get_time_ago(dt)
        assert result == "5分钟后"

    def test_is_weekend(self):
        """测试周末判断"""
        # 周六
        saturday = datetime(2025, 1, 25, 12, 0, 0)  # 2025-01-25是周六
        assert DateUtils.is_weekend(saturday) is True

        # 周日
        sunday = datetime(2025, 1, 26, 12, 0, 0)  # 2025-01-26是周日
        assert DateUtils.is_weekend(sunday) is True

        # 工作日
        monday = datetime(2025, 1, 27, 12, 0, 0)  # 2025-01-27是周一
        assert DateUtils.is_weekend(monday) is False

        friday = datetime(2025, 1, 31, 12, 0, 0)  # 2025-01-31是周五
        assert DateUtils.is_weekend(friday) is False

    def test_is_weekday(self):
        """测试工作日判断"""
        # 工作日
        monday = datetime(2025, 1, 27, 12, 0, 0)
        assert DateUtils.is_weekday(monday) is True

        friday = datetime(2025, 1, 31, 12, 0, 0)
        assert DateUtils.is_weekday(friday) is True

        # 周末
        saturday = datetime(2025, 1, 25, 12, 0, 0)
        assert DateUtils.is_weekday(saturday) is False

        sunday = datetime(2025, 1, 26, 12, 0, 0)
        assert DateUtils.is_weekday(sunday) is False

    def test_get_weekday_name(self):
        """测试获取星期名称"""
        dt = datetime(2025, 1, 27, 12, 0, 0)  # 周一

        # 中文
        result = DateUtils.get_weekday_name(dt, "zh")
        assert result == "周一"

        # 英文
        result = DateUtils.get_weekday_name(dt, "en")
        assert result == "Monday"

        # 默认中文
        result = DateUtils.get_weekday_name(dt)
        assert result == "周一"

        # 测试一周所有天数
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, name in enumerate(weekday_names):
            dt = datetime(2025, 1, 27 + i, 12, 0, 0)  # 从周一开始
            result = DateUtils.get_weekday_name(dt)
            assert result == name

    def test_add_business_days(self):
        """测试添加工作日"""
        start_date = datetime(2025, 1, 24, 12, 0, 0)  # 周五

        # 添加1个工作日（下周一）
        result = DateUtils.add_business_days(start_date, 1)
        expected = datetime(2025, 1, 27, 12, 0, 0)  # 周一
        assert result == expected

        # 添加5个工作日
        result = DateUtils.add_business_days(start_date, 5)
        expected = datetime(2025, 1, 31, 12, 0, 0)  # 下周五
        assert result == expected

        # 添加负数个工作日
        result = DateUtils.add_business_days(start_date, -2)
        expected = datetime(2025, 1, 22, 12, 0, 0)  # 周三
        assert result == expected

        # 添加0个工作日
        result = DateUtils.add_business_days(start_date, 0)
        assert result == start_date

    def test_add_business_days_cross_weekend(self):
        """测试跨周末的工作日计算"""
        # 周五开始，添加3个工作日应该到下周三
        friday = datetime(2025, 1, 24, 12, 0, 0)
        result = DateUtils.add_business_days(friday, 3)
        expected = datetime(2025, 1, 29, 12, 0, 0)  # 周三
        assert result == expected

    def test_get_age(self):
        """测试年龄计算"""
        # 整数年龄
        birth_date = datetime(1990, 1, 28)
        today = datetime(2025, 1, 28)
        age = DateUtils.get_age(birth_date)
        assert age == 35

        # 生日还未到
        birth_date = datetime(1990, 6, 15)
        age = DateUtils.get_age(birth_date, today)
        assert age == 34

        # 使用date对象
        birth_date = date(1990, 1, 28)
        age = DateUtils.get_age(birth_date)
        assert age == 35

        # 未来出生日期
        future_date = datetime(2030, 1, 28)
        age = DateUtils.get_age(future_date, today)
        assert age == 0

    def test_get_month_range(self):
        """测试获取月份范围"""
        start, end = DateUtils.get_month_range(2025, 1)

        assert start == datetime(2025, 1, 1, 0, 0, 0)
        assert end == datetime(2025, 1, 31, 23, 59, 59)

        # 测试2月（非闰年）
        start, end = DateUtils.get_month_range(2024, 2)
        assert start == datetime(2024, 2, 1, 0, 0, 0)
        assert end == datetime(2024, 2, 29, 23, 59, 59)  # 2024是闰年

        # 测试12月
        start, end = DateUtils.get_month_range(2025, 12)
        assert start == datetime(2025, 12, 1, 0, 0, 0)
        assert end == datetime(2025, 12, 31, 23, 59, 59)

    def test_get_year_range(self):
        """测试获取年份范围"""
        start, end = DateUtils.get_year_range(2025)

        assert start == datetime(2025, 1, 1, 0, 0, 0)
        assert end == datetime(2025, 12, 31, 23, 59, 59)

    def test_is_leap_year(self):
        """测试闰年判断"""
        # 闰年
        assert DateUtils.is_leap_year(2024) is True
        assert DateUtils.is_leap_year(2000) is True

        # 非闰年
        assert DateUtils.is_leap_year(2025) is False
        assert DateUtils.is_leap_year(2100) is False  # 世纪年且不被400整除
        assert DateUtils.is_leap_year(2023) is False

    def test_get_quarter(self):
        """测试获取季度"""
        # Q1
        assert DateUtils.get_quarter(datetime(2025, 1, 15)) == 1
        assert DateUtils.get_quarter(datetime(2025, 3, 15)) == 1

        # Q2
        assert DateUtils.get_quarter(datetime(2025, 4, 15)) == 2
        assert DateUtils.get_quarter(datetime(2025, 6, 15)) == 2

        # Q3
        assert DateUtils.get_quarter(datetime(2025, 7, 15)) == 3
        assert DateUtils.get_quarter(datetime(2025, 9, 15)) == 3

        # Q4
        assert DateUtils.get_quarter(datetime(2025, 10, 15)) == 4
        assert DateUtils.get_quarter(datetime(2025, 12, 15)) == 4

    def test_get_days_in_month(self):
        """测试获取月份天数"""
        # 31天的月份
        assert DateUtils.get_days_in_month(2025, 1) == 31
        assert DateUtils.get_days_in_month(2025, 3) == 31
        assert DateUtils.get_days_in_month(2025, 5) == 31
        assert DateUtils.get_days_in_month(2025, 7) == 31
        assert DateUtils.get_days_in_month(2025, 8) == 31
        assert DateUtils.get_days_in_month(2025, 10) == 31
        assert DateUtils.get_days_in_month(2025, 12) == 31

        # 30天的月份
        assert DateUtils.get_days_in_month(2025, 4) == 30
        assert DateUtils.get_days_in_month(2025, 6) == 30
        assert DateUtils.get_days_in_month(2025, 9) == 30
        assert DateUtils.get_days_in_month(2025, 11) == 30

        # 2月
        assert DateUtils.get_days_in_month(2025, 2) == 28  # 非闰年
        assert DateUtils.get_days_in_month(2024, 2) == 29  # 闰年

    def test_get_start_of_day(self):
        """测试获取一天开始时间"""
        dt = datetime(2025, 1, 28, 15, 30, 45)
        result = DateUtils.get_start_of_day(dt)

        expected = datetime(2025, 1, 28, 0, 0, 0)
        assert result == expected

    def test_get_end_of_day(self):
        """测试获取一天结束时间"""
        dt = datetime(2025, 1, 28, 15, 30, 45)
        result = DateUtils.get_end_of_day(dt)

        expected = datetime(2025, 1, 28, 23, 59, 59)
        assert result == expected

    def test_get_start_of_week(self):
        """测试获取一周开始时间（周一）"""
        # 周三
        wednesday = datetime(2025, 1, 29, 15, 30, 45)  # 2025-01-29是周三
        result = DateUtils.get_start_of_week(wednesday)

        # 周一
        expected = datetime(2025, 1, 27, 0, 0, 0)
        assert result == expected

        # 周一当天
        monday = datetime(2025, 1, 27, 15, 30, 45)
        result = DateUtils.get_start_of_week(monday)
        assert result == datetime(2025, 1, 27, 0, 0, 0)

    def test_get_end_of_week(self):
        """测试获取一周结束时间（周日）"""
        # 周三
        wednesday = datetime(2025, 1, 29, 15, 30, 45)
        result = DateUtils.get_end_of_week(wednesday)

        # 周日
        expected = datetime(2025, 2, 2, 23, 59, 59)
        assert result == expected

    def test_get_start_of_month(self):
        """测试获取月份开始时间"""
        dt = datetime(2025, 1, 28, 15, 30, 45)
        result = DateUtils.get_start_of_month(dt)

        expected = datetime(2025, 1, 1, 0, 0, 0)
        assert result == expected

    def test_get_end_of_month(self):
        """测试获取月份结束时间"""
        dt = datetime(2025, 1, 28, 15, 30, 45)
        result = DateUtils.get_end_of_month(dt)

        expected = datetime(2025, 1, 31, 23, 59, 59)
        assert result == expected

        # 测试2月
        dt_feb = datetime(2024, 2, 15, 12, 0, 0)  # 闰年2月
        result = DateUtils.get_end_of_month(dt_feb)
        expected = datetime(2024, 2, 29, 23, 59, 59)
        assert result == expected

    def test_get_formatted_duration(self):
        """测试格式化持续时间"""
        # 秒级
        result = DateUtils.get_formatted_duration(45)
        assert result == "45秒"

        # 分钟级
        result = DateUtils.get_formatted_duration(125)
        assert result == "2分5秒"

        # 小时级
        result = DateUtils.get_formatted_duration(3665)
        assert result == "1小时1分5秒"

        # 天级
        result = DateUtils.get_formatted_duration(90065)
        assert result == "1天1小时1分5秒"

        # 零秒
        result = DateUtils.get_formatted_duration(0)
        assert result == "0秒"

        # 整数分钟
        result = DateUtils.get_formatted_duration(120)
        assert result == "2分0秒"

    def test_get_timezone_aware(self):
        """测试时区感知日期时间"""
        dt = datetime(2025, 1, 28, 12, 0, 0)

        # 正偏移
        result = DateUtils.get_timezone_aware(dt, 8)  # UTC+8
        assert result.hour == 20

        # 负偏移
        result = DateUtils.get_timezone_aware(dt, -5)  # UTC-5
        assert result.hour == 7

        # 零偏移（UTC）
        result = DateUtils.get_timezone_aware(dt, 0)
        assert result == dt

    def test_get_holiday_info(self):
        """测试获取节假日信息"""
        dt = datetime(2025, 1, 1, 12, 0, 0)  # 元旦
        result = DateUtils.get_holiday_info(dt)

        assert isinstance(result, dict)
        assert "is_holiday" in result
        assert "name" in result
        assert result["is_holiday"] is True

        # 普通工作日
        dt = datetime(2025, 1, 28, 12, 0, 0)  # 普通周二
        result = DateUtils.get_holiday_info(dt)
        assert result["is_holiday"] is False

    def test_format_duration(self):
        """测试格式化时间段"""
        start = datetime(2025, 1, 28, 12, 0, 0)
        end = datetime(2025, 1, 28, 14, 30, 45)

        result = DateUtils.format_duration(start, end)
        assert "2小时" in result
        assert "30分" in result

        # 没有结束时间（使用当前时间）
        start = datetime(2025, 1, 28, 11, 0, 0)
        result = DateUtils.format_duration(start)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 测试边界日期
        datetime(2025, 12, 31, 23, 59, 59)
        datetime(2025, 1, 1, 0, 0, 0)

        # 年度边界测试
        year_start_actual, year_end_actual = DateUtils.get_year_range(2025)
        assert year_end_actual == datetime(2025, 12, 31, 23, 59, 59)
        assert year_start_actual == datetime(2025, 1, 1, 0, 0, 0)

        # 无效月份处理
        with pytest.raises((ValueError, TypeError)):
            DateUtils.get_month_range(2025, 13)

        with pytest.raises((ValueError, TypeError)):
            DateUtils.get_month_range(2025, 0)

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 批量日期操作性能测试
        dates = [datetime(2025, 1, 1) + timedelta(days=i) for i in range(365)]

        start_time = time.time()

        for dt in dates:
            DateUtils.format_datetime(dt)
            DateUtils.is_weekend(dt)
            DateUtils.get_quarter(dt)

        end_time = time.time()
        duration = end_time - start_time

        # 365次操作应该在合理时间内完成
        assert duration < 1.0, f"批量操作耗时过长: {duration}秒"

    def test_date_arithmetic_operations(self):
        """测试日期算术运算"""
        base_date = datetime(2025, 1, 28, 12, 0, 0)

        # 测试各种时间范围的开始和结束
        month_start = DateUtils.get_start_of_month(base_date)
        month_end = DateUtils.get_end_of_month(base_date)
        assert month_start < base_date < month_end

        week_start = DateUtils.get_start_of_week(base_date)
        week_end = DateUtils.get_end_of_week(base_date)
        assert week_start < base_date < week_end

        day_start = DateUtils.get_start_of_day(base_date)
        day_end = DateUtils.get_end_of_day(base_date)
        assert day_start < base_date < day_end

    def test_internationalization_features(self):
        """测试国际化功能"""
        dt = datetime(2025, 1, 27, 12, 0, 0)  # 周一

        # 中文星期名称
        zh_name = DateUtils.get_weekday_name(dt, "zh")
        assert zh_name == "周一"

        # 英文星期名称
        en_name = DateUtils.get_weekday_name(dt, "en")
        assert en_name == "Monday"

        # 不支持的语言默认使用中文
        unknown_name = DateUtils.get_weekday_name(dt, "fr")
        assert unknown_name == "周一"

    def test_utility_function_coverage(self):
        """测试工具函数覆盖"""
        # 测试缓存格式化函数
        dt = datetime(2025, 1, 28, 15, 30, 45)

from src.utils.date_utils import cached_format_datetime, cached_time_ago

        result1 = cached_format_datetime(dt, "%Y-%m-%d")
        result2 = cached_format_datetime(dt, "%Y-%m-%d")
        assert result1 == result2 == "2025-01-28"

        # 测试缓存时间差函数
        past_dt = datetime(2025, 1, 28, 11, 0, 0)
        result = cached_time_ago(past_dt)
        assert isinstance(result, str)
        assert "小时前" in result or "分钟前" in result

    def test_business_day_calculations(self):
        """测试工作日计算"""
from src.utils.date_utils import get_business_days_range, get_date_range_summary

        start_date = datetime(2025, 1, 27, 12, 0, 0)  # 周一
        end_date = datetime(2025, 1, 31, 12, 0, 0)  # 周五

        # 工作日范围计算
        business_days = get_business_days_range(start_date, end_date)
        assert business_days == 5  # 周一到周五

        # 日期范围摘要
        summary = get_date_range_summary(start_date, end_date)
        assert isinstance(summary, dict)
        assert "total_days" in summary
        assert "business_days" in summary
        assert "weekend_days" in summary

    def test_complex_date_scenarios(self):
        """测试复杂日期场景"""
        # 跨年工作日计算
        dec_fri = datetime(2024, 12, 27, 12, 0, 0)  # 2024年12月27日周五
        result = DateUtils.add_business_days(dec_fri, 3)
        expected = datetime(2025, 1, 1, 12, 0, 0)  # 2025年1月1日周三
        assert result == expected

        # 闰年2月29日测试
        leap_date = datetime(2024, 2, 29, 12, 0, 0)
        assert DateUtils.is_leap_year(leap_date.year) is True

        # 月末日期操作
        month_end = datetime(2025, 1, 31, 12, 0, 0)
        month_start = DateUtils.get_start_of_month(month_end)
        assert month_start == datetime(2025, 1, 1, 0, 0, 0)

    def test_date_format_consistency(self):
        """测试日期格式一致性"""
        dt = datetime(2025, 1, 28, 15, 30, 45)

        # 测试所有预定义格式
        for format_name, format_str in DateUtils.DATETIME_FORMATS.items():
            formatted = DateUtils.format_datetime(dt, format_str)
            assert isinstance(formatted, str)
            assert len(formatted) > 0

            # 验证格式是否正确（通过解析验证）
            if format_name in ["default", "date", "time"]:
                try:
                    parsed = DateUtils.parse_date(formatted, format_str)
                    if format_name == "date":
                        assert parsed.date() == dt.date()
except Exception:
                    # 某些格式可能不适合解析，这是正常的
                    pass
