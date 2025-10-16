#!/usr/bin/env python3
"""
修复core/config.py的缩进问题
"""

import re
from pathlib import Path

def fix_config_py():
    """修复config.py的缩进问题"""
    file_path = Path('src/core/config.py')
    content = file_path.read_text(encoding='utf-8')

    # 修复第296-304行的问题
    # 将错误的缩进修复
    content = re.sub(
        r'if not value: return \[\],\n    try:\n                parsed',
        r'if not value:\n                return []\n            try:\n                parsed',
        content
    )

    # 修复try-except的缩进
    content = re.sub(
        r'except json\.JSONDecodeError:\n                pass',
        r'            except json.JSONDecodeError:\n                pass',
        content
    )

    # 修复其他缩进问题
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # 特殊处理第296行
        if 'if not value: return [],' in line:
            fixed_lines.append('            if not value:')
            fixed_lines.append('                return []')
        # 特殊处理第297行
        elif i > 0 and 'try:' in line and lines[i-1].strip().endswith('return []'):
            fixed_lines.append('            try:')
        # 修复try-except块
        elif 'except json.JSONDecodeError:' in line and line.startswith('                '):
            fixed_lines.append('            except json.JSONDecodeError:')
        # 修复return语句的缩进
        elif 'return [item.strip()' in line and line.startswith('            '):
            fixed_lines.append('            return [item.strip() for item in value.split(",") if item.strip()]')
        else:
            fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # 写回文件
    file_path.write_text(content, encoding='utf-8')
    print("✓ 修复了 core/config.py 的缩进问题")

    # 验证语法
    try:
        compile(content, str(file_path), 'exec')
        print("✓ core/config.py 语法检查通过")
        return True
    except SyntaxError as e:
        print(f"✗ 仍有语法错误: {e}")
        return False

if __name__ == '__main__':
    fix_config_py()