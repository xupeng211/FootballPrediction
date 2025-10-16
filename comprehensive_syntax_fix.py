#!/usr/bin/env python3
"""
全面的语法错误修复脚本
Comprehensive Syntax Error Fix Script

处理各种类型的语法错误
"""

import ast
import os
import re
from typing import List, Tuple, Optional

def analyze_syntax_error(file_path: str) -> Optional[Tuple[str, int, str]]:
    """分析语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return None
    except SyntaxError as e:
        return (e.msg.lower(), e.lineno, e.text)
    except Exception as e:
        return (str(e).lower(), None, "")

def fix_invalid_syntax_patterns(content: str) -> str:
    """修复常见的无效语法模式"""
    original = content

    # 1. 修复文档字符串格式错误
    content = re.sub(r'^(\s*)"""(\w+)"""', r'\1"""\2"""', content, flags=re.MULTILINE)
    content = re.sub(r'^(\s*)"""(\w+)\n', r'\1"""\n\2\n', content, flags=re.MULTILINE)

    # 2. 修复未闭合的三引号
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检查三引号
        if '"""' in line and not line.strip().endswith('"""'):
            # 检查是否是文档字符串开始
            if i > 0 and not lines[i-1].strip().endswith('"""'):
                # 查找闭合的三引号
                j = i + 1
                found = False
                while j < len(lines):
                    if '"""' in lines[j]:
                        found = True
                        break
                    j += 1
                if not found:
                    # 添加闭合的三引号
                    lines[i] = line.replace('"""', '"""') + '\n"""'
        i += 1
    content = '\n'.join(lines)

    # 3. 修复裸露的中文文本（应该是文档字符串）
    content = re.sub(r'^([^\n"\'#])([\u4e00-\u9fff].*)$', r'"""\n\1\n"""', content, flags=re.MULTILINE)

    # 4. 修复参数列表中缺少逗号的问题
    content = re.sub(r'(\w+):\s*([^,\n)]+)\s*(\w+:)', r'\1: \2,\n    \3', content)

    # 5. 修复类型注解中的括号不匹配
    # Optional[List[str] = None -> Optional[List[str]] = None
    content = re.sub(r'Optional\[([^\]]+)\s*=\s*None\]', r'Optional[\1] = None', content)
    content = re.sub(r'List\[([^\]]+)\s*=\s*None\]', r'List[\1] = None', content)
    content = re.sub(r'Dict\[([^\]]+)\s*=\s*None\]', r'Dict[\1] = None', content)

    # 6. 修复函数定义中的参数类型问题
    content = re.sub(r'def\s+(\w+)\s*\(\s*([^):]+):', r'def \1(\2):', content)

    # 7. 修复类定义后的文档字符串问题
    content = re.sub(r'class\s+(\w+):\s*\n\s*("""[^"]*""")\s*\n', r'class \1):\n    \2\n\n', content)

    return content

def fix_parameter_errors(content: str) -> str:
    """修复参数定义错误"""
    # 修复函数参数中的引号问题
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 修复函数参数行
        if 'def ' in line or 'async def ' in line:
            # 移除参数名中的引号
            line = re.sub(r'"([^"]+)":\s*([^,=:\)]+)', r'\1: \2', line)
            # 修复类型注解
            line = re.sub(r'"([^"]+)":\s*([^:]+):', r'\1\2:', line)
            # 修复默认值
            line = re.sub(r'=:\s*([^,\n)]+)', r'= \1', line)
            lines[i] = line

    return '\n'.join(lines)

def fix_docstring_errors(content: str) -> str:
    """修复文档字符串错误"""
    # 找到所有未闭合的文档字符串
    lines = content.split('\n')
    in_docstring = False
    docstring_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检查三引号
        if '"""' in line:
            if not in_docstring:
                # 开始文档字符串
                in_docstring = True
                docstring_start = i
            else:
                # 结束文档字符串
                in_docstring = False

    # 如果有未闭合的文档字符串，添加闭合
    if in_docstring:
        lines.append('"""')

    return '\n'.join(lines)

def fix_import_errors(content: str) -> str:
    """修复导入错误"""
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # 修复相对导入
        if line.strip().startswith('from .') and 'import' in line:
            parts = line.split(' import ')
            if len(parts) == 2:
                module = parts[0].replace('from ', '')
                imports = parts[1]
                # 检查导入项是否正确
                imports = imports.replace(', ', ', ')
                lines[i] = f'{module} import {imports}'

    return '\n'.join(lines)

def fix_file(file_path: str) -> bool:
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用各种修复
        content = fix_invalid_syntax_patterns(content)
        content = fix_parameter_errors(content)
        content = fix_docstring_errors(content)
        content = fix_import_errors(content)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")

    return False

def main():
    """主函数"""
    error_files = []

    # 扫描所有Python文件
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                error_info = analyze_syntax_error(file_path)
                if error_info:
                    error_files.append((file_path, error_info))

    print(f"找到 {len(error_files)} 个有语法错误的文件")

    # 修复文件
    fixed_count = 0
    for file_path, (msg, line, text) in error_files:
        if fix_file(file_path):
            fixed_count += 1
            rel_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
            print(f"✓ 修复: {rel_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    remaining_errors = 0
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError:
                    remaining_errors += 1

    print(f"剩余语法错误文件: {remaining_errors} 个")

if __name__ == "__main__":
    main()