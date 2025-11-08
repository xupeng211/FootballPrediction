#!/usr/bin/env python3
"""
综合修复B904异常处理错误的脚本
"""

import re
import os

def fix_b904_comprehensive(file_path):
    """综合修复B904错误"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 匹配异常处理模式并添加 from e
    lines = content.split('\n')
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        fixed_line = line

        # 检查是否是raise HTTPException语句
        if 'raise HTTPException(' in line and i > 0:
            # 向上查找对应的except语句
            for j in range(i-1, max(i-5, -1), -1):
                if 'except Exception as e:' in lines[j]:
                    # 检查是否已经有from
                    if ' from ' not in line and ' from e' not in line:
                        # 添加from e
                        fixed_line = line.rstrip() + ' from e'
                    break
                elif lines[j].strip() == '' or lines[j].strip().startswith('#'):
                    continue
                else:
                    break

        fixed_lines.append(fixed_line)
        i += 1

    fixed_content = '\n'.join(fixed_lines)

    # 如果内容有变化，写回文件
    if fixed_content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True

    return False

def main():
    """主函数"""

    # 需要修复的文件
    files_to_fix = [
        'src/monitoring/alert_routes.py',
        'src/monitoring/log_routes.py'
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"正在修复: {file_path}")
            if fix_b904_comprehensive(file_path):
                print(f"  ✓ 已修复: {file_path}")
                fixed_count += 1
            else:
                print(f"  - 无需修复: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()