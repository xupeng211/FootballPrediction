#!/usr/bin/env python3
"""
字符串工具基础测试
测试 src.utils.string_utils 模块的核心功能
"""

import pytest

from src.utils.string_utils import StringUtils


@pytest.mark.unit
class TestStringUtilsBasic:
    """字符串工具基础测试"""

    def test_clean_string_basic(self):
        """测试基础字符串清理"""
        # 测试正常字符串
        result = StringUtils.clean_string("  Hello World  ")
        assert result == "Hello World"

        # 测试空字符串
        assert StringUtils.clean_string("") == ""

        # 测试只有空白字符
        assert StringUtils.clean_string("   \t\n   ") == ""

    def test_clean_string_with_special_chars(self):
        """测试特殊字符清理"""
        text = "Hello\tWorld\nTest"
        result = StringUtils.clean_string(text)
        assert result == "Hello World Test"

    def test_clean_string_remove_special_chars(self):
        """测试移除特殊字符"""
        text = "Hello@World#Test$123"
        result = StringUtils.clean_string(text, remove_special_chars=True)
        # 保留字母数字和基本标点
        assert "Hello World Test 123" in result or "HelloWorldTest123" in result

    def test_clean_string_non_string_input(self):
        """测试非字符串输入"""
        assert StringUtils.clean_string(None) == ""
        assert StringUtils.clean_string(123) == ""
        assert StringUtils.clean_string([]) == ""

    def test_truncate_basic(self):
        """测试基础字符串截断"""
        text = "Hello World"
        result = StringUtils.truncate(text, 5)
        assert result == "Hello..."

    def test_truncate_shorter_text(self):
        """测试截断比长度限制短的文本"""
        text = "Hello"
        result = StringUtils.truncate(text, 10)
        assert result == "Hello"  # 不应该添加后缀

    def test_truncate_custom_suffix(self):
        """测试自定义后缀的截断"""
        text = "Hello World Test"
        result = StringUtils.truncate(text, 5, suffix=" [more]")
        assert result == "Hello [more]"

    def test_truncate_exact_length(self):
        """测试精确长度的截断"""
        text = "Hello"
        result = StringUtils.truncate(text, 5)
        assert result == "Hello"  # 不应该添加后缀

    def test_truncate_empty_string(self):
        """测试空字符串截断"""
        result = StringUtils.truncate("", 10)
        assert result == ""

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        text = "测试中文处理"
        result = StringUtils.clean_string(f"  {text}  ")
        assert result == text

    def test_multiple_spaces(self):
        """测试多个空格的处理"""
        text = "Hello    World     Test"
        result = StringUtils.clean_string(text)
        assert result == "Hello World Test"
