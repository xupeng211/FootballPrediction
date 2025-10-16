#!/usr/bin/env python3
"""
查找所有Python语法错误
"""

import ast
import os
from pathlib import Path
from typing import List, Tuple
import subprocess


def find_all_syntax_errors():
    """查找所有语法错误"""
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    errors = []

    print(f"扫描 {len(python_files)} 个Python文件...\n")

    for file_path in sorted(python_files):
        # 使用python -m py_compile检查
        result = subprocess.run(
            ["python", "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            relative_path = str(file_path)
            errors.append((str(relative_path), result.stderr))
            print(f"✗ {relative_path}")
            # 显示错误信息的前两行
            error_lines = result.stderr.strip().split('\n')[:2]
            for line in error_lines:
                if line.strip():
                    print(f"    {line}")
        else:
            print(f"✓ {file_path}")

    return errors


def main():
    """主函数"""
    print("=" * 60)
    print("Python语法错误扫描工具")
    print("=" * 60)

    errors = find_all_syntax_errors()

    print("\n" + "=" * 60)
    print(f"扫描完成：")
    print(f"  总错误文件数: {len(errors)}")

    if errors:
        print("\n错误文件列表：")
        for i, (file_path, error) in enumerate(errors, 1):
            print(f"\n{i}. {file_path}")
            # 提取错误类型
            if "SyntaxError" in error:
                if "unterminated string literal" in error:
                    print("   错误类型: 未闭合的字符串")
                elif "invalid character" in error:
                    print("   错误类型: 无效字符（通常是中文标点）")
                elif "invalid syntax" in error:
                    print("   错误类型: 语法错误")
                elif "unmatched" in error:
                    print("   错误类型: 括号不匹配")
                else:
                    print("   错误类型: 语法错误")

            # 提取行号
            import re
            line_match = re.search(r'line (\d+)', error)
            if line_match:
                print(f"   错误行号: {line_match.group(1)}")

    return errors


if __name__ == "__main__":
    errors = main()