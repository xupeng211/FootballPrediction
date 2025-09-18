#!/usr/bin/env python3
"""
修复剩余导入问题的针对性脚本
"""

import os
import re
import subprocess
from collections import defaultdict


def get_remaining_errors():
    """获取所有剩余的F821错误"""
    result = subprocess.run(["make", "lint"], capture_output=True, text=True, cwd=".")
    errors = []
    for line in result.stdout.split("\n"):
        if "F821 undefined name" in line:
            match = re.search(r"(.+):(\d+):\d+: F821 undefined name '(.+)'", line)
            if match:
                filepath, line_num, var_name = match.groups()
                errors.append((filepath, int(line_num), var_name))
    return errors


def add_import_to_file(filepath, import_statement):
    """向文件添加导入语句"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查是否已存在该导入
        import_line = import_statement.strip() + "\n"
        for line in lines:
            if import_line.strip() in line.strip():
                return False

        # 找到导入区域的结束位置
        import_end = 0
        in_docstring = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 跳过文档字符串
            if not in_docstring and (
                stripped.startswith('"""') or stripped.startswith("'''")
            ):
                in_docstring = True
                continue
            elif in_docstring and ('"""' in stripped or "'''" in stripped):
                in_docstring = False
                continue

            if in_docstring:
                continue

            # 找到导入语句
            if stripped.startswith(("import ", "from ")):
                import_end = max(import_end, i + 1)
            elif stripped and not stripped.startswith("#") and "import" not in stripped:
                break

        # 在导入区域末尾插入新的导入
        lines.insert(import_end, import_line)

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """主函数"""
    print("获取剩余的F821错误...")
    errors = get_remaining_errors()

    if not errors:
        print("没有发现F821错误！")
        return

    print(f"发现 {len(errors)} 个F821错误")

    # 按变量名统计
    error_stats = defaultdict(lambda: defaultdict(list))
    for filepath, line_num, var_name in errors:
        error_stats[var_name][filepath].append(line_num)

    # 显示统计信息
    print("\n错误统计:")
    for var_name, files in error_stats.items():
        print(
            f"  {var_name}: {len(files)} 个文件, {sum(len(lines) for lines in files.values())} 处错误"
        )

    # 定义常见导入修复
    common_imports = {
        "asyncio": "import asyncio",
        "time": "import time",
        "patch": "from unittest.mock import patch",
        "datetime": "from datetime import datetime",
        "timedelta": "from datetime import timedelta",
    }

    # 修复高频错误
    for var_name in ["asyncio", "time", "patch"]:
        if var_name in error_stats and var_name in common_imports:
            import_statement = common_imports[var_name]
            files_to_fix = list(error_stats[var_name].keys())

            print(f"\n修复 {var_name} 导入问题 ({len(files_to_fix)} 个文件)...")

            fixed_count = 0
            for filepath in files_to_fix:
                if os.path.exists(filepath):
                    if add_import_to_file(filepath, import_statement):
                        fixed_count += 1
                        print(f"  ✓ {filepath}")

            print(f"已修复 {fixed_count} 个文件")

    print("\n第一轮修复完成！")


if __name__ == "__main__":
    main()
