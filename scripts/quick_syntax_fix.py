#!/usr/bin/env python3
"""
快速语法修复工具
Quick Syntax Fix Tool

修复测试文件中的重复参数问题
"""

import os
import re
from pathlib import Path

def fix_duplicate_parameters(file_path):
    """修复文件中的重复参数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复重复的client参数
        # 匹配形如: def test_func(param1, param2, client, client, client):
        pattern = r'(def\s+\w+\([^)]*client)(?:,\s*client)+([^)]*\):)'
        content = re.sub(pattern, r'\1\2', content)

        # 修复空参数问题
        # 匹配形如: def test_func(, client, client):
        pattern = r'(def\s+\w+\s*\(\s*,)([^)]*\):)'
        content = re.sub(pattern, r'(\2', content)

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

def main():
    """主函数"""
    print("🔧 快速语法修复工具")
    print("=" * 50)

    # 查找所有Python测试文件
    test_files = []
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py"):
                test_files.append(Path(root) / file)

    print(f"📁 找到 {len(test_files)} 个测试文件")
    print()

    fixed_count = 0
    for file_path in test_files:
        if fix_duplicate_parameters(file_path):
            fixed_count += 1

    print()
    print(f"🎉 完成！修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()