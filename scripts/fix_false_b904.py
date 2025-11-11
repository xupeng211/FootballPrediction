#!/usr/bin/env python3
"""
修复不在except块中被错误修改的HTTPException语句
"""

import re
from pathlib import Path


def fix_false_b904(content):
    """修复错误的B904修复"""
    lines = content.split('\n')
    result = []
    i = 0
    in_except_block = False

    while i < len(lines):
        line = lines[i]

        # 检测except子句
        if re.match(r'\s*except\s+.+', line):
            in_except_block = True
            result.append(line)
            i += 1
            continue

        # 检测新的代码块开始，结束except块
        if (in_except_block and
            line.strip() and
            not line.startswith(' ') and
            not line.startswith('\t')):
            in_except_block = False

        # 修复不在except块中的HTTPException
        if not in_except_block and 'HTTPException(' in line:
            # 检查这一行是否是raise语句并且格式错误
            if re.match(r'\s*raise\s+HTTPException\([^)]*$', line):
                # 这是一个单行的HTTPException，需要格式化
                indent = len(line) - len(line.lstrip())
                # 提取参数
                match = re.search(r'HTTPException\((.*)', line)
                if match:
                    args = match.group(1)
                    result.append(' ' * indent + 'raise HTTPException(')
                    result.append(' ' * (indent + 4) + args)
                    result.append(' ' * indent + ')')
                    i += 1
                    continue

        result.append(line)
        i += 1

    return '\n'.join(result)

def main():
    """主函数"""

    fixed_files = 0
    for py_file in Path("src").rglob("*.py"):
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 检查是否有问题
            if 'raise HTTPException(... from e' in content:
                fixed_content = fix_false_b904(content)

                if content != fixed_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    fixed_files += 1
        except Exception:
            pass


if __name__ == "__main__":
    main()
