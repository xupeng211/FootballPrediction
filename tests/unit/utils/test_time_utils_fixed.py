from unittest.mock import patch

"""
时间工具测试（修复版）
Tests for Time Utils (Fixed Version)

测试src.utils.time_utils模块的实际功能
"""

from datetime import datetime, timedelta, timezone

import pytest

# 测试导入
try:
    from src.utils.time_utils import TimeUtils, parse_datetime, utc_now

    TIME_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    TIME_UTILS_AVAILABLE = False
    TimeUtils = None


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
@pytest.mark.unit
class TestTimeUtilsBasic:
    """时间工具基础功能测试"""

    def test_time_utils_creation(self):
        """测试：TimeUtils类创建"""
        assert TimeUtils is not None
        assert hasattr(TimeUtils, "now_utc")
        assert hasattr(TimeUtils, "timestamp_to_datetime")
        assert hasattr(TimeUtils, "datetime_to_timestamp")
        assert hasattr(TimeUtils, "format_datetime")
        assert hasattr(TimeUtils, "parse_datetime")

    def test_now_utc(self):
        """测试：获取当前UTC时间"""
        utc_time = TimeUtils.now_utc()
        assert isinstance(utc_time, datetime)
        assert utc_time.tzinfo == timezone.utc

        # 应该是最近的时间（1秒内）
        now = datetime.now(timezone.utc)
        assert abs((utc_time - now).total_seconds()) < 1.0

    def test_timestamp_to_datetime(self):
        """测试：时间戳转datetime"""
        timestamp = 1672531200.0  # 2023-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
        assert dt.tzinfo == timezone.utc

    def test_datetime_to_timestamp(self):
        """测试：datetime转时间戳"""
        dt = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        assert timestamp == 1672531200.0

    def test_format_datetime_default(self):
        """测试：格式化日期时间（默认格式）"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2023-01-01 12:30:45"

    def test_format_datetime_custom(self):
        """测试：格式化日期时间（自定义格式）"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = TimeUtils.format_datetime(dt, "%Y/%m/%d")
        assert formatted == "2023/01/01"

    def test_parse_datetime_default(self):
        """测试：解析日期时间字符串（默认格式）"""
        dt_str = "2023-01-01 12:30:45"
        dt = TimeUtils.parse_datetime(dt_str)

        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_datetime_custom(self):
        """测试：解析日期时间字符串（自定义格式）"""
        dt_str = "2023/01/01"
        dt = TimeUtils.parse_datetime(dt_str, "%Y/%m/%d")

        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1

    def test_roundtrip_conversion(self):
        """测试：往返转换"""
        # datetime -> timestamp -> datetime
        original_dt = datetime(2023, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert original_dt == converted_dt

    def test_format_with_timezone(self):
        """测试：格式化带时区的时间"""
        dt = datetime.now(timezone.utc)
        formatted = TimeUtils.format_datetime(dt)
        assert isinstance(formatted, str)
        assert len(formatted) == 19  # YYYY-MM-DD HH:MM:SS


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsEdgeCases:
    """时间工具边界情况测试"""

    def test_epoch_timestamp(self):
        """测试：Unix纪元时间戳"""
        timestamp = 0.0
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert dt.year == 1970
        assert dt.month == 1
        assert dt.day == 1
        assert dt.tzinfo == timezone.utc

    def test_negative_timestamp(self):
        """测试：负时间戳（1970年前）"""
        timestamp = -86400.0  # 1969-12-31 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert dt.year == 1969
        assert dt.month == 12
        assert dt.day == 31

    def test_far_future_timestamp(self):
        """测试：未来时间戳"""
        timestamp = 4102444800.0  # 2100-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert dt.year == 2100
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_invalid_datetime(self):
        """测试：解析无效日期时间"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("invalid-date")

    def test_parse_empty_string(self):
        """测试：解析空字符串"""
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime("")

    def test_format_microseconds(self):
        """测试：格式化带微秒的时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45, 123456)
        # 默认格式不包含微秒
        formatted = TimeUtils.format_datetime(dt)
        assert "123456" not in formatted

        # 自定义格式包含微秒
        formatted_with_micro = TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S.%f")
        assert "123456" in formatted_with_micro

    def test_parse_with_milliseconds(self):
        """测试：解析带毫秒的ISO格式"""
        dt_str = "2023-01-01T12:30:45.123Z"
        # 默认解析器不支持此格式
        with pytest.raises(ValueError):
            TimeUtils.parse_datetime(dt_str)


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_utc_now_function(self):
        """测试：utc_now函数"""
        utc_time = utc_now()
        assert isinstance(utc_time, datetime)
        assert utc_time.tzinfo == timezone.utc

    def test_utc_now_class_vs_function(self):
        """测试：类方法与函数一致性"""
        class_time = TimeUtils.now_utc()
        function_time = utc_now()

        # 应该是相同的时间类型
        assert type(class_time) is type(function_time)
        assert class_time.tzinfo == function_time.tzinfo

    def test_parse_datetime_function_with_none(self):
        """测试：parse_datetime函数处理None"""
        _result = parse_datetime(None)
        assert _result is None

    def test_parse_datetime_function_empty_string(self):
        """测试：parse_datetime函数处理空字符串"""
        _result = parse_datetime("")
        assert _result is None

    def test_parse_datetime_function_various_formats(self):
        """测试：parse_datetime函数支持多种格式"""
        test_cases = [
            ("2023-01-01T12:30:45.123Z", datetime(2023, 1, 1, 12, 30, 45, 123000)),
            ("2023-01-01T12:30:45Z", datetime(2023, 1, 1, 12, 30, 45)),
            ("2023-01-01T12:30:45", datetime(2023, 1, 1, 12, 30, 45)),
            ("2023-01-01", datetime(2023, 1, 1, 0, 0, 0)),
        ]

        for date_str, expected in test_cases:
            _result = parse_datetime(date_str)
            assert _result is not None
            assert _result.year == expected.year
            assert _result.month == expected.month
            assert _result.day == expected.day
            assert _result.hour == expected.hour
            assert _result.minute == expected.minute
            assert _result.second == expected.second

    def test_parse_datetime_function_invalid(self):
        """测试：parse_datetime函数处理无效格式"""
        invalid_cases = [
            "not-a-date",
            "2023-13-01",  # 无效月份
            "2023-02-30",  # 无效日期
            "2023/01/01",  # 不支持的格式
        ]

        for invalid in invalid_cases:
            _result = parse_datetime(invalid)
            assert _result is None


@pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="Time utils module not available")
class TestTimeUtilsPerformance:
    """时间工具性能测试"""

    def test_performance_now_utc(self):
        """测试：now_utc性能"""
        import time

        start_time = time.perf_counter()
        for _ in range(10000):
            TimeUtils.now_utc()
        end_time = time.perf_counter()

        # 10000次调用应该在0.1秒内完成
        assert end_time - start_time < 0.1

    def test_performance_format(self):
        """测试：格式化性能"""
        dt = datetime.now(timezone.utc)
        import time

        start_time = time.perf_counter()
        for _ in range(10000):
            TimeUtils.format_datetime(dt)
        end_time = time.perf_counter()

        # 10000次格式化应该在0.1秒内完成
        assert end_time - start_time < 0.1

    def test_performance_parse(self):
        """测试：解析性能"""
        dt_str = "2023-01-01 12:30:45"
        import time

        start_time = time.perf_counter()
        for _ in range(10000):
            TimeUtils.parse_datetime(dt_str)
        end_time = time.perf_counter()

        # 10000次解析应该在0.5秒内完成
        assert end_time - start_time < 0.5


@pytest.mark.skipif(
    TIME_UTILS_AVAILABLE, reason="Time utils module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not TIME_UTILS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if TIME_UTILS_AVAILABLE:
        from src.utils.time_utils import TimeUtils, parse_datetime, utc_now

        assert TimeUtils is not None
        assert utc_now is not None
        assert parse_datetime is not None


def test_class_method_signature():
    """测试：类方法签名"""
    if TIME_UTILS_AVAILABLE:
        import inspect

        # 检查方法签名
        assert callable(TimeUtils.now_utc)
        assert callable(TimeUtils.timestamp_to_datetime)
        assert callable(TimeUtils.datetime_to_timestamp)
        assert callable(TimeUtils.format_datetime)
        assert callable(TimeUtils.parse_datetime)


@pytest.mark.asyncio
async def test_async_context_usage():
    """测试：异步上下文中的使用"""
    if TIME_UTILS_AVAILABLE:
        # 在异步上下文中使用时间工具
        start_time = TimeUtils.now_utc()

        # 模拟异步操作
        import asyncio

        await asyncio.sleep(0.01)
        await asyncio.sleep(0.01)
        await asyncio.sleep(0.01)

        end_time = TimeUtils.now_utc()

        # 验证时间差
        time_diff = (end_time - start_time).total_seconds()
        assert 0.01 <= time_diff < 0.02
