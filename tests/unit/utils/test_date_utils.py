"""
日期工具测试
"""

import pytest
from datetime import datetime, timedelta, date
from typing import Optional, List, Tuple


class DateUtils:
    """日期工具类"""

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """判断是否为闰年"""
        if year % 4 != 0:
            return False
        elif year % 100 != 0:
            return True
        else:
            return year % 400 == 0

    @staticmethod
    def days_in_month(year: int, month: int) -> int:
        """获取某年某月的天数"""
        if month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            return 29 if DateUtils.is_leap_year(year) else 28
        else:
            return 31

    @staticmethod
    def get_weekday(date_obj: date) -> str:
        """获取星期几"""
        weekdays = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        return weekdays[date_obj.weekday()]

    @staticmethod
    def get_weekday_chinese(date_obj: date) -> str:
        """获取中文星期几"""
        weekdays = [
            "星期一",
            "星期二",
            "星期三",
            "星期四",
            "星期五",
            "星期六",
            "星期日",
        ]
        return weekdays[date_obj.weekday()]

    @staticmethod
    def add_business_days(start_date: date, days: int) -> date:
        """添加工作日（跳过周末）"""
        current = start_date
        remaining = days

        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:  # 周一到周五
                remaining -= 1

        return current

    @staticmethod
    def get_age(birth_date: date, reference_date: Optional[date] = None) -> int:
        """计算年龄"""
        if reference_date is None:
            reference_date = date.today()

        age = reference_date.year - birth_date.year
        if (reference_date.month, reference_date.day) < (
            birth_date.month,
            birth_date.day,
        ):
            age -= 1

        return age

    @staticmethod
    def get_quarter(date_obj: date) -> int:
        """获取季度"""
        return (date_obj.month - 1) // 3 + 1

    @staticmethod
    def get_week_of_year(date_obj: date) -> int:
        """获取一年中的第几周"""
        return date_obj.isocalendar()[1]

    @staticmethod
    def get_day_of_year(date_obj: date) -> int:
        """获取一年中的第几天"""
        return date_obj.timetuple().tm_yday

    @staticmethod
    def is_weekend(date_obj: date) -> bool:
        """判断是否为周末"""
        return date_obj.weekday() >= 5

    @staticmethod
    def is_same_day(date1: date, date2: date) -> bool:
        """判断是否为同一天"""
        return (
            date1.year == date2.year
            and date1.month == date2.month
            and date1.day == date2.day
        )

    @staticmethod
    def get_date_range(start_date: date, end_date: date) -> List[date]:
        """获取日期范围列表"""
        if start_date > end_date:
            return []

        delta = end_date - start_date
        return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    @staticmethod
    def get_business_days_in_month(year: int, month: int) -> int:
        """获取某月的工作日数"""
        start_date = date(year, month, 1)
        end_date = date(year, month, DateUtils.days_in_month(year, month))

        business_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                business_days += 1
            current += timedelta(days=1)

        return business_days

    @staticmethod
    def get_month_name(month: int, chinese: bool = False) -> str:
        """获取月份名称"""
        if chinese:
            months = [
                "一月",
                "二月",
                "三月",
                "四月",
                "五月",
                "六月",
                "七月",
                "八月",
                "九月",
                "十月",
                "十一月",
                "十二月",
            ]
        else:
            months = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]

        if 1 <= month <= 12:
            return months[month - 1]
        return ""

    @staticmethod
    def format_duration(start_date: date, end_date: date, chinese: bool = False) -> str:
        """格式化日期间隔"""
        delta = end_date - start_date
        years = delta.days // 365
        months = (delta.days % 365) // 30
        days = delta.days % 30

        if chinese:
            parts = []
            if years > 0:
                parts.append(f"{years}年")
            if months > 0:
                parts.append(f"{months}个月")
            if days > 0:
                parts.append(f"{days}天")
            return "".join(parts) if parts else "0天"
        else:
            parts = []
            if years > 0:
                parts.append(f"{years} year{'s' if years > 1 else ''}")
            if months > 0:
                parts.append(f"{months} month{'s' if months > 1 else ''}")
            if days > 0:
                parts.append(f"{days} day{'s' if days > 1 else ''}")
            return ", ".join(parts) if parts else "0 days"

    @staticmethod
    def get_zodiac_sign(birth_date: date) -> str:
        """获取星座"""
        zodiac_dates = [
            ((1, 20), (2, 18), "Aquarius"),
            ((2, 19), (3, 20), "Pisces"),
            ((3, 21), (4, 19), "Aries"),
            ((4, 20), (5, 20), "Taurus"),
            ((5, 21), (6, 20), "Gemini"),
            ((6, 21), (7, 22), "Cancer"),
            ((7, 23), (8, 22), "Leo"),
            ((8, 23), (9, 22), "Virgo"),
            ((9, 23), (10, 22), "Libra"),
            ((10, 23), (11, 21), "Scorpio"),
            ((11, 22), (12, 21), "Sagittarius"),
            ((12, 22), (1, 19), "Capricorn"),
        ]

        month_day = (birth_date.month, birth_date.day)
        for (start_month, start_day), (end_month, end_day), sign in zodiac_dates:
            if start_month == end_month:
                if start_month == month_day[0] and start_day <= month_day[1] <= end_day:
                    return sign
            elif (
                (month_day[0] == start_month and month_day[1] >= start_day)
                or (month_day[0] == end_month and month_day[1] <= end_day)
                or (start_month < month_day[0] < end_month)
            ):
                return sign

        return "Capricorn"

    @staticmethod
    def get_chinese_zodiac(year: int) -> str:
        """获取生肖"""
        zodiacs = [
            "Rat",
            "Ox",
            "Tiger",
            "Rabbit",
            "Dragon",
            "Snake",
            "Horse",
            "Goat",
            "Monkey",
            "Rooster",
            "Dog",
            "Pig",
        ]
        return zodiacs[(year - 4) % 12]

    @staticmethod
    def is_date_in_range(check_date: date, start_date: date, end_date: date) -> bool:
        """检查日期是否在范围内"""
        return start_date <= check_date <= end_date

    @staticmethod
    def get_overlap(
        range1_start: date, range1_end: date, range2_start: date, range2_end: date
    ) -> Optional[Tuple[date, date]]:
        """获取两个日期范围的重叠部分"""
        latest_start = max(range1_start, range2_start)
        earliest_end = min(range1_end, range2_end)

        if latest_start <= earliest_end:
            return (latest_start, earliest_end)
        return None

    @staticmethod
    def get_last_day_of_month(year: int, month: int) -> date:
        """获取某月的最后一天"""
        return date(year, month, DateUtils.days_in_month(year, month))

    @staticmethod
    def get_first_day_of_month(year: int, month: int) -> date:
        """获取某月的第一天"""
        return date(year, month, 1)


