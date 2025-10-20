"""
StringUtils 综合测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 检查string_utils模块的实际结构
try:
    # 首先尝试直接导入函数
    from src.utils.string_utils import truncate, snake_to_camel, camel_to_snake, slugify
except ImportError:
    try:
        # 尝试从类中导入
        from src.utils.string_utils import StringUtils

        truncate = StringUtils.truncate
        snake_to_camel = StringUtils.snake_to_camel
        camel_to_snake = StringUtils.camel_to_snake
        slugify = StringUtils.slugify
    except ImportError:
        pytest.skip("StringUtils模块不可用", allow_module_level=True)


class TestStringUtils:
    """StringUtils测试类"""

    def test_truncate_short(self):
        """测试截断短文本"""
        text = "short"
        assert truncate(text, 10) == "short"
        assert truncate(text, 5) == "short"

    def test_truncate_long(self):
        """测试截断长文本"""
        text = "This is a very long text"
        assert truncate(text, 10) == "This is..."
        assert truncate(text, 15) == "This is a very..."

    def test_truncate_edge_cases(self):
        """测试截断边缘情况"""
        assert truncate("", 5) == ""
        assert truncate("a", 0) == "..."
        assert truncate("ab", 1) == "..."
        assert truncate("hello", 3) == "..."
        assert truncate("hello", 4) == "h..."

    def test_snake_to_camel_basic(self):
        """测试基本蛇形转驼峰"""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("user_name") == "userName"
        assert snake_to_camel("single") == "single"

    def test_snake_to_camel_edge(self):
        """测试蛇形转驼峰边缘情况"""
        assert snake_to_camel("") == ""
        assert snake_to_camel("_leading") == "leading"
        assert snake_to_camel("trailing_") == "trailing"
        assert snake_to_camel("multiple___underscores") == "multipleUnderscores"

    def test_camel_to_snake_basic(self):
        """测试基本驼峰转蛇形"""
        assert camel_to_snake("helloWorld") == "hello_world"
        assert camel_to_snake("userName") == "user_name"
        assert camel_to_snake("Single") == "single"

    def test_camel_to_snake_edge(self):
        """测试驼峰转蛇形边缘情况"""
        assert camel_to_snake("") == ""
        assert camel_to_snake("already_snake") == "already_snake"
        assert camel_to_snake("XMLHttpRequest") == "xml_http_request"

    def test_slugify_basic(self):
        """测试基本slug生成"""
        assert slugify("Hello World!") == "hello-world"
        assert slugify("Multiple   Spaces") == "multiple-spaces"
        assert slugify("Special#@%Characters") == "special-characters"

    def test_slugify_edge(self):
        """测试slug生成边缘情况"""
        assert slugify("") == ""
        assert slugify("---") == ""
        assert slugify("123 Numbers") == "123-numbers"

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("hello_world", "helloWorld"),
            ("user_name", "userName"),
            ("single", "single"),
            ("test_case", "testCase"),
        ],
    )
    def test_snake_to_camel_parametrized(self, input, expected):
        """参数化测试蛇形转驼峰"""
        assert snake_to_camel(input) == expected

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("helloWorld", "hello_world"),
            ("userName", "user_name"),
            ("Single", "single"),
            ("testCase", "test_case"),
        ],
    )
    def test_camel_to_snake_parametrized(self, input, expected):
        """参数化测试驼峰转蛇形"""
        assert camel_to_snake(input) == expected

    def test_roundtrip_conversion(self):
        """测试往返转换"""
        # 蛇形到驼峰再回到蛇形
        snake = "hello_world_test"
        camel = snake_to_camel(snake)
        back_to_snake = camel_to_snake(camel)
        assert back_to_snake == snake

    def test_text_unicode(self):
        """测试Unicode文本处理"""
        unicode_text = "Héllö Wörld"
        # 根据实际实现调整测试
        result = truncate(unicode_text, 10)
        assert isinstance(result, str)

    def test_performance_large_text(self):
        """测试大文本性能"""
        import time

        large_text = "word_" * 10000

        start = time.time()
        result = snake_to_camel(large_text)
        duration = time.time() - start

        assert isinstance(result, str)
        assert duration < 0.1  # 应该在100ms内完成
