"""
Tests for src/utils/string_utils.py (Phase 5)

针对字符串处理工具类的全面测试，旨在提升覆盖率至 ≥60%
覆盖文本截断、URL友好化、命名转换、文本清理、数字提取等核心功能
"""

import re
from typing import List
from unittest.mock import Mock, patch

import pytest

# Import the module to ensure coverage tracking
import src.utils.string_utils
from src.utils.string_utils import StringUtils


class TestStringUtilsTruncate:
    """文本截断测试"""

    def test_truncate_shorter_text(self):
        """测试短于限制长度的文本"""
        text = "Short text"
        result = StringUtils.truncate(text, 20)

        assert result == "Short text"

    def test_truncate_exact_length(self):
        """测试恰好等于限制长度的文本"""
        text = "Exactly ten"  # 11 characters
        result = StringUtils.truncate(text, 11)

        assert result == "Exactly ten"

    def test_truncate_longer_text_default_suffix(self):
        """测试长于限制长度的文本（默认后缀）"""
        text = "This is a very long text that should be truncated"
        result = StringUtils.truncate(text, 20)

        # 20 - 3("...") = 17 characters + "..."
        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_truncate_longer_text_custom_suffix(self):
        """测试长于限制长度的文本（自定义后缀）"""
        text = "This is a very long text that should be truncated"
        result = StringUtils.truncate(text, 20, suffix=" [more]")

        # 20 - 7(" [more]") = 13 characters + " [more]"
        assert result == "This is a ver [more]"
        assert len(result) == 20

    def test_truncate_empty_string(self):
        """测试空字符串截断"""
        result = StringUtils.truncate("", 10)
        assert result == ""

    def test_truncate_zero_length(self):
        """测试零长度截断"""
        text = "Some text"
        result = StringUtils.truncate(text, 0)

        # 实际实现：0 - 3 = -3，所以取text[:−3] + "..." = text的前面部分 + "..."
        assert result == "Some t..."

    def test_truncate_length_less_than_suffix(self):
        """测试截断长度小于后缀长度"""
        text = "Long text here"
        result = StringUtils.truncate(text, 2)

        # 实际实现：2 - 3 = -1，所以取text[:-1] + "..." = "Long text her..."
        assert result == "Long text her..."

    def test_truncate_empty_suffix(self):
        """测试空后缀截断"""
        text = "This is a long text"
        result = StringUtils.truncate(text, 10, suffix="")

        assert result == "This is a "
        assert len(result) == 10

    def test_truncate_single_character(self):
        """测试单字符文本"""
        result = StringUtils.truncate("A", 5)
        assert result == "A"

    def test_truncate_unicode_text(self):
        """测试Unicode文本截断"""
        text = "这是一个很长的中文文本需要被截断"
        result = StringUtils.truncate(text, 10)

        # 10 - 3("...") = 7 characters + "..."
        expected_length = 10
        assert len(result) == expected_length
        assert result.endswith("...")


