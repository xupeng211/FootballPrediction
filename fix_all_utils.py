#!/usr/bin/env python3
"""
修复 utils 目录的所有语法错误
"""

import ast
from pathlib import Path

def fix_utils_syntax():
    """修复 utils 目录的语法错误"""
    print("修复 utils 目录的语法错误...")

    utils_files = list(Path('src/utils').rglob('*.py'))
    fixed_count = 0

    for py_file in utils_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试解析 AST
            try:
                ast.parse(content)
                print(f"✓ 正常: {py_file}")
                continue
            except SyntaxError:
                print(f"⚠ 需要修复: {py_file}")

            # 备份原文件
            original = content

            # 修复多行括号内的缩进问题
            lines = content.split('\n')
            fixed_lines = []
            in_multiline_paren = False
            paren_indent = 0

            for line in lines:
                stripped = line.strip()

                # 检查是否开始多行括号
                if '(' in line and ')' not in line and line.count('(') > line.count(')'):
                    in_multiline_paren = True
                    paren_indent = len(line) - len(line.lstrip())

                # 修复多行括号内的内容
                if in_multiline_paren:
                    # 如果是括号内的内容且没有正确缩进
                    if stripped and not line.startswith(' ' * (paren_indent + 4)) and not stripped.startswith('#'):
                        # 添加适当的缩进
                        line = ' ' * (paren_indent + 4) + stripped

                # 检查是否结束多行括号
                if ')' in line and line.count(')') >= line.count('('):
                    in_multiline_paren = False

                # 修复其他常见的语法问题
                # 1. 修复未闭合的括号
                if stripped.endswith('(') and not line.endswith(','):
                    # 下一行需要缩进
                    pass

                fixed_lines.append(line)

            content = '\n'.join(fixed_lines)

            # 修复特定的错误模式
            # 1. 修复 pattern = () 模式
            import re
            content = re.sub(r'pattern = \(\s*\n((?:\s+r".*"\n)*)\s*\)', 
                           lambda m: 'pattern = (\n' + m.group(1) + '    )', 
                           content)

            # 2. 修复 password_bytes = () 模式
            content = re.sub(r'password_bytes = \(\s*\n((?:\s+.*\n)*)\s*\)',
                           lambda m: 'password_bytes = (\n' + m.group(1) + '        )',
                           content)

            # 3. 修复 hashed_bytes = () 模式
            content = re.sub(r'hashed_bytes = \(\s*\n((?:\s+.*\n)*)\s*\)',
                           lambda m: 'hashed_bytes = (\n' + m.group(1) + '        )',
                           content)

            # 4. 修复未闭合的三引号
            if '"""' in content:
                quote_count = content.count('"""')
                if quote_count % 2 != 0:
                    content = content.rstrip() + '\n"""'

            # 验证修复结果
            try:
                ast.parse(content)
                if content != original:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
                    print(f"✓ 修复: {py_file}")
                else:
                    print(f"⚠ 未改变: {py_file}")
            except SyntaxError as e:
                print(f"✗ 仍有错误: {py_file} - {e}")

        except Exception as e:
            print(f"✗ 处理失败: {py_file} - {e}")

    print(f"\n修复完成！修复了 {fixed_count} 个文件")

if __name__ == '__main__':
    fix_utils_syntax()
