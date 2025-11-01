#!/usr/bin/env python3
"""
修复变量命名问题的自动化脚本
"""

import re
import os
from pathlib import Path


def fix_variable_naming_in_file(file_path):
    """修复单个文件中的变量命名问题"""
    if not os.path.exists(file_path):
        return False, "File not found"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content
    changes_made = []

    # 1. 修复 _result → result
    # 需要小心，只替换变量名，不替换方法名或其他用法
    patterns_to_fix = [
        # _result 变量赋值
        (r"(\s+)_result\s*=", r"\1result ="),
        (r"(\s+)_result\s*:", r"\1result:"),
        # _result 变量使用（在表达式中）
        (r"(\W)_result(\W)", r"\1result\2"),
        # _data → data (参数)
        (r"(\s+)_data\s*:", r"\1data:"),
        (r"(\s+)_data\s*=", r"\1data ="),
        (r"(\W)_data(\W)", r"\1data\2"),
        # _config → config
        (r"(\s+)_config\s*:", r"\1config:"),
        (r"(\s+)_config\s*=", r"\1config ="),
        (r"(\W)_config(\W)", r"\1config\2"),
        # _metadata → metadata
        (r"(\s+)_metadata\s*:", r"\1metadata:"),
        (r"(\s+)_metadata\s*=", r"\1metadata ="),
        (r"(\W)_metadata(\W)", r"\1metadata\2"),
        # _stats → stats
        (r"(\s+)_stats\s*:", r"\1stats:"),
        (r"(\s+)_stats\s*=", r"\1stats ="),
        (r"(\W)_stats(\W)", r"\1stats\2"),
    ]

    for pattern, replacement in patterns_to_fix:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made.append(f"Applied: {pattern} → {replacement}")
            content = new_content

    # 特殊修复：处理一些特殊情况
    # 修复 Team 构造函数中的 _stats → stats
    content = re.sub(r"Team\([^)]*?_stats\s*=", r"Team(stats=", content)

    # 修复 CommandResult 中的 _data → data
    content = re.sub(r"CommandResult\([^)]*?_data\s*=", r"CommandResult(data=", content)

    # 修复 CommandResponse 中的 _data → data
    content = re.sub(r"CommandResponse\([^)]*?_data\s*=", r"CommandResponse(data=", content)

    # 如果有修改，写回文件
    if content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Fixed {len(changes_made)} patterns: {'; '.join(changes_made[:3])}"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"


def fix_files_in_directory(directory, file_patterns=None):
    """修复目录中的文件"""
    if file_patterns is None:
        file_patterns = ["*.py"]

    fixed_files = []
    failed_files = []

    for pattern in file_patterns:
        for file_path in Path(directory).rglob(pattern):
            # 跳过一些特殊目录
            if any(skip in str(file_path) for skip in [".venv", "__pycache__", ".git"]):
                continue

            success, message = fix_variable_naming_in_file(str(file_path))
            if success:
                fixed_files.append((str(file_path), message))
                print(f"✅ Fixed: {file_path}")
            else:
                if "No changes needed" not in message:
                    failed_files.append((str(file_path), message))
                    print(f"❌ Failed: {file_path} - {message}")

    return fixed_files, failed_files


def main():
    """主函数"""
    print("🔧 开始修复变量命名问题...")

    src_dir = "/home/user/projects/FootballPrediction/src"

    # 修复 src 目录
    print(f"\n📁 处理目录: {src_dir}")
    fixed, failed = fix_files_in_directory(src_dir, ["*.py"])

    print("\n📊 修复结果:")
    print(f"✅ 成功修复: {len(fixed)} 个文件")
    print(f"❌ 修复失败: {len(failed)} 个文件")

    if failed:
        print("\n❌ 失败的文件:")
        for file_path, error in failed[:5]:  # 只显示前5个
            print(f"  {file_path}: {error}")
        if len(failed) > 5:
            print(f"  ... 还有 {len(failed) - 5} 个文件")

    # 显示一些修复的例子
    if fixed:
        print("\n✅ 修复示例:")
        for file_path, message in fixed[:3]:
            print(f"  {file_path}: {message}")
        if len(fixed) > 3:
            print(f"  ... 还有 {len(fixed) - 3} 个文件")


if __name__ == "__main__":
    main()
