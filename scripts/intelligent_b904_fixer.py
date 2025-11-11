#!/usr/bin/env python3
"""
智能B904异常处理修复工具 - 区分HTTPException和其他异常
Intelligent B904 Exception Handling Fixer - Distinguish HTTPException and other exceptions
"""

import os
import re


def is_http_exception_line(line: str) -> bool:
    """检查是否是HTTPException相关的raise语句"""
    return 'raise HTTPException' in line

def is_simple_builtin_exception(line: str) -> bool:
    """检查是否是简单的内置异常，不需要from子句"""
    patterns = [
        r'raise ValueError\(',
        r'raise TypeError\(',
        r'raise AttributeError\(',
        r'raise KeyError\(',
        r'raise IndexError\(',
    ]
    return any(re.search(pattern, line) for pattern in patterns)

def fix_b904_intelligently(file_path: str) -> int:
    """智能修复文件中的B904错误"""

    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        fixes_count = 0

        # 逐行分析和修复
        for i, line in enumerate(lines):
            # 跳过HTTPException行，不需要from子句
            if is_http_exception_line(line):
                continue

            # 跳过简单的内置异常
            if is_simple_builtin_exception(line):
                continue

            # 查找其他raise语句在except块中的情况
            if 'raise ' in line and 'from e' not in line:
                # 检查前面的代码是否有except语句
                context_lines = lines[max(0, i-10):i]
                in_except_block = False

                for ctx_line in reversed(context_lines):
                    if ctx_line.strip().startswith('except'):
                        in_except_block = True
                        break
                    elif ctx_line.strip().startswith(('def ', 'class ', 'try:', 'if ', 'for ', 'while ')):
                        break

                if in_except_block:
                    # 只对特定类型的异常添加from子句
                    # 检查是否是自定义异常或需要保持异常链的情况
                    custom_exception_patterns = [
                        r'raise UserAlreadyExistsError\(',
                        r'raise UserNotFoundError\(',
                        r'raise InvalidCredentialsError\(',
                        r'raise DatabaseError\(',
                        r'raise CacheError\(',
                        r'raise PredictionError\(',
                        r'raise ModelNotFoundError\(',
                    ]

                    should_add_from = any(re.search(pattern, line) for pattern in custom_exception_patterns)

                    if should_add_from:
                        # 保留注释和格式
                        stripped_line = line.strip()
                        if '#' in stripped_line:
                            # 有注释的情况，不添加from子句以避免语法错误
                            continue

                        # 安全添加from e
                        lines[i] = line.rstrip() + ' from e\n'
                        fixes_count += 1

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return fixes_count

    except Exception:
        return 0

def main():
    """主函数"""

    # 需要修复的文件
    files_to_fix = [
        "src/api/betting_api.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/routes/user_management.py",
        "src/api/simple_auth.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        fixes = fix_b904_intelligently(file_path)
        total_fixes += fixes


if __name__ == "__main__":
    main()
