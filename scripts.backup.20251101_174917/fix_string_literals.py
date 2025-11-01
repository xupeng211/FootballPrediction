#!/usr/bin/env python3
"""
修复未闭合字符串字面量的专用工具
"""

import os
import re
from pathlib import Path

def fix_string_literals_in_file(file_path):
    """修复单个文件中的未闭合字符串字面量"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取 {file_path}: {e}")
        return False

    lines = content.split('\n')
    fixed_lines = []
    fixes_count = 0

    for line in lines:
        fixed_line = line

        # 检查单引号
        single_quotes = line.count("'")
        # 检查双引号
        double_quotes = line.count('"')

        # 简单修复：如果引号数量为奇数，添加闭合引号
        if single_quotes % 2 == 1 and double_quotes % 2 == 0:
            # 优先修复单引号
            if line.strip():
                fixed_line += "'"
                fixes_count += 1
        elif double_quotes % 2 == 1 and single_quotes % 2 == 0:
            # 修复双引号
            if line.strip():
                fixed_line += '"'
                fixes_count += 1

        # 修复三引号字符串的问题
        if '"""' in line and line.count('"""') % 2 == 1:
            # 在行尾添加闭合的三引号
            fixed_line += '"""'
            fixes_count += 1

        fixed_lines.append(fixed_line)

    # 写回文件
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
        return fixes_count > 0
    except Exception as e:
        print(f"❌ 无法写入 {file_path}: {e}")
        return False

def fix_all_string_literals(failed_files_list):
    """修复所有失败文件中的字符串字面量"""

    print("🔧 开始修复未闭合的字符串字面量...")

    total_fixes = 0
    fixed_count = 0

    for file_path in failed_files_list:
        if os.path.exists(file_path):
            print(f"   🔍 修复: {file_path}")
            if fix_string_literals_in_file(file_path):
                fixed_count += 1
                print(f"      ✅ 已修复")
            else:
                print(f"      ⚠️ 未修复")
        else:
            print(f"   ⚠️ 文件不存在: {file_path}")

    print(f"\n📊 字符串修复结果:")
    print(f"   修复文件数: {fixed_count}")
    print(f"   总修复数: {total_fixes}")

    return fixed_count

def main():
    """主函数"""
    print("🚀 字符串字面量修复工具启动...")

    # 从之前的修复报告中读取失败的文件列表
    try:
        import json
        with open('syntax_fix_report.json', 'r', encoding='utf-8') as f:
            report = json.load(f)

        failed_files = report['src_summary']['failed_files_list'] + report['tests_summary']['failed_files_list']
        print(f"📋 从报告中找到 {len(failed_files)} 个失败文件")

    except Exception as e:
        print(f"⚠️ 无法读取修复报告: {e}")
        print("🔍 手动查找有语法错误的文件...")
        # 使用ruff查找有语法错误的文件
        failed_files = []
        result = os.popen("ruff check --select=E9 --output-format=concise | cut -d: -f1 | sort | uniq").read()
        failed_files = [line.strip() for line in result.split('\n') if line.strip()]
        print(f"📋 找到 {len(failed_files)} 个有语法错误的文件")

    if failed_files:
        fixed_count = fix_all_string_literals(failed_files)

        if fixed_count > 0:
            print("\n✅ 字符串字面量修复完成！")
            print("💡 建议再次运行语法检查工具验证修复结果")
        else:
            print("\n⚠️ 没有文件需要修复")
    else:
        print("✅ 没有发现需要修复的文件")

if __name__ == "__main__":
    main()