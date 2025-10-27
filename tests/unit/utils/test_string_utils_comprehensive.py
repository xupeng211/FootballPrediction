"""字符串工具综合测试"""

import pytest

# from src.utils.string_utils import StringUtils


@pytest.mark.unit
class TestStringUtils:
    """测试字符串工具函数"""

    def test_truncate(self):
        """测试字符串截断"""
        text = "This is a long string"
        assert StringUtils.truncate(text, 10) == "This is..."
        assert StringUtils.truncate(text, 30) == "This is a long string"

    def test_slugify(self):
        """测试生成 slug"""
        assert StringUtils.slugify("Hello World!") == "hello-world"
        assert StringUtils.slugify("This is a test") == "this-is-a-test"
        assert StringUtils.slugify("Multiple   Spaces") == "multiple-spaces"

    def test_camel_to_snake(self):
        """测试驼峰转蛇形命名"""
        assert StringUtils.camel_to_snake("CamelCase") == "camel_case"
        assert StringUtils.camel_to_snake("PascalCase") == "pascal_case"
        assert StringUtils.camel_to_snake("already_snake") == "already_snake"

    def test_snake_to_camel(self):
        """测试蛇形转驼峰命名"""
        assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
        assert StringUtils.snake_to_camel("already_snake") == "alreadySnake"

    def test_clean_text(self):
        """测试清理文本"""
        assert StringUtils.clean_text("  Hello   World  ") == "Hello World"
        assert StringUtils.clean_text("Hello\nWorld") == "Hello World"

    def test_extract_numbers(self):
        """测试提取数字"""
        text = "The price is 12.99 dollars"
        numbers = StringUtils.extract_numbers(text)
        assert 12.99 in numbers
