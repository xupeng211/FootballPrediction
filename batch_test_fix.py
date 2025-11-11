#!/usr/bin/env python3
"""
批量测试文件语法修复工具
专门修复常见的测试文件语法错误
"""

import re
from pathlib import Path


def fix_test_syntax(content):
    """修复测试文件中的常见语法错误"""

    # 1. 修复分离的字符串
    content = re.sub(
        r'f"([^"]*)"\s*\n\s*"([^"]*)"',
        r'f"\1\2"',
        content
    )

    # 2. 修复分离的函数调用
    content = re.sub(
        r'(\w+)\(\s*\n\s*([^\)]+)\)',
        r'\1(\2)',
        content
    )

    # 3. 修复缩进问题 - 标准化缩进
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 标准化缩进（4个空格）
        if line.startswith('\t'):
            line = '    ' + line[1:]
        # 修复多余空格导致的缩进错误
        line = line.rstrip()
        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def main():
    """主修复函数"""
    # 需要修复的测试文件
    test_files = [
        'tests/integration/test_auth_integration.py',
        'tests/integration/test_betting_ev_strategy.py',
        'tests/integration/test_ci_cd_basic.py',
        'tests/integration/test_data_integration.py',
        'tests/integration/test_ml_pipeline.py',
        'tests/integration/test_simple_auth.py',
        'tests/unit/utils/test_date_utils_enhanced_final.py'
    ]

    fixed_count = 0

    for test_file in test_files:
        path = Path(test_file)
        if not path.exists():
            continue


        try:
            with open(path, encoding='utf-8') as f:
                original_content = f.read()

            fixed_content = fix_test_syntax(original_content)

            if fixed_content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                fixed_count += 1
            else:
                pass

        except Exception:
            pass


    # 验证修复结果
    import ast

    for test_file in test_files:
        path = Path(test_file)
        if path.exists():
            try:
                with open(path, encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError:
                pass

if __name__ == "__main__":
    main()
