#!/usr/bin/env python3
"""
批量修复Python文件中的语法错误
主要是修复类型注解中的括号不匹配问题
"""

import re
import os
from pathlib import Path
from typing import List, Tuple


def fix_type_annotations(file_path: str) -> Tuple[int, List[str]]:
    """修复文件中的类型注解错误"""
    fixes_made = 0
    fix_messages = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        original_content = content

    # 修复模式: Dict[str, Dict[str, Any] = {}  ->  Dict[str, Dict[str, Any]] = {}

    # 特殊修复：处理 Dict[str, Dict[str, Any] = {} 模式
    special_pattern = r"(\w+:\s*Dict\[str,\s*Dict\[str,\s*Any])\s*=\s*"
    content = re.sub(special_pattern, r"\1] = ", content)
    if content != original_content:
        fixes_made += 1
        fix_messages.append("Fixed Dict type annotation")

    # 修复 ]]= 现象
    content = re.sub(r"\]\]\]", "]]", content)

    # 修复 ])= 现象
    content = re.sub(r"\]\)\]", "])", content)

    # 修复 f-string 路由定义
    route_pattern = r'@router\.(get|post|put|delete|patch)\(f"/([^"]+)"'
    matches = re.findall(route_pattern, content)
    for match in matches:
        old_pattern = f'@router.{match[0]}(f"/{match[1]}"'
        new_pattern = f'@router.{match[0]}("/{match[1]}"'
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            fixes_made += 1
            fix_messages.append(f"Fixed f-string route: {match[0]} /{match[1]}")

    # 写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return fixes_made, fix_messages


def main():
    """主函数"""
    src_dir = Path("src")
    total_fixes = 0

    print("开始修复Python语法错误...")

    for py_file in src_dir.rglob("*.py"):
        if "stubs" in str(py_file) or "__pycache__" in str(py_file):
            continue

        fixes, messages = fix_type_annotations(str(py_file))
        if fixes > 0:
            total_fixes += fixes
            print(f"✓ {py_file}: {fixes} fixes")
            for msg in messages:
                print(f"  - {msg}")

    print(f"\n总计修复了 {total_fixes} 个语法错误")


if __name__ == "__main__":
    main()
