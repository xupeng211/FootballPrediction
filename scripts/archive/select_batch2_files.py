#!/usr/bin/env python3
"""
批次文件选择器 - 简化版本
"""

from pathlib import Path
import sys

def select_files():
    """选择文件"""
    test_dir = Path("tests")
    if not test_dir.exists():
        print("❌ tests目录不存在")
        return 0
    
    py_files = list(test_dir.rglob("*.py"))
    print(f"📁 找到 {len(py_files)} 个Python文件")
    return len(py_files)

if __name__ == '__main__':
    count = select_files()
    print(f"✅ 文件选择完成: {count} 个文件")
    sys.exit(0)
