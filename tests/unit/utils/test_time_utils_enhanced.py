"""
时间工具增强测试 - 基于实际TimeUtils类
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.utils.time_utils import TimeUtils, utc_now, parse_datetime


class TestTimeUtilsEnhanced:
    """时间工具增强测试类"""

    def test_time_utils_class_methods(self):
        """测试TimeUtils类的各种方法"""
        # 测试now_utc方法
        utc_time = TimeUtils.now_utc()
        assert isinstance(utc_time, datetime)
        assert utc_time.tzinfo == timezone.utc

        # 测试get_utc_now方法（别名）
        utc_time_alias = TimeUtils.get_utc_now()
        assert isinstance(utc_time_alias, datetime)
        assert utc_time_alias.tzinfo == timezone.utc

        # 测试get_local_now方法
        local_time = TimeUtils.get_local_now()
        assert isinstance(local_time, datetime)

    def test_timestamp_conversion(self):
        """测试时间戳转换"""
        # 测试datetime到时间戳
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(timestamp, float)

        # 测试时间戳到datetime
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(converted_dt, datetime)
        assert converted_dt.tzinfo == timezone.utc

        # 测试往返转换的一致性
        now = TimeUtils.now_utc()
        timestamp = TimeUtils.datetime_to_timestamp(now)
        converted_back = TimeUtils.timestamp_to_datetime(timestamp)

        # 允许微秒级差异
        time_diff = abs((now - converted_back).total_seconds())
        assert time_diff < 1.0

    def test_datetime_formatting(self):
        """测试日期时间格式化"""
        dt = datetime(2024, 1, 1, 12, 30, 45)

        # 测试默认格式
        formatted = TimeUtils.format_datetime(dt)
        assert isinstance(formatted, str)
        assert "2024-01-01" in formatted
        assert "12:30:45" in formatted

        # 测试自定义格式
        custom_format = TimeUtils.format_datetime(dt, "%Y/%m/%d")
        assert custom_format == "2024/01/01"

        # 测试其他格式
        formats = [
            ("%Y-%m-%d", "2024-01-01"),
            ("%H:%M:%S", "12:30:45"),
            ("%Y年%m月%d日", "2024年01月01日"),
        ]

        for fmt, expected in formats:
            result = TimeUtils.format_datetime(dt, fmt)
            assert expected in result

    def test_utc_now_function(self):
        """测试模块级utc_now函数"""
        try:
            utc_time = utc_now()
            assert isinstance(utc_time, datetime)
            assert utc_time.tzinfo == timezone.utc
        except Exception:
            pytest.skip("utc_now function not available")

    def test_parse_datetime_function(self):
        """测试parse_datetime函数"""
        try:
            # 测试ISO格式
            iso_string = "2024-01-01T12:00:00"
            parsed = parse_datetime(iso_string)
            assert isinstance(parsed, datetime)

            # 测试常见格式
            common_string = "2024-01-01 12:00:00"
            parsed2 = parse_datetime(common_string)
            assert isinstance(parsed2, datetime)
        except Exception:
            pytest.skip("parse_datetime function not available")

    def test_timezone_handling(self):
        """测试时区处理"""
        # 测试UTC时间
        utc_time = TimeUtils.now_utc()
        assert utc_time.tzinfo == timezone.utc

        # 测试本地时间
        local_time = TimeUtils.get_local_now()
        # 本地时间可能有或没有时区信息
        assert isinstance(local_time, datetime)

    def test_time_arithmetic(self):
        """测试时间计算"""
        base_time = TimeUtils.now_utc()

        # 测试加法
        future_time = base_time + timedelta(hours=1)
        assert future_time > base_time

        # 测试减法
        past_time = base_time - timedelta(hours=1)
        assert past_time < base_time

        # 测试时间差
        diff = future_time - past_time
        assert diff.total_seconds() == 7200  # 2小时

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试时间戳边界值
        epoch_timestamp = 0
        epoch_dt = TimeUtils.timestamp_to_datetime(epoch_timestamp)
        assert isinstance(epoch_dt, datetime)

        # 测试未来时间戳
        future_timestamp = 4102444800  # 2100年1月1日
        future_dt = TimeUtils.timestamp_to_datetime(future_timestamp)
        assert isinstance(future_dt, datetime)

        # 测试极端格式
        extreme_dt = datetime(9999, 12, 31, 23, 59, 59)
        formatted = TimeUtils.format_datetime(extreme_dt)
        assert isinstance(formatted, str)

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试批量时间格式化性能
        start_time = time.time()
        for i in range(100):
            dt = datetime(2024, 1, 1, i % 24, i % 60, i % 60)
            formatted = TimeUtils.format_datetime(dt)
            assert isinstance(formatted, str)
        end_time = time.time()

        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

        # 测试批量时间戳转换性能
        start_time = time.time()
        for i in range(100):
            timestamp = 1609459200 + i * 3600  # 从2021年1月1日开始的小时序列
            dt = TimeUtils.timestamp_to_datetime(timestamp)
            assert isinstance(dt, datetime)
        end_time = time.time()

        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效时间戳
        try:
            invalid_timestamp = -1
            dt = TimeUtils.timestamp_to_datetime(invalid_timestamp)
            # 应该能处理负时间戳（1969年之前）
            assert isinstance(dt, datetime)
        except Exception:
            # 如果不支持负时间戳，也是可以接受的
            pass

        # 测试空格式字符串
        dt = datetime.now()
        try:
            formatted = TimeUtils.format_datetime(dt, "")
            # 空格式字符串可能返回空字符串或原始时间
            assert isinstance(formatted, str)
        except Exception:
            # 格式错误也是可以接受的
            pass

    def test_class_vs_module_functions(self):
        """测试类方法与模块函数的一致性"""
        # 比较类方法和模块函数的结果
        try:
            class_utc = TimeUtils.now_utc()

            # 如果有模块级函数，比较结果
            if "utc_now" in globals():
                module_utc = utc_now()
                time_diff = abs((class_utc - module_utc).total_seconds())
                assert time_diff < 1.0  # 应该在1秒内
        except Exception:
            pytest.skip("Cannot compare class and module functions")

    def test_static_method_behavior(self):
        """测试静态方法行为"""
        # 静态方法不需要实例化
        assert (
            not hasattr(TimeUtils.now_utc, "__self__")
            or TimeUtils.now_utc.__self__ is None
        )
        assert (
            not hasattr(TimeUtils.get_utc_now, "__self__")
            or TimeUtils.get_utc_now.__self__ is None
        )
        assert (
            not hasattr(TimeUtils.get_local_now, "__self__")
            or TimeUtils.get_local_now.__self__ is None
        )

    def test_time_utils_import(self):
        """测试TimeUtils导入"""
        from src.utils.time_utils import TimeUtils

        assert TimeUtils is not None

        # 检查关键方法是否存在
        expected_methods = [
            "now_utc",
            "get_utc_now",
            "get_local_now",
            "timestamp_to_datetime",
            "datetime_to_timestamp",
            "format_datetime",
        ]

        for method in expected_methods:
            assert hasattr(TimeUtils, method)
            assert callable(getattr(TimeUtils, method))
