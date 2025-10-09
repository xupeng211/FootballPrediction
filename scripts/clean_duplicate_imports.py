#!/usr/bin/env python3
"""
清理重复的导入语句
"""

import re
from pathlib import Path
from collections import defaultdict


def clean_file(file_path: Path):
    """清理单个文件的重复导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    seen_imports = set()
    new_lines = []
    removed = 0

    for line in lines:
        # 检查是否是导入语句
        if line.startswith("from ") or line.startswith("import "):
            # 标准化导入语句进行比较
            normalized = line.strip()
            if normalized not in seen_imports:
                seen_imports.add(normalized)
                new_lines.append(line)
            else:
                removed += 1
                print(f"  移除重复: {line}")
        else:
            new_lines.append(line)

    # 移除连续的空行
    final_lines = []
    prev_empty = False
    for line in new_lines:
        if line.strip() == "":
            if not prev_empty:
                final_lines.append(line)
            prev_empty = True
        else:
            final_lines.append(line)
            prev_empty = False

    # 写回文件
    new_content = "\n".join(final_lines)
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return removed

    return 0


def main():
    """主函数"""
    print("清理重复的导入语句...")

    models_dir = Path("src/database/models")
    total_removed = 0

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        removed = clean_file(py_file)
        if removed > 0:
            print(f"✓ {py_file.relative_to('.')}: 移除了 {removed} 个重复导入")
            total_removed += removed

    print(f"\n清理完成！共移除 {total_removed} 个重复导入")


if __name__ == "__main__":
    main()
