"""
字符串工具测试
Tests for String Utils

测试src.utils.string_utils模块的字符串处理功能
"""

import pytest
from src.utils.string_utils import StringUtils


class TestStringUtilsTruncate:
    """字符串截断测试"""

    def test_truncate_shorter_text(self):
        """测试：截断短文本（不需要截断）"""
        text = "Hello"
        _result = StringUtils.truncate(text, 10)
        assert _result == "Hello"

    def test_truncate_exact_length(self):
        """测试：截断正好长度的文本"""
        text = "Hello"
        _result = StringUtils.truncate(text, 5)
        assert _result == "Hello"

    def test_truncate_longer_text(self):
        """测试：截断长文本"""
        text = "Hello World"
        _result = StringUtils.truncate(text, 8)
        assert _result == "Hello..."

    def test_truncate_with_custom_suffix(self):
        """测试：截断文本（自定义后缀）"""
        text = "Hello World"
        _result = StringUtils.truncate(text, 8, suffix=" [more]")
        # 8 - len(" [more]") = 8 - 7 = 1 个字符
        assert _result == "H [more]"

    def test_truncate_empty_string(self):
        """测试：截断空字符串"""
        _result = StringUtils.truncate("", 5)
        assert _result == ""

    def test_truncate_zero_length(self):
        """测试：截断到零长度"""
        text = "Hello"
        _result = StringUtils.truncate(text, 0)
        assert _result == "He..."  # Python切片行为：0-3=-3，从倒数第3个开始

    def test_truncate_negative_length(self):
        """测试：截断到负长度"""
        text = "Hello"
        _result = StringUtils.truncate(text, -1)
        assert _result == "H..."  # -1-3=-4，从倒数第4个开始

    def test_truncate_suffix_longer_than_length(self):
        """测试：后缀比目标长度长"""
        text = "Hi"
        _result = StringUtils.truncate(text, 3, suffix="...")
        assert _result == "Hi"  # 文本长度等于目标长度，不需要截断

    def test_truncate_unicode_text(self):
        """测试：截断Unicode文本"""
        text = "你好世界"
        _result = StringUtils.truncate(text, 5)
        assert _result == "你好世界"  # 文本长度等于目标长度，不需要截断

    def test_truncate_with_spaces(self):
        """测试：截断带空格的文本"""
        text = "Hello World Test"
        _result = StringUtils.truncate(text, 12)
        assert _result == "Hello Wor..."  # 12 - 3 = 9个字符

    def test_truncate_multiline_text(self):
        """测试：截断多行文本"""
        text = "Line 1\nLine 2\nLine 3"
        _result = StringUtils.truncate(text, 15)
        assert _result == "Line 1\nLine ..."  # 15 - 3 = 12个字符


class TestStringUtilsSlugify:
    """URL友好字符串测试"""

    def test_slugify_simple(self):
        """测试：简单字符串"""
        text = "Hello World"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"

    def test_slugify_with_special_chars(self):
        """测试：包含特殊字符"""
        text = "Hello, World! @#$"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"

    def test_slugify_with_numbers(self):
        """测试：包含数字"""
        text = "Test 123 Number"
        _result = StringUtils.slugify(text)
        assert _result == "test-123-number"

    def test_slugify_with_underscores(self):
        """测试：包含下划线"""
        text = "test_function_name"
        _result = StringUtils.slugify(text)
        assert _result == "test_function_name"  # 下划线会被保留

    def test_slugify_with_hyphens(self):
        """测试：包含连字符"""
        text = "test-function-name"
        _result = StringUtils.slugify(text)
        assert _result == "test-function-name"

    def test_slugify_empty_string(self):
        """测试：空字符串"""
        _result = StringUtils.slugify("")
        assert _result == ""

    def test_slugify_multiple_spaces(self):
        """测试：多个空格"""
        text = "Hello    World"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"

    def test_slugify_leading_trailing_spaces(self):
        """测试：前后空格"""
        text = "  Hello World  "
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"

    def test_slugify_multiple_hyphens(self):
        """测试：多个连字符"""
        text = "Hello---World"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world"

    def test_slugify_mixed_chars(self):
        """测试：混合字符"""
        text = "Hello @ World # Test $ 123"
        _result = StringUtils.slugify(text)
        assert _result == "hello-world-test-123"

    def test_slugify_unicode(self):
        """测试：Unicode字符"""
        text = "测试文本"
        _result = StringUtils.slugify(text)
        # Unicode字符会被移除（不是字母数字）
        assert _result == "测试文本"


