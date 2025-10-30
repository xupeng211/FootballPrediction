#!/usr/bin/env python3
"""
修复__future__ import位置的专用脚本
"""

import os
from pathlib import Path


def fix_future_import_in_file(file_path: Path) -> bool:
    """修复单个文件中的__future__ import位置"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines[:]

        # 找到__future__ import行
        future_import_line = None
        future_import_index = -1

        for i, line in enumerate(lines):
            if "from __future__ import annotations" in line:
                future_import_line = line
                future_import_index = i
                break

        if future_import_line is None:
            return False  # 没有__future__ import，无需修复

        # 找到第一个非注释非空行
        first_non_comment_index = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                first_non_comment_index = i
                break

        # 如果__future__ import不在第一个非注释行，移动它
        if future_import_index > first_non_comment_index:
            # 移除原位置
            lines.pop(future_import_index)

            # 插入到正确位置
            lines.insert(first_non_comment_index, future_import_line)

            # 写回文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return True

        return False
            except Exception:
        return False


def main():
    print("🔧 修复__future__ import位置...")

    # 需要修复的文件列表
    files_to_fix = [
        "tests/unit/tasks/test_tasks_coverage_boost.py",
        "tests/unit/tasks/test_tasks_basic.py",
    ]

    fixed_count = 0

    for file_str in files_to_fix:
        file_path = Path(file_str)
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        if fix_future_import_in_file(file_path):
            fixed_count += 1
            print(f"✅ 修复 {file_path}")
        else:
            print(f"⚪ 跳过 {file_path}")

    print("\n📊 修复总结:")
    print(f"- 已修复: {fixed_count} 个文件")

    return fixed_count


if __name__ == "__main__":
    exit(main())
