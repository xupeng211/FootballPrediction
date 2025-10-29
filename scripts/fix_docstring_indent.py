#!/usr/bin/env python3
"""
修复docstring缩进问题
"""

import os
import re
import ast


def fix_docstring_indentation(filepath):
    """修复docstring缩进问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # 修复第10行和第7行的缩进问题
            if line_num in [7, 10]:
                if line.strip().startswith('"""') or line.strip().startswith("Issue"):
                    # 移除多余缩进
                    fixed_lines.append(line.lstrip())
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        fixed_content = "\n".join(fixed_lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        return True
    except Exception:
        return False


def main():
    """主函数"""
    print("🔧 修复docstring缩进问题")

    # 查找所有有语法错误的文件
    error_files = []
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError:
                    error_files.append(filepath)

    print(f"找到 {len(error_files)} 个需要修复的文件")

    fixed_count = 0
    for filepath in error_files:
        relative_path = os.path.relpath(filepath, "tests")
        print(f"  修复: {relative_path}")

        if fix_docstring_indentation(filepath):
            print("    ✅ 修复成功")
            fixed_count += 1
        else:
            print("    ❌ 修复失败")

    print(f"\n📊 修复总结: {fixed_count}/{len(error_files)} 个文件已修复")


if __name__ == "__main__":
    main()
