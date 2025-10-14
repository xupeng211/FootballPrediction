#!/usr/bin/env python3
"""
修复核心模块的 MyPy 类型错误 - 简化版
"""

import re
import ast
from pathlib import Path
from typing import Dict, List
import sys

PROJECT_ROOT = Path(__file__).parent.parent

# 要修复的核心模块
CORE_MODULES = [
    "src/core",
    "src/services",
    "src/api",
    "src/domain",
    "src/repositories",
    "src/database/repositories",
]


def fix_file(file_path: Path) -> int:
    """修复单个文件的错误"""
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes_count = 0

    # 1. 修复 _result -> result
    pattern = r"\b_result\b(?!\s*#)"
    count = len(re.findall(pattern, content))
    if count > 0:
        content = re.sub(pattern, "result", content)
        fixes_count += count
        print(f"  • 修复 _result -> result: {count} 处")

    # 2. 修复缺少的返回类型注解
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        # 检查是否是函数定义且没有返回类型
        if re.match(r"^\s*def\s+\w+\s*\([^)]*\)\s*:\s*$", line):
            # 添加 -> None
            if line.strip().endswith(":"):
                line = line[:-1] + " -> None:"
            else:
                line = line + " -> None:"
            fixes_count += 1
            print(f"  • 添加返回类型: {line.strip()}")
        new_lines.append(line)

    content = "\n".join(new_lines)

    # 3. 修复 Optional 类型注解
    # 将 Optional[Type] = None 改为 Optional[Type] | None
    pattern = r"(\w+):\s*Optional\[([^\]]+)\]\s*=\s*None"
    matches = re.findall(pattern, content)
    if matches:
        for var_name, type_name in matches:
            old_pattern = f"{var_name}: Optional[{type_name}] = None"
            new_pattern = f"{var_name}: Optional[{type_name}] | None = None"
            content = content.replace(old_pattern, new_pattern)
            fixes_count += 1
            print(f"  • 修复 Optional 类型: {var_name}")

    # 写回文件
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print(f"✓ 修复 {file_path.relative_to(PROJECT_ROOT)} - 共 {fixes_count} 处")

    return fixes_count


def main():
    print("🔧 修复核心模块 MyPy 类型错误")
    print("=" * 50)

    total_fixes = 0
    total_files = 0

    # 遍历核心模块
    for module in CORE_MODULES:
        module_path = PROJECT_ROOT / module
        if not module_path.exists():
            continue

        print(f"\n📁 处理模块: {module}")

        for py_file in module_path.glob("**/*.py"):
            if py_file.name == "__init__.py":
                continue

            fixes = fix_file(py_file)
            if fixes > 0:
                total_fixes += fixes
                total_files += 1

    print("\n" + "=" * 50)
    print(f"✅ 完成！修复了 {total_files} 个文件的 {total_fixes} 处错误")

    # 运行 MyPy 验证
    print("\n🔍 验证修复效果...")
    import subprocess

    # 先检查核心模块
    cmd = [
        "mypy",
        "src/core",
        "src/services",
        "src/api",
        "src/domain",
        "src/repositories",
        "src/database/repositories",
        "--no-error-summary",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 核心模块类型检查通过！")
    else:
        errors = result.stdout.count("error:")
        print(f"⚠️  核心模块还有 {errors} 个错误")

        # 显示前几个错误
        error_lines = [line for line in result.stdout.split("\n") if "error:" in line][
            :5
        ]
        for error in error_lines:
            print(f"  • {error}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
