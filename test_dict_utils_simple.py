#!/usr/bin/env python3
"""
简单的DictUtils测试
"""

from src.utils.dict_utils import DictUtils

def test_methods():
    """测试DictUtils方法"""

    # 测试get_nested
    data = {"a": {"b": {"c": 123}}}
    result = DictUtils.get_nested(data, "a.b.c")
    assert result == 123
    print("✓ get_nested 测试通过")

    # 测试set_nested
    data = {}
    DictUtils.set_nested(data, "a.b.c", 123)
    assert data == {"a": {"b": {"c": 123}}}
    print("✓ set_nested 测试通过")

    # 测试merge
    dict1 = {"a": 1, "b": 2}
    dict2 = {"c": 3, "d": 4}
    result = DictUtils.merge(dict1, dict2)
    assert result == {"a": 1, "b": 2, "c": 3, "d": 4}
    print("✓ merge 测试通过")

    # 测试flatten
    data = {"a": {"b": {"c": 1}, "d": 2}, "e": 3}
    result = DictUtils.flatten(data)
    expected = {"a.b.c": 1, "a.d": 2, "e": 3}
    assert result == expected
    print("✓ flatten 测试通过")

    print("\n所有测试通过！")

if __name__ == "__main__":
    test_methods()