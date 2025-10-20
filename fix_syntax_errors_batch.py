#!/usr/bin/env python3
"""
批量修复Python语法错误
"""

import os
import re
from pathlib import Path


def fix_bracket_syntax(content):
    """修复 ] = 的语法错误"""
    # 修复 ] = None 的模式
    content = re.sub(r"\s*]\s*=\s*None\s*$", " = None", content, flags=re.MULTILINE)
    return content


def fix_typing_imports(content):
    """修复 typing 导入语句的语法错误"""
    # 修复重复的 Any 导入
    content = re.sub(
        r"from typing import Any,.*?\bAny\b.*",
        lambda m: m.group(0).replace(", Any", "").replace("  Any", " Any"),
        content,
    )
    # 修复 Dict[str, Any] 语法
    content = re.sub(r"\bAny,  Dict\[str, Any\]", "Any, Dict", content)
    return content


def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复 typing 导入
        content = fix_typing_imports(content)

        # 修复括号语法
        content = fix_bracket_syntax(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    src_dir = Path("src")

    fixed_count = 0
    total_count = 0

    # 遍历所有 Python 文件
    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if fix_file_syntax(py_file):
            fixed_count += 1

    print("\n修复完成！")
    print(f"总计检查文件: {total_count}")
    print(f"修复文件数: {fixed_count}")


if __name__ == "__main__":
    main()
