#!/usr/bin/env python3
"""
精准语法修复工具
Targeted Syntax Fix Tool

只修复项目源代码和测试文件中的语法错误
"""

import os
import re
from pathlib import Path

def fix_project_files():
    """只修复项目文件，不包括虚拟环境"""
    print("🔧 精准语法修复工具")
    print("=" * 50)

    # 只处理项目根目录下的文件，排除.venv
    python_files = []

    # 添加主要的Python目录
    for directory in ["src", "tests", "scripts"]:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                # 跳过隐藏目录和缓存目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(Path(root) / file)

    # 添加根目录下的Python文件
    for file in os.listdir("."):
        if file.endswith(".py") and os.path.isfile(file):
            python_files.append(Path(file))

    print(f"📁 找到 {len(python_files)} 个项目Python文件")
    print()

    fixed_count = 0
    error_count = 0

    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 修复重复的client参数
            content = re.sub(
                r'(def\s+\w+\s*\([^)]*client,)\s*client,\s*client,\s*client,\s*client,\s*client,\s*client,\s*client([^)]*\):)',
                r'\1\2',
                content
            )

            # 修复其他重复参数
            content = re.sub(
                r'(def\s+\w+\s*\([^)]*client,)\s*client,\s*client,\s*client,\s*client,\s*client([^)]*\):)',
                r'\1\2',
                content
            )

            content = re.sub(
                r'(def\s+\w+\s*\([^)]*client,)\s*client,\s*client,\s*client,\s*client([^)]*\):)',
                r'\1\2',
                content
            )

            content = re.sub(
                r'(def\s+\w+\s*\([^)]*client,)\s*client,\s*client,\s*client([^)]*\):)',
                r'\1\2',
                content
            )

            # 修复空参数开头
            content = re.sub(
                r'(def\s+\w+\s*\(\s*,)([^)]*\):)',
                r'(\2',
                content
            )

            # 修复参数列表末尾多余的逗号
            content = re.sub(
                r'(def\s+\w+\s*\([^)]*),\s*\):)',
                r'\1):',
                content
            )

            # 修复参数列表中连续的逗号
            content = re.sub(
                r'(def\s+\w+\s*\([^)]*),\s*,([^)]*\):)',
                r'\1,\2',
                content
            )

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了 {file_path}")
                fixed_count += 1

        except Exception as e:
            print(f"❌ 处理失败 {file_path}: {e}")
            error_count += 1

    print()
    print(f"🎉 完成！修复了 {fixed_count} 个文件，失败 {error_count} 个文件")

if __name__ == "__main__":
    fix_project_files()