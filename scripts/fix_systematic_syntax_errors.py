#!/usr/bin/env python3
"""
系统性语法错误修复工具
专门处理项目中常见的缩进和语法问题
"""

import os
import re
import py_compile
from pathlib import Path

def fix_indentation_errors(file_path):
    """修复文件中的缩进错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复模式1: 函数定义后的文档字符串和pass语句缩进
        pattern1 = r'(    def \w+\([^)]*\):\n)(    \"\"\"[^\"]*\"\"\"\n)(    pass)'
        content = re.sub(pattern1, lambda m: m.group(1) + m.group(2).replace('    ', '        ') + m.group(3).replace('    ', '        ') + '\n', content)

        # 修复模式2: 函数定义后直接跟着pass语句的情况
        pattern2 = r'(    def \w+\([^)]*\):\n)(    pass)'
        content = re.sub(pattern2, lambda m: m.group(1) + m.group(2).replace('    ', '        ') + '\n', content)

        # 修复模式3: 类方法缩进问题
        pattern3 = r'(class \w+.*:\n\n?)(    def \w+\([^)]*\):\n)(    \"\"\"[^\"]*\"\"\"\n)(    pass)'
        content = re.sub(pattern3, lambda m: m.group(1) + m.group(2) + m.group(3).replace('    ', '        ') + m.group(4).replace('    ', '        ') + '\n', content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def check_syntax(file_path):
    """检查文件语法是否正确"""
    try:
        py_compile.compile(file_path, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        return False
    except Exception as e:
        return False

def fix_all_python_files(root_dir="src"):
    """修复所有Python文件的语法错误"""
    fixed_files = []
    error_files = []

    # 遍历所有Python文件
    for py_file in Path(root_dir).rglob("*.py"):
        if check_syntax(py_file):
            continue  # 语法正确，跳过

        print(f"🔧 修复文件: {py_file}")
        if fix_indentation_errors(py_file):
            fixed_files.append(py_file)
            # 再次检查语法
            if check_syntax(py_file):
                print(f"✅ 修复成功: {py_file}")
            else:
                print(f"❌ 修复失败: {py_file}")
                error_files.append(py_file)
        else:
            error_files.append(py_file)

    return fixed_files, error_files

def main():
    print("🚀 开始系统性语法错误修复...")
    print("=" * 50)

    fixed_files, error_files = fix_all_python_files()

    print("\n" + "=" * 50)
    print("📊 修复结果统计:")
    print(f"✅ 修复成功: {len(fixed_files)} 个文件")
    print(f"❌ 修复失败: {len(error_files)} 个文件")

    if fixed_files:
        print("\n✅ 修复成功的文件:")
        for file_path in fixed_files:
            print(f"  - {file_path}")

    if error_files:
        print("\n❌ 修复失败的文件:")
        for file_path in error_files:
            print(f"  - {file_path}")

    print("\n🎉 系统性语法错误修复完成!")

if __name__ == "__main__":
    main()