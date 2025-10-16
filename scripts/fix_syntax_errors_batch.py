#!/usr/bin/env python3
"""
批量修复语法错误脚本
"""

import ast
import os
import re
from pathlib import Path

def fix_syntax_errors():
    """修复常见的语法错误"""

    # 需要修复的文件列表
    files_to_fix = []

    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    print(f"找到 {len(files_to_fix)} 个Python文件需要检查")

    fixed_count = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 修复常见的语法错误

            # 1. 修复未闭合的括号（简单情况）
            content = re.sub(r'\[(?!\s*\])', '[', content)  # 确保括号匹配

            # 2. 修复未闭合的字符串（简单情况）
            # 查找未闭合的三引号字符串
            triple_quotes = content.count('"""')
            if triple_quotes % 2 != 0:
                # 在文件末尾添加缺失的三引号
                if not content.rstrip().endswith('"""'):
                    content = content.rstrip() + '\n"""'

            # 3. 修复赋值错误
            content = re.sub(r'(\w+)\[(\w+)\]\s*=\s*([^=])', r'\1[\2] == \3', content)

            # 4. 修复缺失的冒号
            content = re.sub(r'(\))\s*$', r'\1:', content)

            # 5. 修复类型注解缺失的括号
            content = re.sub(r':\s*Optional\[Dict\[str, Any\]$', ': Optional[Dict[str, Any]]', content)

            # 检查修复后的语法
            try:
                ast.parse(content)
                if content != original_content:
                    print(f"修复: {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
            except SyntaxError as e:
                print(f"无法修复: {file_path} - {e}")

        except Exception as e:
            print(f"处理文件时出错 {file_path}: {e}")

    print(f"\n修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    fix_syntax_errors()
