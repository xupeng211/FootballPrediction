#!/usr/bin/env python3
"""批量修复类型注解错误"""

import os
import re
from pathlib import Path


def fix_type_annotations(file_path):
    """修复文件中的类型注解错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复 Optional[Type] ] -> Optional[Type]
        content = re.sub(r"Optional\[([^\]]+)\] \]", r"Optional[\1]", content)

        # 修复 List[Any][Type] -> List[Type]
        content = re.sub(r"List\[Any\]\[([^\]]+)\]", r"List[\1]", content)

        # 修复 Dict[str, Any][str, Type] -> Dict[str, Type]
        content = re.sub(
            r"Dict\[str, Any\]\[str, ([^\]]+)\]", r"Dict[str, \1]", content
        )

        # 修复 Optional[Dict[str, Any][str, Any]] -> Optional[Dict[str, Any]]
        content = re.sub(
            r"Optional\[Dict\[str, Any\]\[str, Any\]\]",
            r"Optional[Dict[str, Any]]",
            content,
        )

        # 修复 List[Any][Dict[str, Any][str, Any]] -> List[Dict[str, Any]]
        content = re.sub(
            r"List\[Any\]\[Dict\[str, Any\]\[str, Any\]\]",
            r"List[Dict[str, Any]]",
            content,
        )

        # 修复重复的 Any 导入
        content = re.sub(
            r"from typing import Any,  Any,", "from typing import Any,", content
        )
        content = re.sub(
            r"from typing import Any, Any, ", "from typing import Any, ", content
        )

        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """主函数"""
    src_dir = Path("src")
    fixed_count = 0

    # 查找所有 Python 文件
    for py_file in src_dir.rglob("*.py"):
        if fix_type_annotations(py_file):
            print(f"Fixed: {py_file}")
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
