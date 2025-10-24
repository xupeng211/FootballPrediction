#!/usr/bin/env python3
"""
缩进错误自动修复工具
批量修复Python代码中的缩进问题
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import json


def fix_indentation_errors(file_path: str) -> Tuple[bool, str]:
    """
    修复单个文件的缩进错误

    Returns:
        Tuple[bool, str]: (是否修复成功, 修复描述)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 检查是否真的有语法错误
        try:
            ast.parse(original_content)
            return True, "没有语法错误"
        except SyntaxError:
            pass  # 继续修复

        # 应用常见的修复模式
        fixed_content = apply_indentation_fixes(original_content)

        # 验证修复后的代码
        try:
            ast.parse(fixed_content)
            # 修复成功，写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, "缩进错误修复成功"
        except SyntaxError as e:
            return False, f"修复失败: {e}"

    except Exception as e:
        return False, f"读取文件失败: {e}"


def apply_indentation_fixes(content: str) -> str:
    """
    应用多种缩进修复策略
    """
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 跳过空行和注释行
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 修复常见的缩进问题
        fixed_line = fix_line_indentation(line, i, lines)
        fixed_lines.append(fixed_line)

    return '\n'.join(fixed_lines)


def fix_line_indentation(line: str, line_num: int, all_lines: List[str]) -> str:
    """
    修复单行的缩进问题
    """
    stripped = line.strip()

    # 如果行以def开头且有docstring在同一行，需要特殊处理
    if stripped.startswith('def ') and '"""' in stripped:
        # 检查是否是类中的方法
        prev_line = all_lines[line_num - 1] if line_num > 0 else ""

        # 如果上一行是类的__init__方法或者是空行后的第一个def，这应该是类方法
        if should_be_class_method(prev_line, line_num, all_lines):
            # 分离方法定义和docstring
            parts = stripped.split('"""', 1)
            if len(parts) == 2:
                method_def = parts[0].strip()
                docstring_part = '"""' + parts[1]
                return f"    {method_def}\n        {docstring_part}"

    # 修复方法定义后缺少缩进的问题
    if stripped.startswith('def ') and not line.startswith('    '):
        # 检查是否应该在类中
        if is_in_class_context(line_num, all_lines):
            return f"    {stripped}"

    # 修复类定义后缺少缩进的问题
    if stripped.startswith('class ') and not line.startswith('    '):
        # 检查是否应该在模块级别
        if is_nested_class(line_num, all_lines):
            return f"    {stripped}"

    # 修复变量赋值后缺少缩进的问题
    if ('=' in stripped and
        not stripped.startswith('def ') and
        not stripped.startswith('class ') and
        not line.startswith('    ') and
        is_in_method_context(line_num, all_lines)):
        return f"        {stripped}"

    # 修复其他常见的缩进问题
    return line


def should_be_class_method(prev_line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    判断是否应该是类方法
    """
    # 如果上一行是__init__方法或者是类定义后的空行
    if ('def __init__' in prev_line or
        'class ' in prev_line or
        (prev_line.strip() == '' and line_num > 1 and
         'class ' in all_lines[line_num - 2])):
        return True
    return False


def is_in_class_context(line_num: int, all_lines: List[str]) -> bool:
    """
    判断当前行是否在类上下文中
    """
    # 向上查找最近的类定义
    for i in range(line_num - 1, -1, -1):
        line = all_lines[i].strip()
        if line.startswith('class '):
            return True
        elif line.startswith('def ') and not line.startswith('    '):
            return False  # 遇到模块级函数，不在类中
    return False


def is_nested_class(line_num: int, all_lines: List[str]) -> bool:
    """
    判断是否是嵌套类
    """
    # 向上查找，检查是否在另一个类中
    indent_level = 0
    for i in range(line_num - 1, -1, -1):
        line = all_lines[i]
        if line.strip().startswith('class '):
            return indent_level > 0
        elif line.strip():  # 非空行
            if line.startswith('    '):
                indent_level = max(indent_level, len(line) - len(line.lstrip()))
            else:
                indent_level = 0
    return False


def is_in_method_context(line_num: int, all_lines: List[str]) -> bool:
    """
    判断当前行是否在方法上下文中
    """
    # 向上查找最近的方法定义
    for i in range(line_num - 1, -1, -1):
        line = all_lines[i].strip()
        if line.startswith('def ') and i > 0:
            prev_line = all_lines[i - 1]
            # 如果方法定义有4个空格缩进，说明在类中
            if prev_line.startswith('    def '):
                return True
        elif line.startswith('class '):
            return False
    return False


def batch_fix_files(file_paths: List[str]) -> Dict[str, Tuple[bool, str]]:
    """
    批量修复文件
    """
    results = {}

    for file_path in file_paths:
        print(f"修复 {file_path}...")
        success, message = fix_indentation_errors(file_path)
        results[file_path] = (success, message)

        if success:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")

    return results


def main():
    print("🔧 开始批量修复缩进错误...")

    # 读取错误报告
    with open('syntax_errors_report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)

    # 获取需要修复的文件列表
    files_to_fix = [file_path for file_path in report['categories']['indentation_errors']
                   if file_path not in ['src/data/quality/anomaly_detector.py',
                                       'src/data/quality/exception_handler.py',
                                       'src/data/quality/exception_handler_mod/__init__.py',
                                       'src/models/common_models.py']]  # 排除已修复的文件

    print(f"\n📝 需要修复的文件数: {len(files_to_fix)}")

    # 批量修复
    results = batch_fix_files(files_to_fix)

    # 统计结果
    success_count = sum(1 for success, _ in results.values() if success)
    failed_files = [path for path, (success, _) in results.items() if not success]

    print("\n📊 修复结果:")
    print(f"   成功: {success_count}/{len(files_to_fix)}")
    print(f"   失败: {len(failed_files)}")

    if failed_files:
        print("\n❌ 修复失败的文件:")
        for file_path in failed_files:
            print(f"   - {file_path}: {results[file_path][1]}")

    # 保存修复报告
    fix_report = {
        'total_files': len(files_to_fix),
        'success_count': success_count,
        'failed_count': len(failed_files),
        'failed_files': failed_files,
        'results': {path: {"success": success, "message": msg}
                   for path, (success, msg) in results.items()}
    }

    with open('indentation_fixes_report.json', 'w', encoding='utf-8') as f:
        json.dump(fix_report, f, indent=2, ensure_ascii=False)

    print("\n📄 修复报告已保存到: indentation_fixes_report.json")

    return fix_report


if __name__ == "__main__":
    main()