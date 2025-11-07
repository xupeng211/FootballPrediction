#!/usr/bin/env python3
"""
精确B904异常处理修复工具 - 专门处理剩余的B904错误
Precise B904 Exception Handling Fixer - Handle remaining B904 errors
"""

import os
import re


def fix_b904_errors_in_file(file_path: str) -> int:
    """精确修复文件中的B904错误"""

    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return 0

    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        fixes_count = 0

        # 逐行分析和修复
        for i, line in enumerate(lines):
            # 查找raise语句在except块中的情况
            if 'raise HTTPException' in line and 'from e' not in line:
                # 检查前面的代码是否有except语句
                context_lines = lines[max(0, i-10):i]
                in_except_block = False

                for ctx_line in reversed(context_lines):
                    if ctx_line.strip().startswith('except'):
                        in_except_block = True
                        break
                    elif ctx_line.strip().startswith(('def', 'class', 'try:', 'if', 'for', 'while')):
                        break

                if in_except_block:
                    # 检查行尾是否有注释
                    comment_part = ''
                    code_part = line.strip()

                    if '#' in code_part:
                        comment_start = code_part.find('#')
                        comment_part = code_part[comment_start:]
                        code_part = code_part[:comment_start].strip()

                    # 添加from e，但保持注释
                    if comment_part:
                        lines[i] = line.replace(code_part, code_part + ' from e')
                    else:
                        lines[i] = line.rstrip() + ' from e\n'
                    fixes_count += 1

            # 处理其他类型的异常
            elif 'raise ' in line and 'from e' not in line and 'HTTPException' not in line:
                # 类似的逻辑处理其他异常
                context_lines = lines[max(0, i-10):i]
                in_except_block = False

                for ctx_line in reversed(context_lines):
                    if ctx_line.strip().startswith('except'):
                        in_except_block = True
                        break
                    elif ctx_line.strip().startswith(('def', 'class', 'try:', 'if', 'for', 'while')):
                        break

                if in_except_block:
                    # 检查是否是简单的raise语句
                    simple_raise = re.match(r'^\s*raise (\w+)\([^)]*\)', line.strip())
                    if simple_raise:
                        # 跳过不需要from子句的异常
                        exception_name = simple_raise.group(1)
                        if exception_name in ['ValueError', 'TypeError', 'AttributeError', 'KeyError', 'IndexError']:
                            continue

                        # 添加from e
                        lines[i] = line.rstrip() + ' from e\n'
                        fixes_count += 1

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return fixes_count

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return 0

def main():
    """主函数"""
    print("开始精确修复剩余B904错误...")

    # 需要修复的文件
    files_to_fix = [
        "src/api/betting_api.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        print(f"\n处理文件: {file_path}")
        fixes = fix_b904_errors_in_file(file_path)
        total_fixes += fixes
        print(f"修复了 {fixes} 个B904错误")

    print(f"\n总计修复 {total_fixes} 个B904错误")

if __name__ == "__main__":
    main()
