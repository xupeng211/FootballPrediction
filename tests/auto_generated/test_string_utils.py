"""
Auto-generated tests for src.utils.string_utils module
"""

import pytest
from src.utils.string_utils import StringUtils


class TestStringUtils:
    """测试字符串处理工具类"""

    # Truncate tests
    def test_truncate_no_truncation_needed(self):
        """测试不需要截断的情况"""
        text = "短文本"
        result = StringUtils.truncate(text, 10)
        assert result == text

    def test_truncate_exact_length(self):
        """测试刚好等于指定长度"""
        text = "刚好十个字长"
        result = StringUtils.truncate(text, 6)
        assert result == text

    def test_truncate_with_default_suffix(self):
        """测试使用默认后缀截断"""
        text = "这是一个很长的文本需要被截断"
        result = StringUtils.truncate(text, 10)
        assert result == "这是一个很..."
        assert len(result) == 10

    def test_truncate_with_custom_suffix(self):
        """测试使用自定义后缀截断"""
        text = "这是一个很长的文本需要被截断"
        result = StringUtils.truncate(text, 12, suffix=">>")
        assert result == "这是一个很长的文本>>"
        assert len(result) == 12

    def test_truncate_empty_string(self):
        """测试空字符串截断"""
        result = StringUtils.truncate("", 5)
        assert result == ""

    def test_truncate_suffix_longer_than_text(self):
        """测试后缀比文本长的情况"""
        text = "短"
        result = StringUtils.truncate(text, 5, suffix="...")
        assert result == text

    @pytest.mark.parametrize("text,length,suffix,expected", [
        ("Hello World", 5, "...", "He..."),
        ("Hello World", 8, "...", "Hello..."),
        ("Hello World", 20, "...", "Hello World"),
        ("Test", 2, ".", "T."),
        ("Test", 1, "", "T"),
        ("", 5, "...", ""),
    ])
    def test_truncate_parametrized(self, text, length, suffix, expected):
        """测试截断参数化"""
        result = StringUtils.truncate(text, length, suffix)
        assert result == expected

    # Slugify tests
    def test_slugify_basic(self):
        """测试基本slugify功能"""
        text = "Hello World"
        result = StringUtils.slugify(text)
        assert result == "hello-world"

    def test_slugify_with_special_chars(self):
        """测试带特殊字符的slugify"""
        text = "Hello @World# Test$%"
        result = StringUtils.slugify(text)
        assert result == "hello-world-test"

    def test_slugify_with_multiple_spaces(self):
        """测试多个空格的slugify"""
        text = "Hello   World   Test"
        result = StringUtils.slugify(text)
        assert result == "hello-world-test"

    def test_slugify_with_dashes(self):
        """测试带连字符的slugify"""
        text = "Hello - World - Test"
        result = StringUtils.slugify(text)
        assert result == "hello-world-test"

    def test_slugify_empty_string(self):
        """测试空字符串的slugify"""
        result = StringUtils.slugify("")
        assert result == ""

    def test_slugify_trimming_dashes(self):
        """测试去除首尾连字符"""
        text = "---Hello World---"
        result = StringUtils.slugify(text)
        assert result == "hello-world"

    @pytest.mark.parametrize("text,expected", [
        ("Hello World", "hello-world"),
        ("Hello World Test", "hello-world-test"),
        ("Hello   World", "hello-world"),
        ("Hello@World#Test", "helloworldtest"),
        ("Hello-World-Test", "hello-world-test"),
        ("  Hello World  ", "hello-world"),
        ("", ""),
        ("123 ABC", "123-abc"),
        ("ABCdef", "abcdef"),
    ])
    def test_slugify_parametrized(self, text, expected):
        """测试slugify参数化"""
        result = StringUtils.slugify(text)
        assert result == expected

    # Camel to snake tests
    def test_camel_to_snake_simple(self):
        """测试简单驼峰转下划线"""
        result = StringUtils.camel_to_snake("camelCase")
        assert result == "camel_case"

    def test_camel_to_snake_multiple_words(self):
        """测试多词驼峰转下划线"""
        result = StringUtils.camel_to_snake("CamelCaseString")
        assert result == "camel_case_string"

    def test_camel_to_snake_with_numbers(self):
        """测试带数字的驼峰转下划线"""
        result = StringUtils.camel_to_snake("camelCase2String")
        assert result == "camel_case2_string"

    def test_camel_to_snake_all_caps(self):
        """测试全大写的驼峰转下划线"""
        result = StringUtils.camel_to_snake("XMLHttpRequest")
        assert result == "xml_http_request"

    def test_camel_to_snake_single_word(self):
        """测试单次驼峰转下划线"""
        result = StringUtils.camel_to_snake("simple")
        assert result == "simple"

    def test_camel_to_snake_empty_string(self):
        """测试空字符串驼峰转下划线"""
        result = StringUtils.camel_to_snake("")
        assert result == ""

    @pytest.mark.parametrize("input_str,expected", [
        ("camelCase", "camel_case"),
        ("CamelCase", "camel_case"),
        ("CamelCaseString", "camel_case_string"),
        ("XMLHttpRequest", "xml_http_request"),
        ("simple", "simple"),
        ("", ""),
        ("aBC", "a_bc"),
        ("ABCd", "a_b_cd"),
    ])
    def test_camel_to_snake_parametrized(self, input_str, expected):
        """测试驼峰转下划线参数化"""
        result = StringUtils.camel_to_snake(input_str)
        assert result == expected

    # Snake to camel tests
    def test_snake_to_camel_simple(self):
        """测试简单下划线转驼峰"""
        result = StringUtils.snake_to_camel("snake_case")
        assert result == "snakeCase"

    def test_snake_to_camel_multiple_words(self):
        """测试多词下划线转驼峰"""
        result = StringUtils.snake_to_camel("snake_case_string")
        assert result == "snakeCaseString"

    def test_snake_to_camel_single_word(self):
        """测试单次下划线转驼峰"""
        result = StringUtils.snake_to_camel("simple")
        assert result == "simple"

    def test_snake_to_camel_empty_string(self):
        """测试空字符串下划线转驼峰"""
        result = StringUtils.snake_to_camel("")
        assert result == ""

    def test_snake_to_camel_with_numbers(self):
        """测试带数字的下划线转驼峰"""
        result = StringUtils.snake_to_camel("snake_case_2")
        assert result == "snakeCase2"

    @pytest.mark.parametrize("input_str,expected", [
        ("snake_case", "snakeCase"),
        ("snake_case_string", "snakeCaseString"),
        ("simple", "simple"),
        ("", ""),
        ("a_b_c", "aBC"),
        ("snake_case_2", "snakeCase2"),
        ("_leading", "Leading"),  # Edge case
        ("trailing_", "trailing_"),  # Edge case
    ])
    def test_snake_to_camel_parametrized(self, input_str, expected):
        """测试下划线转驼峰参数化"""
        result = StringUtils.snake_to_camel(input_str)
        assert result == expected

    # Clean text tests
    def test_clean_text_basic(self):
        """测试基本文本清理"""
        text = "  Hello   World  "
        result = StringUtils.clean_text(text)
        assert result == "Hello World"

    def test_clean_text_multiple_spaces(self):
        """测试多个空格清理"""
        text = "Hello    World    Test"
        result = StringUtils.clean_text(text)
        assert result == "Hello World Test"

    def test_clean_text_newlines_and_tabs(self):
        """测试换行符和制表符清理"""
        text = "Hello\nWorld\tTest\n  Multiple   Spaces  "
        result = StringUtils.clean_text(text)
        assert result == "Hello World Test Multiple Spaces"

    def test_clean_text_only_whitespace(self):
        """测试只有空白字符的清理"""
        text = "   \n\t  \r\n  "
        result = StringUtils.clean_text(text)
        assert result == ""

    def test_clean_text_empty_string(self):
        """测试空字符串清理"""
        result = StringUtils.clean_text("")
        assert result == ""

    def test_clean_text_no_whitespace_needed(self):
        """测试不需要清理的文本"""
        text = "Hello World"
        result = StringUtils.clean_text(text)
        assert result == text

    @pytest.mark.parametrize("text,expected", [
        ("  Hello   World  ", "Hello World"),
        ("Hello    World", "Hello World"),
        ("Hello\nWorld", "Hello World"),
        ("Hello\tWorld", "Hello World"),
        ("  Hello  World  Test  ", "Hello World Test"),
        ("\nHello\nWorld\n", "Hello World"),
        ("   ", ""),
        ("", ""),
        ("HelloWorld", "HelloWorld"),
    ])
    def test_clean_text_parametrized(self, text, expected):
        """测试文本清理参数化"""
        result = StringUtils.clean_text(text)
        assert result == expected

    # Extract numbers tests
    def test_extract_numbers_basic(self):
        """测试基本数字提取"""
        text = "Hello 123 World"
        result = StringUtils.extract_numbers(text)
        assert result == [123.0]

    def test_extract_numbers_multiple(self):
        """测试多个数字提取"""
        text = "Hello 123 World 456 Test 789"
        result = StringUtils.extract_numbers(text)
        assert result == [123.0, 456.0, 789.0]

    def test_extract_numbers_decimal(self):
        """测试小数提取"""
        text = "Price: 19.99, Discount: 5.5"
        result = StringUtils.extract_numbers(text)
        assert result == [19.99, 5.5]

    def test_extract_numbers_negative(self):
        """测试负数提取"""
        text = "Temperature: -5, Balance: -100.50"
        result = StringUtils.extract_numbers(text)
        assert result == [-5.0, -100.50]

    def test_extract_numbers_mixed(self):
        """测试混合数字提取"""
        text = "Values: 123, -45.67, 89.0, -12"
        result = StringUtils.extract_numbers(text)
        assert result == [123.0, -45.67, 89.0, -12.0]

    def test_extract_numbers_no_numbers(self):
        """测试无数字提取"""
        text = "Hello World Test"
        result = StringUtils.extract_numbers(text)
        assert result == []

    def test_extract_numbers_empty_string(self):
        """测试空字符串数字提取"""
        result = StringUtils.extract_numbers("")
        assert result == []

    def test_extract_numbers_edge_cases(self):
        """测试边界情况数字提取"""
        # 测试只有数字的字符串
        result = StringUtils.extract_numbers("123")
        assert result == [123.0]

        # 测试只有小数点的字符串
        result = StringUtils.extract_numbers(".")
        assert result == []

        # 测试只有负号的字符串
        result = StringUtils.extract_numbers("-")
        assert result == []

    @pytest.mark.parametrize("text,expected", [
        ("Hello 123 World", [123.0]),
        ("Price: 19.99", [19.99]),
        ("Temperature: -5.5", [-5.5]),
        ("Values: 1, 2.5, -3", [1.0, 2.5, -3.0]),
        ("No numbers here", []),
        ("", []),
        ("123", [123.0]),
        ("-123.45", [-123.45]),
        ("123.45.67", [123.45, 67.0]),  # Multiple decimals
    ])
    def test_extract_numbers_parametrized(self, text, expected):
        """测试数字提取参数化"""
        result = StringUtils.extract_numbers(text)
        assert result == expected

    # Integration tests
    def test_string_processing_pipeline(self):
        """测试字符串处理管道"""
        original = "  Hello   World-Test@123  "

        # 清理文本
        cleaned = StringUtils.clean_text(original)
        assert cleaned == "Hello World-Test@123"

        # Slugify
        slugified = StringUtils.slugify(cleaned)
        assert slugified == "hello-world-test123"

        # 截断
        truncated = StringUtils.truncate(slugified, 15)
        assert len(truncated) <= 15

    def test_case_conversion_round_trip(self):
        """测试大小写转换往返"""
        snake = "camel_case_string"
        camel = StringUtils.snake_to_camel(snake)
        back_to_snake = StringUtils.camel_to_snake(camel)
        assert back_to_snake == snake

    def test_text_analysis_workflow(self):
        """测试文本分析工作流"""
        text = "  Order #123: 2 items at $19.99 each  "

        # 清理
        cleaned = StringUtils.clean_text(text)
        assert cleaned == "Order #123: 2 items at $19.99 each"

        # 提取数字
        numbers = StringUtils.extract_numbers(cleaned)
        assert numbers == [123.0, 2.0, 19.99]

        # 转换为友好格式
        slug = StringUtils.slugify(cleaned)
        assert "order-123" in slug

    def test_edge_case_combinations(self):
        """测试边界情况组合"""
        # 测试各种特殊字符组合
        test_cases = [
            ("", "", "", ""),
            ("   ", "", "", ""),
            ("A", "a", "a", "a"),
            ("Hello World", "hello-world", "hello_world", "helloWorld"),
            ("XMLParser", "xmlparser", "xml_parser", "xmlParser"),
        ]

        for original, expected_slug, expected_snake, expected_camel in test_cases:
            if original:  # Skip empty string for some operations
                assert StringUtils.slugify(original) == expected_slug
                assert StringUtils.camel_to_snake(expected_camel) == expected_snake
                assert StringUtils.snake_to_camel(expected_snake) == expected_camel

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        # 测试中文字符
        chinese_text = "你好世界"
        cleaned = StringUtils.clean_text(chinese_text)
        assert cleaned == chinese_text

        # 测试带空格的中文
        chinese_with_spaces = "  你好  世界  "
        cleaned = StringUtils.clean_text(chinese_with_spaces)
        assert cleaned == "你好 世界"

    def test_performance_considerations(self):
        """测试性能考虑"""
        # 测试长文本处理
        long_text = " " * 1000 + "Hello" + " " * 1000 + "World"

        result = StringUtils.clean_text(long_text)
        assert result == "Hello World"

        # 测试多次转换的性能
        text = "camelCaseString"
        for _ in range(100):
            snake = StringUtils.camel_to_snake(text)
            camel = StringUtils.snake_to_camel(snake)

        assert snake == "camel_case_string"
        assert camel == "camelCaseString"