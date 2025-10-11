#!/usr/bin/env python3
"""
修复 undefined name 错误（F821）
"""

import os
import re
import subprocess


def fix_undefined_names(filepath):
    """修复单个文件的 undefined name"""
    print(f"处理: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        new_lines = []

        # 常见的未定义名称映射
        common_fixes = {
            # 测试相关的
            "pytest": "import pytest",
            "Mock": "from unittest.mock import Mock",
            "MagicMock": "from unittest.mock import MagicMock",
            "AsyncMock": "from unittest.mock import AsyncMock",
            "patch": "from unittest.mock import patch",
            "fixture": "import pytest",
            # 类型相关
            "List": "from typing import List",
            "Dict": "from typing import Dict",
            "Optional": "from typing import Optional",
            "Union": "from typing import Union",
            "Tuple": "from typing import Tuple",
            "Set": "from typing import Set",
            "Any": "from typing import Any",
            # 数据库相关
            "Session": "from sqlalchemy.orm import Session",
            "create_engine": "from sqlalchemy import create_engine",
            "select": "from sqlalchemy import select",
            # 其他常见
            "logger": "import logging",
            "utcnow": "from datetime import datetime, timezone",
        }

        # 检查是否需要添加导入
        imports_needed = set()

        for i, line in enumerate(lines):
            # 检查是否有未定义的名称
            for name, import_stmt in common_fixes.items():
                # 使用正则表达式查找独立的名称
                pattern = rf"\b{name}\b"
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    # 检查是否已经在导入中
                    if import_stmt not in content:
                        imports_needed.add(import_stmt)

            new_lines.append(line)

        # 添加需要的导入
        if imports_needed:
            # 找到第一个导入位置
            import_insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import ") or line.strip().startswith(
                    "from "
                ):
                    import_insert_pos = i
                    break

            # 插入新的导入
            for import_stmt in sorted(imports_needed):
                new_lines.insert(import_insert_pos, import_stmt)
                import_insert_pos += 1

        content = "\n".join(new_lines)

        # 写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print("  ✅ 已修复")
            return True
        else:
            print("  - 无需修复")
            return False

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def main():
    """主函数"""
    # 获取所有有 F821 错误的文件
    result = subprocess.run(
        ["ruff", "check", "--select=F821", "--output-format=concise"],
        capture_output=True,
        text=True,
    )

    files = set()
    for line in result.stdout.split("\n"):
        if line:
            filepath = line.split(":")[0]
            if os.path.exists(filepath):
                files.add(filepath)

    print(f"找到 {len(files)} 个需要修复的文件")
    print("=" * 60)

    fixed_count = 0
    for filepath in sorted(files):
        if fix_undefined_names(filepath):
            fixed_count += 1

    print("=" * 60)
    print(f"✅ 修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    result = subprocess.run(
        ["ruff", "check", "--select=F821"], capture_output=True, text=True
    )

    remaining = len(result.stdout.split("\n")) if result.stdout.strip() else 0
    print(f"剩余 {remaining} 个 F821 错误")

    if remaining > 0:
        print("\n前 10 个错误:")
        for line in result.stdout.split("\n")[:10]:
            if line:
                print(f"  {line}")


if __name__ == "__main__":
    main()