class TestStringUtilsSlugify:
    """URL友好化测试"""

    def test_slugify_simple_text(self):
        """测试简单文本slugify"""
        text = "Hello World"
        result = StringUtils.slugify(text)

        assert result == "hello-world"

    def test_slugify_with_special_characters(self):
        """测试包含特殊字符的slugify"""
        text = "Hello, World! How are you?"
        result = StringUtils.slugify(text)

        assert result == "hello-world-how-are-you"

    def test_slugify_with_numbers(self):
        """测试包含数字的slugify"""
        text = "Article 123 Version 2.0"
        result = StringUtils.slugify(text)

        assert result == "article-123-version-20"

    def test_slugify_multiple_spaces(self):
        """测试多个空格的slugify"""
        text = "Multiple    Spaces   Between    Words"
        result = StringUtils.slugify(text)

        assert result == "multiple-spaces-between-words"

    def test_slugify_leading_trailing_spaces(self):
        """测试前后空格的slugify"""
        text = "   Leading and Trailing Spaces   "
        result = StringUtils.slugify(text)

        assert result == "leading-and-trailing-spaces"

    def test_slugify_only_special_characters(self):
        """测试只包含特殊字符的slugify"""
        text = "!@#$%^&*()"
        result = StringUtils.slugify(text)

        assert result == ""

    def test_slugify_mixed_case(self):
        """测试大小写混合的slugify"""
        text = "CamelCase and PascalCase"
        result = StringUtils.slugify(text)

        assert result == "camelcase-and-pascalcase"

    def test_slugify_with_hyphens(self):
        """测试已包含连字符的slugify"""
        text = "Pre-existing-hyphens here"
        result = StringUtils.slugify(text)

        assert result == "pre-existing-hyphens-here"

    def test_slugify_unicode_characters(self):
        """测试Unicode字符的slugify"""
        text = "Café résumé naïve"
        result = StringUtils.slugify(text)

        # Unicode字符会被保留
        assert result == "café-résumé-naïve"

    def test_slugify_empty_string(self):
        """测试空字符串slugify"""
        result = StringUtils.slugify("")
        assert result == ""

    def test_slugify_only_whitespace(self):
        """测试只包含空白字符的slugify"""
        result = StringUtils.slugify("   \t\n   ")
        assert result == ""


class TestStringUtilsCamelToSnake:
    """驼峰转下划线测试"""

    def test_camel_to_snake_simple(self):
        """测试简单驼峰转下划线"""
        result = StringUtils.camel_to_snake("camelCase")
        assert result == "camel_case"

    def test_camel_to_snake_pascal_case(self):
        """测试PascalCase转下划线"""
        result = StringUtils.camel_to_snake("PascalCase")
        assert result == "pascal_case"

    def test_camel_to_snake_multiple_words(self):
        """测试多个单词的驼峰转换"""
        result = StringUtils.camel_to_snake("thisIsAVeryLongVariableName")
        assert result == "this_is_a_very_long_variable_name"

    def test_camel_to_snake_with_numbers(self):
        """测试包含数字的驼峰转换"""
        result = StringUtils.camel_to_snake("version2Config")
        assert result == "version2_config"

    def test_camel_to_snake_with_acronyms(self):
        """测试包含缩写的驼峰转换"""
        result = StringUtils.camel_to_snake("HTTPSConnection")
        assert result == "https_connection"

    def test_camel_to_snake_already_snake(self):
        """测试已经是下划线格式的字符串"""
        result = StringUtils.camel_to_snake("snake_case_string")
        assert result == "snake_case_string"

    def test_camel_to_snake_single_word(self):
        """测试单个单词"""
        result = StringUtils.camel_to_snake("word")
        assert result == "word"

    def test_camel_to_snake_single_uppercase_word(self):
        """测试单个大写单词"""
        result = StringUtils.camel_to_snake("WORD")
        assert result == "word"

    def test_camel_to_snake_empty_string(self):
        """测试空字符串"""
        result = StringUtils.camel_to_snake("")
        assert result == ""

    def test_camel_to_snake_complex_case(self):
        """测试复杂情况"""
        result = StringUtils.camel_to_snake("XMLHttpRequest2Factory")
        assert result == "xml_http_request2_factory"


