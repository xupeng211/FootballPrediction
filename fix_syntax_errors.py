#!/usr/bin/env python3
"""
系统性修复Python语法错误
Systematic Python Syntax Error Fixer

专门修复try/except语法错误和缩进问题
"""

import os
import ast
import sys
from pathlib import Path
import re


def fix_python_syntax(file_path):
    """
    修复Python文件的语法错误
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 尝试解析语法
        try:
            ast.parse(original_content)
            print(f"✅ {file_path}: 语法正确")
            return False
        except SyntaxError:
            print(f"🔧 {file_path}: 发现语法错误，开始修复...")

        lines = original_content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检查是否是语法错误的except语句
            if stripped.startswith('except Exception:') or stripped.startswith('except'):
                # 检查前面是否有对应的try
                has_try = False
                try_indent = 0
                current_indent = len(line) - len(line.lstrip())

                # 向上查找try语句
                for j in range(i-1, -1, -1):
                    prev_line = lines[j]
                    prev_stripped = prev_line.strip()

                    # 如果遇到空行或注释，继续查找
                    if not prev_stripped or prev_stripped.startswith('#'):
                        continue

                    # 如果缩进级别相同或更小，且不是try，则说明有问题
                    prev_indent = len(prev_line) - len(prev_line.lstrip())

                    if prev_indent < current_indent:
                        if prev_stripped.startswith('try:'):
                            has_try = True
                            try_indent = prev_indent
                        break
                    elif prev_indent == current_indent:
                        if prev_stripped.startswith('try:'):
                            has_try = True
                            try_indent = prev_indent
                        break

                if not has_try:
                    # 找到最近的代码块，在前面添加try
                    for j in range(i-1, -1, -1):
                        prev_line = lines[j]
                        prev_stripped = prev_line.strip()
                        if prev_stripped and not prev_stripped.startswith('#'):
                            # 在这行前面插入try
                            prev_indent = len(prev_line) - len(prev_line.lstrip())
                            try_line = ' ' * prev_indent + 'try:'
                            fixed_lines.append(try_line)
                            # 调整当前except的缩进
                            fixed_except = ' ' * (prev_indent + 4) + stripped
                            fixed_lines.append(fixed_except)
                            i += 1
                            break
                else:
                    # 修复缩进
                    fixed_lines.append(' ' * (try_indent + 4) + stripped)
                    i += 1
            else:
                fixed_lines.append(line)
                i += 1

        fixed_content = '\n'.join(fixed_lines)

        # 验证修复后的语法
        try:
            ast.parse(fixed_content)
            print(f"✅ {file_path}: 语法修复成功")

            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True

        except SyntaxError as e:
            print(f"❌ {file_path}: 语法修复失败: {e}")
            return False

    except Exception as e:
        print(f"❌ {file_path}: 处理失败: {e}")
        return False


def main():
    """
    主函数
    """
    print("🔧 系统性Python语法修复工具")
    print("=" * 50)

    # 获取所有Python文件
    python_files = []
    for root, dirs, files in os.walk('.'):
        # 跳过虚拟环境和git目录
        if '.venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"📁 找到 {len(python_files)} 个Python文件")
    print()

    fixed_count = 0
    failed_count = 0

    for file_path in python_files:
        if fix_python_syntax(file_path):
            fixed_count += 1
        else:
            failed_count += 1

    print()
    print("📊 修复统计:")
    print(f"  ✅ 成功修复: {fixed_count} 个文件")
    print(f"  ❌ 修复失败: {failed_count} 个文件")
    print(f"  📁 总计处理: {len(python_files)} 个文件")


if __name__ == "__main__":
    main()