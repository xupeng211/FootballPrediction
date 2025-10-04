"""示例测试文件"""

import pytest

pytestmark = pytest.mark.example


def test_example():
    """示例测试函数"""
    assert 1 + 1 == 2


def test_string_operations():
    """字符串操作测试"""
    text = "Hello, World!"
    assert text.upper() == "HELLO, WORLD!"
    assert text.lower() == "hello, world!"


class TestExampleClass:
    """示例测试类"""

    def test_list_operations(self):
        """列表操作测试"""
        test_list = [1, 2, 3]
        test_list.append(4)
        assert len(test_list) == 4
        assert test_list[-1] == 4
