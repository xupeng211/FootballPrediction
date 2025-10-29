#!/usr/bin/env python3
"""
修复__init__.py文件中的F401错误
"""

from pathlib import Path
import subprocess


def find_init_files():
    """查找所有__init__.py文件"""
    src_path = Path("src")
    init_files = list(src_path.glob("**/__init__.py"))
    return init_files


def fix_init_file(file_path):
    """修复单个__init__.py文件的F401错误"""
    print(f"\n处理: {file_path}")

    # 读取原文件
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines = []

    # 跳过第一行的导入（如果只是导入typing）
    skip_first = False
    if len(lines) > 1:
        first_line = lines[0].strip()
        if first_line.startswith("from typing import") and len(first_line.split(",")) > 2:
            # 如果第一行只是导入typing的多个类型，跳过
            print(f"  - 跳过typing导入: {first_line}")
            skip_first = True

    # 保留非空行和非纯typing导入行
    for i, line in enumerate(lines):
        if i == 0 and skip_first:
            continue

        # 跳过空的typing导入
        if line.strip().startswith("from typing import") and line.strip().endswith("Union"):
            continue

        new_lines.append(line)

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    # 使用ruff修复
    cmd = f"ruff check --fix --select F401 {file_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True)

    if result.returncode == 0:
        print("  ✅ 已修复")
    else:
        print("  ⚠️ 需要手动检查")


def main():
    """主函数"""
    print("🔧 修复__init__.py文件中的F401错误")

    init_files = find_init_files()
    print(f"\n找到 {len(init_files)} 个__init__.py文件")

    fixed_count = 0
    for file_path in init_files:
        # 检查是否有F401错误
        cmd = f"ruff check --select F401 {file_path} 2>/dev/null | grep F401"
        result = subprocess.run(cmd, shell=True, capture_output=True)

        if result.returncode == 0 and result.stdout:
            fix_init_file(file_path)
            fixed_count += 1

    print(f"\n✅ 处理了 {fixed_count} 个文件")

    # 统计剩余错误
    cmd = "ruff check --select F401 src/ 2>&1 | grep 'F401' | wc -l"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    remaining = int(result.stdout.strip()) if result.stdout.strip() else 0

    print(f"\n📊 剩余F401错误: {remaining}个")


if __name__ == "__main__":
    main()
