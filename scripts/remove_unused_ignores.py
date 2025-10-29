#!/usr/bin/env python3
"""
自动移除unused type: ignore注释的脚本
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple


def get_unused_ignore_errors() -> List[Tuple[str, int]]:
    """获取所有unused-ignore错误"""
    cmd = ["mypy", "src/", "--ignore-missing-imports", "--show-error-codes", "--no-error-summary"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    errors = []

    for line in result.stdout.strip().split("\n"):
        if "unused-ignore" in line:
            # 解析格式: filename:line: error: message [unused-ignore]
            match = re.match(r"^([^:]+):(\d+):", line)
            if match:
                filename, line_num = match.groups()
                errors.append((filename, int(line_num)))

    return errors


def remove_unused_ignore_from_file(file_path: str, line_num: int) -> bool:
    """从指定文件中移除特定行的type: ignore注释"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 确保行号有效
        if 1 <= line_num <= len(lines):
            line = lines[line_num - 1]

            # 移除 type: ignore 注释
            # 支持多种格式: # type: ignore,  # type: ignore,  # type: ignore[error_code]
            updated_line = re.sub(r"\s*#\s*type:\s*ignore(?:\[[^\]]*\])?\s*$", "", line)

            # 如果行有变化，更新文件
            if updated_line != line:
                lines[line_num - 1] = updated_line
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True

        return False
    except Exception as e:
        print(f"   ❌ 处理 {file_path}:{line_num} 时出错: {e}")
        return False


def main():
    """主函数"""
    print("🔧 开始移除unused type: ignore注释...")

    # 获取所有unused-ignore错误
    errors = get_unused_ignore_errors()

    if not errors:
        print("✅ 没有发现unused-ignore错误")
        return 0

    print(f"📊 发现 {len(errors)} 个unused-ignore错误")

    # 按文件分组处理
    files_to_fix = {}
    for filename, line_num in errors:
        if filename not in files_to_fix:
            files_to_fix[filename] = []
        files_to_fix[filename].append(line_num)

    fixed_count = 0

    # 处理每个文件
    for filename, line_nums in files_to_fix.items():
        print(f"🔧 处理文件: {filename}")

        # 从大到小排序行号，避免移除时行号变化的问题
        line_nums.sort(reverse=True)

        for line_num in line_nums:
            if remove_unused_ignore_from_file(filename, line_num):
                print(f"   ✅ 移除第 {line_num} 行的type: ignore")
                fixed_count += 1

    print("\n📈 修复结果:")
    print(f"   处理错误数: {len(errors)}")
    print(f"   成功修复数: {fixed_count}")

    # 验证修复结果
    print("\n🔍 验证修复结果...")
    remaining_errors = get_unused_ignore_errors()

    if remaining_errors:
        print(f"   ⚠️  剩余 {len(remaining_errors)} 个unused-ignore错误")
    else:
        print("   ✅ 所有unused-ignore错误已清理")

    return 0


if __name__ == "__main__":
    exit(main())
