#!/usr/bin/env python3
"""
快速语法检查脚本
"""

import ast
import os
import sys
from pathlib import Path

def check_syntax(directory):
    """检查目录中的所有Python文件语法"""
    errors = []
    total_files = 0

    for py_file in Path(directory).rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        total_files += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            errors.append((str(py_file), e.msg, e.lineno))

    return total_files, errors

def main():
    """主函数"""
    print("🔍 Python语法检查\n")

    # 检查核心目录
    modules = ['src/core', 'src/api', 'src/utils']
    all_errors = []
    total_files = 0

    for module in modules:
        if os.path.exists(module):
            print(f"检查 {module}...")
            count, errors = check_syntax(module)
            total_files += count

            if errors:
                print(f"  ❌ 发现 {len(errors)} 个错误")
                all_errors.extend(errors)
            else:
                print(f"  ✅ 全部正确")

    print(f"\n📊 总计:")
    print(f"  检查文件: {total_files}")
    print(f"  错误文件: {len(all_errors)}")

    if all_errors:
        print(f"\n❌ 语法错误列表:")
        for file_path, error, line in all_errors[:10]:  # 只显示前10个
            print(f"  {file_path}:{line} - {error}")

        if len(all_errors) > 10:
            print(f"  ... 还有 {len(all_errors) - 10} 个错误")

        sys.exit(1)
    else:
        print(f"\n✅ 所有文件语法正确！")
        sys.exit(0)

if __name__ == "__main__":
    main()
