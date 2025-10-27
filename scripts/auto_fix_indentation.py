#!/usr/bin/env python3
"""
自动修复缩进语法错误
"""

import ast
import os
import re

def fix_file_indentation(filepath):
    """修复单个文件的缩进问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试解析语法
        try:
            ast.parse(content)
            return True  # 语法正确，无需修复
        except SyntaxError:
            pass  # 需要修复

        # 修复常见缩进问题
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复缩进级别问题
            if line.strip():
                # 检查是否有过深缩进（8空格以上应该检查）
                if line.startswith('        ') and not line.startswith('            '):
                    # 可能是缩进过深，减少一层
                    stripped = line.lstrip()
                    if stripped.startswith(('if ', 'for ', 'while ', 'try:', 'except', 'def ', 'class ', 'with ')):
                        # 这是一个语句块开头，保持当前缩进
                        fixed_lines.append(line)
                    else:
                        # 可能是语句块内容，检查是否需要减少缩进
                        if line.startswith('            '):
                            fixed_lines.append(line)
                        else:
                            # 减少一层缩进
                            fixed_lines.append('    ' + stripped)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        # 验证修复后的语法
        try:
            ast.parse(fixed_content)
            # 写回修复后的内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        except SyntaxError:
            # 如果修复失败，尝试更激进的修复
            return aggressive_fix(filepath, content)

    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False

def aggressive_fix(filepath, content):
    """更激进的修复方法"""
    try:
        # 使用正则表达式修复明显的缩进问题
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 查找并修复过深的缩进
            if re.match(r'^\s{16,}', line):  # 16个或更多空格
                stripped = line.lstrip()
                # 减少到合理缩进（最多12个空格）
                fixed_lines.append('            ' + stripped)  # 12个空格
            elif re.match(r'^\s{12,}', line) and not line.strip().startswith('#'):
                stripped = line.lstrip()
                # 检查是否是def或class，如果是保持8空格缩进
                if stripped.startswith(('def ', 'class ', '@', 'async def')):
                    fixed_lines.append('        ' + stripped)  # 8个空格
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        # 验证修复后的语法
        try:
            ast.parse(fixed_content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        except SyntaxError:
            return False

    except Exception:
        return False

def main():
    """主函数"""
    import sys

    # 查找所有有语法错误的文件
    error_files = []
    test_dir = 'tests'

    for root, dirs, files in os.walk(test_dir):
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

    print(f"🔧 找到 {len(error_files)} 个语法错误文件")

    fixed_count = 0
    for filepath in error_files:
        print(f"  修复中: {os.path.relpath(filepath, 'tests')}")
        if fix_file_indentation(filepath):
            print(f"  ✅ 修复成功: {os.path.relpath(filepath, 'tests')}")
            fixed_count += 1
        else:
            print(f"  ❌ 修复失败: {os.path.relpath(filepath, 'tests')}")

    print("\n📊 修复总结:")
    print(f"   总错误文件: {len(error_files)}")
    print(f"   修复成功: {fixed_count}")
    print(f"   修复失败: {len(error_files) - fixed_count}")
    print(f"   成功率: {(fixed_count / len(error_files) * 100):.1f}%")

if __name__ == "__main__":
    main()