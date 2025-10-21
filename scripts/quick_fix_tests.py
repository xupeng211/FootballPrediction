#!/usr/bin/env python3
"""
快速修复测试中的常见变量名错误
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path: Path):
    """修复单个测试文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复常见的变量名问题
        # 1. data -> _data (在assert语句中)
        content = re.sub(
            r'assert\s+"[^"]*"?\s+in\s+data([^_])',
            r'assert "\g<0>" in _data\g<1>',
            content,
        )

        # 更通用的修复
        content = re.sub(
            r"\bassert\s+.*?\s+in\s+data\b(?!\s*=)",
            lambda m: m.group(0).replace(" in data", " in _data"),
            content,
        )

        # 2. 修复 config -> _config
        content = re.sub(r"\bconfig\.([a-zA-Z_][a-zA-Z0-9_]*)", r"_config.\1", content)

        # 3. 修复 result -> _result
        content = re.sub(r"\bassert\s+result\b", "assert _result", content)

        # 保存文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")

    return False


def main():
    """主函数"""
    test_dir = Path("tests/unit")
    fixed_count = 0

    print("🔧 开始快速修复测试文件...")

    # 遍历所有测试文件
    for test_file in test_dir.rglob("test_*.py"):
        if fix_test_file(test_file):
            fixed_count += 1

    print(f"\n✅ 完成！修复了 {fixed_count} 个文件。")


if __name__ == "__main__":
    main()
