#!/usr/bin/env python3
"""
批量修复测试文件中的语法错误
主要修复未终止的字符串字面量问题
"""

import re
from pathlib import Path

def fix_syntax_errors_in_file(file_path: Path) -> bool:
    """修复单个文件中的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复未终止的三引号字符串
        # 查找 """"""" 并替换为 """
        content = re.sub(r'"{6,}', '"""', content)

        # 修复混合的三引号字符串
        # 查找 """""""  并替换为 """
        content = re.sub(r'"{5}\'{3,}', '"""', content)
        content = re.sub(r'\'{3}"{5,}', '"""', content)

        # 修复其他异常的三引号组合
        content = re.sub(r'"{4,}\'{3,}', '"""', content)
        content = re.sub(r'\'{3,}"{4,}', '"""', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed syntax errors in: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_syntax_errors(directory: Path) -> int:
    """修复目录中所有文件的语法错误"""
    fixed_count = 0

    # 查找所有Python文件
    for py_file in directory.rglob("*.py"):
        if fix_syntax_errors_in_file(py_file):
            fixed_count += 1

    return fixed_count

def main():
    """主函数"""
    print("开始批量修复语法错误...")

    # 修复 tests/unit 目录
    tests_dir = Path("tests/unit")
    if tests_dir.exists():
        fixed_count = fix_all_syntax_errors(tests_dir)
        print(f"修复了 {fixed_count} 个文件的语法错误")
    else:
        print("tests/unit 目录不存在")

    # 修复其他测试目录
    other_dirs = ["tests/integration", "tests/e2e", "tests/auto_generated"]
    for dir_name in other_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            fixed_count = fix_all_syntax_errors(dir_path)
            print(f"在 {dir_name} 中修复了 {fixed_count} 个文件的语法错误")

    print("语法错误修复完成！")

if __name__ == "__main__":
    main()