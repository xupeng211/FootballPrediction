#!/usr/bin/env python3
"""
继续修复语法错误
"""

import re
from pathlib import Path

def main():
    """主函数"""
    print("继续修复语法错误...")

    fixed_count = 0

    # 重点修复 utils 目录的文件
    for py_file in Path('src/utils').rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 修复缩进错误
            lines = content.split('\n')
            new_lines = []

            for line in lines:
                # 修复常见的缩进问题
                if line.strip().startswith(('if ', 'for ', 'while ', 'with ', 'try:', 'except', 'elif ')):
                    # 检查下一行是否需要缩进
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1]
                        if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                            if next_line.strip() and not next_line.strip().startswith('#'):
                                # 修复缩进
                                lines[idx + 1] = '    ' + next_line.strip()

                new_lines.append(line)

            content = '\n'.join(new_lines)

            # 修复括号问题
            content = content.replace('password_bytes = (', 'password_bytes = (')
            content = content.replace('hashed_bytes = (', 'hashed_bytes = (')

            # 修复未闭合的三引号
            if '"""' in content:
                quote_count = content.count('"""')
                if quote_count % 2 != 0:
                    content = content.rstrip() + '\n"""'

            if content != original:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"✓ 修复: {py_file}")

        except Exception as e:
            print(f"✗ 错误: {py_file} - {e}")

    print(f"\n修复完成！修复了 {fixed_count} 个文件")

if __name__ == '__main__':
    main()