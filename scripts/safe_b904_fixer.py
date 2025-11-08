#!/usr/bin/env python3
"""
安全的B904异常处理修复工具 - 专门处理HTTPException
Safe B904 Exception Handling Fixer - Specifically for HTTPException
"""

import os
import re


def fix_http_exception_b904_safely(file_path: str) -> int:
    """安全地修复文件中的HTTPException B904错误"""

    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_count = 0

        # 模式1: 修复简单的raise HTTPException，不添加from子句（因为HTTPException不需要）
        pattern1 = r'raise HTTPException\(([^)]+)\)\s*from e'
        content = re.sub(pattern1, r'raise HTTPException(\1)', content)
        if content != original_content:
            fixes_count += len(re.findall(pattern1, original_content))

        original_content = content

        # 模式2: 修复其他异常的raise语句，添加from e
        # 这个模式更保守，只处理明确的异常类型
        pattern2 = r'raise (\w+)\(([^)]+)\)\s*$'
        matches = re.findall(pattern2, content, re.MULTILINE)

        for exception_name, exception_args in matches:
            # 跳过HTTPException，因为它是HTTP异常，不需要from子句
            if exception_name == 'HTTPException':
                continue

            # 跳过ValueError等内置异常，它们通常不需要from子句
            if exception_name in ['ValueError', 'TypeError', 'AttributeError', 'KeyError', 'IndexError']:
                continue

            # 查找这个异常的上下文，如果在try-except块中，则添加from e
            exception_pattern = rf'(\s+?)raise {exception_name}\({re.escape(exception_args)}\)(\s*$)'

            def add_from_if_in_except(match):
                indent = match.group(1)
                ending = match.group(2)

                # 检查前面是否有except语句
                lines_before = content[:match.start()].split('\n')
                if len(lines_before) >= 2:
                    last_two_lines = lines_before[-2:]
                    for line in last_two_lines:
                        if 'except' in line and ('Exception' in line or 'Error' in line):
                            return f'{indent}raise {exception_name}({exception_args}) from e{ending}'

                return match.group(0)

            content = re.sub(exception_pattern, add_from_if_in_except, content, flags=re.MULTILINE)

        # 重新计算修复数量
        final_content = content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        return fixes_count

    except Exception:
        return 0

def main():
    """主函数"""

    # 要修复的API文件列表
    api_files = [
        "src/api/betting_api.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/routes/user_management.py",
        "src/api/simple_auth.py"
    ]

    total_fixes = 0

    for file_path in api_files:
        fixes = fix_http_exception_b904_safely(file_path)
        total_fixes += fixes


if __name__ == "__main__":
    main()
