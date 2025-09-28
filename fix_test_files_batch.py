#!/usr/bin/env python3
"""
批量修复测试文件缩进错误
"""

import os
import re
from pathlib import Path

def fix_indentation_errors(file_path):
    """修复文件的缩进错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        indent_stack = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue

            # 计算当前缩进
            indent = len(line) - len(line.lstrip())

            # 特殊处理assert语句和其他缩进问题
            if stripped.startswith('assert ') and i > 1:
                # assert语句应该与上一级代码块保持一致
                if indent_stack:
                    expected_indent = indent_stack[-1]
                    if indent != expected_indent and indent > expected_indent:
                        # 修正assert语句的缩进
                        fixed_line = ' ' * expected_indent + stripped + '\n'
                        fixed_lines.append(fixed_line)
                        continue

            # 处理函数和类的定义
            if stripped.startswith(('def ', 'class ', 'async def ')):
                # 顶层定义应该缩进为0
                if indent > 0 and not indent_stack:
                    fixed_line = stripped + '\n'
                    fixed_lines.append(fixed_line)
                    continue
                # 更新缩进栈
                indent_stack = indent_stack[:1]  # 保留顶层缩进

            # 普通代码行
            fixed_lines.append(line)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        return True

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    base_dir = Path("tests")

    # 查找所有.bak文件
    bak_files = list(base_dir.rglob("*.bak"))

    print(f"找到 {len(bak_files)} 个需要修复的测试文件")

    fixed_count = 0
    for bak_file in bak_files:
        original_file = bak_file.with_suffix('')

        print(f"正在修复: {bak_file}")

        if fix_indentation_errors(bak_file):
            # 重命名文件，移除.bak扩展名
            try:
                bak_file.rename(original_file)
                fixed_count += 1
                print(f"✅ 修复成功: {original_file}")
            except Exception as e:
                print(f"❌ 重命名失败: {e}")
        else:
            print(f"❌ 修复失败: {bak_file}")

    print(f"\n修复完成: {fixed_count}/{len(bak_files)} 个文件")

if __name__ == "__main__":
    main()