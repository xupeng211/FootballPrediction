#!/usr/bin/env python3
"""
修复拆分文件的语法错误
"""

import os
import re
import ast

def fix_split_file_syntax(filepath):
    """修复拆分文件的语法错误"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # 跳过文件头部分（前10行）
            if line_num <= 10:
                fixed_lines.append(line)
                continue

            # 修复常见语法问题
            if line.strip():
                # 1. 修复缩进问题
                if line.strip().startswith(('def ', 'class ', '@', 'async def ')):
                    # 函数/类定义应该没有缩进
                    fixed_lines.append(line.lstrip())
                elif line.strip().startswith(('if ', 'for ', 'while ', 'try:', 'except', 'else:', 'finally:', 'with ', 'elif')):
                    # 控制语句应该有适当缩进
                    if not line.startswith('    '):
                        fixed_lines.append('    ' + line.lstrip())
                    else:
                        fixed_lines.append(line)
                elif re.match(r'^\s{8,}', line):  # 8个或更多空格缩进
                    # 检查是否是过深缩进
                    stripped = line.lstrip()
                    if stripped.startswith(('def ', 'class ', '@')):
                        fixed_lines.append('    ' + stripped)  # 4个空格
                    else:
                        fixed_lines.append('        ' + stripped)  # 8个空格
                elif line.startswith('    ') and not line.strip().startswith('#'):
                    # 已经有4个空格缩进，保持
                    fixed_lines.append(line)
                else:
                    # 其他情况，检查是否需要缩进
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        # 如果不是空行或注释，检查是否应该缩进
                        if i > 0 and lines[i-1].strip().endswith(':'):
                            # 上一行是控制语句，这一行应该缩进
                            fixed_lines.append('    ' + stripped)
                        else:
                            fixed_lines.append(stripped)
                    else:
                        fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        fixed_content = '\n'.join(fixed_lines)

        # 验证语法
        try:
            ast.parse(fixed_content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        except SyntaxError as e:
            print(f"    语法错误仍然存在: 第{e.lineno}行")
            return False

    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 查找所有拆分的文件
    import glob
    pattern = 'tests/unit/utils/test_date_time_utils_part_*.py'
    split_files = glob.glob(pattern)

    print("🔧 修复拆分文件语法错误...")
    print(f"找到 {len(split_files)} 个拆分文件")

    fixed_count = 0
    error_count = 0

    for filepath in split_files:
        filename = os.path.basename(filepath)
        print(f"  修复: {filename}")

        if fix_split_file_syntax(filepath):
            print("  ✅ 修复成功")
            fixed_count += 1
        else:
            print("  ❌ 修复失败")
            error_count += 1

    print("\n📊 修复总结:")
    print(f"   修复成功: {fixed_count}")
    print(f"   修复失败: {error_count}")

    # 最终验证
    print("\n🔍 最终验证...")
    syntax_ok = 0
    for filepath in split_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            syntax_ok += 1
        except SyntaxError:
            pass

    print(f"   语法正确: {syntax_ok}/{len(split_files)}")

    if syntax_ok == len(split_files):
        print("🎉 所有拆分文件语法修复完成！")
    else:
        print(f"⚠️ 还有 {len(split_files) - syntax_ok} 个文件需要手动修复")

if __name__ == "__main__":
    main()