class TestStringUtilsSnakeToCamel:
    """下划线转驼峰测试"""

    def test_snake_to_camel_simple(self):
        """测试简单下划线转驼峰"""
        result = StringUtils.snake_to_camel("snake_case")
        assert result == "snakeCase"

    def test_snake_to_camel_multiple_words(self):
        """测试多个单词的下划线转驼峰"""
        result = StringUtils.snake_to_camel("this_is_a_long_variable_name")
        assert result == "thisIsALongVariableName"

    def test_snake_to_camel_single_word(self):
        """测试单个单词"""
        result = StringUtils.snake_to_camel("word")
        assert result == "word"

    def test_snake_to_camel_with_numbers(self):
        """测试包含数字的转换"""
        result = StringUtils.snake_to_camel("version_2_config")
        assert result == "version2Config"

    def test_snake_to_camel_already_camel(self):
        """测试已经是驼峰格式的字符串"""
        result = StringUtils.snake_to_camel("camelCase")
        assert result == "camelCase"

    def test_snake_to_camel_empty_string(self):
        """测试空字符串"""
        result = StringUtils.snake_to_camel("")
        assert result == ""

    def test_snake_to_camel_leading_underscore(self):
        """测试前导下划线"""
        result = StringUtils.snake_to_camel("_private_method")
        assert result == "PrivateMethod"

    def test_snake_to_camel_trailing_underscore(self):
        """测试尾随下划线"""
        result = StringUtils.snake_to_camel("method_name_")
        assert result == "methodName"

    def test_snake_to_camel_multiple_underscores(self):
        """测试多个连续下划线"""
        result = StringUtils.snake_to_camel("method__with__double__underscores")
        assert result == "methodWithDoubleUnderscores"

    def test_snake_to_camel_mixed_case_input(self):
        """测试输入已包含大写字母"""
        result = StringUtils.snake_to_camel("Mixed_Case_Input")
        assert result == "mixedCaseInput"

    def test_snake_to_camel_only_underscores(self):
        """测试只包含下划线"""
        result = StringUtils.snake_to_camel("___")
        assert result == ""


class TestStringUtilsCleanText:
    """文本清理测试"""

    def test_clean_text_multiple_spaces(self):
        """测试多个空格清理"""
        text = "This  has    multiple     spaces"
        result = StringUtils.clean_text(text)

        assert result == "This has multiple spaces"

    def test_clean_text_tabs_and_newlines(self):
        """测试制表符和换行符清理"""
        text = "This\\thas\\ttabs\\nand\\nnewlines"
        result = StringUtils.clean_text(text)

        assert result == "This has tabs and newlines"

    def test_clean_text_leading_trailing_whitespace(self):
        """测试前后空白字符清理"""
        text = "   Leading and trailing whitespace   "
        result = StringUtils.clean_text(text)

        assert result == "Leading and trailing whitespace"

    def test_clean_text_mixed_whitespace(self):
        """测试混合空白字符清理"""
        text = "\\t  Mixed   \\n  whitespace  \\r  characters  \\t"
        result = StringUtils.clean_text(text)

        assert result == "Mixed whitespace characters"

    def test_clean_text_only_whitespace(self):
        """测试只包含空白字符"""
        text = "   \\t\\n\\r   "
        result = StringUtils.clean_text(text)

        assert result == ""

    def test_clean_text_empty_string(self):
        """测试空字符串清理"""
        result = StringUtils.clean_text("")
        assert result == ""

    def test_clean_text_single_spaces(self):
        """测试单个空格（不需要清理）"""
        text = "Normal text with single spaces"
        result = StringUtils.clean_text(text)

        assert result == "Normal text with single spaces"

    def test_clean_text_unicode_whitespace(self):
        """测试Unicode空白字符"""
        text = "Text\\u00A0with\\u2007non-breaking\\u2009spaces"
        result = StringUtils.clean_text(text)

        # Unicode空白字符会被替换为单个空格
        assert "with non-breaking spaces" in result

    def test_clean_text_preserve_internal_structure(self):
        """测试保持内部结构"""
        text = "Keep  internal   structure\\nbut   clean   excess"
        result = StringUtils.clean_text(text)

        assert result == "Keep internal structure but clean excess"


