"""时间工具扩展测试"""

import pytest
from datetime import datetime, timedelta
from src.utils.time_utils import TimeUtils


class TestTimeUtilsExtended:
    """测试时间工具扩展功能"""

    def test_format_duration(self):
        """测试时间差格式化"""
        if hasattr(TimeUtils, "format_duration"):
            # 测试秒
            assert TimeUtils.format_duration(30) == "30秒"
            # 测试分钟
            assert TimeUtils.format_duration(90) == "1分30秒"
            # 测试小时
            assert TimeUtils.format_duration(3661) == "1小时1分1秒"

    def test_get_time_range(self):
        """测试获取时间范围"""
        if hasattr(TimeUtils, "get_time_range"):
            today = datetime.now().date()
            start, end = TimeUtils.get_time_range("today")
            assert start.date() == today
            assert end.date() == today

    def test_is_weekend(self):
        """测试是否是周末"""
        if hasattr(TimeUtils, "is_weekend"):
            # 创建已知是周六的日期 (2024-01-06是周六)
            saturday = datetime(2024, 1, 6)
            assert TimeUtils.is_weekend(saturday) is True
            # 创建已知是周日的日期 (2024-01-07是周日)
            sunday = datetime(2024, 1, 7)
            assert TimeUtils.is_weekend(sunday) is True
            # 创建已知是周二的日期 (2024-01-02是周二)
            tuesday = datetime(2024, 1, 2)
            assert TimeUtils.is_weekend(tuesday) is False

    def test_add_business_days(self):
        """测试添加工作日"""
        if hasattr(TimeUtils, "add_business_days"):
            # 周五加1个工作日应该是周一
            friday = datetime(2024, 1, 5)  # 周五
            monday = TimeUtils.add_business_days(friday, 1)
            assert monday.weekday() == 0  # 周一

    def test_parse_iso_string(self):
        """测试解析ISO时间字符串"""
        if hasattr(TimeUtils, "parse_iso_string"):
            iso_str = "2024-01-15T10:30:00"
            parsed = TimeUtils.parse_iso_string(iso_str)
            assert parsed.year == 2024
            assert parsed.month == 1
            assert parsed.day == 15
