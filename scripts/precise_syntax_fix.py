#!/usr/bin/env python3
"""
精确语法修复工具
使用 AST 和 tokenize 模块精确定位并修复语法错误
"""

import os
import ast
import tokenize
import io
import re
from pathlib import Path
from typing import List, Tuple, Optional

def check_syntax(file_path: str) -> Tuple[bool, Optional[SyntaxError]]:
    """检查文件语法并返回错误信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, e
    except Exception as e:
        return False, None

def fix_unclosed_string(content: str, error_line: int, error_col: int) -> str:
    """修复未闭合的字符串"""
    lines = content.split('\n')
    if error_line - 1 < len(lines):
        line = lines[error_line - 1]

        # 查找字符串开始位置
        in_string = False
        string_start = 0
        string_char = None

        for i, char in enumerate(line):
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_start = i
                    string_char = char
            else:
                if char == string_char:
                    in_string = False

        # 如果字符串未闭合，添加闭合引号
        if in_string and string_char:
            # 检查行尾是否有逗号
            if line.strip().endswith(','):
                lines[error_line - 1] = line[:-1] + string_char + ','
            else:
                lines[error_line - 1] = line + string_char

            print(f"  修复未闭合的{string_char}字符串在第{error_line}行")

    return '\n'.join(lines)

def fix_bracket_mismatch(content: str, error_line: int, error_col: int) -> str:
    """修复括号不匹配"""
    lines = content.split('\n')
    if error_line - 1 < len(lines):
        line = lines[error_line - 1]

        # 常见的括号不匹配模式
        patterns = [
            # List[Dict[str, Any]) -> List[Dict[str, Any]]
            (r'List\[Dict\[str, Any\]\)', r'List[Dict[str, Any]]'),
            # Optional[Dict[str, Any]) -> Optional[Dict[str, Any]]
            (r'Optional\[Dict\[str, Any\]\)', r'Optional[Dict[str, Any]]'),
            # (data: List[Dict[str, Any]) -> (data: List[Dict[str, Any]])
            (r'\(([^)]*List\[Dict\[str, Any\])\)', r'(\1])'),
            # List[Dict[str, Any] -> List[User]: -> List[Dict[str, Any]]) -> List[User]:
            (r'List\[Dict\[str, Any\]\s*->\s*List\[\w+\]:',
             r'List[Dict[str, Any]]) -> List[\1]:'),
            # 函数参数中的错误
            (r'->\s*Dict\[str, Any\s*$', r'-> Dict[str, Any]:'),
            # Dict[str, Any] -> Dict[str, Any]]:
            (r'Dict\[str, Any\]\s*->\s*Dict\[str, Any\]:',
             r'Dict[str, Any]]) -> Dict[str, Any]:'),
        ]

        original_line = line
        for pattern, replacement in patterns:
            if re.search(pattern, line):
                line = re.sub(pattern, replacement, line)
                break

        if line != original_line:
            lines[error_line - 1] = line
            print(f"  修复括号不匹配在第{error_line}行")

    return '\n'.join(lines)

def fix_specific_errors(content: str, file_path: str, error: SyntaxError) -> str:
    """修复特定的语法错误"""
    error_msg = error.msg.lower()

    # 根据错误类型选择修复方法
    if 'unterminated string literal' in error_msg:
        content = fix_unclosed_string(content, error.lineno, error.offset)
    elif 'does not match opening parenthesis' in error_msg or 'mismatch' in error_msg:
        content = fix_bracket_mismatch(content, error.lineno, error.offset)
    elif 'leading zeros' in error_msg:
        # 修复前导零问题（主要在迁移文件中）
        lines = content.split('\n')
        if error.lineno - 1 < len(lines):
            line = lines[error.lineno - 1]
            # 修复八进制字面量
            if 'Revision ID:' in line:
                line = re.sub(r'(Revision ID:\s*)0+(\d+)', r'\1\2', line)
                lines[error.lineno - 1] = line
                print(f"  修复前导零问题在第{error.lineno}行")
        content = '\n'.join(lines)
    elif 'invalid syntax' in error_msg:
        # 处理特定的无效语法
        if file_path.endswith('cqrs/application.py'):
            # 这个文件可能是注释问题
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == 'CQRS Application Services':
                    lines[i] = '"""CQRS Application Services"""'
                    print(f"  修复注释格式在第{i+1}行")
                    break
            content = '\n'.join(lines)

    return content

def fix_all_errors_in_file(file_path: str) -> bool:
    """修复文件中的所有错误"""
    # 首先读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查语法
    is_valid, error = check_syntax(file_path)

    # 多次尝试修复，直到没有错误或没有改进
    max_attempts = 10
    attempts = 0

    while not is_valid and attempts < max_attempts:
        if error:
            print(f"  尝试修复: {error.msg}")
            content = fix_specific_errors(content, file_path, error)

            # 保存修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 再次检查
            is_valid, error = check_syntax(file_path)
            attempts += 1
        else:
            break

    return is_valid

def main():
    """主函数"""
    print("开始精确语法修复...")

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # 找出有语法错误的文件
    error_files = []
    for file_path in python_files:
        is_valid, _ = check_syntax(file_path)
        if not is_valid:
            error_files.append(file_path)

    print(f"\n发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("✓ 所有文件语法都正确！")
        return

    # 修复每个文件
    fixed_count = 0
    failed_files = []

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            if fix_all_errors_in_file(file_path):
                print(f"  ✓ 修复成功")
                fixed_count += 1
            else:
                print(f"  ✗ 修复失败")
                failed_files.append(file_path)
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            failed_files.append(file_path)

    # 总结
    print(f"\n修复完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")
    print(f"- 修复失败: {len(failed_files)}")

    if failed_files:
        print(f"\n以下文件仍需手动修复:")
        for file_path in failed_files[:20]:
            print(f"  - {file_path}")
        if len(failed_files) > 20:
            print(f"  ... 还有 {len(failed_files) - 20} 个文件")

        # 生成详细的错误报告
        print("\n生成错误详情报告...")
        with open('syntax_errors_details.txt', 'w') as f:
            f.write("语法错误详情报告\n")
            f.write("=" * 50 + "\n\n")

            for file_path in failed_files:
                f.write(f"文件: {file_path}\n")
                is_valid, error = check_syntax(file_path)
                if error:
                    f.write(f"  错误: 第{error.lineno}行: {error.msg}\n")
                    f.write(f"  位置: 列{error.offset}\n")
                f.write("\n")

        print("已生成 syntax_errors_details.txt 文件")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")

if __name__ == "__main__":
    main()
