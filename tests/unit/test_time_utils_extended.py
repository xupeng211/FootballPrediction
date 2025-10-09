"""时间工具测试"""
import pytest
from datetime import datetime, timedelta
from src.utils.time_utils import TimeUtils

class TestTimeUtils:
    """时间工具测试"""

    def test_format_duration(self):
        """测试格式化持续时间"""
        seconds = 3665
        result = TimeUtils.format_duration(seconds)
        assert "1 hour" in result or "61 minutes" in result

    def test_is_future(self):
        """测试是否是未来时间"""
        now = datetime.now()
        future = now + timedelta(hours=1)
        assert TimeUtils.is_future(future) is True
        assert TimeUtils.is_future(now) is False

    def test_days_between(self):
        """测试计算天数差"""
        date1 = datetime(2024, 1, 1)
        date2 = datetime(2024, 1, 3)
        result = TimeUtils.days_between(date1, date2)
        assert result == 2

    def test_start_of_day(self):
        """测试获取一天开始时间"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        start = TimeUtils.start_of_day(dt)
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

    def test_add_working_days(self):
        """测试添加工作日"""
        start = datetime(2024, 1, 1)  # 周一
        result = TimeUtils.add_working_days(start, 5)
        # 5个工作日后应该是下周一
        assert result.weekday() == 0  # 周一
