#!/usr/bin/env python3
"""
修复src目录下的语法错误
"""

import os
import re
from pathlib import Path

def fix_file_syntax(file_path: Path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的语法错误模式

        # 1. 修复中文标点符号
        content = re.sub(r'([^\"]*)。([^\"]*)', r'\1.\2', content)
        content = re.sub(r'([^\"]*)，([^\"]*)', r'\1,\2', content)
        content = re.sub(r'([^\"]*)、([^\"]*)', r'\1,\2', content)
        content = re.sub(r'([^\"]*)：([^\"]*)', r'\1:\2', content)
        content = re.sub(r'([^\"]*)；([^\"]*)', r'\1;\2', content)

        # 2. 修复未闭合的字符串字面量
        content = re.sub(r'"""""""', '"""', content)

        # 3. 修复类型注解
        content = re.sub(r'Dict\[str\]', 'Dict[str, Any]', content)

        # 4. 修复不匹配的括号（简单修复）
        # 查找并修复明显的不匹配括号
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens > close_parens:
            content += ')' * (open_parens - close_parens)

        open_brackets = content.count('[')
        close_brackets = content.count(']')
        if open_brackets > close_brackets:
            content += ']' * (open_brackets - close_brackets)

        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)

        # 5. 修复import中的Dialect问题
        if 'from sqlalchemy.engine.interfaces import Dialect' not in content and 'Dialect' in content:
            if 'from sqlalchemy import' in content:
                content = content.replace(
                    'from sqlalchemy import',
                    'from sqlalchemy import JSON, Text, TypeDecorator\nfrom sqlalchemy.engine.interfaces import Dialect\nfrom sqlalchemy import'
                )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 修复src目录语法错误...")

    src_dir = Path("src")
    if not src_dir.exists():
        print("❌ src目录不存在")
        return

    fixed_files = []

    # 只处理src目录下的Python文件
    for py_file in src_dir.rglob("*.py"):
        if fix_file_syntax(py_file):
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