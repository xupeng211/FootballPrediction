#!/usr/bin/env python3
"""
修复多余的右括号
"""

import os
import re
from pathlib import Path


def fix_extra_brackets(file_path: Path):
    """修复文件中的多余右括号"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        new_lines = []
        modified = False
        fixes = []

        for i, line in enumerate(lines, 1):
            original_line = line

            # 修复模式: ]]) 或 ]]  -> ]
            line = re.sub(r"]]$", "]", line)

            # 修复模式: ]]  -> ] (在行尾，不是注释前)
            if line != original_line:
                modified = True
                fixes.append(f"Line {i}: Fixed extra bracket")

            new_lines.append(line)

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
            print(f"Fixed {file_path}")
            for fix in fixes:
                print(f"  - {fix}")
            return True

        return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """主函数"""
    # 检查特定文件
    files_to_check = [
        "src/decorators/decorators.py",
    ]

    fixed_count = 0

    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            if fix_extra_brackets(path):
                fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