@pytest.mark.unit

class TestDateUtils:
    """测试日期工具类"""

    def test_is_leap_year(self):
        """测试闰年判断"""
        assert DateUtils.is_leap_year(2000) is True  # 能被400整除
        assert DateUtils.is_leap_year(2020) is True  # 能被4整除但不能被100整除
        assert DateUtils.is_leap_year(1900) is False  # 能被100整除但不能被400整除
        assert DateUtils.is_leap_year(2021) is False  # 不能被4整除
        assert DateUtils.is_leap_year(2400) is True  # 能被400整除

    def test_days_in_month(self):
        """测试每月天数"""
        assert DateUtils.days_in_month(2020, 2) == 29  # 闰年2月
        assert DateUtils.days_in_month(2021, 2) == 28  # 平年2月
        assert DateUtils.days_in_month(2021, 1) == 31  # 1月
        assert DateUtils.days_in_month(2021, 4) == 30  # 4月
        assert DateUtils.days_in_month(2021, 12) == 31  # 12月

    def test_get_weekday(self):
        """测试获取星期几"""
        # 2021年10月11日是星期一
        test_date = date(2021, 10, 11)
        assert DateUtils.get_weekday(test_date) == "Monday"

        # 2021年10月16日是星期六
        test_date = date(2021, 10, 16)
        assert DateUtils.get_weekday(test_date) == "Saturday"

    def test_get_weekday_chinese(self):
        """测试获取中文星期几"""
        test_date = date(2021, 10, 11)  # 星期一
        assert DateUtils.get_weekday_chinese(test_date) == "星期一"

        test_date = date(2021, 10, 16)  # 星期六
        assert DateUtils.get_weekday_chinese(test_date) == "星期六"

    def test_add_business_days(self):
        """测试添加工作日"""
        start = date(2021, 10, 11)  # 星期一

        # 添加5个工作日（应该是下周一）
        _result = DateUtils.add_business_days(start, 5)
        assert _result.weekday() == 0  # 星期一
        assert _result == date(2021, 10, 18)

        # 添加1个工作日
        _result = DateUtils.add_business_days(start, 1)
        assert _result == date(2021, 10, 12)  # 星期二

        # 从周五开始添加1天
        friday = date(2021, 10, 15)
        _result = DateUtils.add_business_days(friday, 1)
        assert _result == date(2021, 10, 18)  # 下周一

    def test_get_age(self):
        """测试计算年龄"""
        birth_date = date(1990, 10, 11)
        reference_date = date(2021, 10, 10)  # 前一天

        age = DateUtils.get_age(birth_date, reference_date)
        assert age == 30

        # 生日当天
        reference_date = date(2021, 10, 11)
        age = DateUtils.get_age(birth_date, reference_date)
        assert age == 31

        # 使用当前日期
        age = DateUtils.get_age(birth_date)
        assert isinstance(age, int)

    def test_get_quarter(self):
        """测试获取季度"""
        assert DateUtils.get_quarter(date(2021, 1, 15)) == 1
        assert DateUtils.get_quarter(date(2021, 3, 31)) == 1
        assert DateUtils.get_quarter(date(2021, 4, 1)) == 2
        assert DateUtils.get_quarter(date(2021, 7, 15)) == 3
        assert DateUtils.get_quarter(date(2021, 10, 31)) == 4
        assert DateUtils.get_quarter(date(2021, 12, 25)) == 4

    def test_get_week_of_year(self):
        """测试获取一年中的第几周"""
        # 2021年1月1日是第53周（2020年的）
        assert DateUtils.get_week_of_year(date(2021, 1, 1)) == 53
        # 2021年1月4日是第1周
        assert DateUtils.get_week_of_year(date(2021, 1, 4)) == 1
        # 2021年7月15日是第28周
        assert DateUtils.get_week_of_year(date(2021, 7, 15)) == 28

    def test_get_day_of_year(self):
        """测试获取一年中的第几天"""
        assert DateUtils.get_day_of_year(date(2021, 1, 1)) == 1
        assert DateUtils.get_day_of_year(date(2021, 12, 31)) == 365
        assert DateUtils.get_day_of_year(date(2020, 12, 31)) == 366  # 闰年
        assert DateUtils.get_day_of_year(date(2021, 7, 1)) == 182

    def test_is_weekend(self):
        """测试判断是否为周末"""
        assert DateUtils.is_weekend(date(2021, 10, 16)) is True  # 星期六
        assert DateUtils.is_weekend(date(2021, 10, 17)) is True  # 星期日
        assert DateUtils.is_weekend(date(2021, 10, 15)) is False  # 星期五
        assert DateUtils.is_weekend(date(2021, 10, 11)) is False  # 星期一

    def test_is_same_day(self):
        """测试判断是否为同一天"""
        date1 = date(2021, 10, 11)
        date2 = date(2021, 10, 11)
        date3 = date(2021, 10, 12)

        assert DateUtils.is_same_day(date1, date2) is True
        assert DateUtils.is_same_day(date1, date3) is False

    def test_get_date_range(self):
        """测试获取日期范围"""
        start = date(2021, 10, 11)
        end = date(2021, 10, 15)

        range_dates = DateUtils.get_date_range(start, end)
        assert len(range_dates) == 5
        assert range_dates[0] == start
        assert range_dates[-1] == end

        # 空范围
        empty_range = DateUtils.get_date_range(end, start)
        assert len(empty_range) == 0

    def test_get_business_days_in_month(self):
        """测试获取某月工作日数"""
        # 2021年10月有21个工作日
        assert DateUtils.get_business_days_in_month(2021, 10) == 21

        # 2021年2月有20个工作日
        assert DateUtils.get_business_days_in_month(2021, 2) == 20

    def test_get_month_name(self):
        """测试获取月份名称"""
        assert DateUtils.get_month_name(1) == "January"
        assert DateUtils.get_month_name(12) == "December"
        assert DateUtils.get_month_name(7) == "July"

        assert DateUtils.get_month_name(1, chinese=True) == "一月"
        assert DateUtils.get_month_name(12, chinese=True) == "十二月"
        assert DateUtils.get_month_name(13) == ""

    def test_format_duration(self):
        """测试格式化日期间隔"""
        start = date(2021, 1, 1)
        end = date(2022, 3, 15)

        duration = DateUtils.format_duration(start, end)
        assert "1 year" in duration
        assert "2 months" in duration
        assert "14 days" in duration

        duration_cn = DateUtils.format_duration(start, end, chinese=True)
        assert "1年" in duration_cn
        assert "2个月" in duration_cn
        assert "14天" in duration_cn

    def test_get_zodiac_sign(self):
        """测试获取星座"""
        assert DateUtils.get_zodiac_sign(date(2021, 1, 20)) == "Aquarius"
        assert DateUtils.get_zodiac_sign(date(2021, 2, 18)) == "Aquarius"
        assert DateUtils.get_zodiac_sign(date(2021, 7, 23)) == "Leo"
        assert DateUtils.get_zodiac_sign(date(2021, 12, 25)) == "Capricorn"

    def test_get_chinese_zodiac(self):
        """测试获取生肖"""
        assert DateUtils.get_chinese_zodiac(2020) == "Rat"
        assert DateUtils.get_chinese_zodiac(2021) == "Ox"
        assert DateUtils.get_chinese_zodiac(1990) == "Horse"
        assert DateUtils.get_chinese_zodiac(2000) == "Dragon"

    def test_is_date_in_range(self):
        """测试检查日期是否在范围内"""
        start = date(2021, 10, 1)
        end = date(2021, 10, 31)
        check = date(2021, 10, 15)

        assert DateUtils.is_date_in_range(check, start, end) is True
        assert DateUtils.is_date_in_range(start, start, end) is True
        assert DateUtils.is_date_in_range(end, start, end) is True
        assert DateUtils.is_date_in_range(date(2021, 9, 30), start, end) is False
        assert DateUtils.is_date_in_range(date(2021, 11, 1), start, end) is False

    def test_get_overlap(self):
        """测试获取日期范围重叠"""
        range1_start = date(2021, 10, 1)
        range1_end = date(2021, 10, 15)
        range2_start = date(2021, 10, 10)
        range2_end = date(2021, 10, 20)

        overlap = DateUtils.get_overlap(
            range1_start, range1_end, range2_start, range2_end
        )
        assert overlap == (date(2021, 10, 10), date(2021, 10, 15))

        # 无重叠
        no_overlap = DateUtils.get_overlap(
            date(2021, 10, 1), date(2021, 10, 5), date(2021, 10, 6), date(2021, 10, 10)
        )
        assert no_overlap is None

    def test_get_last_day_of_month(self):
        """测试获取某月最后一天"""
        assert DateUtils.get_last_day_of_month(2021, 2) == date(2021, 2, 28)
        assert DateUtils.get_last_day_of_month(2020, 2) == date(2020, 2, 29)  # 闰年
        assert DateUtils.get_last_day_of_month(2021, 4) == date(2021, 4, 30)
        assert DateUtils.get_last_day_of_month(2021, 12) == date(2021, 12, 31)

    def test_get_first_day_of_month(self):
        """测试获取某月第一天"""
        assert DateUtils.get_first_day_of_month(2021, 10) == date(2021, 10, 1)
        assert DateUtils.get_first_day_of_month(2021, 1) == date(2021, 1, 1)
        assert DateUtils.get_first_day_of_month(2021, 12) == date(2021, 12, 1)
