#!/usr/bin/env python3
"""
修复语法错误的脚本
"""

import os
from pathlib import Path


def fix_conftest_syntax():
    """修复conftest.py的语法错误"""
    file_path = Path("tests/unit/api/conftest.py")

    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")

    # 修复缩进问题
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # 移除开头的多余空格
        if line.startswith("        "):
            # 检查是否是导入语句
            stripped = line.lstrip()
            if stripped.startswith(("import ", "from ", "#")):
                line = stripped

        fixed_lines.append(line)

    # 重新写入
    fixed_content = "\n".join(fixed_lines)
    file_path.write_text(fixed_content, encoding="utf-8")

    return True


def main():
    """主函数"""
    print("修复语法错误...")

    # 修复conftest.py
    if fix_conftest_syntax():
        print("  ✓ 修复了 tests/unit/api/conftest.py")

    print("\n✅ 语法错误修复完成！")


if __name__ == "__main__":
    main()
