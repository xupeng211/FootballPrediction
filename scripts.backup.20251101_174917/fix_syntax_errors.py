#!/usr/bin/env python3
"""
系统性语法错误修复脚本
基于Issue #171: 修复剩余71个语法错误
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

def check_syntax_errors(directory: str = "src") -> List[Tuple[str, str]]:
    """检查Python语法错误

    Args:
        directory: 要检查的目录

    Returns:
        List[Tuple[str, str]]: 错误列表 (文件路径, 错误信息)
    """
    errors = []

    for py_file in Path(directory).rglob("*.py"):
        try:
            # 使用python -m py_compile检查语法
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                errors.append((str(py_file), result.stderr))
        except subprocess.TimeoutExpired:
            errors.append((str(py_file), "Timeout during compilation"))
        except Exception as e:
            errors.append((str(py_file), f"Error checking file: {e}"))

    return errors

def categorize_errors(errors: List[Tuple[str, str]]) -> dict:
    """按目录分类错误

    Args:
        errors: 错误列表

    Returns:
        dict: 按目录分类的错误
    """
    categories = {
        "api": [],
        "services": [],
        "core": [],
        "database": [],
        "domain": [],
        "utils": [],
        "other": []
    }

    for file_path, error_msg in errors:
        if "src/api/" in file_path:
            categories["api"].append((file_path, error_msg))
        elif "src/services/" in file_path:
            categories["services"].append((file_path, error_msg))
        elif "src/core/" in file_path:
            categories["core"].append((file_path, error_msg))
        elif "src/database/" in file_path:
            categories["database"].append((file_path, error_msg))
        elif "src/domain/" in file_path:
            categories["domain"].append((file_path, error_msg))
        elif "src/utils/" in file_path:
            categories["utils"].append((file_path, error_msg))
        else:
            categories["other"].append((file_path, error_msg))

    return categories

def print_error_summary(categories: dict):
    """打印错误摘要

    Args:
        categories: 按目录分类的错误
    """
    total_errors = sum(len(errors) for errors in categories.values())

    print("=" * 60)
    print(f"📊 语法错误检查结果 - 总计: {total_errors} 个文件有错误")
    print("=" * 60)

    for category, errors in categories.items():
        if errors:
            print(f"\n🔸 {category.upper()} 目录 ({len(errors)} 个文件):")
            for i, (file_path, error_msg) in enumerate(errors[:3], 1):  # 只显示前3个
                print(f"  {i}. {file_path}")
                # 提取关键错误信息
                lines = error_msg.split('\n')
                for line in lines:
                    if 'SyntaxError' in line or 'IndentationError' in line:
                        print(f"     错误: {line.strip()}")
                        break

            if len(errors) > 3:
                print(f"     ... 还有 {len(errors) - 3} 个文件")

    print(f"\n📈 错误分布统计:")
    for category, errors in categories.items():
        if errors:
            percentage = (len(errors) / total_errors) * 100
            print(f"  - {category}: {len(errors)} 个文件 ({percentage:.1f}%)")

def run_ruff_check():
    """运行Ruff检查并尝试自动修复"""
    print("\n🔧 运行Ruff自动修复...")

    try:
        # 运行ruff自动修复
        result = subprocess.run(
            ["ruff", "check", "src/", "--fix"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.stdout:
            print("Ruff修复输出:")
            print(result.stdout)

        if result.stderr:
            print("Ruff警告/错误:")
            print(result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⚠️ Ruff检查超时")
        return False
    except FileNotFoundError:
        print("⚠️ Ruff未安装，跳过自动修复")
        return False

def main():
    """主函数"""
    print("🚀 开始系统性语法错误检查和修复...")

    # 1. 运行Ruff自动修复
    ruff_success = run_ruff_check()

    # 2. 检查剩余语法错误
    print("\n🔍 检查剩余语法错误...")
    errors = check_syntax_errors()

    if not errors:
        print("✅ 恭喜！没有发现语法错误")
        return

    # 3. 按目录分类错误
    categories = categorize_errors(errors)

    # 4. 打印错误摘要
    print_error_summary(categories)

    # 5. 生成修复计划
    print(f"\n📋 修复建议:")
    print("🎯 高优先级 (1-2天):")
    for category in ["api", "services", "core"]:
        if categories[category]:
            print(f"  - 修复 {category} 目录 ({len(categories[category])} 个文件)")

    print("🔄 中优先级 (1天):")
    for category in ["database", "domain", "utils", "other"]:
        if categories[category]:
            print(f"  - 修复 {category} 目录 ({len(categories[category])} 个文件)")

    # 6. 保存详细错误报告
    with open("syntax_errors_report.txt", "w", encoding="utf-8") as f:
        f.write("语法错误详细报告\n")
        f.write("=" * 40 + "\n\n")

        for category, error_list in categories.items():
            if error_list:
                f.write(f"{category.upper()} 目录:\n")
                f.write("-" * 20 + "\n")
                for file_path, error_msg in error_list:
                    f.write(f"文件: {file_path}\n")
                    f.write(f"错误: {error_msg}\n")
                    f.write("-" * 40 + "\n")
                f.write("\n")

    print(f"\n💾 详细错误报告已保存到: syntax_errors_report.txt")

    # 7. 返回状态码
    total_errors = len(errors)
    if total_errors == 0:
        print("✅ 所有语法错误已修复")
        return 0
    else:
        print(f"⚠️ 还有 {total_errors} 个文件需要修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())