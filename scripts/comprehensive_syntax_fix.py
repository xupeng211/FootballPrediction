#!/usr/bin/env python3
"""
综合语法修复工具
Comprehensive Syntax Fix Tool

修复所有Python文件中的语法错误
"""

import os
import re
from pathlib import Path

def fix_function_signatures(file_path):
    """修复函数签名中的重复参数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复更复杂的重复参数模式
        # 匹配: def test_func(param1, param2, client, client, client):
        content = re.sub(
            r'(def\s+\w+\s*\([^)]*)(client,\s*){2,}([^)]*\):)',
            r'\1client\3',
            content
        )

        # 修复空参数开头: def test_func(, param):
        content = re.sub(
            r'(def\s+\w+\s*\(\s*,)([^)]*\):)',
            r'(\2',
            content
        )

        # 修复参数列表末尾多余的逗号: def test_func(param1, param2,)
        content = re.sub(
            r'(def\s+\w+\s*\([^)]*),\s*\):)',
            r'\1):',
            content
        )

        # 修复参数列表中连续的逗号: def test_func(param1,, param2)
        content = re.sub(
            r'(def\s+\w+\s*\([^)]*),\s*,([^)]*\):)',
            r'\1,\2',
            content
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path}")
            return True
        else:
            print(f"⚪ 无需修复 {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def fix_invalid_annotations(file_path):
    """修复无效的类型注解"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复只有参数列表没有函数名的情况
        content = re.sub(
            r'^\s*\(\s*[^)]*\)\s*:.*?(?:\n|$)',
            '',
            content,
            flags=re.MULTILINE
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了注解问题 {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ 修复注解问题失败 {file_path}: {e}")
        return False

def fix_all_python_files():
    """修复所有Python文件"""
    print("🔧 综合语法修复工具")
    print("=" * 50)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    print(f"📁 找到 {len(python_files)} 个Python文件")
    print()

    fixed_count = 0
    for file_path in python_files:
        if fix_function_signatures(file_path):
            fixed_count += 1
        if fix_invalid_annotations(file_path):
            fixed_count += 1

    print()
    print(f"🎉 完成！修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    fix_all_python_files()