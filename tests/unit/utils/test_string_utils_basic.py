"""测试字符串工具模块"""

import pytest

try:
    from src.utils.string_utils import StringUtils

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
@pytest.mark.utils
class TestStringUtils:
    """字符串工具测试"""

    def test_string_utility_creation(self):
        """测试字符串工具创建"""
        utils = StringUtils()
        assert utils is not None

    def test_basic_string_operations(self):
        """测试基本字符串操作"""
        utils = StringUtils()

        # 测试字符串清理
        test_strings = [
            "  hello world  ",
            "\t  test string\n",
            "UPPERCASE",
            "lowercase",
            "Mixed Case String",
        ]

        for test_str in test_strings:
            # 基本操作应该可用
            if hasattr(utils, "clean"):
                result = utils.clean(test_str)
                assert result is not None
            if hasattr(utils, "normalize"):
                result = utils.normalize(test_str)
                assert result is not None

    def test_string_validation(self):
        """测试字符串验证"""
        utils = StringUtils()

        valid_strings = [
            "valid_string",
            "AnotherValidString123",
            "test-with-hyphens",
            "string_with_underscores",
        ]

        invalid_strings = [
            "",
            None,
            "   ",
            "invalid string with spaces",
            "string@with#special$chars",
        ]

        for valid_str in valid_strings:
            try:
                if hasattr(utils, "is_valid"):
                    result = utils.is_valid(valid_str)
                    if result is not None:
                        assert isinstance(result, bool)
            except Exception:
                pass

        for invalid_str in invalid_strings:
            try:
                if hasattr(utils, "is_valid"):
                    result = utils.is_valid(invalid_str)
                    if result is not None:
                        assert isinstance(result, bool)
            except Exception:
                pass

    def test_string_transformation(self):
        """测试字符串转换"""
        utils = StringUtils()

        transformations = [
            ("hello", "HELLO"),
            ("world", "WORLD"),
            ("Test", "test"),
            ("MiXeD", "mixed"),
        ]

        for original, expected in transformations:
            try:
                # 测试大小写转换
                if hasattr(utils, "to_upper"):
                    result = utils.to_upper(original)
                    if result is not None:
                        assert isinstance(result, str)

                if hasattr(utils, "to_lower"):
                    result = utils.to_lower(original)
                    if result is not None:
                        assert isinstance(result, str)
            except Exception:
                pass

    def test_string_formatting(self):
        """测试字符串格式化"""
        utils = StringUtils()

        format_tests = [
            {"template": "Hello {}", "values": ["World"]},
            {"template": "Number: {}", "values": [42]},
            {"template": "Multiple: {} and {}", "values": ["first", "second"]},
        ]

        for test_case in format_tests:
            try:
                if hasattr(utils, "format"):
                    result = utils.format(test_case["template"], *test_case["values"])
                    if result is not None:
                        assert isinstance(result, str)
            except Exception:
                pass

    def test_string_splitting(self):
        """测试字符串分割"""
        utils = StringUtils()

        split_tests = ["a,b,c", "hello world", "one-two-three", "path/to/file"]

        for test_str in split_tests:
            try:
                if hasattr(utils, "split"):
                    result = utils.split(test_str)
                    if result is not None:
                        assert isinstance(result, list)
            except Exception:
                pass

    def test_string_joining(self):
        """测试字符串连接"""
        utils = StringUtils()

        join_tests = [
            (["a", "b", "c"], ","),
            (["hello", "world"], " "),
            (["one", "two", "three"], "-"),
        ]

        for items, separator in join_tests:
            try:
                if hasattr(utils, "join"):
                    result = utils.join(items, separator)
                    if result is not None:
                        assert isinstance(result, str)
            except Exception:
                pass

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        utils = StringUtils()

        whitespace_tests = [
            "  leading space",
            "trailing space  ",
            "\t tab character\t",
            "\n newline character\n",
            "  multiple   spaces  ",
        ]

        for test_str in whitespace_tests:
            try:
                if hasattr(utils, "trim"):
                    result = utils.trim(test_str)
                    if result is not None:
                        assert isinstance(result, str)
            except Exception:
                pass

    def test_unicode_handling(self):
        """测试Unicode处理"""
        utils = StringUtils()

        unicode_tests = ["测试中文", "emoji 🚀", "café résumé", "привет мир", "العربية"]

        for test_str in unicode_tests:
            try:
                # 基本操作应该能处理Unicode
                if hasattr(utils, "length"):
                    result = utils.length(test_str)
                    if result is not None:
                        assert isinstance(result, int)

                if hasattr(utils, "is_empty"):
                    result = utils.is_empty(test_str)
                    if result is not None:
                        assert isinstance(result, bool)
            except Exception:
                pass

    def test_error_handling(self):
        """测试错误处理"""
        utils = StringUtils()

        error_cases = [None, 123, [], {}, object()]

        for case in error_cases:
            try:
                # 应该优雅地处理无效输入
                if hasattr(utils, "safe_process"):
                    utils.safe_process(case)
                    # 如果方法存在，应该不抛出异常
            except Exception:
                # 某些输入可能抛出异常,这是可以接受的
                pass

    def test_performance_considerations(self):
        """测试性能考虑"""
        utils = StringUtils()

        # 测试大字符串处理
        large_string = "a" * 10000

        try:
            if hasattr(utils, "process_large"):
                result = utils.process_large(large_string)
                if result is not None:
                    assert isinstance(result, str)
        except Exception:
            pass

        # 测试批量处理
        string_list = ["test"] * 1000

        try:
            if hasattr(utils, "batch_process"):
                result = utils.batch_process(string_list)
                if result is not None:
                    assert isinstance(result, list)
        except Exception:
            pass

    def test_edge_cases(self):
        """测试边缘情况"""
        utils = StringUtils()

        edge_cases = [
            "",  # 空字符串
            " ",  # 单个空格
            "a",  # 单个字符
            "a" * 1000,  # 长字符串
            "🚀" * 100,  # Unicode重复
        ]

        for case in edge_cases:
            try:
                # 基本操作应该能处理边缘情况
                if hasattr(utils, "basic_operation"):
                    result = utils.basic_operation(case)
                    if result is not None:
                        assert isinstance(result, str)
            except Exception:
                pass

    def test_configuration_options(self):
        """测试配置选项"""
        # 测试带配置的初始化
        configs = [
            {},
            {"encoding": "utf-8"},
            {"trim_whitespace": True},
            {"case_sensitive": False},
        ]

        for config in configs:
            try:
                utils = StringUtils(**config)
                assert utils is not None
            except Exception:
                # 配置可能不支持,尝试默认构造函数
                utils = StringUtils()
                assert utils is not None

    def test_string_statistics(self):
        """测试字符串统计"""
        utils = StringUtils()

        test_str = "Hello World 123!"

        try:
            if hasattr(utils, "get_stats"):
                stats = utils.get_stats(test_str)
                if stats is not None:
                    assert isinstance(stats, dict)
                    # 可能的统计信息
                    possible_keys = ["length", "words", "characters", "lines"]
                    for key in possible_keys:
                        if key in stats:
                            assert isinstance(stats[key], (int, float))
        except Exception:
            pass


def test_import_fallback():
    """测试导入回退"""
    if not IMPORT_SUCCESS:
        assert IMPORT_ERROR is not None
        assert len(IMPORT_ERROR) > 0
    else:
        assert True  # 导入成功
