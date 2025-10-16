import pytest

def test_calculator_add():
    """测试计算器加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5

def test_calculator_add_negative():
    """测试负数加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(-2, -3)
    assert result == -5

def test_calculator_add_zero():
    """测试零值加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(0, 5)
    assert result == 5
