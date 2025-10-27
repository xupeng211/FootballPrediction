"""
字符串工具测试
Tests for String Utils

测试src.utils.string_utils模块的功能
"""

import pytest

from src.utils.string_utils import StringUtils


@pytest.mark.unit
class TestStringUtils:
    """字符串工具测试"""

    # ==================== 截断字符串测试 ====================

    def test_truncate_shorter_text(self):
        """测试：短文本不需要截断"""
        text = "Hello"
        _result = StringUtils.truncate(text, 10)
        assert _result == "Hello"

    def test_truncate_exact_length(self):
        """测试：正好等于长度限制"""
        text = "Hello World"
        _result = StringUtils.truncate(text, 11)
        assert _result == "Hello World"

    def test_truncate_longer_text(self):
        """测试：长文本需要截断"""
        text = "This is a very long text"
        _result = StringUtils.truncate(text, 10)
        assert _result == "This is..."

    def test_truncate_custom_suffix(self):
        """测试：自定义后缀"""
        text = "This is a very long text"
        _result = StringUtils.truncate(text, 10, suffix=" [more]")
        # 计算正确的结果：10 - len(" [more]") = 10 - 7 = 3个字符
        assert _result == "Thi [more]"

    def test_truncate_empty_text(self):
        """测试：空文本"""
        assert StringUtils.truncate("", 5) == ""

    def test_truncate_zero_length(self):
        """测试：零长度限制"""
        text = "Hello"
        _result = StringUtils.truncate(text, 0)
        # 0长度意味着只能放后缀，但truncate会保留至少后缀长度的字符
        assert _result == "He..."

    # ==================== Slugify测试 ====================

    def test_slugify_simple(self):
        """测试：简单slugify"""
        assert StringUtils.slugify("Hello World") == "hello-world"

    def test_slugify_with_special_chars(self):
        """测试：包含特殊字符"""
        assert StringUtils.slugify("Python & AI") == "python-ai"

    def test_slugify_with_spaces(self):
        """测试：多余空格"""
        assert StringUtils.slugify("  Trim spaces  ") == "trim-spaces"

    def test_slugify_with_hyphens(self):
        """测试：连字符处理"""
        assert StringUtils.slugify("word-word word") == "word-word-word"

    def test_slugify_empty(self):
        """测试：空字符串"""
        assert StringUtils.slugify("") == ""

    def test_slugify_numbers_and_symbols(self):
        """测试：数字和符号"""
        assert StringUtils.slugify("Test 123!@#") == "test-123"

    # ==================== 驼峰转下划线测试 ====================

    def test_camel_to_snake_simple(self):
        """测试：简单驼峰转下划线"""
        assert StringUtils.camel_to_snake("helloWorld") == "hello_world"

    def test_camel_to_snake_multiple_words(self):
        """测试：多个单词"""
        assert StringUtils.camel_to_snake("HelloWorldTest") == "hello_world_test"

    def test_camel_to_snake_with_numbers(self):
        """测试：包含数字"""
        assert StringUtils.camel_to_snake("test123Value") == "test123_value"

    def test_camel_to_snake_with_acronyms(self):
        """测试：包含缩写"""
        assert StringUtils.camel_to_snake("HTMLParser") == "html_parser"

    def test_camel_to_snake_already_snake(self):
        """测试：已经是下划线格式"""
        assert StringUtils.camel_to_snake("hello_world") == "hello_world"

    def test_camel_to_snake_empty(self):
        """测试：空字符串"""
        assert StringUtils.camel_to_snake("") == ""

    # ==================== 下划线转驼峰测试 ====================

    def test_snake_to_camel_simple(self):
        """测试：简单下划线转驼峰"""
        assert StringUtils.snake_to_camel("hello_world") == "helloWorld"

    def test_snake_to_camel_multiple(self):
        """测试：多个下划线"""
        assert StringUtils.snake_to_camel("hello_world_test") == "helloWorldTest"

    def test_snake_to_camel_single_word(self):
        """测试：单个单词"""
        assert StringUtils.snake_to_camel("hello") == "hello"

    def test_snake_to_camel_with_numbers(self):
        """测试：包含数字"""
        assert StringUtils.snake_to_camel("test_123_value") == "test123Value"

    def test_snake_to_camel_with_underscores(self):
        """测试：开头结尾的下划线"""
        # 实际实现会去掉开头和结尾的下划线
        assert StringUtils.snake_to_camel("_hello_world_") == "HelloWorld"

    def test_snake_to_camel_empty(self):
        """测试：空字符串"""
        assert StringUtils.snake_to_camel("") == ""

    # ==================== 清理文本测试 ====================

    def test_clean_text_simple(self):
        """测试：简单清理"""
        text = "  Hello   World  "
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_with_newlines(self):
        """测试：包含换行"""
        text = "Hello\n\nWorld\n\n"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_with_tabs(self):
        """测试：包含制表符"""
        text = "Hello\t\tWorld\t"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_mixed_whitespace(self):
        """测试：混合空白字符"""
        text = "  Hello \n\n\t World  \t\n"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_already_clean(self):
        """测试：已经干净的文本"""
        text = "Hello World"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_empty(self):
        """测试：空文本"""
        assert StringUtils.clean_text("") == ""

    def test_clean_text_only_whitespace(self):
        """测试：只有空白字符"""
        text = "   \n\n\t   "
        _result = StringUtils.clean_text(text)
        assert _result == ""

    # ==================== 提取数字测试 ====================

    def test_extract_numbers_simple(self):
        """测试：简单数字提取"""
        text = "abc123def456"
        _result = StringUtils.extract_numbers(text)
        assert _result == [123.0, 456.0]

    def test_extract_numbers_no_numbers(self):
        """测试：没有数字"""
        text = "no numbers here"
        _result = StringUtils.extract_numbers(text)
        assert _result == []

    def test_extract_numbers_with_decimals(self):
        """测试：包含小数"""
        text = "The price is 12.99 dollars"
        _result = StringUtils.extract_numbers(text)
        assert _result == [12.99]

    def test_extract_numbers_negative_numbers(self):
        """测试：负数"""
        text = "Temperature is -5 degrees"
        _result = StringUtils.extract_numbers(text)
        assert _result == [-5.0]

    def test_extract_numbers_mixed(self):
        """测试：混合数字"""
        text = "Values: -1.5, 2, 3.14, and 100"
        _result = StringUtils.extract_numbers(text)
        assert _result == [-1.5, 2.0, 3.14, 100.0]

    def test_extract_numbers_only_numbers(self):
        """测试：只有数字"""
        text = "123"
        _result = StringUtils.extract_numbers(text)
        assert _result == [123.0]

    def test_extract_numbers_empty(self):
        """测试：空字符串"""
        assert StringUtils.extract_numbers("") == []

    # ==================== 组合测试 ====================

    def test_combined_operations(self):
        """测试：组合操作"""
        # 清理并截断
        text = "  Hello   World! This is a test.  "
        cleaned = StringUtils.clean_text(text)
        truncated = StringUtils.truncate(cleaned, 15)
        assert truncated == "Hello World!..."

        # slugify并清理
        slug = StringUtils.slugify("  Hello & World!  ")
        assert slug == "hello-world"

    def test_round_trip_conversions(self):
        """测试：往返转换"""
        # 驼峰到下划线再回到驼峰
        camel = "helloWorldTest"
        snake = StringUtils.camel_to_snake(camel)
        back_to_camel = StringUtils.snake_to_camel(snake)
        assert back_to_camel == camel

        # 下划线到驼峰再回到下划线
        snake = "hello_world_test"
        camel = StringUtils.snake_to_camel(snake)
        back_to_snake = StringUtils.camel_to_snake(camel)
        # 注意：开头的小写会丢失
        assert back_to_snake == "hello_world_test"

    # ==================== 边界条件测试 ====================

    def test_unicode_handling(self):
        """测试：Unicode处理"""
        text = "测试文本"
        # slugify可能会移除Unicode字符
        slug = StringUtils.slugify(text)
        assert isinstance(slug, str)

        # truncate应该正确处理
        _result = StringUtils.truncate(text, 3)
        assert len(result) <= 3 + len("...")

    def test_very_long_text(self):
        """测试：非常长的文本"""
        text = "A" * 10000
        _result = StringUtils.truncate(text, 100)
        assert len(result) == 100
        assert _result.endswith("...")

    def test_text_with_line_breaks_in_slugify(self):
        """测试：slugify处理换行"""
        text = "Hello\nWorld"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"
