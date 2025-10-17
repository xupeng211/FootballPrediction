#!/usr/bin/env python3
"""
修复 string_utils 测试文件的缩进问题
"""

import re
from pathlib import Path


def fix_string_utils_test():
    """修复 string_utils 测试文件的缩进"""
    file_path = Path('tests/unit/utils/test_string_utils.py')

    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复类和方法的缩进
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 修复类定义
        if stripped.startswith('class Test'):
            fixed_lines.append(stripped)
            continue

        # 修复方法定义
        if stripped.startswith('def test_') or stripped.startswith('"""'):
            # 添加 4 个空格缩进
            fixed_lines.append('    ' + stripped)
            continue

        # 修复其他内容（如果不在类中）
        if line and not line.startswith(' ') and not line.startswith('\t'):
            # 可能是模块级函数
            if stripped.startswith('def ') or stripped.startswith('from ') or stripped.startswith('import '):
                fixed_lines.append(line)
            else:
                # 添加适当的缩进
                if any(keyword in stripped for keyword in ['assert', 'with', 'for', 'if', 'return', 'result =', 'text =', 'name =']):
                    fixed_lines.append('        ' + stripped)  # 8 个空格（方法内）
                else:
                    fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # 重新修复方法内的内容
    lines = fixed_lines
    fixed_lines = []
    in_method = False
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测方法定义
        if re.match(r'\s*def test_', line):
            in_method = True
            indent_level = len(line) - len(line.lstrip())
            fixed_lines.append(line)
            continue

        # 检测类定义
        if stripped.startswith('class '):
            in_method = False
            fixed_lines.append(line)
            continue

        # 在方法内部
        if in_method and stripped:
            current_indent = len(line) - len(line.lstrip())

            # 如果是文档字符串或特殊行
            if stripped.startswith('"""') or stripped.startswith('with pytest.raises'):
                # 应该有 8 个空格缩进
                if current_indent != 8:
                    fixed_lines.append('        ' + stripped)
                else:
                    fixed_lines.append(line)
            # 如果是 assert 或其他代码
            elif any(stripped.startswith(x) for x in ['assert', 'result', 'text', 'name', 'for', 'with ', 'return']):
                # 应该有 8 个空格缩进
                if current_indent != 8:
                    fixed_lines.append('        ' + stripped)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # 写回文件
    content = '\n'.join(fixed_lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"修复完成: {file_path}")


if __name__ == '__main__':
    fix_string_utils_test()