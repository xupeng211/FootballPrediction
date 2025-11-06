#!/usr/bin/env python3
"""
字符串工具实际功能单元测试

基于 src.utils.string_utils 模块的实际函数编写测试
"""

import pytest
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.string_utils import (
    cached_slug,
    batch_clean_strings,
    validate_batch_emails,
    normalize_string,
    truncate_string,
    is_empty,
    strip_html,
    format_currency,
    snake_to_camel,
    camel_to_snake
)


class TestStringUtilsActual:
    """字符串工具实际功能测试类"""

    def test_cached_slug_basic(self):
        """测试缓存slug生成"""
        result1 = cached_slug("Hello World")
        result2 = cached_slug("Hello World")  # 应该使用缓存

        assert result1 == "hello-world"
        assert result2 == "hello-world"
        assert result1 == result2  # 缓存应该返回相同结果

    def test_cached_slug_different_inputs(self):
        """测试不同输入的slug生成"""
        result1 = cached_slug("Python Programming")
        result2 = cached_slug("Web Development")

        assert result1 == "python-programming"
        assert result2 == "web-development"
        assert result1 != result2

    def test_batch_clean_strings(self):
        """测试批量字符串清理"""
        input_strings = ["  Hello  ", "World  ", "  Python  "]
        result = batch_clean_strings(input_strings)

        assert len(result) == 3
        assert result[0] == "Hello"
        assert result[1] == "World"
        assert result[2] == "Python"

    def test_batch_clean_strings_empty(self):
        """测试空列表批量清理"""
        result = batch_clean_strings([])
        assert result == []

    def test_validate_batch_emails(self):
        """测试批量邮箱验证"""
        emails = ["test@example.com", "invalid-email", "user@domain.org"]
        result = validate_batch_emails(emails)

        assert isinstance(result, dict)
        assert "valid" in result
        assert "invalid" in result
        assert len(result["valid"]) >= 1
        assert len(result["invalid"]) >= 1

    def test_normalize_string(self):
        """测试字符串标准化"""
        # 测试基础标准化
        result = normalize_string("  Hello World  ")
        assert result.strip() == "Hello World"

        # 测试特殊字符处理
        result = normalize_string("café")
        # 应该移除或替换重音符号
        assert isinstance(result, str)

    def test_truncate_string(self):
        """测试字符串截断"""
        text = "This is a long string that needs to be truncated"

        # 基础截断
        result = truncate_string(text, 20)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")

        # 测试短文本
        short_text = "Short"
        result = truncate_string(short_text, 20)
        assert result == short_text

    def test_truncate_string_custom_suffix(self):
        """测试自定义后缀截断"""
        text = "This is a very long string"
        result = truncate_string(text, 15, suffix="[...]")

        assert len(result) <= 19  # 15 + "[...]"
        assert "[...]" in result

    def test_is_empty(self):
        """测试空字符串检测"""
        assert is_empty("") is True
        assert is_empty("   ") is True
        assert is_empty("hello") is False
        assert is_empty("  hello  ") is False

    def test_strip_html(self):
        """测试HTML标签清理"""
        html_text = "<p>Hello <strong>World</strong></p>"
        result = strip_html(html_text)

        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_html_complex(self):
        """测试复杂HTML清理"""
        html_text = """
        <div class="container">
            <h1>Title</h1>
            <p>Paragraph with <a href="#">link</a></p>
        </div>
        """
        result = strip_html(html_text)

        assert "<div" not in result
        assert "<h1>" not in result
        assert "<a" not in result
        assert "Title" in result
        assert "link" in result

    def test_format_currency(self):
        """测试货币格式化"""
        # 默认美元格式
        result = format_currency(1234.56)
        assert "$" in result
        assert "1234.56" in result or "1,234.56" in result

        # 自定义货币
        result = format_currency(1234.56, "€")
        assert "€" in result

        # 整数金额
        result = format_currency(1000)
        assert "$" in result

    def test_snake_to_camel(self):
        """测试蛇形转驼峰命名"""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("python_programming") == "pythonProgramming"
        assert snake_to_camel("single") == "single"
        assert snake_to_camel("") == ""

    def test_snake_to_camel_multiple_words(self):
        """测试多词蛇形转驼峰"""
        assert snake_to_camel("this_is_a_test") == "thisIsATest"
        assert snake_to_camel("convert_to_camel_case") == "convertToCamelCase"

    def test_camel_to_snake(self):
        """测试驼峰转蛇形命名"""
        assert camel_to_snake("helloWorld") == "hello_world"
        assert camel_to_snake("pythonProgramming") == "python_programming"
        assert camel_to_snake("Single") == "single"
        assert camel_to_snake("") == ""

    def test_camel_to_snake_pascal(self):
        """测试帕斯卡命名转蛇形"""
        assert camel_to_snake("HelloWorld") == "hello_world"
        assert camel_to_snake("PythonProgramming") == "python_programming"

    def test_round_trip_conversion(self):
        """测试往返转换"""
        # 蛇形 -> 驼峰 -> 蛇形
        original = "hello_world_test"
        camel = snake_to_camel(original)
        back_to_snake = camel_to_snake(camel)
        assert back_to_snake == original

        # 驼峰 -> 蛇形 -> 驼峰
        original_camel = "helloWorldTest"
        snake = camel_to_snake(original_camel)
        back_to_camel = snake_to_camel(snake)
        assert back_to_camel == original_camel

    def test_edge_cases(self):
        """测试边界情况"""
        # 空字符串
        assert cached_slug("") == ""
        assert normalize_string("") == ""
        assert truncate_string("", 10) == ""
        assert is_empty("") is True
        assert strip_html("") == ""

        # 单字符
        assert snake_to_camel("a") == "a"
        assert camel_to_snake("A") == "a"

    def test_unicode_handling(self):
        """测试Unicode处理"""
        unicode_text = "Héllo Wörld"
        result = normalize_string(unicode_text)
        assert isinstance(result, str)

        # 测试中文slug
        chinese_slug = cached_slug("你好世界")
        assert isinstance(chinese_slug, str)
        assert len(chinese_slug) > 0

    def test_performance_large_input(self):
        """测试大输入性能"""
        import time

        # 大批量字符串清理
        large_list = ["  test string {}  ".format(i) for i in range(1000)]

        start_time = time.time()
        result = batch_clean_strings(large_list)
        end_time = time.time()

        assert len(result) == 1000
        assert (end_time - start_time) < 5.0  # 应该在5秒内完成

    def test_html_edge_cases(self):
        """测试HTML边界情况"""
        # 嵌套标签
        nested_html = "<div><p><strong>Nested</strong> text</p></div>"
        result = strip_html(nested_html)
        assert "Nested" in result
        assert "text" in result
        assert "<" not in result

        # 自闭合标签
        self_closing = "<img src='test.jpg' /><br/>"
        result = strip_html(self_closing)
        assert "<img" not in result
        assert "<br" not in result

    @pytest.mark.parametrize("input_snake,expected_camel", [
        ("hello", "hello"),
        ("hello_world", "helloWorld"),
        ("test_case", "testCase"),
        ("multiple_words_here", "multipleWordsHere"),
        ("", ""),
    ])
    def test_snake_to_camel_parametrized(self, input_snake, expected_camel):
        """参数化测试蛇形转驼峰"""
        result = snake_to_camel(input_snake)
        assert result == expected_camel

    @pytest.mark.parametrize("input_camel,expected_snake", [
        ("hello", "hello"),
        ("helloWorld", "hello_world"),
        ("testCase", "test_case"),
        ("multipleWordsHere", "multiple_words_here"),
        ("HelloWorld", "hello_world"),
        ("", ""),
    ])
    def test_camel_to_snake_parametrized(self, input_camel, expected_snake):
        """参数化测试驼峰转蛇形"""
        result = camel_to_snake(input_camel)
        assert result == expected_snake

    def test_error_handling(self):
        """测试错误处理"""
        # 测试非字符串输入
        with pytest.raises((TypeError, AttributeError)):
            cached_slug(123)

        with pytest.raises((TypeError, AttributeError)):
            truncate_string(None, 10)

    def test_memory_efficiency(self):
        """测试内存效率"""
        # 处理大字符串
        large_string = "x" * 100000

        result = truncate_string(large_string, 1000)
        assert len(result) <= 1003  # 1000 + "..."
        assert isinstance(result, str)

    def test_batch_operations_mixed(self):
        """测试混合批量操作"""
        # 混合有效和无效的邮箱
        mixed_emails = [
            "valid@example.com",
            "invalid-email",
            "user@domain.org",
            "another.invalid",
            "test123@test.com"
        ]

        result = validate_batch_emails(mixed_emails)
        assert len(result["valid"]) >= 2
        assert len(result["invalid"]) >= 2
        assert len(result["valid"]) + len(result["invalid"]) == len(mixed_emails)