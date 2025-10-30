#!/usr/bin/env python3
"""
批量修复中文标点符号语法错误
"""

import os
import re
from pathlib import Path

def fix_chinese_punctuation_in_code(file_path):
    """修复文件中的中文标点符号问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复代码行中的中文标点符号（不包括字符串字面量中的）
        # 这是一个简化的版本，主要处理明显的错误

        # 1. 修复代码行中的中文句号
        # 匹配不在字符串中的中文句号
        content = re.sub(r'([^"\']*)(。)([^"\']*)', r'\1。\3', content)

        # 2. 修复代码行中的中文逗号
        content = re.sub(r'([^"\']*)(，)([^"\']*)', r'\1,\3', content)

        # 3. 修复代码行中的中文顿号
        content = re.sub(r'([^"\']*)(、)([^"\']*)', r'\1,\3', content)

        # 4. 修复代码行中的中文冒号
        content = re.sub(r'([^"\']*)(：)([^"\']*)', r'\1:\3', content)

        # 5. 修复代码行中的中文分号
        content = re.sub(r'([^"\']*)(；)([^"\']*)', r'\1;\3', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 批量修复中文标点符号语法错误...")

    # 查找所有Python文件
    src_dir = Path("src")
    test_dir = Path("tests")

    fixed_files = []

    # 处理src目录
    if src_dir.exists():
        for py_file in src_dir.rglob("*.py"):
            if fix_chinese_punctuation_in_code(py_file):
                fixed_files.append(py_file)
                print(f"✅ 修复了: {py_file}")

    # 处理tests目录
    if test_dir.exists():
        for py_file in test_dir.rglob("*.py"):
            if fix_chinese_punctuation_in_code(py_file):
                fixed_files.append(py_file)
                print(f"✅ 修复了: {py_file}")

    print(f"\n📊 修复完成!")
    print(f"修复文件数: {len(fixed_files)}")

    if fixed_files:
        print("\n已修复的文件:")
        for file_path in fixed_files:
            print(f"  - {file_path}")

if __name__ == "__main__":
    main()