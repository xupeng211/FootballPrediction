#!/usr/bin/env python3
"""
快速修复语法错误
"""

import os
from pathlib import Path


def fix_missing_import(file_path: Path, module_name: str = "sys"):
    """修复缺失的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if f"{module_name}.modules" in content and f"import {module_name}" not in content:
        # 在第一个导入后添加sys导入
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "import" in line and not line.strip().startswith("#"):
                lines.insert(i + 1, f"import {module_name}")
                break
        content = "\n".join(lines)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def fix_indentation(file_path: Path):
    """修复缩进错误"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 修复孤立的except块
    import re

    content = re.sub(
        r"\n\s+except Exception:\s*\n\s+pytest\.skip\([^)]+\)",
        "\n        pass  # Skip test",
        content,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    """主函数"""
    base_dir = Path("tests/unit")

    # 需要修复的文件
    files_to_fix = [
        "api/monitoring_test.py",
        "core/auto_binding_test.py",
        "core/config_di_test.py",
        "adapters/registry_test.py",
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"修复: {file_path}")
            if fix_missing_import(full_path, "sys"):
                print("  ✅ 添加了sys导入")
                fixed_count += 1
            if "except Exception:" in full_path.read_text():
                fix_indentation(full_path)
                print("  ✅ 修复了缩进")

    print(f"\n修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
