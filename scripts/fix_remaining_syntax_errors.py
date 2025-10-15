#!/usr/bin/env python3
"""
修复剩余的语法错误
"""

import re
from pathlib import Path

def fix_file_syntax(file_path: str, patterns: list):
    """修复文件中的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path}")
            return True
        else:
            print(f"  无需修复 {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False

def main():
    """修复所有剩余的语法错误"""

    print("开始修复剩余的语法错误...")

    # 定义修复模式
    fix_patterns = [
        # football.py
        (r'(\s+)(async def get_standings\([^)]+)) -> \1\2:', r'\1\2:'),

        # performance.py - 修复未终止的字符串
        (r'f"([^"]*?)(\s*#?.*)$', r'f"\1"\2'),

        # facades.py - 修复括号不匹配
        (r'strategies: Optional\[List\[str\]\] = None\)', r'strategies: Optional[List[str]] = None'),

        # 通用模式 - 修复方括号不匹配的类型注解
        (r': Optional\[Dict\[str, Any\] = None', r': Optional[Dict[str, Any]] = None'),
        (r': Dict\[str, Type\[Any, Adapter\] = {}', r': Dict[str, Type[Adapter]] = {}'),
    ]

    # 修复各个文件
    files_to_fix = [
        'src/adapters/football.py',
        'src/api/performance.py',
        'src/api/facades.py'
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if fix_file_syntax(file_path, fix_patterns):
            fixed_count += 1

    print(f"\n修复完成！共修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果：")
    for file_path in files_to_fix:
        try:
            import ast
            with open(file_path, 'r') as f:
                content = f.read()
            ast.parse(content)
            print(f"✅ {file_path}: 语法正确")
        except SyntaxError as e:
            print(f"❌ {file_path}: Line {e.lineno} - {e.msg}")

if __name__ == "__main__":
    main()
