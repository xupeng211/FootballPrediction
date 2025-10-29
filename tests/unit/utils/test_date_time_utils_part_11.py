from datetime import datetime
"""
test_date_time_utils - 第11部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307180
包含项目: 5 个 (函数/类)
"""


class TestDateTimeUtilsPart11:
    """测试类"""

    def test_is_weekday(self):
        """测试工作日检查"""
        # 周一
        monday = datetime.date(2023, 12, 25)
        assert DateUtils.is_weekday(monday) is True

        # 周五
        friday = datetime.date(2023, 12, 22)
        assert DateUtils.is_weekday(friday) is True

        # 周六
        saturday = datetime.date(2023, 12, 23)
        assert DateUtils.is_weekday(saturday) is False

    def test_start_of_week(self):
        """测试获取周开始"""
        # 周三
        wednesday = datetime.date(2023, 12, 27)  # 2023-12-27是周三
        result = DateUtils.start_of_week(wednesday)
        expected = datetime.date(2023, 12, 25)  # 周一
        assert result == expected

        # 周一
        monday = datetime.date(2023, 12, 25)
        result = DateUtils.start_of_week(monday)
        assert result == monday

    def test_end_of_week(self):
        """测试获取周末"""
        # 周三
        wednesday = datetime.date(2023, 12, 27)
        result = DateUtils.end_of_week(wednesday)
        expected = datetime.date(2023, 12, 31)  # 周日
        assert result == expected

        # 周日
        sunday = datetime.date(2023, 12, 31)
        result = DateUtils.end_of_week(sunday)
        assert result == sunday

    def test_start_of_month(self):
        """测试获取月开始"""
        date_obj = datetime.date(2023, 12, 25)
        result = DateUtils.start_of_month(date_obj)
        expected = datetime.date(2023, 12, 1)
        assert result == expected

    def test_end_of_month(self):
        """测试获取月末"""
        date_obj = datetime.date(2023, 12, 15)
        result = DateUtils.end_of_month(date_obj)
        expected = datetime.date(2023, 12, 31)
        assert result == expected

        # 二月测试
        date_obj = datetime.date(2024, 2, 10)  # 2024是闰年
        result = DateUtils.end_of_month(date_obj)
        expected = datetime.date(2024, 2, 29)
        assert result == expected
