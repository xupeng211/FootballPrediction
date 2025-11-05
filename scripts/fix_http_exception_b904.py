#!/usr/bin/env python3
"""
快速修复HTTPException B904错误的专用工具
"""

import re
from pathlib import Path

def fix_file(file_path: str) -> int:
    """修复单个文件的HTTPException B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 使用正则表达式匹配并修复所有HTTPException模式
        # 匹配: except Exception as e: ... raise HTTPException(...)
        pattern = r'(\s+)(except\s+\w+\s+as\s+\w+:.*?\n)(\s+)(raise\s+HTTPException\([^)]*\))\n'

        def replacer(match):
            return f"{match.group(1)}{match.group(2)}{match.group(3)} from e\n"

        content, count = re.subn(pattern, replacer, content, flags=re.DOTALL)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return count
        else:
            return 0

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0

# 修复data_router.py
file_path = "src/api/data_router.py"
fixes = fix_file(file_path)
print(f"✅ {file_path}: 修复了 {fixes} 个B904错误")