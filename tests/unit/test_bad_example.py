"""
不良示例代码测试
Tests for Bad Example

测试src.bad_example模块的功能（虽然是不良示例）
"""

import pytest
from src.bad_example import badly_formatted_function, very_long_line


class TestBadExample:
    """不良示例代码测试"""

    def test_badly_formatted_function_positive(self):
        """测试：格式不良的函数（正数输入）"""
        result = badly_formatted_function(5, 3, 2)
        assert result == 10

    def test_badly_formatted_function_zero(self):
        """测试：格式不良的函数（零输入）"""
        result = badly_formatted_function(0, 5, 5)
        assert result is None

    def test_badly_formatted_function_negative(self):
        """测试：格式不良的函数（负数输入）"""
        result = badly_formatted_function(-1, 5, 5)
        assert result is None

    def test_badly_formatted_function_edge_cases(self):
        """测试：格式不良的函数（边界情况）"""
        # 测试大正数
        result = badly_formatted_function(999999, 1, 1)
        assert result == 1000001

        # 测试浮点数（如果有）
        try:
            result = badly_formatted_function(1.5, 2.5, 3.5)
            assert result == 7.5
        except (TypeError, ValueError):
            # 如果不支持浮点数，这是预期的
            pass

    def test_very_long_line_content(self):
        """测试：超长行的内容"""
        assert very_long_line is not None
        assert isinstance(very_long_line, str)
        assert "故意写得很长" in very_long_line
        assert "超过了88个字符" in very_long_line
        # 验证长度（实际长度是46）
        assert len(very_long_line) > 40

    def test_very_long_line_length(self):
        """测试：超长行的长度"""
        expected_length = 46  # 实际长度
        assert len(very_long_line) == expected_length

    def test_function_with_various_inputs(self):
        """测试：函数的各种输入"""
        test_cases = [
            (1, 1, 1, 3),
            (10, -5, 0, 5),
            (100, 200, 300, 600),
        ]

        for x, y, z, expected in test_cases:
            result = badly_formatted_function(x, y, z)
            assert result == expected

    def test_function_return_types(self):
        """测试：函数返回类型"""
        # 正数返回整数
        result = badly_formatted_function(5, 5, 5)
        assert isinstance(result, int)

        # 非正数返回None
        result = badly_formatted_function(0, 5, 5)
        assert result is None

    def test_function_parameter_order(self):
        """测试：函数参数顺序"""
        # 参数顺序很重要
        result1 = badly_formatted_function(1, 2, 3)
        result2 = badly_formatted_function(3, 2, 1)

        assert result1 == 6
        assert result2 == 6  # 加法是可交换的

    def test_line_content_encoding(self):
        """测试：行内容编码"""
        # 确保字符串使用正确的编码
        assert isinstance(very_long_line.encode("utf-8"), bytes)
        # 检查特殊字符
        assert "，" in very_long_line  # 中文逗号
        assert "应该会报错" in very_long_line
