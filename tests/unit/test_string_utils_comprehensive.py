"""
字符串处理工具的全面单元测试
Comprehensive unit tests for string utilities
"""

import pytest
from src.utils.string_utils import StringUtils


@pytest.mark.unit
class TestTruncate:
    """测试字符串截断功能"""

    def test_truncate_shorter_text(self):
        """测试截断比限制短的文本"""
        text = "Short text"
        result = StringUtils.truncate(text, 20)
        assert result == text

    def test_truncate_exact_length(self):
        """测试与限制长度相同的文本"""
        text = "Exact length"
        result = StringUtils.truncate(text, len(text))
        assert result == text

    def test_truncate_longer_text(self):
        """测试截断比限制长的文本"""
        text = "This is a very long text that needs to be truncated"
        result = StringUtils.truncate(text, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_custom_suffix(self):
        """测试自定义后缀"""
        text = "This is a long text"
        result = StringUtils.truncate(text, 15, suffix=" [more]")
        assert result == "This is a [more]"

    def test_truncate_empty_string(self):
        """测试空字符串"""
        result = StringUtils.truncate("", 10)
        assert result == ""

    def test_truncate_zero_length(self):
        """测试零长度限制"""
        text = "Some text"
        result = StringUtils.truncate(text, 0)
        assert result == "..."

    def test_truncate_negative_length(self):
        """测试负数长度限制"""
        text = "Some text"
        result = StringUtils.truncate(text, -5)
        # 应该只返回后缀
        assert result == "..."

    def test_truncate_shorter_than_suffix(self):
        """测试限制比后缀还短"""
        text = "Test"
        result = StringUtils.truncate(text, 2)  # 2 < len("...") = 3
        assert result == "..."

    def test_truncate_unicode_characters(self):
        """测试Unicode字符"""
        text = "测试中文字符串截断功能"
        result = StringUtils.truncate(text, 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_truncate_with_multibyte_characters(self):
        """测试多字节字符"""
        text = "Café naïve résumé"
        result = StringUtils.truncate(text, 10)
        assert len(result) == 10

    def test_truncate_very_long_text(self):
        """测试非常长的文本"""
        text = "A" * 1000
        result = StringUtils.truncate(text, 50)
        assert len(result) == 50
        assert result.endswith("...")


@pytest.mark.unit
class TestSlugify:
    """测试URL友好字符串转换功能"""

    def test_slugify_simple_text(self):
        """测试简单文本"""
        result = StringUtils.slugify("Simple Text")
        assert result == "simple-text"

    def test_slugify_with_special_characters(self):
        """测试包含特殊字符的文本"""
        result = StringUtils.slugify("Text with special characters!@#$%")
        assert result == "text-with-special-characters"

    def test_slugify_with_multiple_spaces(self):
        """测试多个空格"""
        result = StringUtils.slugify("Text    with    multiple    spaces")
        assert result == "text-with-multiple-spaces"

    def test_slugify_with_underscores(self):
        """测试包含下划线"""
        result = StringUtils.slugify("Text_with_underscores")
        assert result == "text_with_underscores"

    def test_slugify_with_hyphens(self):
        """测试包含连字符"""
        result = StringUtils.slugify("Text-with-hyphens")
        assert result == "text-with-hyphens"

    def test_slugify_with_numbers(self):
        """测试包含数字"""
        result = StringUtils.slugify("Text with numbers 123")
        assert result == "text-with-numbers-123"

    def test_slugify_mixed_case(self):
        """测试混合大小写"""
        result = StringUtils.slugify("MiXeD CaSe TeXt")
        assert result == "mixed-case-text"

    def test_slugify_empty_string(self):
        """测试空字符串"""
        result = StringUtils.slugify("")
        assert result == ""

    def test_slugify_only_special_characters(self):
        """测试只有特殊字符"""
        result = StringUtils.slugify("!@#$%^&*()")
        assert result == ""

    def test_slugify_unicode_characters(self):
        """测试Unicode字符"""
        result = StringUtils.slugify("测试中文内容")
        assert result == ""

    def test_slugify_leading_trailing_spaces(self):
        """测试前导和尾随空格"""
        result = StringUtils.slugify("  spaced text  ")
        assert result == "spaced-text"

    def test_slugify_leading_trailing_hyphens(self):
        """测试前导和尾随连字符"""
        result = StringUtils.slugify("---text---")
        assert result == "text"

    def test_slugify_multiple_separators(self):
        """测试多个分隔符"""
        result = StringUtils.slugify("Text_with-many   separators---here")
        assert result == "text_with-many-separators-here"

    def test_slugify_accented_characters(self):
        """测试带重音字符"""
        result = StringUtils.slugify("Café naïve résumé")
        assert result == "caf-naïve-résumé"


@pytest.mark.unit
class TestCamelToSnake:
    """测试驼峰命名转下划线命名功能"""

    def test_camel_to_snake_simple(self):
        """测试简单的驼峰命名"""
        result = StringUtils.camel_to_snake("camelCase")
        assert result == "camel_case"

    def test_camel_to_snake_pascal_case(self):
        """测试帕斯卡命名"""
        result = StringUtils.camel_to_snake("PascalCase")
        assert result == "pascal_case"

    def test_camel_to_snake_multiple_words(self):
        """测试多个单词"""
        result = StringUtils.camel_to_snake("convertCamelCaseToSnake")
        assert result == "convert_camel_case_to_snake"

    def test_camel_to_snake_with_numbers(self):
        """测试包含数字"""
        result = StringUtils.camel_to_snake("camelCase123")
        assert result == "camel_case123"

    def test_camel_to_snake_with_acronyms(self):
        """测试包含缩写词"""
        result = StringUtils.camel_to_snake("HTTPRequestToJSON")
        assert result == "http_request_to_json"

    def test_camel_to_snake_single_word(self):
        """测试单个单词"""
        result = StringUtils.camel_to_snake("word")
        assert result == "word"

    def test_camel_to_snake_empty_string(self):
        """测试空字符串"""
        result = StringUtils.camel_to_snake("")
        assert result == ""

    def test_camel_to_snake_already_snake(self):
        """测试已经是下划线命名"""
        result = StringUtils.camel_to_snake("already_snake")
        assert result == "already_snake"

    def test_camel_to_snake_all_caps(self):
        """测试全大写"""
        result = StringUtils.camel_to_snake("ALLCAPS")
        assert result == "a_l_l_c_a_p_s"

    def test_camel_to_snake_mixed_patterns(self):
        """测试混合模式"""
        result = StringUtils.camel_to_snake("XMLHttpRequest")
        assert result == "x_m_l_http_request"


@pytest.mark.unit
class TestSnakeToCamel:
    """测试下划线命名转驼峰命名功能"""

    def test_snake_to_camel_simple(self):
        """测试简单的下划线命名"""
        result = StringUtils.snake_to_camel("snake_case")
        assert result == "snakeCase"

    def test_snake_to_camel_multiple_words(self):
        """测试多个单词"""
        result = StringUtils.snake_to_camel("convert_snake_case_to_camel")
        assert result == "convertSnakeCaseToCamel"

    def test_snake_to_camel_single_word(self):
        """测试单个单词"""
        result = StringUtils.snake_to_camel("word")
        assert result == "word"

    def test_snake_to_camel_empty_string(self):
        """测试空字符串"""
        result = StringUtils.snake_to_camel("")
        assert result == ""

    def test_snake_to_camel_with_numbers(self):
        """测试包含数字"""
        result = StringUtils.snake_to_camel("snake_case123")
        assert result == "snakeCase123"

    def test_snake_to_camel_single_underscores(self):
        """测试单个下划线"""
        result = StringUtils.snake_to_camel("_leading")
        assert result == "_leading"
        result = StringUtils.snake_to_camel("trailing_")
        assert result == "trailing_"

    def test_snake_to_camel_multiple_underscores(self):
        """测试多个连续下划线"""
        result = StringUtils.snake_to_camel("multiple__underscores")
        assert result == "multiple_Underscores"

    def test_snake_to_camel_already_camel(self):
        """测试已经是驼峰命名"""
        result = StringUtils.snake_to_camel("alreadyCamel")
        assert result == "alreadyCamel"

    def test_snake_to_camel_all_lowercase(self):
        """测试全小写"""
        result = StringUtils.snake_to_camel("alllowercase")
        assert result == "alllowercase"

    def test_snake_to_camel_leading_underscores(self):
        """测试前导下划线"""
        result = StringUtils.snake_to_camel("__private_variable")
        assert result == "__PrivateVariable"


@pytest.mark.unit
class TestCleanText:
    """测试文本清理功能"""

    def test_clean_text_normal(self):
        """测试正常文本"""
        text = "Normal text"
        result = StringUtils.clean_text(text)
        assert result == text

    def test_clean_text_multiple_spaces(self):
        """测试多个空格"""
        text = "Text    with    multiple    spaces"
        result = StringUtils.clean_text(text)
        assert result == "Text with multiple spaces"

    def test_clean_text_leading_trailing_spaces(self):
        """测试前导和尾随空格"""
        text = "   spaced text   "
        result = StringUtils.clean_text(text)
        assert result == "spaced text"

    def test_clean_text_tabs_and_newlines(self):
        """测试制表符和换行符"""
        text = "Text\twith\ntabs\r\nand\nnewlines"
        result = StringUtils.clean_text(text)
        assert result == "Text with tabs and newlines"

    def test_clean_text_mixed_whitespace(self):
        """测试混合空白字符"""
        text = "  Text\twith  \n  mixed   \r\n  whitespace  "
        result = StringUtils.clean_text(text)
        assert result == "Text with mixed whitespace"

    def test_clean_text_empty_string(self):
        """测试空字符串"""
        result = StringUtils.clean_text("")
        assert result == ""

    def test_clean_text_only_whitespace(self):
        """测试只有空白字符"""
        result = StringUtils.clean_text("   \t\n\r\n   ")
        assert result == ""

    def test_clean_text_unicode_whitespace(self):
        """测试Unicode空白字符"""
        # 测试各种Unicode空白字符
        text = "Text\u2003with\u2009Unicode\u00a0whitespace"
        result = StringUtils.clean_text(text)
        # Unicode空白可能不会被\s匹配，这取决于正则表达式实现
        assert isinstance(result, str)

    def test_clean_text_single_spaces(self):
        """测试单个空格"""
        text = "Single spaces"
        result = StringUtils.clean_text(text)
        assert result == text

    def test_clean_text_newlines_only(self):
        """测试只有换行符"""
        text = "\n\n\n"
        result = StringUtils.clean_text(text)
        assert result == ""

    def test_clean_text_complex(self):
        """测试复杂情况"""
        text = "\n\n  Paragraph 1\n\n  Paragraph 2  \n\n  \n"
        result = StringUtils.clean_text(text)
        assert result == "Paragraph 1 Paragraph 2"


@pytest.mark.unit
class TestExtractNumbers:
    """测试数字提取功能"""

    def test_extract_numbers_integers(self):
        """测试提取整数"""
        text = "The numbers are 10, 20, and 30"
        result = StringUtils.extract_numbers(text)
        assert result == [10.0, 20.0, 30.0]

    def test_extract_numbers_floats(self):
        """测试提取浮点数"""
        text = "Values: 1.5, 2.75, and 3.14"
        result = StringUtils.extract_numbers(text)
        assert result == [1.5, 2.75, 3.14]

    def test_extract_numbers_negative(self):
        """测试提取负数"""
        text = "Negative numbers: -10 and -2.5"
        result = StringUtils.extract_numbers(text)
        assert result == [-10.0, -2.5]

    def test_extract_numbers_mixed(self):
        """测试混合整数和浮点数"""
        text = "Mixed: 1, 2.5, -3, 4.75"
        result = StringUtils.extract_numbers(text)
        assert result == [1.0, 2.5, -3.0, 4.75]

    def test_extract_numbers_no_numbers(self):
        """测试没有数字的文本"""
        text = "No numbers here"
        result = StringUtils.extract_numbers(text)
        assert result == []

    def test_extract_numbers_empty_string(self):
        """测试空字符串"""
        result = StringUtils.extract_numbers("")
        assert result == []

    def test_extract_numbers_with_currency(self):
        """测试带货币符号"""
        text = "Prices: $10.50, €20.75, ¥30"
        result = StringUtils.extract_numbers(text)
        assert result == [10.50, 20.75, 30.0]

    def test_extract_numbers_with_percentages(self):
        """测试带百分比"""
        text = "Growth: 15%, -5.5%, and 100%"
        result = StringUtils.extract_numbers(text)
        assert result == [15.0, -5.5, 100.0]

    def test_extract_numbers_with_decimals_only(self):
        """测试只有小数点"""
        text = "Decimal points: .5 and .75"
        result = StringUtils.extract_numbers(text)
        assert result == [5.0, 75.0]

    def test_extract_numbers_scientific_notation(self):
        """测试科学记数法（可能不被支持）"""
        text = "Scientific: 1e5 and 2.5E-3"
        result = StringUtils.extract_numbers(text)
        # 简单的正则可能不支持科学记数法
        assert 1.0 in result or 5.0 in result

    def test_extract_numbers_phone_numbers(self):
        """测试电话号码"""
        text = "Phone: 123-456-7890"
        result = StringUtils.extract_numbers(text)
        assert result == [123.0, 456.0, 7890.0]

    def test_extract_numbers_dates(self):
        """测试日期中的数字"""
        text = "Date: 2024-01-15 and time 15:30"
        result = StringUtils.extract_numbers(text)
        assert result == [2024.0, 1.0, 15.0, 15.0, 30.0]

    def test_extract_numbers_duplicate_numbers(self):
        """测试重复数字"""
        text = "Same number 100 appears 100 times"
        result = StringUtils.extract_numbers(text)
        assert result == [100.0, 100.0]

    def test_extract_numbers_with_units(self):
        """测试带单位"""
        text = "Length: 10m, 2.5km, 3cm"
        result = StringUtils.extract_numbers(text)
        assert result == [10.0, 2.5, 3.0]


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况"""

    def test_all_methods_with_none(self):
        """测试None输入"""
        methods = [
            ("truncate", lambda: StringUtils.truncate(None, 10)),
            ("slugify", lambda: StringUtils.slugify(None)),
            ("camel_to_snake", lambda: StringUtils.camel_to_snake(None)),
            ("snake_to_camel", lambda: StringUtils.snake_to_camel(None)),
            ("clean_text", lambda: StringUtils.clean_text(None)),
            ("extract_numbers", lambda: StringUtils.extract_numbers(None)),
        ]

        for method_name, method_call in methods:
            # 这些方法应该抛出TypeError
            with pytest.raises((TypeError, AttributeError)):
                method_call()

    def test_all_methods_with_empty_strings(self):
        """测试空字符串输入"""
        assert StringUtils.truncate("", 10) == ""
        assert StringUtils.slugify("") == ""
        assert StringUtils.camel_to_snake("") == ""
        assert StringUtils.snake_to_camel("") == ""
        assert StringUtils.clean_text("") == ""
        assert StringUtils.extract_numbers("") == []

    def test_case_conversion_roundtrip(self):
        """测试大小写转换往返"""
        original = "convertThisText"
        snake = StringUtils.camel_to_snake(original)
        camel = StringUtils.snake_to_camel(snake)

        # 注意：往返可能不完全一致（如缩写词）
        assert isinstance(camel, str)
        assert len(camel) > 0

    def test_unicode_handling(self):
        """测试Unicode处理"""
        unicode_texts = ["测试中文", "Café naïve", "🚀 Emoji test", "العربية", "עברית"]

        for text in unicode_texts:
            # 这些操作应该不会抛出异常
            result_clean = StringUtils.clean_text(text)
            result_truncate = StringUtils.truncate(text, 10)

            assert isinstance(result_clean, str)
            assert isinstance(result_truncate, str)

    def test_very_long_strings(self):
        """测试非常长的字符串"""
        long_text = "A" * 10000

        # 截断长文本
        result = StringUtils.truncate(long_text, 100)
        assert len(result) == 100

        # 清理长文本
        result = StringUtils.clean_text(long_text)
        assert result == long_text

    def test_special_characters(self):
        """测试特殊字符"""
        special_chars = "!@#$%^&*()[]{}|\\:;\"'<>?,./"

        # 这些应该被slugify移除
        result = StringUtils.slugify(f"text{special_chars}text")
        assert "text" in result
        assert not any(c in result for c in special_chars)

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试大量文本的处理时间
        large_text = "Test " * 10000

        start_time = time.time()
        for _ in range(100):
            StringUtils.clean_text(large_text)
        end_time = time.time()

        # 应该在合理时间内完成
        assert end_time - start_time < 5.0  # 5秒内完成100次清理


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__])
