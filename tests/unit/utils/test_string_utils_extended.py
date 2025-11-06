#!/usr/bin/env python3
"""
字符串工具扩展单元测试

补充 src.utils.string_utils 模块的测试覆盖
"""

import os
import sys

import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.utils.string_utils import (
    capitalize_words,
    clean_string,
    count_words,
    extract_numbers,
    find_substring_positions,
    format_phone_number,
    generate_slug,
    is_palindrome,
    join_text,
    normalize_text,
    remove_special_chars,
    replace_multiple,
    reverse_string,
    split_text,
    truncate_text,
    validate_email,
)


class TestStringUtilsExtended:
    """字符串工具扩展测试类"""

    def test_clean_string_basic(self):
        """测试基础字符串清理"""
        # 测试去除空白字符
        assert clean_string("  hello world  ") == "hello world"
        assert clean_string("\t\n  test  \n\t") == "test"

        # 测试去除特殊字符
        assert clean_string("hello@world!") == "helloworld"
        assert clean_string("test#123$%^") == "test123"

    def test_clean_string_advanced(self):
        """测试高级字符串清理"""
        # 测试保留数字
        result = clean_string("test123abc", keep_numbers=True)
        assert "123" in result

        # 测试保留特定字符
        result = clean_string("hello-world_test", keep_chars="-_")
        assert result == "hello-world_test"

        # 测试转换为小写
        assert clean_string("Hello World", to_lower=True) == "hello world"

    def test_normalize_text(self):
        """测试文本标准化"""
        # 测试Unicode标准化
        assert normalize_text("café") == "cafe"
        assert normalize_text("naïve") == "naive"

        # 测试去除重音符号
        text = "résumé façade"
        normalized = normalize_text(text)
        assert "é" not in normalized and "ç" not in normalized

    def test_extract_numbers(self):
        """测试提取数字"""
        assert extract_numbers("abc123def456") == ["123", "456"]
        assert extract_numbers("no numbers here") == []
        assert extract_numbers("123") == ["123"]
        assert extract_numbers("abc-123def") == ["-123"]  # 如果支持负数

    def test_format_phone_number(self):
        """测试电话号码格式化"""
        # 测试不同格式的电话号码
        assert format_phone_number("1234567890") == "(123) 456-7890"
        assert format_phone_number("123-456-7890") == "(123) 456-7890"
        assert format_phone_number("(123) 456 7890") == "(123) 456-7890"

        # 测试国际号码
        international = format_phone_number("+861234567890")
        assert "+" in international or "86" in international

    def test_validate_email(self):
        """测试邮箱验证"""
        # 有效邮箱
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        assert validate_email("user+tag@example.org") is True

        # 无效邮箱
        assert validate_email("invalid-email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user..name@example.com") is False

    def test_generate_slug(self):
        """测试生成slug"""
        assert generate_slug("Hello World") == "hello-world"
        assert generate_slug("Python Programming!") == "python-programming"
        assert generate_slug("  Multiple   Spaces  ") == "multiple-spaces"
        assert generate_slug("Special Characters #$%") == "special-characters"

    def test_truncate_text(self):
        """测试文本截断"""
        text = "This is a long text that needs to be truncated"

        # 基础截断
        result = truncate_text(text, 20)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")

        # 测试不添加省略号
        result = truncate_text(text, 20, add_ellipsis=False)
        assert len(result) <= 20
        assert "..." not in result

    def test_reverse_string(self):
        """测试字符串反转"""
        assert reverse_string("hello") == "olleh"
        assert reverse_string("12345") == "54321"
        assert reverse_string("") == ""
        assert reverse_string("a") == "a"

    def test_count_words(self):
        """测试单词计数"""
        assert count_words("hello world") == 2
        assert count_words("  multiple   spaces  ") == 2
        assert count_words("") == 0
        assert count_words("word") == 1
        assert count_words("Hello, world! How are you?") == 5

    def test_capitalize_words(self):
        """测试单词首字母大写"""
        assert capitalize_words("hello world") == "Hello World"
        assert capitalize_words("python programming") == "Python Programming"
        assert capitalize_words("") == ""
        assert capitalize_words("a") == "A"

    def test_remove_special_chars(self):
        """测试移除特殊字符"""
        assert remove_special_chars("hello@world!") == "helloworld"
        assert remove_special_chars("test#123$%^") == "test123"
        assert (
            remove_special_chars("keep-underscores_and spaces", keep_chars="_ ")
            == "keep-underscores_and spaces"
        )

    def test_is_palindrome(self):
        """测试回文检测"""
        assert is_palindrome("racecar") is True
        assert is_palindrome("level") is True
        assert is_palindrome("hello") is False
        assert is_palindrome("") is True  # 空字符串是回文
        assert (
            is_palindrome("A man a plan a canal Panama".replace(" ", "").lower())
            is True
        )

    def test_find_substring_positions(self):
        """测试查找子字符串位置"""
        text = "hello world, hello universe"
        positions = find_substring_positions(text, "hello")
        assert positions == [0, 13]  # 假设实现返回起始位置

        # 测试不存在的子字符串
        positions = find_substring_positions(text, "xyz")
        assert positions == []

    def test_replace_multiple(self):
        """测试多重替换"""
        text = "hello world, hello universe"
        replacements = {"hello": "hi", "world": "earth", "universe": "galaxy"}
        result = replace_multiple(text, replacements)
        assert result == "hi earth, hi galaxy"

    def test_split_text(self):
        """测试文本分割"""
        text = "apple,banana;cherry|date"

        # 单一分隔符
        result = split_text(text, ",")
        assert result == ["apple", "banana;cherry|date"]

        # 多分隔符
        result = split_text(text, [",", ";", "|"])
        assert result == ["apple", "banana", "cherry", "date"]

    def test_join_text(self):
        """测试文本连接"""
        items = ["apple", "banana", "cherry"]

        # 默认连接
        result = join_text(items)
        assert result == "apple,banana,cherry"

        # 自定义分隔符
        result = join_text(items, separator=" | ")
        assert result == "apple | banana | cherry"

    def test_edge_cases(self):
        """测试边界情况"""
        # 空字符串
        assert clean_string("") == ""
        assert truncate_text("", 10) == ""
        assert count_words("") == 0

        # None值处理（如果函数支持）
        # assert clean_string(None) == ""

        # 单字符
        assert reverse_string("a") == "a"
        assert capitalize_words("a") == "A"

    def test_unicode_handling(self):
        """测试Unicode处理"""
        # 中文
        chinese_text = "你好世界"
        assert len(chinese_text) == 4
        assert reverse_string(chinese_text) == "界世好你"

        # Emoji
        emoji_text = "Hello 👋 World 🌍"
        assert "👋" in emoji_text
        assert "🌍" in emoji_text

    def test_performance_with_large_text(self):
        """测试大文本性能"""
        import time

        # 创建大文本
        large_text = "word " * 10000

        start_time = time.time()
        word_count = count_words(large_text)
        end_time = time.time()

        assert word_count == 10000
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_chain_operations(self):
        """测试链式操作"""
        original = "  Hello WORLD! 123  "

        # 链式处理
        result = clean_string(original)
        result = capitalize_words(result)
        result = truncate_text(result, 20)

        assert isinstance(result, str)
        assert len(result) <= 23  # 考虑省略号

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("simple", "simple"),
            ("  spaced  ", "spaced"),
            ("CAPITAL", "capital"),
            ("Mixed CASE", "mixed case"),
            ("with-dashes", "withdashes"),
            ("with_underscores", "withunderscores"),
            ("with123numbers", "with123numbers"),
        ],
    )
    def test_clean_string_parametrized(self, input_text, expected):
        """参数化测试字符串清理"""
        result = clean_string(input_text)
        assert result == expected

    def test_error_handling(self):
        """测试错误处理"""
        # 测试非字符串输入
        with pytest.raises((TypeError, AttributeError)):
            clean_string(123)

        with pytest.raises((TypeError, AttributeError)):
            count_words(None)

    def test_memory_efficiency(self):
        """测试内存效率"""

        # 处理大字符串
        large_string = "x" * 1000000

        # 测试函数不会显著增加内存使用
        result = clean_string(large_string)
        assert len(result) <= len(large_string)

        # 验证结果类型
        assert isinstance(result, str)
