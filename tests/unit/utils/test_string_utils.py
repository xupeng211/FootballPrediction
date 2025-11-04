"""
字符串工具测试
"""

import pytest
from src.utils.string_utils import (
    normalize_string, truncate_string, snake_to_camel, camel_to_snake,
    is_empty, strip_html, format_currency
)


class TestStringUtils:
    """字符串工具测试类"""

    def test_normalize_string(self):
        """测试字符串标准化"""
        assert normalize_string("  Hello World  ") == "hello world"
        assert normalize_string("Héllo Wörld") == "hello world"
        assert normalize_string("Multiple   Spaces") == "multiple spaces"
        assert normalize_string("") == ""
        assert normalize_string(None) == ""

    def test_truncate_string(self):
        """测试字符串截断"""
        text = "This is a long string"
        assert truncate_string(text, 10) == "This is..."
        assert truncate_string(text, 20) == "This is a long string"
        assert truncate_string("", 10) == ""
        assert truncate_string(None, 10) == ""

    def test_snake_to_camel(self):
        """测试蛇形转驼峰（camelCase格式）"""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("test_case") == "testCase"
        assert snake_to_camel("single") == "single"
        assert snake_to_camel("") == ""

    def test_camel_to_snake(self):
        """测试驼峰转蛇形"""
        assert camel_to_snake("HelloWorld") == "hello_world"
        assert camel_to_snake("TestCase") == "test_case"
        assert camel_to_snake("Single") == "single"
        assert camel_to_snake("") == ""

    def test_is_empty(self):
        """测试空值判断"""
        assert is_empty("") is True
        assert is_empty(None) is True
        assert is_empty("   ") is True
        assert is_empty("hello") is False
        assert is_empty(" hello ") is False

    def test_strip_html(self):
        """测试HTML标签清除"""
        assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"
        assert strip_html("<div>Content</div>") == "Content"
        assert strip_html("Plain text") == "Plain text"
        assert strip_html("") == ""

    def test_format_currency(self):
        """测试货币格式化"""
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(0) == "$0.00"
        assert format_currency(1000000) == "$1,000,000.00"
        assert format_currency(-123.45) == "-$123.45"