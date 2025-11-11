#!/usr/bin/env python3
"""
修复测试文件中的双冒号语法错误
"""

import re
from pathlib import Path


def fix_double_colons(file_path):
    """修复单个文件中的双冒号语法错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复函数定义中的双冒号
        # 匹配 def function_name(client):: 模式
        pattern = r'(def\s+\w+\s*\([^)]*\))::'

        def replace_func(match):
            func_def = match.group(1)  # def function_name(client)
            return f"{func_def}:"

        content = re.sub(pattern, replace_func, content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""
    tests_dir = Path("tests")

    if not tests_dir.exists():
        return

    fixed_count = 0
    total_count = 0

    # 遍历所有Python文件
    for py_file in tests_dir.rglob("*.py"):
        if py_file.is_file():
            total_count += 1
            if fix_double_colons(str(py_file)):
                fixed_count += 1


if __name__ == "__main__":
    main()
