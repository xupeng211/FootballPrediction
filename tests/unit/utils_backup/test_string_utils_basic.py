"""字符串工具基础测试"""

from src.utils.string_utils import StringUtils


class TestStringUtilsBasic:
    """字符串工具基础测试"""

    def test_truncate(self):
        """测试字符串截断"""
        # 正常截断
        text = "This is a long string"
        result = StringUtils.truncate(text, 10)
        assert result == "This is..."

        # 不需要截断
        result = StringUtils.truncate(text, 30)
        assert result == "This is a long string"

        # 边界情况
        result = StringUtils.truncate("Hello", 5)
        assert result == "Hello"

        # 自定义后缀
        result = StringUtils.truncate(text, 10, suffix="[...]")
        assert result == "This [...]"

    def test_slugify(self):
        """测试生成slug"""
        # 基本转换
        result = StringUtils.slugify("Hello World!")
        assert result == "hello-world"

        # 多个空格和特殊字符
        result = StringUtils.slugify("This is a test --- with special chars!")
        assert result == "this-is-a-test-with-special-chars"

        # 已经是slug格式
        result = StringUtils.slugify("already-slug")
        assert result == "already-slug"

    def test_camel_to_snake(self):
        """测试驼峰转蛇形命名"""
        # 基本转换
        result = StringUtils.camel_to_snake("CamelCase")
        assert result == "camel_case"

        # 缩写词
        result = StringUtils.camel_to_snake("HTMLParser")
        assert result == "html_parser"

        # 数字
        result = StringUtils.camel_to_snake("test123Case")
        assert result == "test123_case"

    def test_snake_to_camel(self):
        """测试蛇形转驼峰命名"""
        # 基本转换
        result = StringUtils.snake_to_camel("snake_case")
        assert result == "snakeCase"

        # 单个词
        result = StringUtils.snake_to_camel("word")
        assert result == "word"

        # 多个下划线
        result = StringUtils.snake_to_camel("multiple_under_scores")
        assert result == "multipleUnderScores"

    def test_clean_text(self):
        """测试清理文本"""
        # 多余空格
        result = StringUtils.clean_text("  Hello   World  ")
        assert result == "Hello World"

        # 换行符和制表符
        result = StringUtils.clean_text("Hello\nWorld\tTest")
        assert result == "Hello World Test"

        # 空字符串
        result = StringUtils.clean_text("")
        assert result == ""

    def test_extract_numbers(self):
        """测试提取数字"""
        # 整数和小数
        text = "The price is 12.99 dollars and 10 items"
        result = StringUtils.extract_numbers(text)
        assert 12.99 in result
        assert 10.0 in result

        # 负数
        text = "Temperature is -5.5 degrees"
        result = StringUtils.extract_numbers(text)
        assert -5.5 in result

        # 无数字
        text = "No numbers here"
        result = StringUtils.extract_numbers(text)
        assert result == []
