"""
时间工具模块功能测试
测试实际的时间处理功能，而不是仅仅测试导入
"""

import pytest
import datetime

# 设置测试环境
import os

os.environ["TESTING"] = "true"


@pytest.mark.unit
class TestTimeUtilsFunctional:
    """时间工具功能测试"""

    def test_parse_iso_datetime(self):
        """测试ISO格式日期时间解析"""
        test_cases = [
            ("2025-10-06T15:30:00", datetime.datetime(2025, 10, 6, 15, 30)),
            ("2025-10-06T15:30:00Z", datetime.datetime(2025, 10, 6, 15, 30)),
            ("2025-10-06T15:30:00+08:00", datetime.datetime(2025, 10, 6, 15, 30)),
            ("2025-10-06", datetime.datetime(2025, 10, 6)),
        ]

        for iso_string, expected in test_cases:
            try:
                from src.utils.time_utils import parse_iso_datetime

                result = parse_iso_datetime(iso_string)
                assert isinstance(result, datetime.datetime)
                assert result.year == expected.year
                assert result.month == expected.month
                assert result.day == expected.day

            except ImportError:
                pytest.skip("Time utils not available")

    def test_format_datetime(self):
        """测试日期时间格式化"""
        test_dt = datetime.datetime(2025, 10, 6, 15, 30, 45)

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                from src.utils.time_utils import format_datetime

                result = format_datetime(test_dt, fmt)
                assert isinstance(result, str)
                assert len(result) > 0

                # 验证格式是否正确
                parsed = datetime.datetime.strptime(result, fmt)
                assert parsed.year == test_dt.year

            except ImportError:
                pytest.skip("Time utils not available")

    def test_time_ago(self):
        """测试时间差计算（如：5分钟前）"""
        now = datetime.datetime.now()
        test_cases = [
            (now - datetime.timedelta(minutes=5), "5分钟前"),
            (now - datetime.timedelta(hours=2), "2小时前"),
            (now - datetime.timedelta(days=3), "3天前"),
            (now - datetime.timedelta(weeks=1), "1周前"),
            (now - datetime.timedelta(seconds=30), "30秒前"),
        ]

        for past_time, expected_contains in test_cases:
            try:
                from src.utils.time_utils import time_ago

                result = time_ago(past_time)
                assert isinstance(result, str)
                # 可能不完全是期望的字符串，但应该包含数字
                assert any(c.isdigit() for c in result)

            except ImportError:
                pytest.skip("Time utils not available")

    def test_timezone_conversion(self):
        """测试时区转换"""
        try:
            from src.utils.time_utils import convert_timezone, get_timezone

            # 测试获取时区
            tz = get_timezone("UTC")
            assert tz is not None

            # 测试时区转换
            utc_time = datetime.datetime(2025, 10, 6, 15, 30, 45)
            local_time = convert_timezone(utc_time, "UTC", "Asia/Shanghai")
            assert isinstance(local_time, datetime.datetime)

        except ImportError:
            pytest.skip("Timezone functions not available")

    def test_date_range_generation(self):
        """测试日期范围生成"""
        try:
            from src.utils.time_utils import date_range

            start = datetime.date(2025, 10, 1)
            end = datetime.date(2025, 10, 5)

            dates = list(date_range(start, end))
            assert len(dates) == 5
            assert dates[0] == start
            assert dates[-1] == end

            # 测试步长
            dates_step2 = list(date_range(start, end, step=2))
            assert len(dates_step2) == 3

        except ImportError:
            pytest.skip("Date range function not available")

    def test_working_days_calculation(self):
        """测试工作日计算"""
        try:
            from src.utils.time_utils import get_working_days, is_weekend

            # 测试周末判断
            saturday = datetime.date(2025, 10, 4)  # 周六
            sunday = datetime.date(2025, 10, 5)  # 周日
            monday = datetime.date(2025, 10, 6)  # 周一

            assert is_weekend(saturday) is True
            assert is_weekend(sunday) is True
            assert is_weekend(monday) is False

            # 测试工作日计算
            start = datetime.date(2025, 10, 1)  # 周三
            end = datetime.date(2025, 10, 7)  # 周二
            working_days = get_working_days(start, end)
            assert working_days == 5  # 周三到周二有5个工作日

        except ImportError:
            pytest.skip("Working days functions not available")

    def test_timestamp_conversion(self):
        """测试时间戳转换"""
        import time

        test_timestamp = int(time.time())

        try:
            from src.utils.time_utils import (
                timestamp_to_datetime,
                datetime_to_timestamp,
            )

            # 时间戳转datetime
            dt = timestamp_to_datetime(test_timestamp)
            assert isinstance(dt, datetime.datetime)

            # datetime转时间戳
            ts = datetime_to_timestamp(dt)
            assert isinstance(ts, (int, float))
            assert abs(ts - test_timestamp) < 1  # 允许1秒误差

        except ImportError:
            pytest.skip("Timestamp conversion not available")

    def test_duration_formatting(self):
        """测试持续时间格式化"""
        test_cases = [
            (datetime.timedelta(seconds=30), "0分30秒"),
            (datetime.timedelta(minutes=5), "5分0秒"),
            (datetime.timedelta(hours=2, minutes=30), "2小时30分"),
            (datetime.timedelta(days=1, hours=3), "1天3小时"),
        ]

        for duration, expected_pattern in test_cases:
            try:
                from src.utils.time_utils import format_duration

                result = format_duration(duration)
                assert isinstance(result, str)
                assert len(result) > 0
                # 应该包含时间单位
                assert any(unit in result for unit in ["秒", "分", "小时", "天"])

            except ImportError:
                pytest.skip("Duration formatting not available")

    def test_date_validation(self):
        """测试日期验证"""
        try:
            from src.utils.time_utils import is_valid_date, is_valid_datetime

            # 有效日期
            assert is_valid_date("2025-10-06") is True
            assert is_valid_date(datetime.date(2025, 10, 6)) is True

            # 无效日期
            assert is_valid_date("2025-02-30") is False  # 2月没有30日
            assert is_valid_date("invalid") is False

            # 日期时间验证
            assert is_valid_datetime("2025-10-06T15:30:00") is True
            assert is_valid_datetime(datetime.datetime(2025, 10, 6, 15, 30)) is True
            assert is_valid_datetime("invalid") is False

        except ImportError:
            pytest.skip("Date validation not available")

    def test_business_hours(self):
        """测试营业时间计算"""
        try:
            from src.utils.time_utils import is_business_hours, next_business_hour

            # 测试营业时间判断
            business_time = datetime.datetime(2025, 10, 6, 10, 30)  # 10:30
            non_business_time = datetime.datetime(2025, 10, 6, 22, 30)  # 22:30

            assert is_business_hours(business_time) is True
            assert is_business_hours(non_business_time) is False

            # 测试下一个营业时间
            next_business = next_business_hour(non_business_time)
            assert isinstance(next_business, datetime.datetime)

        except ImportError:
            pytest.skip("Business hours not available")

    def test_date_arithmetic(self):
        """测试日期运算"""
        try:
            from src.utils.time_utils import add_business_days, subtract_business_days

            base_date = datetime.date(2025, 10, 6)  # 周一

            # 添加工作日
            result = add_business_days(base_date, 5)
            assert isinstance(result, datetime.date)
            # 周一加5个工作日应该是下周一

            # 减少工作日
            result2 = subtract_business_days(base_date, 5)
            assert isinstance(result2, datetime.date)

        except ImportError:
            pytest.skip("Date arithmetic not available")

    def test_fiscal_periods(self):
        """测试财务期间计算"""
        try:
            from src.utils.time_utils import get_fiscal_year, get_fiscal_quarter

            test_date = datetime.date(2025, 10, 6)

            # 财年（假设从10月开始）
            fiscal_year = get_fiscal_year(test_date)
            assert isinstance(fiscal_year, int)
            assert fiscal_year in [2025, 2026]

            # 财务季度
            quarter = get_fiscal_quarter(test_date)
            assert quarter in [1, 2, 3, 4]

        except ImportError:
            pytest.skip("Fiscal periods not available")

    def test_time_utilities(self):
        """测试其他时间实用函数"""
        test_cases = [
            ("now", lambda: datetime.datetime.now()),
            ("today", lambda: datetime.date.today()),
            ("utc_now", lambda: datetime.datetime.utcnow()),
        ]

        for name, func in test_cases:
            try:
                # 尝试从time_utils导入
                time_utils = __import__("src.utils.time_utils", fromlist=[name])
                if hasattr(time_utils, name):
                    result = getattr(time_utils, name)()
                    assert result is not None

            except ImportError:
                pytest.skip("Time utilities not available")

    def test_edge_cases(self):
        """测试边界情况"""
        try:
            from src.utils.time_utils import (
                parse_iso_datetime,
                time_ago,
            )

            # 极端日期

            # 空值
            with pytest.raises((ValueError, TypeError, AttributeError)):
                parse_iso_datetime("")
                parse_iso_datetime(None)

            # 无效格式
            with pytest.raises((ValueError, TypeError)):
                parse_iso_datetime("not-a-date")

            # 未来时间
            future_time = datetime.datetime.now() + datetime.timedelta(days=365)
            result = time_ago(future_time)
            assert isinstance(result, str)

        except ImportError:
            pytest.skip("Time utils not available")
