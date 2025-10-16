#!/usr/bin/env python3
"""
快速修复中文标点符号
"""

import os
import re
from pathlib import Path

def fix_chinese_punctuation_in_file(file_path: str) -> bool:
    """修复文件中的中文标点"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 修复常见的中文标点
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        content = content.replace('：', ': ')
        content = content.replace('；', '; ')
        content = content.replace('，', ', ')
        content = content.replace('。', '. ')
        content = content.replace('、', ', ')

        # 修复三引号文档字符串
        content = re.sub(r'""\s*([^"]*?)\s*""', r'"""\1"""', content)

        # 修复函数定义
        content = re.sub(r'"""([^"]*?)""\s*@staticmethod', r'"""\1"""\n    @staticmethod', content)
        content = re.sub(r'"""([^"]*?)""\s*def', r'"""\1"""\n    def', content)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复: {file_path}")
            return True
        else:
            print(f"○ 无需修复: {file_path}")
            return False
    except Exception as e:
        print(f"✗ 错误: {file_path} - {e}")
        return False

def main():
    """主函数"""
    base_dir = Path("src/utils")

    # 修复utils模块的所有文件
    python_files = list(base_dir.rglob("*.py"))

    print(f"修复 {len(python_files)} 个文件...")

    fixed_count = 0
    for file_path in python_files:
        if fix_chinese_punctuation_in_file(str(file_path)):
            fixed_count += 1

    print(f"\n修复完成！共修复 {fixed_count} 个文件")

    # 验证语法
    print("\n验证语法...")
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, str(file_path), 'exec')
            print(f"✓ {file_path.relative_to(Path.cwd())}")
        except SyntaxError as e:
            print(f"✗ {file_path.relative_to(Path.cwd())}: {e}")

if __name__ == "__main__":
    main()