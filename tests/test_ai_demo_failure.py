"""
演示用的失败测试，用于测试 AI 修复功能
"""

import pytest


def test_intentional_failure():
    """故意失败的测试"""
    # 缺少导入
    result = undefined_function()  # NameError
    assert result == "expected"


def test_name_error():
    """名称错误测试"""
    # NameError
    result = undefined_function()
    assert result == "expected"


def test_assertion_error():
    """断言错误测试"""
    value = 42
    assert value == 100, "Value should be 100"