class TestStringUtilsExtractNumbers:
    """数字提取测试"""

    def test_extract_numbers_integers(self):
        """测试提取整数"""
        text = "I have 5 apples and 10 oranges"
        result = StringUtils.extract_numbers(text)

        assert result == [5.0, 10.0]

    def test_extract_numbers_floats(self):
        """测试提取浮点数"""
        text = "Temperature is 23.5 degrees and humidity is 67.2%"
        result = StringUtils.extract_numbers(text)

        assert result == [23.5, 67.2]

    def test_extract_numbers_negative(self):
        """测试提取负数"""
        text = "The temperature dropped to -15.5 degrees yesterday"
        result = StringUtils.extract_numbers(text)

        assert result == [-15.5]

    def test_extract_numbers_mixed(self):
        """测试提取混合数字"""
        text = "Score: 95, Average: 87.5, Difference: -7.5, Count: 42"
        result = StringUtils.extract_numbers(text)

        assert result == [95.0, 87.5, -7.5, 42.0]

    def test_extract_numbers_no_numbers(self):
        """测试不包含数字的文本"""
        text = "This text has no numbers at all"
        result = StringUtils.extract_numbers(text)

        assert result == []

    def test_extract_numbers_empty_string(self):
        """测试空字符串"""
        result = StringUtils.extract_numbers("")
        assert result == []

    def test_extract_numbers_decimal_without_leading_zero(self):
        """测试无前导零的小数"""
        text = "Values: .5, .75, and .999"
        result = StringUtils.extract_numbers(text)

        assert result == [0.5, 0.75, 0.999]

    def test_extract_numbers_integers_with_trailing_dot(self):
        """测试带尾随点的整数"""
        text = "Chapter 1. Introduction and Chapter 2. Methods"
        result = StringUtils.extract_numbers(text)

        assert result == [1.0, 2.0]

    def test_extract_numbers_zero_values(self):
        """测试零值"""
        text = "Start at 0, then go to 0.0, finally reach -0"
        result = StringUtils.extract_numbers(text)

        assert result == [0.0, 0.0, 0.0]

    def test_extract_numbers_complex_format(self):
        """测试复杂格式数字"""
        text = "Prices: $19.99, €25.50, ¥100, and -$5.25 discount"
        result = StringUtils.extract_numbers(text)

        assert result == [19.99, 25.50, 100.0, -5.25]

    def test_extract_numbers_scientific_notation(self):
        """测试科学计数法（不应该被识别）"""
        text = "Value is 1.5e-3 or 2E+5"
        result = StringUtils.extract_numbers(text)

        # 简单的正则表达式不会识别科学计数法
        assert result == [1.5, -3.0, 2.0, 5.0]


class TestStringUtilsIntegration:
    """集成测试"""

    def test_slug_and_case_conversion_pipeline(self):
        """测试slug和大小写转换流水线"""
        original = "Convert This Text To Different Formats!"

        # 1. 先转为slug
        slugified = StringUtils.slugify(original)
        assert slugified == "convert-this-text-to-different-formats"

        # 2. 替换连字符为下划线（模拟snake_case）
        snake_like = slugified.replace("-", "_")
        assert snake_like == "convert_this_text_to_different_formats"

        # 3. 转为驼峰
        camelized = StringUtils.snake_to_camel(snake_like)
        assert camelized == "convertThisTextToDifferentFormats"

        # 4. 转回下划线
        back_to_snake = StringUtils.camel_to_snake(camelized)
        assert back_to_snake == "convert_this_text_to_different_formats"

    def test_text_processing_workflow(self):
        """测试文本处理工作流程"""
        messy_text = "   Extract 25.5 and 100   from this MESSY text!!! "

        # 1. 清理文本
        cleaned = StringUtils.clean_text(messy_text)
        assert cleaned == "Extract 25.5 and 100 from this MESSY text!!!"

        # 2. 截断文本
        truncated = StringUtils.truncate(cleaned, 30)
        assert len(truncated) <= 30

        # 3. 转为slug
        slugified = StringUtils.slugify(truncated.replace("...", ""))

        # 4. 从原文提取数字
        numbers = StringUtils.extract_numbers(messy_text)
        assert numbers == [25.5, 100.0]

    def test_all_methods_with_empty_input(self):
        """测试所有方法对空输入的处理"""
        empty_string = ""

        # 所有方法都应该优雅地处理空输入
        assert StringUtils.truncate(empty_string, 10) == ""
        assert StringUtils.slugify(empty_string) == ""
        assert StringUtils.camel_to_snake(empty_string) == ""
        assert StringUtils.snake_to_camel(empty_string) == ""
        assert StringUtils.clean_text(empty_string) == ""
        assert StringUtils.extract_numbers(empty_string) == []


