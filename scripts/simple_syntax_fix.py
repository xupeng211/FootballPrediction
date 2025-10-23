#!/usr/bin/env python3
"""
简单语法修复工具
Simple Syntax Fix Tool

专注于修复重复的client参数问题
"""

import os
import re
from pathlib import Path

def fix_duplicate_client_params(file_path):
    """修复重复的client参数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复重复的client参数问题
        # 匹配: def test_func(client, client, client, client, client, client):
        patterns = [
            # 6个重复的client
            (r'(def\s+\w+\s*\([^)]*client)(?:,\s*client){5}([^)]*\):)', r'\1\2'),
            # 5个重复的client
            (r'(def\s+\w+\s*\([^)]*client)(?:,\s*client){4}([^)]*\):)', r'\1\2'),
            # 4个重复的client
            (r'(def\s+\w+\s*\([^)]*client)(?:,\s*client){3}([^)]*\):)', r'\1\2'),
            # 3个重复的client
            (r'(def\s+\w+\s*\([^)]*client)(?:,\s*client){2}([^)]*\):)', r'\1\2'),
            # 2个重复的client
            (r'(def\s+\w+\s*\([^)]*client),\s*client([^)]*\):)', r'\1\2'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # 修复空参数开头的问题
        content = re.sub(r'(def\s+\w+\s*\(\s*,)([^)]*\):)', r'(\2', content, flags=re.MULTILINE)

        # 修复参数列表末尾多余的逗号
        content = re.sub(r'(def\s+\w+\s*\([^)]*),\s*\):)', r'\1):', content, flags=re.MULTILINE)

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
    print("🔧 简单语法修复工具")
    print("=" * 40)

    # 查找所有Python测试文件
    python_files = []
    for root, dirs, files in os.walk("tests"):
        # 跳过缓存目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    print(f"📁 找到 {len(python_files)} 个测试文件")

    fixed_count = 0
    for file_path in python_files:
        if fix_duplicate_client_params(file_path):
            print(f"✅ 修复了 {file_path}")
            fixed_count += 1

    print(f"\n🎉 完成！修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()