# from src.utils.string_utils import StringUtils

"""
测试字符串处理工具模块
"""


class TestStringUtils:
    """测试StringUtils类"""

    def test_truncate_no_truncate_needed(self):
        """测试不需要截断的情况"""
        text = "Hello"
        result = StringUtils.truncate(text, 10)
        assert result == "Hello"

    def test_truncate_with_default_suffix(self):
        """测试使用默认后缀截断"""
        text = "Hello World"
        result = StringUtils.truncate(text, 8)
        assert result == "Hello..."

    def test_truncate_with_custom_suffix(self):
        """测试使用自定义后缀截断"""
        text = "Hello World"
        result = StringUtils.truncate(text, 8, suffix="---")
        assert result == "Hello---"

    def test_truncate_exact_length(self):
        """测试长度正好相等的情况"""
        text = "Hello"
        result = StringUtils.truncate(text, 5)
        assert result == "Hello"

    def test_truncate_empty_string(self):
        """测试空字符串"""
        text = ""
        result = StringUtils.truncate(text, 5)
        assert result == ""

    def test_truncate_shorter_than_suffix(self):
        """测试长度小于后缀长度"""
        text = "Hi"
        result = StringUtils.truncate(text, 5, suffix="...")
        assert result == "Hi"

    def test_slugify_simple(self):
        """测试简单的slugify"""
        text = "Hello World"
        result = StringUtils.slugify(text)
        assert result == "hello-world"

    def test_slugify_with_special_chars(self):
        """测试包含特殊字符的slugify"""
        text = "Hello, World! How are you?"
        result = StringUtils.slugify(text)
        assert result == "hello-world-how-are-you"

    def test_slugify_with_multiple_spaces(self):
        """测试多个空格的slugify"""
        text = "Hello   World"
        result = StringUtils.slugify(text)
        assert result == "hello-world"

    def test_slugify_with_dashes(self):
        """测试包含破折号的slugify"""
        text = "Hello-World"
        result = StringUtils.slugify(text)
        assert result == "hello-world"

    def test_slugify_empty(self):
        """测试空字符串的slugify"""
        text = ""
        result = StringUtils.slugify(text)
        assert result == ""

    def test_camel_to_snake_simple(self):
        """测试简单的驼峰转下划线"""
        name = "helloWorld"
        result = StringUtils.camel_to_snake(name)
        assert result == "hello_world"

    def test_camel_to_snake_multiple_caps(self):
        """测试多个大写字母的驼峰转下划线"""
        name = "HelloWorldTest"
        result = StringUtils.camel_to_snake(name)
        assert result == "hello_world_test"

    def test_camel_to_snake_with_numbers(self):
        """测试包含数字的驼峰转下划线"""
        name = "test123Value"
        result = StringUtils.camel_to_snake(name)
        assert result == "test123_value"

    def test_camel_to_snake_all_caps(self):
        """测试全大写的驼峰转下划线"""
        name = "HTMLParser"
        result = StringUtils.camel_to_snake(name)
        assert result == "html_parser"

    def test_camel_to_snake_empty(self):
        """测试空字符串的驼峰转下划线"""
        name = ""
        result = StringUtils.camel_to_snake(name)
        assert result == ""

    def test_snake_to_camel_simple(self):
        """测试简单的下划线转驼峰"""
        name = "hello_world"
        result = StringUtils.snake_to_camel(name)
        assert result == "helloWorld"

    def test_snake_to_camel_multiple_underscores(self):
        """测试多个下划线的转驼峰"""
        name = "hello_world_test"
        result = StringUtils.snake_to_camel(name)
        assert result == "helloWorldTest"

    def test_snake_to_camel_single_word(self):
        """测试单个单词的转驼峰"""
        name = "hello"
        result = StringUtils.snake_to_camel(name)
        assert result == "hello"

    def test_snake_to_camel_with_numbers(self):
        """测试包含数字的转驼峰"""
        name = "test_123_value"
        result = StringUtils.snake_to_camel(name)
        assert result == "test123Value"

    def test_snake_to_camel_empty(self):
        """测试空字符串的转驼峰"""
        name = ""
        result = StringUtils.snake_to_camel(name)
        assert result == ""

    def test_snake_to_camel_trailing_underscore(self):
        """测试末尾下划线的转驼峰"""
        name = "hello_"
        result = StringUtils.snake_to_camel(name)
        assert result == "hello"

    def test_clean_text_remove_extra_spaces(self):
        """测试移除多余空格"""
        text = "Hello    World"
        result = StringUtils.clean_text(text)
        assert result == "Hello World"

    def test_clean_text_remove_newlines(self):
        """测试移除换行符"""
        text = "Hello\n\nWorld"
        result = StringUtils.clean_text(text)
        assert result == "Hello World"

    def test_clean_text_remove_tabs(self):
        """测试移除制表符"""
        text = "Hello\t\tWorld"
        result = StringUtils.clean_text(text)
        assert result == "Hello World"

    def test_clean_text_mixed_whitespace(self):
        """测试混合空白字符"""
        text = "  Hello \n\t World  "
        result = StringUtils.clean_text(text)
        assert result == "Hello World"

    def test_clean_text_empty(self):
        """测试空字符串清理"""
        text = ""
        result = StringUtils.clean_text(text)
        assert result == ""

    def test_clean_text_only_whitespace(self):
        """测试只有空白字符的清理"""
        text = "   \n\t  "
        result = StringUtils.clean_text(text)
        assert result == ""

    def test_extract_numbers_integers(self):
        """测试提取整数"""
        text = "I have 2 cats and 3 dogs"
        result = StringUtils.extract_numbers(text)
        assert result == [2.0, 3.0]

    def test_extract_numbers_floats(self):
        """测试提取浮点数"""
        text = "The price is 19.99 dollars"
        result = StringUtils.extract_numbers(text)
        assert result == [19.99]

    def test_extract_numbers_negative(self):
        """测试提取负数"""
        text = "Temperature is -5 degrees"
        result = StringUtils.extract_numbers(text)
        assert result == [-5.0]

    def test_extract_numbers_mixed(self):
        """测试提取混合数字"""
        text = "Values: 1, -2.5, 3.14, -10"
        result = StringUtils.extract_numbers(text)
        assert result == [1.0, -2.5, 3.14, -10.0]

    def test_extract_numbers_no_numbers(self):
        """测试没有数字的情况"""
        text = "No numbers here"
        result = StringUtils.extract_numbers(text)
        assert result == []

    def test_extract_numbers_empty(self):
        """测试空字符串的数字提取"""
        text = ""
        result = StringUtils.extract_numbers(text)
        assert result == []

    def test_extract_numbers_with_decimals(self):
        """测试提取带小数的数字"""
        text = "Pi is approximately 3.14159"
        result = StringUtils.extract_numbers(text)
        assert result == [3.14159]

    def test_extract_numbers_scientific_notation(self):
        """测试科学计数法（不支持）"""
        text = "Value is 1.23e4"
        result = StringUtils.extract_numbers(text)
        # 应该提取1.23和4，因为不支持科学计数法
        assert result == [1.23, 4.0]
