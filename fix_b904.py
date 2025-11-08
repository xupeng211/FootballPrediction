#!/usr/bin/env python3
"""
自动修复B904异常处理错误的脚本
"""

import re
import os

def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 原始内容用于对比
    original_content = content

    # 匹配B904错误模式：在except子句中raise但没有from
    # pattern: raise SomeException(...)
    pattern = r'(\s+)(raise\s+\w+\([^)]*\))\s*$'

    lines = content.split('\n')
    modified_lines = []

    for i, line in enumerate(lines):
        modified_line = line

        # 检查是否是raise语句
        if re.match(pattern, line):
            # 向上查找对应的except语句
            for j in range(i-1, max(i-10, -1), -1):
                if 'except' in lines[j] and 'as' in lines[j]:
                    # 提取异常变量名
                    except_match = re.search(r'except\s+\w+(?:\s+as\s+(\w+))?', lines[j])
                    if except_match:
                        exc_var = except_match.group(1) or 'e'
                        # 检查是否已经有from
                        if ' from ' not in line:
                            # 添加from语句
                            modified_line = line + f' from {exc_var}'
                    break
                elif lines[j].strip() == '' or lines[j].strip().startswith('#'):
                    continue
                else:
                    break

        modified_lines.append(modified_line)

    fixed_content = '\n'.join(modified_lines)

    # 如果内容有变化，写回文件
    if fixed_content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True

    return False

def main():
    """主函数"""

    # 需要修复的文件列表
    files_to_fix = [
        'src/monitoring/alert_routes.py',
        'src/monitoring/log_routes.py',
        'src/realtime/match_api.py'
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"正在修复: {file_path}")
            if fix_b904_in_file(file_path):
                print(f"  ✓ 已修复: {file_path}")
                fixed_count += 1
            else:
                print(f"  - 无需修复: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()