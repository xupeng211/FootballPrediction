#!/usr/bin/env python3
"""
最终语法错误清理 - P1优先级任务
目标: 将剩余语法错误从27个减少到0个
"""

import os
import re
import ast

def fix_first_line_indentation(filepath):
    """修复第一行缩进问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        if lines:
            first_line = lines[0]
            # 如果第一行是缩进的docstring开始，修复它
            if first_line.strip().startswith('"""') and first_line.startswith('    '):
                lines[0] = first_line.lstrip()

                # 写回文件
                fixed_content = '\n'.join(lines)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return True
        return False
    except Exception:
        return False

def fix_function_body(filepath):
    """修复函数体缺失问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # 检查函数定义行
            if re.match(r'^\s*def\s+\w+.*\:$', line):
                fixed_lines.append(line)

                # 检查下一行是否为空或缺少代码块
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() == '' or not next_line.startswith('    '):
                        # 添加pass语句
                        indent = '    '  # 4个空格
                        if line.startswith('    '):
                            indent = '        '  # 8个空格
                        fixed_lines.append(f'{indent}pass  # TODO: 实现函数逻辑')
                        continue

            fixed_lines.append(line)

        # 写回文件
        fixed_content = '\n'.join(fixed_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        return True
    except Exception:
        return False

def fix_generic_indentation(filepath):
    """修复通用缩进问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            if line.strip():
                # 检查是否有过深缩进
                if re.match(r'^\s{12,}', line):  # 12个或更多空格
                    stripped = line.lstrip()
                    # 判断应该的缩进级别
                    if stripped.startswith(('def ', 'class ', '@')):
                        fixed_lines.append('    ' + stripped)  # 4个空格
                    elif stripped.startswith(('if ', 'for ', 'while ', 'try:', 'except', 'else:', 'finally:', 'with ')):
                        fixed_lines.append('    ' + stripped)  # 4个空格
                    else:
                        fixed_lines.append('        ' + stripped)  # 8个空格
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        fixed_content = '\n'.join(fixed_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        return True
    except Exception:
        return False

def main():
    """主函数"""
    print("🚀 P1任务: 最终语法错误清理")
    print("=" * 60)

    # 获取所有有语法错误的文件
    error_files = []
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError:
                    error_files.append(filepath)
                except Exception:
                    pass

    print(f"发现 {len(error_files)} 个语法错误文件")

    fixed_count = 0
    for filepath in error_files:
        relative_path = os.path.relpath(filepath, 'tests')
        print(f"\n修复: {relative_path}")

        # 尝试不同的修复方法
        fixed = False

        # 方法1: 修复第一行缩进
        if fix_first_line_indentation(filepath):
            print("  ✅ 第一行缩进修复")
            fixed = True

        # 方法2: 修复函数体
        elif fix_function_body(filepath):
            print("  ✅ 函数体修复")
            fixed = True

        # 方法3: 修复通用缩进
        elif fix_generic_indentation(filepath):
            print("  ✅ 通用缩进修复")
            fixed = True

        if fixed:
            fixed_count += 1
        else:
            print("  ❌ 修复失败")

    print("\n📊 P1任务总结:")
    print(f"   错误文件: {len(error_files)}")
    print(f"   修复成功: {fixed_count}")
    print(f"   修复失败: {len(error_files) - fixed_count}")

    # 最终验证
    final_errors = []
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError:
                    final_errors.append(filepath)
                except Exception:
                    pass

    print("\n🎯 最终结果:")
    print(f"   剩余错误: {len(final_errors)}")

    if len(final_errors) == 0:
        print("🎉 P1任务完美完成！所有语法错误已修复！")
    elif len(final_errors) < 5:
        print(f"✅ P1任务基本完成！仅剩 {len(final_errors)} 个错误需要手动处理")
    else:
        print(f"⚠️ P1任务部分完成，还需处理 {len(final_errors)} 个错误")

if __name__ == "__main__":
    main()