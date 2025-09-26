"""
单元测试：字符串工具模块

测试StringUtils类的所有方法，确保字符串处理功能正确性。
"""

import pytest

from src.utils.string_utils import StringUtils

pytestmark = pytest.mark.unit


class TestStringUtils:
    """测试字符串工具类"""

    def test_truncate_short_text(self):
        """测试截断短文本（不需要截断）"""
        text = "Hello"
        result = StringUtils.truncate(text, 10)
    assert result == "Hello"

    def test_truncate_long_text(self):
        """测试截断长文本"""
        text = "Hello World, this is a long text"
        result = StringUtils.truncate(text, 10)
    assert result == "Hello W..."
    assert len(result) == 10

    def test_truncate_custom_suffix(self):
        """测试自定义后缀的截断"""
        text = "Hello World"
        result = StringUtils.truncate(text, 8, suffix=">>")
    assert result == "Hello >>"

    def test_truncate_exact_length(self):
        """测试正好等于长度限制的文本"""
        text = "Hello"
        result = StringUtils.truncate(text, 5)
    assert result == "Hello"

    def test_slugify_basic(self):
        """测试基本URL友好化"""
        text = "Hello World"
        result = StringUtils.slugify(text)
    assert result == "hello-world"

    def test_slugify_special_chars(self):
        """测试包含特殊字符的URL友好化"""
        text = "Hello, World! & More"
        result = StringUtils.slugify(text)
    assert result == "hello-world-more"

    def test_slugify_multiple_spaces(self):
        """测试多个空格的处理"""
        text = "Hello    World"
        result = StringUtils.slugify(text)
    assert result == "hello-world"

    def test_camel_to_snake_basic(self):
        """测试基本驼峰转下划线"""
    assert StringUtils.camel_to_snake("camelCase") == "camel_case"
    assert StringUtils.camel_to_snake("PascalCase") == "pascal_case"

    def test_camel_to_snake_multiple_words(self):
        """测试多单词驼峰转换"""
    assert StringUtils.camel_to_snake("getUserName") == "get_user_name"
    assert StringUtils.camel_to_snake("XMLHttpRequest") == "xml_http_request"

    def test_camel_to_snake_numbers(self):
        """测试包含数字的转换"""
    assert StringUtils.camel_to_snake("version2Api") == "version2_api"

    def test_snake_to_camel_basic(self):
        """测试基本下划线转驼峰"""
    assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
    assert StringUtils.snake_to_camel("user_name") == "userName"

    def test_snake_to_camel_single_word(self):
        """测试单词下划线转换"""
    assert StringUtils.snake_to_camel("hello") == "hello"

    def test_snake_to_camel_multiple_underscores(self):
        """测试多个下划线的转换"""
    assert StringUtils.snake_to_camel("get_user_name_by_id") == "getUserNameById"

    def test_clean_text_multiple_spaces(self):
        """测试清理多余空格"""
        text = "Hello    World   Test"
        result = StringUtils.clean_text(text)
    assert result == "Hello World Test"

    def test_clean_text_leading_trailing_spaces(self):
        """测试清理前后空格"""
        text = "   Hello World   "
        result = StringUtils.clean_text(text)
    assert result == "Hello World"

    def test_clean_text_newlines_tabs(self):
        """测试清理换行符和制表符"""
        text = "Hello\n\tWorld\r\n  Test"
        result = StringUtils.clean_text(text)
    assert result == "Hello World Test"

    def test_extract_numbers_integers(self):
        """测试提取整数"""
        text = "There are 5 apples and 10 oranges"
        result = StringUtils.extract_numbers(text)
    assert result == [5.0, 10.0]

    def test_extract_numbers_floats(self):
        """测试提取浮点数"""
        text = "Price is 12.99 and discount 5.5%"
        result = StringUtils.extract_numbers(text)
    assert result == [12.99, 5.5]

    def test_extract_numbers_negative(self):
        """测试提取负数"""
        text = "Temperature: -15.5 degrees"
        result = StringUtils.extract_numbers(text)
    assert result == [-15.5]

    def test_extract_numbers_no_numbers(self):
        """测试没有数字的文本"""
        text = "Hello World"
        result = StringUtils.extract_numbers(text)
    assert result == []

    def test_extract_numbers_mixed(self):
        """测试混合数字格式"""
        text = "Score: 85, Average: 12.5, Change: -3.2"
        result = StringUtils.extract_numbers(text)
    assert result == [85.0, 12.5, -3.2]


class TestStringUtilsEdgeCases:
    """测试字符串工具的边界情况"""

    def test_empty_string_handling(self):
        """测试空字符串处理"""
    assert StringUtils.truncate("", 5) == ""
    assert StringUtils.slugify("") == ""
    assert StringUtils.clean_text("") == ""
    assert StringUtils.extract_numbers("") == []

    def test_none_handling(self):
        """测试None值处理（预期会抛出异常）"""
        with pytest.raises(TypeError):
            StringUtils.truncate(None, 5)

    def test_zero_truncate_length(self):
        """测试0长度截断"""
        result = StringUtils.truncate("Hello", 0, suffix="")
    assert result == ""

    def test_negative_truncate_length(self):
        """测试负数长度截断"""
        # 应该能处理而不崩溃
        result = StringUtils.truncate("Hello", -1)
        # 具体行为取决于实现，这里主要验证不崩溃
    assert isinstance(result, str)

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        text = "你好世界"
        result = StringUtils.clean_text(text)
    assert result == "你好世界"

        # 测试Unicode数字提取
        unicode_text = "价格：￥123.45"
        numbers = StringUtils.extract_numbers(unicode_text)
    assert 123.45 in numbers

    def test_very_long_strings(self):
        """测试极长字符串"""
        long_string = "a" * 10000
        result = StringUtils.truncate(long_string, 50)
    assert len(result) == 50
    assert result.endswith("...")
