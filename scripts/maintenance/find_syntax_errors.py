#!/usr/bin/env python3
"""
查找所有语法错误的测试文件
"""

import os
import py_compile
from pathlib import Path

def find_syntax_errors(directory="tests/"):
    """找到所有语法错误的文件"""
    syntax_errors = []
    syntax_correct = []

    test_files = list(Path(directory).rglob("*.py"))

    for file_path in test_files:
        try:
            py_compile.compile(file_path, doraise=True)
            syntax_correct.append(file_path)
        except Exception as e:
            syntax_errors.append((file_path, str(e)))

    return syntax_correct, syntax_errors

def main():
    print("🔍 搜索所有测试文件中的语法错误...")

    syntax_correct, syntax_errors = find_syntax_errors()

    print("\n📊 统计结果:")
    print(f"- 总测试文件数: {len(syntax_correct) + len(syntax_errors)}")
    print(f"- 语法正确: {len(syntax_correct)}")
    print(f"- 语法错误: {len(syntax_errors)}")

    if syntax_errors:
        print("\n❌ 语法错误的文件:")
        for file_path, error in syntax_errors:
            print(f"   - {file_path}: {error}")
    else:
        print("\n✅ 所有测试文件语法正确!")

    return len(syntax_errors)

if __name__ == "__main__":
    exit(main())