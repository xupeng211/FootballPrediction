#!/usr/bin/env python3
"""
快速修复缩进语法错误
"""

import os
import re


def fix_indentation_errors(filepath):
    """修复文件的缩进错误"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        fixed_lines = []
        for line in lines:
            # 修复常见的缩进问题
            # 移除行尾空格
            fixed_line = line.rstrip()
            # 确保缩进使用空格而不是tab
            fixed_line = fixed_line.expandtabs()
            # 修复空行
            if fixed_line.strip() == "":
                fixed_line = "\n"
            else:
                fixed_line = fixed_line + "\n"
            fixed_lines.append(fixed_line)

        # 写回文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(fixed_lines)

        return True
    except Exception as e:
        print(f"修复 {filepath} 时出错: {e}")
        return False


def main():
    """主函数"""
    error_files = [
        "tests/unit/adapters/base_test_phase3.py",
        "tests/unit/api/data_router_test_phase3.py",
        "tests/unit/api/decorators_test_phase3.py",
        "tests/unit/utils/helpers_test_phase3.py",
        "tests/unit/utils/formatters_test_phase3.py",
    ]

    print("🔧 修复缩进语法错误...")

    fixed_count = 0
    for filepath in error_files:
        if os.path.exists(filepath):
            if fix_indentation_errors(filepath):
                print(f"✅ 修复 {filepath}")
                fixed_count += 1
            else:
                print(f"❌ 修复失败 {filepath}")
        else:
            print(f"⚠️  文件不存在: {filepath}")

    print(f"\n📊 修复总结: {fixed_count}/{len(error_files)} 个文件已修复")


if __name__ == "__main__":
    main()
