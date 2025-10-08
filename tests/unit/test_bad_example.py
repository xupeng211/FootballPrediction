from src.bad_example import badly_formatted_function
import src.bad_example

"""Bad Example模块测试 - 消除零覆盖率"""

import pytest


class TestBadExample:
    """BadExample模块测试"""

    def test_import_module(self):
        """测试模块导入"""
        try:
            from src.bad_example import badly_formatted_function

            assert badly_formatted_function is not None
        except ImportError as e:
            pytest.skip(f"无法导入bad_example模块: {e}")

    def test_badly_formatted_function_positive(self):
        """测试正数输入"""

        result = badly_formatted_function(1, 2, 3)
        assert result == 6

    def test_badly_formatted_function_zero(self):
        """测试零输入"""
        from src.bad_example import badly_formatted_function

        result = badly_formatted_function(0, 2, 3)
        assert result is None

    def test_badly_formatted_function_negative(self):
        """测试负数输入"""

        result = badly_formatted_function(-1, 2, 3)
        assert result is None

    def test_badly_formatted_function_large_numbers(self):
        """测试大数输入"""
        from src.bad_example import badly_formatted_function

        result = badly_formatted_function(1000, 2000, 3000)
        assert result == 6000

    def test_badly_formatted_function_floats(self):
        """测试浮点数输入"""

        result = badly_formatted_function(1.5, 2.5, 3.0)
        assert result == 7.0

    def test_long_line_variable(self):
        """测试长行变量"""
        try:
            from src.bad_example import very_long_line

            assert isinstance(very_long_line, str)
            assert len(very_long_line) > 40  # 实际长度是46
            assert "flake8" in very_long_line
        except ImportError:
            pytest.skip("无法导入very_long_line变量")

    def test_imports(self):
        """测试模块导入"""
        # 测试模块是否可以导入（即使有未使用的导入）

        assert src.bad_example is not None

        # 检查是否有必要的函数
        assert hasattr(src.bad_example, "badly_formatted_function")