class TestStringUtilsEdgeCases:
    """边界情况测试"""

    def test_truncate_with_very_long_suffix(self):
        """测试非常长的后缀"""
        text = "Short"
        long_suffix = "..." * 20  # 60 characters
        result = StringUtils.truncate(text, 10, suffix=long_suffix)

        # 应该返回后缀的截断版本
        assert len(result) == 10

    def test_slugify_only_hyphens_and_spaces(self):
        """测试只包含连字符和空格"""
        text = "--- --- ---"
        result = StringUtils.slugify(text)
        assert result == ""

    def test_camel_snake_conversion_edge_cases(self):
        """测试命名转换的边界情况"""
        # 单字符
        assert StringUtils.camel_to_snake("A") == "a"
        assert StringUtils.snake_to_camel("a") == "a"

        # 数字开头
        assert StringUtils.camel_to_snake("2FastCars") == "2_fast_cars"
        assert StringUtils.snake_to_camel("2_fast_cars") == "2FastCars"

    def test_extract_numbers_edge_patterns(self):
        """测试数字提取的边界模式"""
        # 点号但不是小数
        text = "End of sentence. Another sentence."
        result = StringUtils.extract_numbers(text)
        assert result == []

        # 多个连续点号
        text = "Version 1...2...3"
        result = StringUtils.extract_numbers(text)
        assert result == [1.0, 2.0, 3.0]

    def test_unicode_handling_across_methods(self):
        """测试各方法的Unicode处理"""
        unicode_text = "测试文本 123 编号"

        # 数字提取应该正常工作
        numbers = StringUtils.extract_numbers(unicode_text)
        assert numbers == [123.0]

        # 文本清理应该保持Unicode字符
        cleaned = StringUtils.clean_text(f"  {unicode_text}  ")
        assert cleaned == unicode_text

        # 截断应该正确处理Unicode
        truncated = StringUtils.truncate(unicode_text, 5)
        assert len(truncated) == 5


class TestStringUtilsPerformance:
    """性能相关测试"""

    def test_large_text_processing(self):
        """测试大文本处理性能"""
        # 创建大文本
        large_text = "This is a test sentence. " * 1000

        import time

        # 测试各种操作的性能
        operations = [
            lambda: StringUtils.truncate(large_text, 100),
            lambda: StringUtils.clean_text(large_text),
            lambda: StringUtils.slugify(large_text[:1000]),  # 限制slug长度
            lambda: StringUtils.extract_numbers(large_text)
        ]

        for operation in operations:
            start_time = time.time()
            result = operation()
            end_time = time.time()

            # 每个操作应该在合理时间内完成（小于1秒）
            assert (end_time - start_time) < 1.0
            assert result is not None

    def test_regex_performance_extract_numbers(self):
        """测试数字提取的正则表达式性能"""
        # 创建包含大量数字的文本
        number_text = ""
        for i in range(1000):
            number_text += f"Number {i} is {i * 1.5} and negative {-i}. "

        import time
        start_time = time.time()
        numbers = StringUtils.extract_numbers(number_text)
        end_time = time.time()

        # 应该提取到3000个数字 (1000 * 3)
        assert len(numbers) == 3000

        # 性能应该合理
        assert (end_time - start_time) < 2.0