"""
test_date_time_utils - 第17部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.308057
包含项目: 5 个 (函数/类)
"""


class TestDateTimeUtilsPart17:
    """测试类"""

    def test_count_working_days_with_holidays(self):
        """测试计算工作日数量（排除假期）"""
        start = datetime.date(2023, 12, 25)  # 周一
        end = datetime.date(2023, 12, 29)  # 周五
        holidays = [datetime.date(2023, 12, 26)]  # 周二为假期

        result = DateRangeCalculator.count_working_days(start, end, holidays)
        assert result == 4  # 5个工作日 - 1个假期

    """工作日计算器测试"""

    def test_add_working_days_forward(self):
        """测试向前添加工作日"""
        start = datetime.date(2023, 12, 22)  # 周五

        result = WorkingDayCalculator.add_working_days(start, 3)
        expected = datetime.date(2023, 12, 27)  # 周三（跳过周末）
        assert result == expected

    def test_add_working_days_backward(self):
        """测试向后添加工作日"""
        start = datetime.date(2023, 12, 25)  # 周一

        result = WorkingDayCalculator.add_working_days(start, -3)
        expected = datetime.date(2023, 12, 20)  # 周三（跳过周末）
        assert result == expected

    def test_add_working_days_with_holidays(self):
        """测试添加工作日（排除假期）"""
        start = datetime.date(2023, 12, 22)  # 周五
        holidays = [datetime.date(2023, 12, 25)]  # 周一为假期

        result = WorkingDayCalculator.add_working_days(start, 3, holidays)
        expected = datetime.date(2023, 12, 28)  # 周四（跳过周末和假期）
        assert result == expected