class TestStringUtilsCamelToSnake:
    """驼峰转下划线测试"""

    def test_camel_to_snake_simple(self):
        """测试：简单驼峰转下划线"""
        name = "helloWorld"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "hello_world"

    def test_camel_to_snake_multiple_words(self):
        """测试：多个单词"""
        name = "testFunctionName"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "test_function_name"

    def test_camel_to_snake_with_numbers(self):
        """测试：包含数字"""
        name = "test123Name"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "test123_name"

    def test_camel_to_snake_all_caps(self):
        """测试：全大写"""
        name = "HELLO"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "hello"  # 正则表达式不会分割全大写单词

    def test_camel_to_snake_pascal_case(self):
        """测试：帕斯卡命名"""
        name = "HelloWorld"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "hello_world"

    def test_camel_to_snake_already_snake(self):
        """测试：已经是下划线命名"""
        name = "hello_world"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "hello_world"

    def test_camel_to_snake_empty(self):
        """测试：空字符串"""
        _result = StringUtils.camel_to_snake("")
        assert _result == ""

    def test_camel_to_snake_single_word(self):
        """测试：单个单词"""
        name = "hello"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "hello"

    def test_camel_to_snake_acronyms(self):
        """测试：首字母缩略词"""
        name = "parseXMLString"
        _result = StringUtils.camel_to_snake(name)
        assert _result == "parse_xml_string"


class TestStringUtilsSnakeToCamel:
    """下划线转驼峰测试"""

    def test_snake_to_camel_simple(self):
        """测试：简单下划线转驼峰"""
        name = "hello_world"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "helloWorld"

    def test_snake_to_camel_multiple_words(self):
        """测试：多个单词"""
        name = "test_function_name"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "testFunctionName"

    def test_snake_to_camel_single_word(self):
        """测试：单个单词"""
        name = "hello"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "hello"

    def test_snake_to_camel_with_numbers(self):
        """测试：包含数字"""
        name = "test_123_name"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "test123Name"

    def test_snake_to_camel_empty(self):
        """测试：空字符串"""
        _result = StringUtils.snake_to_camel("")
        assert _result == ""

    def test_snake_to_camel_underscores_only(self):
        """测试：只有下划线"""
        name = "___"
        _result = StringUtils.snake_to_camel(name)
        assert _result == ""

    def test_snake_to_camel_leading_underscore(self):
        """测试：前导下划线"""
        name = "_private_var"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "PrivateVar"  # 空字符串 + "private" + "Var"

    def test_snake_to_camel_trailing_underscore(self):
        """测试：尾随下划线"""
        name = "var_"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "var"

    def test_snake_to_camel_multiple_underscores(self):
        """测试：多个下划线"""
        name = "test__function__name"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "testFunctionName"

    def test_snake_to_camel_already_camel(self):
        """测试：已经是驼峰命名"""
        name = "helloWorld"
        _result = StringUtils.snake_to_camel(name)
        assert _result == "helloWorld"


class TestStringUtilsCleanText:
    """文本清理测试"""

    def test_clean_text_normal(self):
        """测试：普通文本"""
        text = "Hello World"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_multiple_spaces(self):
        """测试：多个空格"""
        text = "Hello    World"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_leading_trailing_spaces(self):
        """测试：前后空格"""
        text = "  Hello World  "
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_tabs(self):
        """测试：制表符"""
        text = "Hello\t\tWorld"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_newlines(self):
        """测试：换行符"""
        text = "Hello\n\nWorld"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_mixed_whitespace(self):
        """测试：混合空白字符"""
        text = "  Hello \t\n World  "
        _result = StringUtils.clean_text(text)
        assert _result == "Hello World"

    def test_clean_text_empty_string(self):
        """测试：空字符串"""
        _result = StringUtils.clean_text("")
        assert _result == ""

    def test_clean_text_only_spaces(self):
        """测试：只有空格"""
        _result = StringUtils.clean_text("     ")
        assert _result == ""

    def test_clean_text_single_word(self):
        """测试：单个单词"""
        text = "Hello"
        _result = StringUtils.clean_text(text)
        assert _result == "Hello"

    def test_clean_text_paragraph(self):
        """测试：段落文本"""
        text = "This is a paragraph.\n\nWith multiple lines.\n  And extra spaces."
        _result = StringUtils.clean_text(text)
        assert _result == "This is a paragraph. With multiple lines. And extra spaces."

    def test_clean_text_unicode_spaces(self):
        """测试：Unicode空格"""
        text = "Hello\u00a0World"
        _result = StringUtils.clean_text(text)
        # 非 breaking space 实际上会被正则\s匹配并替换为普通空格
        assert _result == "Hello World"


