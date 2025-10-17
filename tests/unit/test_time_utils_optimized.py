"""
优化后的time_utils测试
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.utils.time_utils import TimeUtils


class TestTimeUtilsBasic:
    """基础时间工具测试"""

    def test_now_utc(self):
        """测试获取UTC时间"""
        now = TimeUtils.now_utc()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_to_timestamp(self):
        """测试转换为时间戳"""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.to_timestamp(dt)
        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_from_timestamp(self):
        """测试从时间戳创建时间"""
        timestamp = 1672574400.0  # 2023-01-01 00:00:00 UTC
        dt = TimeUtils.from_timestamp(timestamp)
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc

    def test_format_datetime(self):
        """测试时间格式化"""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S")
        assert isinstance(formatted, str)
        assert "2024-01-01" in formatted

    def test_parse_datetime(self):
        """测试解析时间字符串"""
        dt_str = "2024-01-01 12:00:00"
        dt = TimeUtils.parse_datetime(dt_str, "%Y-%m-%d %H:%M:%S")
        assert isinstance(dt, datetime)

    def test_add_timedelta(self):
        """测试时间加减"""
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        new_dt = TimeUtils.add_timedelta(dt, days=1, hours=2)
        assert new_dt.day == 2
        assert new_dt.hour == 2

    def test_is_future(self):
        """测试是否为未来时间"""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert TimeUtils.is_future(future) is True
        assert TimeUtils.is_future(past) is False

    def test_is_past(self):
        """测试是否为过去时间"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        assert TimeUtils.is_past(past) is True
        assert TimeUtils.is_past(future) is False

    def test_days_between(self):
        """测试计算日期差"""
        dt1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 3, tzinfo=timezone.utc)
        days = TimeUtils.days_between(dt1, dt2)
        assert days == 2

    def test_human_readable_duration(self):
        """测试人类可读的时间差"""
        dt1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 1, 12, 1, 30, tzinfo=timezone.utc)
        duration = TimeUtils.human_readable_duration(dt1, dt2)
        assert isinstance(duration, str)
        assert "1分" in duration or "minute" in duration.lower()


if __name__ == "__main__":
    pytest.main([__file__])
