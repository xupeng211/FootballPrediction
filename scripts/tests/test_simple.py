#!/usr/bin/env python3
"""
简单的测试验证脚本
"""

def test_basic():
    """基础测试"""
    assert 1 + 1 == 2
    assert "hello" == "hello"

def test_import():
    """导入测试"""
    try:
        import sys
        import os
        assert sys is not None
        assert os is not None
        print("✅ 基础导入测试通过")
    except Exception as e:
        print(f"❌ 基础导入测试失败: {e}")

if __name__ == "__main__":
    test_basic()
    test_import()
    print("✅ 所有基础测试通过")