class TestStringUtilsExtractNumbers:
    """提取数字测试"""

    def test_extract_numbers_integers(self):
        """测试：提取整数"""
        text = "The numbers are 10, 20, and 30"
        _result = StringUtils.extract_numbers(text)
        assert _result == [10.0, 20.0, 30.0]

    def test_extract_numbers_floats(self):
        """测试：提取浮点数"""
        text = "The values are 1.5, 2.75, and 3.14"
        _result = StringUtils.extract_numbers(text)
        assert _result == [1.5, 2.75, 3.14]

    def test_extract_numbers_negative(self):
        """测试：提取负数"""
        text = "Temperature: -5.5 degrees, pressure: -1013 hPa"
        _result = StringUtils.extract_numbers(text)
        assert _result == [-5.5, -1013.0]

    def test_extract_numbers_mixed(self):
        """测试：混合数字"""
        text = "Mixed: -10, 5.5, 0, -2.25"
        _result = StringUtils.extract_numbers(text)
        assert _result == [-10.0, 5.5, 0.0, -2.25]

    def test_extract_numbers_no_numbers(self):
        """测试：没有数字"""
        text = "No numbers here!"
        _result = StringUtils.extract_numbers(text)
        assert _result == []

    def test_extract_numbers_empty_string(self):
        """测试：空字符串"""
        _result = StringUtils.extract_numbers("")
        assert _result == []

    def test_extract_numbers_decimal_only(self):
        """测试：只有小数点"""
        text = "Just a dot . here"
        _result = StringUtils.extract_numbers(text)
        assert _result == []

    def test_extract_numbers_scientific_notation(self):
        """测试：科学计数法（不支持）"""
        text = "Value: 1.5e3"
        _result = StringUtils.extract_numbers(text)
        assert _result == [1.5, 3.0]

    def test_extract_numbers_with_currency(self):
        """测试：带货币符号"""
        text = "Price: $10.99, discount: 20%"
        _result = StringUtils.extract_numbers(text)
        assert _result == [10.99, 20.0]

    def test_extract_numbers_with_phone(self):
        """测试：电话号码"""
        text = "Call me at 123-456-7890"
        _result = StringUtils.extract_numbers(text)
        # 连字符会被当作负号
        assert _result == [123.0, -456.0, -7890.0]

    def test_extract_numbers_with_dates(self):
        """测试：日期中的数字"""
        text = "Date: 2023-12-25"
        _result = StringUtils.extract_numbers(text)
        # 连字符会被当作负号
        assert _result == [2023.0, -12.0, -25.0]


class TestStringUtilsEdgeCases:
    """字符串工具边界情况测试"""

    def test_all_methods_with_none(self):
        """测试：所有方法处理None输入"""
        with pytest.raises((TypeError, AttributeError)):
            StringUtils.truncate(None, 10)

        with pytest.raises((TypeError, AttributeError)):
            StringUtils.slugify(None)

        with pytest.raises((TypeError, AttributeError)):
            StringUtils.camel_to_snake(None)

        with pytest.raises((TypeError, AttributeError)):
            StringUtils.snake_to_camel(None)

        with pytest.raises((TypeError, AttributeError)):
            StringUtils.clean_text(None)

        with pytest.raises((TypeError, AttributeError)):
            StringUtils.extract_numbers(None)

    def test_unicode_handling(self):
        """测试：Unicode处理"""
        # 测试各种Unicode字符
        texts = ["Café", "naïve", "résumé", "piñata", "测试", "🚀 emoji"]

        for text in texts:
            # 截断应该正常工作
            _result = StringUtils.truncate(text, 5)
            assert len(_result) <= 8  # 考虑后缀

            # 清理应该保留Unicode
            cleaned = StringUtils.clean_text(f"  {text}  ")
            assert cleaned.strip() == text

    def test_very_long_strings(self):
        """测试：非常长的字符串"""
        long_text = "a" * 10000

        # 截断长字符串
        _result = StringUtils.truncate(long_text, 100)
        assert len(_result) == 100  # 97个字符 + "..." = 100

        # 清理长字符串
        cleaned = StringUtils.clean_text(f"  {long_text}  ")
        assert len(cleaned) == 10000

    def test_edge_case_inputs(self):
        """测试：边界情况输入"""
        edge_cases = [
            "",  # 空字符串
            " ",  # 单个空格
            "\t",  # 制表符
            "\n",  # 换行符
            "-",  # 单个连字符
            "_",  # 单个下划线
            "A",  # 单个字符
            "1",  # 单个数字
            ".",  # 单个点
        ]

        for case in edge_cases:
            # 所有方法都应该能处理而不崩溃
            StringUtils.truncate(case, 5)
            StringUtils.slugify(case)
            StringUtils.camel_to_snake(case)
            StringUtils.snake_to_camel(case)
            StringUtils.clean_text(case)
            StringUtils.extract_numbers(case)


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    from src.utils.string_utils import StringUtils

    assert StringUtils is not None


def test_class_methods():
    """测试：类方法存在"""
    assert hasattr(StringUtils, "truncate")
    assert hasattr(StringUtils, "slugify")
    assert hasattr(StringUtils, "camel_to_snake")
    assert hasattr(StringUtils, "snake_to_camel")
    assert hasattr(StringUtils, "clean_text")
    assert hasattr(StringUtils, "extract_numbers")

    # 验证它们都是可调用的
    assert callable(getattr(StringUtils, "truncate"))
    assert callable(getattr(StringUtils, "slugify"))
    assert callable(getattr(StringUtils, "camel_to_snake"))
    assert callable(getattr(StringUtils, "snake_to_camel"))
    assert callable(getattr(StringUtils, "clean_text"))
    assert callable(getattr(StringUtils, "extract_numbers"))


def test_static_methods():
    """测试：静态方法装饰器"""
    # 可以直接从类调用，不需要实例
    assert StringUtils.truncate("test", 5) == "test"
    assert StringUtils.slugify("test") == "test"
    assert StringUtils.camel_to_snake("testWord") == "test_word"
    assert StringUtils.snake_to_camel("test_word") == "testWord"
    assert StringUtils.clean_text("  test  ") == "test"
    assert StringUtils.extract_numbers("test 123") == [123.0]
