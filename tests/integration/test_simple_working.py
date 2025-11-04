#!/usr/bin/env python3
"""
简单的测试文件，验证pytest环境是否正常工作
"""


def test_basic_math():
    """测试基础数学运算"""
    assert 2 + 2 == 4
    assert 10 - 5 == 5
    assert 3 * 3 == 9
    assert 8 / 2 == 4


def test_string_operations():
    """测试字符串操作"""
    text = "Hello, World!"
    assert "Hello" in text
    assert text.upper() == "HELLO, WORLD!"
    assert text.lower() == "hello, world!"


def test_list_operations():
    """测试列表操作"""
    items = [1, 2, 3, 4, 5]
    assert len(items) == 5
    assert 3 in items
    assert items[0] == 1


if __name__ == "__main__":
    # 直接运行测试
    test_basic_math()
    test_string_operations()
    test_list_operations()
    logger.debug("✅ 所有测试通过！")  # TODO: Add logger import if needed
