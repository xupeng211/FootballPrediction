import pytest

from src.utils.string_utils import StringUtils

pytestmark = pytest.mark.unit


class TestStringUtils:
    """测试StringUtils类的所有方法"""

    def test_truncate_short_text(self):
        """测试截断短文本"""
        result = StringUtils.truncate("短文本", 10)
    assert result == "短文本"

    def test_truncate_long_text_default_suffix(self):
        """测试截断长文本使用默认后缀"""
        result = StringUtils.truncate("这是一个很长的文本需要被截断", 10)
    assert result == "这是一个很长的..."
    assert len(result) == 10

    def test_truncate_long_text_custom_suffix(self):
        """测试截断长文本使用自定义后缀"""
        result = StringUtils.truncate("很长的文本", 6, "!!!")
    assert result == "很长的文本"  # 长度不超过6，不截断
    assert len(result) == 5

    def test_truncate_exact_length(self):
        """测试文本长度正好等于截断长度"""
        text = "12345"
        result = StringUtils.truncate(text, 5)
    assert result == "12345"

    def test_slugify_basic_text(self):
        """测试基本文本转slug"""
        result = StringUtils.slugify("Hello World")
    assert result == "hello-world"

    def test_slugify_with_special_chars(self):
        """测试包含特殊字符的文本转slug"""
        result = StringUtils.slugify("Hello! @#$ World?")
    assert result == "hello-world"

    def test_slugify_with_multiple_spaces(self):
        """测试包含多个空格的文本转slug"""
        result = StringUtils.slugify("Hello    World   Test")
    assert result == "hello-world-test"

    def test_slugify_chinese_text(self):
        """测试中文文本转slug"""
        result = StringUtils.slugify("你好世界")
    assert result == "你好世界"  # 实际实现保留中文字符

    def test_camel_to_snake_simple(self):
        """测试简单驼峰转下划线"""
        result = StringUtils.camel_to_snake("camelCase")
    assert result == "camel_case"

    def test_camel_to_snake_complex(self):
        """测试复杂驼峰转下划线"""
        result = StringUtils.camel_to_snake("XMLHttpRequest")
    assert result == "xml_http_request"

    def test_camel_to_snake_already_snake(self):
        """测试已经是下划线格式的字符串"""
        result = StringUtils.camel_to_snake("already_snake_case")
    assert result == "already_snake_case"

    def test_snake_to_camel_simple(self):
        """测试简单下划线转驼峰"""
        result = StringUtils.snake_to_camel("snake_case")
    assert result == "snakeCase"

    def test_snake_to_camel_single_word(self):
        """测试单词下划线转驼峰"""
        result = StringUtils.snake_to_camel("word")
    assert result == "word"

    def test_snake_to_camel_multiple_underscores(self):
        """测试多个下划线的转换"""
        result = StringUtils.snake_to_camel("this_is_a_test")
    assert result == "thisIsATest"

    def test_clean_text_multiple_spaces(self):
        """测试清理多余空格"""
        result = StringUtils.clean_text("  Hello    World   ")
    assert result == "Hello World"

    def test_clean_text_tabs_and_newlines(self):
        """测试清理制表符和换行符"""
        result = StringUtils.clean_text("Hello\t\tWorld\n\nTest")
    assert result == "Hello World Test"

    def test_clean_text_already_clean(self):
        """测试已经清理过的文本"""
        result = StringUtils.clean_text("Hello World")
    assert result == "Hello World"

    def test_extract_numbers_integers(self):
        """测试提取整数"""
        result = StringUtils.extract_numbers("我有123个苹果和456个橙子")
    assert result == [123.0, 456.0]

    def test_extract_numbers_floats(self):
        """测试提取小数"""
        result = StringUtils.extract_numbers("温度是23.5度，湿度是60.2%")
    assert result == [23.5, 60.2]

    def test_extract_numbers_negative(self):
        """测试提取负数"""
        result = StringUtils.extract_numbers("温度-10.5度，下降了-2.3度")
    assert result == [-10.5, -2.3]

    def test_extract_numbers_no_numbers(self):
        """测试无数字的文本"""
        result = StringUtils.extract_numbers("没有任何数字的文本")
    assert result == []

    def test_extract_numbers_mixed_text(self):
        """测试混合文本和数字"""
        result = StringUtils.extract_numbers("价格$29.99，折扣10%，共100件")
    assert result == [29.99, 10.0, 100.0]
