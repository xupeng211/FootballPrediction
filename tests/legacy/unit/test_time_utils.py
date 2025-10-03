from datetime import datetime, timezone

from src.utils.time_utils import TimeUtils
import pytest
import os

pytestmark = pytest.mark.unit
class TestTimeUtils:
    """测试时间工具类"""
    def test_now_utc(self):
        """测试获取当前UTC时间"""
        result = TimeUtils.now_utc()
    assert isinstance(result, datetime)
    assert result.tzinfo ==timezone.utc
    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        timestamp = 1735732800.0  # 2025-01-01 12:0000 UTC
        result = TimeUtils.timestamp_to_datetime(timestamp)
    assert isinstance(result, datetime)
    assert result.year ==2025
    assert result.month ==1
    assert result.day ==1
    assert result.hour ==12
    assert result.tzinfo ==timezone.utc
    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.datetime_to_timestamp(dt)
    assert isinstance(result, float)
    assert result ==1735732800.0
    def test_format_datetime_default(self):
        """测试默认格式的日期时间格式化"""
        dt = datetime(2025, 1, 1, 12, 30, 45)
        result = TimeUtils.format_datetime(dt)
    assert result =="2025-01-01 123045[" def test_format_datetime_custom("
    """"
        "]""测试自定义格式的日期时间格式化"""
        dt = datetime(2025, 1, 1, 12, 30, 45)
        result = TimeUtils.format_datetime(dt, "%Y_%m/%d %H%M[")": assert result =="]2025/01/01 1230[" def test_parse_datetime_default("
    """"
        "]""测试默认格式的日期时间解析"""
        date_str = "2025-01-01 12:3045[": result = TimeUtils.parse_datetime(date_str)": assert isinstance(result, datetime)" assert result.year ==2025[""
    assert result.month ==1
    assert result.day ==1
    assert result.hour ==12
    assert result.minute ==30
    assert result.second ==45
    def test_parse_datetime_custom(self):
        "]]""测试自定义格式的日期时间解析"""
        date_str = os.getenv("TEST_TIME_UTILS_DATE_STR_49"): result = TimeUtils.parse_datetime(date_str, "]%Y/%m/%d %H%M[")": assert isinstance(result, datetime)" assert result.year ==2025[""
    assert result.month ==1
    assert result.day ==1
    assert result.hour ==12
    assert result.minute ==30
    def test_round_trip_conversion(self):
        "]]""测试datetime和时间戳的往返转换"""
        original_dt = datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        # datetime -> timestamp -> datetime
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)
    assert converted_dt ==original_dt
    def test_format_parse_round_trip(self):
        """测试格式化和解析的往返转换"""
        original_dt = datetime(2025, 6, 15, 14, 30, 45)
        # datetime -> string -> datetime
        formatted = TimeUtils.format_datetime(original_dt)
        parsed_dt = TimeUtils.parse_datetime(formatted)
    assert parsed_dt ==original_dt
    def test_all_methods_exist(self):
        """确保所有方法都存在且可调用"""
        methods = [
        "now_utc[",""""
        "]timestamp_to_datetime[",""""
        "]datetime_to_timestamp[",""""
        "]format_datetime[",""""
            "]parse_datetime["]"]": for method_name in methods:": assert hasattr(TimeUtils, method_name)"
    assert callable(getattr(TimeUtils, method_name))