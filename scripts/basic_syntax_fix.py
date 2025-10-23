#!/usr/bin/env python3
"""
基础语法修复工具
Basic Syntax Fix Tool

简单直接的语法修复，避免复杂的正则表达式
"""

import os
from pathlib import Path

def fix_file_content(content):
    """修复文件内容中的重复参数问题"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 检查是否是函数定义行
        if line.strip().startswith('def ') and 'client' in line:
            # 简单的重复client参数检查和修复
            if line.count('client') > 1:
                # 提取函数名和参数列表
                parts = line.split(':', 1)
                if len(parts) == 2:
                    func_def = parts[0]
                    rest = parts[1]

                    # 简单修复：只保留第一个client
                    client_count = func_def.count('client')
                    if client_count > 1:
                        # 移除重复的client
                        parts = func_def.split('client')
                        if len(parts) > 1:
                            fixed_line = parts[0] + 'client' + ''.join(parts[1:])
                            # 修复参数列表
                            if 'client,' in fixed_line:
                                fixed_line = fixed_line.replace('client,', 'client', 1)
                            fixed_line = fixed_line.rstrip(',') + ':' + rest
                            fixed_lines.append(fixed_line)
                            continue

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_file(file_path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixed_content = fix_file_content(content)

        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 基础语法修复工具")
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
        if fix_file(file_path):
            print(f"✅ 修复了 {file_path}")
            fixed_count += 1

    print(f"\n🎉 完成！修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()