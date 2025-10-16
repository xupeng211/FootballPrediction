#!/usr/bin/env python3
"""简单的语法错误修复脚本"""

import os
import re
from pathlib import Path

def fix_file_syntax(file_path):
    """修复单个文件的常见语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 1. 修复类定义中的多余右括号
        # 例如: class MyClass): -> class MyClass:
        content = re.sub(r'^\s*class\s+(\w+)\):\s*$', r'class \1:', content, flags=re.MULTILINE)

        # 2. 修复函数定义中的参数类型错误
        # 例如: def func(param): Type) -> ReturnType: -> def func(param: Type) -> ReturnType:
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\)\s*->\s*([^:]+):',
                        r'def \1(\2: \3) -> \4:', content)

        # 3. 修复更简单的情况: def func(param): Type) -> ReturnType:
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\)\s*->\s*([^:\s]+)\s*:',
                        r'def \1(\2: \3) -> \4:', content)

        # 4. 修复只有一个参数的情况
        # 例如: def func(param): Type): -> def func(param: Type):
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\)\s*:',
                        r'def \1(\2: \3):', content)

        # 5. 修复函数参数列表中的错误
        # 例如: def func(data): dict, fields): list -> def func(data: dict, fields: list)
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\),\s*([^)]+?)\)\s*:',
                        r'def \1(\2: \3, \4):', content)

        # 6. 修复中文逗号为英文逗号
        content = content.replace('，', ',')

        # 7. 修复未闭合的三引号字符串
        lines = content.split('\n')
        new_lines = []
        in_string = False
        string_type = None

        for line in lines:
            # 检查三引号
            if '"""' in line:
                count = line.count('"""')
                if not in_string:
                    if count % 2 == 1:
                        in_string = True
                        string_type = '"""'
                else:
                    if count % 2 == 1:
                        in_string = False
                        string_type = None

            new_lines.append(line)

        # 如果文件结束时字符串未闭合，添加闭合
        if in_string:
            new_lines.append(string_type)

        content = '\n'.join(new_lines)

        # 8. 修复类方法中的self参数类型错误
        # 例如: def method(self): Type) -> Type: -> def method(self: Type) -> Type:
        content = re.sub(r'def\s+(\w+)\(self\)\s*:\s*([^)]+?)\)\s*->\s*([^:]+):',
                        r'def \1(self: \2) -> \3:', content)

        # 写回文件
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

    return False

def verify_syntax(file_path):
    """验证文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), str(file_path), 'exec')
        return True
    except SyntaxError:
        return False

def main():
    """主函数"""
    src_dir = Path('src')
    fixed_count = 0
    still_error_count = 0

    print("开始修复语法错误...")
    print("-" * 50)

    # 首先统计错误数量
    error_files = []
    for py_file in src_dir.rglob('*.py'):
        if not verify_syntax(py_file):
            error_files.append(py_file)

    print(f"发现 {len(error_files)} 个文件有语法错误")

    # 逐个修复
    for py_file in error_files:
        if fix_file_syntax(py_file):
            print(f"✓ 尝试修复: {py_file.relative_to(src_dir)}")
            if verify_syntax(py_file):
                fixed_count += 1
                print(f"  ✓ 修复成功")
            else:
                still_error_count += 1
                # 尝试再次查看错误
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        compile(f.read(), str(py_file), 'exec')
                except SyntaxError as e:
                    print(f"  ✗ 仍有错误: {e.msg[:50]}")
        else:
            still_error_count += 1
            print(f"- 跳过: {py_file.relative_to(src_dir)} (无需修复)")

    print("-" * 50)
    print(f"修复完成!")
    print(f"成功修复: {fixed_count}")
    print(f"仍有错误: {still_error_count}")

    # 显示仍有错误的文件（前10个）
    if still_error_count > 0:
        print("\n仍有错误的文件（前10个）:")
        count = 0
        for py_file in src_dir.rglob('*.py'):
            if not verify_syntax(py_file) and count < 10:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        compile(f.read(), str(py_file), 'exec')
                except SyntaxError as e:
                    print(f"  {py_file.relative_to(src_dir)}: {e.msg[:50]}")
                    count += 1

if __name__ == '__main__':
    main()