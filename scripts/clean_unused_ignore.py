#!/usr/bin/env python3
"""
清理未使用的 type: ignore 注释
"""

import re
import os
from pathlib import Path

def clean_unused_ignore_comments(file_path):
    """清理单个文件中未使用的 type: ignore 注释"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        # 查找包含 "Unused 'type: ignore' comment" 的错误模式
        # 我们直接删除这些注释
        if 'Unused "type: ignore" comment' in line:
            continue

        # 移除简单的 type: ignore 注释（如果它们是唯一的注释）
        # 保留有具体错误代码的 type: ignore
        new_line = line

        # 移除没有错误代码的 type: ignore
        new_line = re.sub(r'\s*# type:\s*ignore(?!\s*\[)', '', new_line)

        # 清理多余的空白
        new_line = re.sub(r'\s+$', '', new_line)

        # 如果整行都是空的，保留空行
        if new_line.strip() == '' and line.strip() != '':
            new_line = ''

        new_lines.append(new_line)

    new_content = '\n'.join(new_lines)

    if new_content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, "Cleaned unused type: ignore comments"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"

def clean_files_in_directory(directory, file_patterns=None):
    """清理目录中的文件"""
    if file_patterns is None:
        file_patterns = ['*.py']

    fixed_files = []
    failed_files = []

    for pattern in file_patterns:
        for file_path in Path(directory).rglob(pattern):
            # 跳过一些特殊目录
            if any(skip in str(file_path) for skip in ['.venv', '__pycache__', '.git']):
                continue

            success, message = clean_unused_ignore_comments(str(file_path))

            if success:
                fixed_files.append((str(file_path), message))
                print(f"✅ Cleaned: {file_path}")
            else:
                if "No changes needed" not in message:
                    failed_files.append((str(file_path), message))
                    print(f"❌ Failed: {file_path} - {message}")

    return fixed_files, failed_files

def main():
    """主函数"""
    print("🧹 开始清理未使用的 type: ignore 注释...")

    src_dir = '/home/user/projects/FootballPrediction/src'

    # 修复 src 目录
    print(f"\n📁 处理目录: {src_dir}")
    fixed, failed = clean_files_in_directory(src_dir, ['*.py'])

    print(f"\n📊 清理结果:")
    print(f"✅ 成功清理: {len(fixed)} 个文件")
    print(f"❌ 清理失败: {len(failed)} 个文件")

    # 显示一些清理的例子
    if fixed:
        print(f"\n✅ 清理示例:")
        for file_path, message in fixed[:3]:
            print(f"  {file_path}: {message}")
        if len(fixed) > 3:
            print(f"  ... 还有 {len(fixed) - 3} 个文件")

if __name__ == '__main__':
    main()