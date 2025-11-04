"""
工具类测试 - 自动生成扩展
"""

import pytest
from src.utils.dict_utils import filter_dict, rename_keys
from src.utils.string_utils import snake_to_camel, camel_to_snake, is_empty, strip_html
from src.utils.time_utils import (
    calculate_duration,
    get_current_timestamp,
    is_valid_datetime_format,
)
from datetime import datetime, timedelta


class TestUtilsExtended:
    """扩展工具类测试"""

    def test_dict_filter_functional(self):
        """测试字典过滤功能"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["a", "c"]
        result = filter_dict(data, keys)
        expected = {"a": 1, "c": 3}
        assert result == expected

    def test_dict_rename_functional(self):
        """测试字典重命名功能"""
        data = {"old_name": "value", "another_name": "value2"}
        key_map = {"old_name": "new_name", "another_name": "new_another"}
        result = rename_keys(data, key_map)
        expected = {"new_name": "value", "new_another": "value2"}
        assert result == expected

    def test_string_case_conversion(self):
        """测试字符串大小写转换"""
        # snake_to_camel
        assert snake_to_camel("test_string") == "testString"
        assert snake_to_camel("another_test_case") == "anotherTestCase"

        # camel_to_snake
        assert camel_to_snake("testString") == "test_string"
        assert camel_to_snake("anotherTestCase") == "another_test_case"

    def test_string_utility_functions(self):
        """测试字符串工具函数"""
        assert is_empty("") is True
        assert is_empty("   ") is True
        assert is_empty("test") is False

        assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"
        assert strip_html("plain text") == "plain text"

    def test_time_utility_functions(self):
        """测试时间工具函数"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        duration = calculate_duration(start_time, end_time)
        assert duration.total_seconds() == 7200  # 2小时

        timestamp = get_current_timestamp()
        assert isinstance(timestamp, float)
        assert timestamp > 0

        assert is_valid_datetime_format("2024-01-01 12:00:00") is True
        assert is_valid_datetime_format("invalid-date") is False
