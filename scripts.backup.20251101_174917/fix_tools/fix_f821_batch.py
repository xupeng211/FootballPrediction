#!/usr/bin/env python3
"""
批量修复F821错误的高效脚本
专门处理常见的导入和函数引用问题
"""

import os
import re
import subprocess
from collections import defaultdict


def get_f821_errors():
    """获取所有F821错误"""
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
    """安全地向文件添加导入语句"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已存在该导入
        if import_statement.strip() in content:
            return False

        lines = content.split("\n")

        # 找到导入区域的结束位置
        import_end = 0
        in_docstring = False
        docstring_chars = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 处理文档字符串
            if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
                in_docstring = True
                docstring_chars = stripped[:3]
                continue
            elif in_docstring and docstring_chars in stripped:
                in_docstring = False
                continue

            if in_docstring:
                continue

            # 找到导入语句
            if stripped.startswith(("import ", "from ")) and "import" in stripped:
                import_end = max(import_end, i + 1)
            elif stripped and not stripped.startswith("#") and "import" not in stripped:
                break

        # 插入导入语句
        lines.insert(import_end, import_statement)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """主函数"""
    print("🔍 获取F821错误...")
    errors = get_f821_errors()

    if not errors:
        print("✅ 没有发现F821错误！")
        return

    print(f"📊 发现 {len(errors)} 个F821错误")

    # 按变量名分组统计
    error_stats = defaultdict(lambda: defaultdict(list))
    for filepath, line_num, var_name in errors:
        error_stats[var_name][filepath].append(line_num)

    # 显示错误分布
    print("\n📈 错误分布统计:")
    for var_name, files in sorted(
        error_stats.items(),
        key=lambda x: sum(len(lines) for lines in x[1].values()),
        reverse=True,
    ):
        total_count = sum(len(lines) for lines in files.values())
        print(f"  {var_name}: {total_count}个错误 ({len(files)}个文件)")

    # 定义修复映射
    import_fixes = {
        # 标准库导入
        "time": "import time",
        "datetime": "from datetime import datetime",
        "timedelta": "from datetime import timedelta",
        "asyncio": "import asyncio",
        # Mock和测试相关
        "patch": "from unittest.mock import patch",
        "MagicMock": "from unittest.mock import MagicMock",
        "Mock": "from unittest.mock import Mock",
        "AsyncMock": "from unittest.mock import AsyncMock",
    }

    # 批量修复导入错误
    total_fixed = 0
    for var_name in [
        "time",
        "datetime",
        "timedelta",
        "asyncio",
        "patch",
        "MagicMock",
        "Mock",
        "AsyncMock",
    ]:
        if var_name in error_stats and var_name in import_fixes:
            import_statement = import_fixes[var_name]
            files_to_fix = list(error_stats[var_name].keys())

            print(f"\n🔧 修复 '{var_name}' 导入问题 ({len(files_to_fix)} 个文件)...")

            fixed_count = 0
            for filepath in files_to_fix:
                if os.path.exists(filepath):
                    if add_import_to_file(filepath, import_statement):
                        fixed_count += 1
                        total_fixed += 1
                        print(f"  ✅ {filepath}")

            if fixed_count > 0:
                print(f"  📈 已修复 {fixed_count} 个文件")

    print(f"\n🎉 总计修复了 {total_fixed} 个文件")

    # 再次检查错误数量
    print("\n🔍 重新检查错误数量...")
    new_errors = get_f821_errors()
    print(f"修复后剩余 {len(new_errors)} 个F821错误")

    if len(new_errors) < len(errors):
        reduction = len(errors) - len(new_errors)
        print(f"✅ 成功减少了 {reduction} 个错误 ({reduction/len(errors)*100:.1f}%)")

        # 显示剩余错误的主要类型
        remaining_stats = defaultdict(int)
        for _, _, var_name in new_errors:
            remaining_stats[var_name] += 1

        print("\n📋 剩余错误Top 10:")
        for var_name, count in sorted(remaining_stats.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]:
            print(f"  {var_name}: {count}个")


if __name__ == "__main__":
    main()
