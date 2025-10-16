#!/usr/bin/env python3
"""
系统性修复所有语法错误
"""

import os
import re
import ast
from pathlib import Path

def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 1. 修复类型注解中缺失的括号
        content = re.sub(r':\s*Optional\[Dict\[str,\s*Any\](?!\])\s*$',
                        r': Optional[Dict[str, Any]]', content)
        content = re.sub(r':\s*List\[Dict\[str,\s*Any\](?!\])\s*$',
                        r': List[Dict[str, Any]]', content)
        content = re.sub(r':\s*Dict\[str,\s*Any\](?!\])\s*$',
                        r': Dict[str, Any]]', content)

        # 2. 修复未闭合的三引号字符串
        lines = content.split('\n')
        in_triple_string = False
        quote_char = None

        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                # 检查是否有未闭合的三引号
                if not in_triple_string:
                    if line.count('"""') % 2 == 1:
                        in_triple_string = True
                        quote_char = '"""'
                    elif line.count("'''") % 2 == 1:
                        in_triple_string = True
                        quote_char = "'''"
                else:
                    if quote_char in line:
                        in_triple_string = False
                        quote_char = None

        # 如果最后仍有未闭合的三引号，添加闭合
        if in_triple_string:
            content = content.rstrip() + '\n' + quote_char

        # 3. 修复未闭合的括号（简化版）
        # 这是一个复杂的问题，这里只处理一些简单情况

        # 4. 修复未闭合的字符串字面量
        # 检查单行字符串
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # 跳过注释行
            if line.strip().startswith('#'):
                continue

            # 检查未闭合的字符串
            # 计算引号数量
            single_quotes = line.count("'") - line.count("\\'")
            double_quotes = line.count('"') - line.count('\\"')

            # 如果是字符串定义行且引号不匹配
            if ('"' in line or "'" in line) and (single_quotes % 2 == 1 or double_quotes % 2 == 1):
                # 尝试修复
                if single_quotes % 2 == 1 and not line.rstrip().endswith("'"):
                    lines[i] = line.rstrip() + "'"
                elif double_quotes % 2 == 1 and not line.rstrip().endswith('"'):
                    lines[i] = line.rstrip() + '"'

        content = '\n'.join(lines)

        # 5. 修复冒号缺失（简单情况）
        content = re.sub(r'(\))\s*$', r'\1:', content)

        # 6. 修复赋值表达式错误（将 = 改为 == 在某些上下文中）
        # 这需要更复杂的解析，暂时跳过

        # 检查语法是否正确
        try:
            ast.parse(content)
            if content != original:
                print(f"✓ 修复: {file_path}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        except SyntaxError as e:
            # 如果还有语法错误，尝试更激进的修复
            print(f"✗ 仍有错误: {file_path} - {e}")

            # 尝试添加缺失的括号
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # 如果行包含函数定义且类型注解不完整
                if 'def ' in line and '->' in line and ']' not in line:
                    if 'Optional[Dict[str, Any]' in line:
                        lines[i] = line + ']'
                    elif 'List[Dict[str, Any]' in line:
                        lines[i] = line + ']'
                    elif 'Dict[str, Any]' in line:
                        lines[i] = line + ']'

            content = '\n'.join(lines)

            try:
                ast.parse(content)
                print(f"✓ 二次修复: {file_path}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            except SyntaxError:
                print(f"✗ 无法修复: {file_path}")
                return False

    except Exception as e:
        print(f"✗ 处理文件出错 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("开始修复语法错误...")

    # 扫描所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    fixed_count = 0
    error_count = 0

    for file_path in python_files:
        if fix_file_syntax(file_path):
            fixed_count += 1
        else:
            error_count += 1

    print(f"\n修复完成:")
    print(f"  成功修复: {fixed_count} 个文件")
    print(f"  仍有错误: {error_count} 个文件")

if __name__ == "__main__":
    main()
