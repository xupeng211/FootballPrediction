"""字符串工具测试"""

import pytest
from src.utils.string_utils import StringUtils


class TestStringUtils:
    """字符串工具测试"""

    def test_truncate_string(self):
        """测试截断字符串"""
        text = "This is a very long string"
        result = StringUtils.truncate(text, 10)
        assert result == "This is..."
        assert len(result) <= 13  # 10 + 3 for ...

    def test_truncate_string_short(self):
        """测试短字符串截断"""
        text = "short"
        result = StringUtils.truncate(text, 10)
        assert result == "short"

    def test_truncate_with_suffix(self):
        """测试自定义后缀截断"""
        text = "This is a very long string"
        result = StringUtils.truncate(text, 10, suffix=" [more]")
        # 截断长度10包含后缀，所以实际文本长度是 10 - 7 = 3
        assert result == "Thi [more]"

    def test_slugify(self):
        """测试转换为URL友好字符串"""
        text = "Hello World! This is a Test"
        result = StringUtils.slugify(text)
        assert result == "hello-world-this-is-a-test"

    def test_camel_to_snake(self):
        """测试驼峰转下划线"""
        assert StringUtils.camel_to_snake("camelCase") == "camel_case"
        assert StringUtils.camel_to_snake("CamelCase") == "camel_case"
        assert StringUtils.camel_to_snake("XMLHttpRequest") == "xml_http_request"

    def test_snake_to_camel(self):
        """测试下划线转驼峰"""
        assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
        assert StringUtils.snake_to_camel("snake_case_test") == "snakeCaseTest"

    def test_clean_text(self):
        """测试清理文本"""
        text = "  This   has    extra   spaces  "
        result = StringUtils.clean_text(text)
        assert result == "This has extra spaces"

    def test_extract_numbers(self):
        """测试提取数字"""
        text = "The price is $19.99 and discount is 2.5%"
        numbers = StringUtils.extract_numbers(text)
        assert 19.99 in numbers
        assert 2.5 in numbers
        assert len(numbers) == 2

    def test_extract_negative_numbers(self):
        """测试提取负数"""
        text = "Temperature is -5.5 degrees"
        numbers = StringUtils.extract_numbers(text)
        assert -5.5 in numbers

    def test_string_imports(self):
        """测试字符串工具导入"""
        from src.utils.string_utils import StringUtils

        assert hasattr(StringUtils, "truncate")
        assert hasattr(StringUtils, "slugify")
        assert hasattr(StringUtils, "camel_to_snake")
