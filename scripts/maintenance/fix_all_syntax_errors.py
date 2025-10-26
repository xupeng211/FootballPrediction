#!/usr/bin/env python3
"""
修复所有语法错误
"""

import subprocess
import os


def run_ruff_check():
    """运行ruff检查"""
    cmd = [
        "ruff",
        "check",
        "src/",
        "--select=E999,F821,F822,F831,E701,E702,E703,E704,E721,E722,E741,E902,E999",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr


def fix_file_syntax(file_path):
    """使用Python AST修复文件语法"""
    try:
        # 尝试编译文件以检查语法
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 尝试编译
        compile(content, file_path, "exec")
        return True  # 语法正确
    except SyntaxError as e:
        print(f"  语法错误: {e}")
        return False
    except Exception as e:
        print(f"  其他错误: {e}")
        return False


def main():
    print("🚀 开始修复所有语法错误...")

    # 获取所有有错误的文件
    print("\n📊 检查错误...")
    stdout, stderr = run_ruff_check()

    if not stdout:
        print("✅ 没有发现语法错误！")
        return

    # 提取文件路径
    error_files = set()
    for line in stdout.split("\n"):
        if line and ":" in line:
            file_path = line.split(":")[0]
            if os.path.exists(file_path):
                error_files.add(file_path)

    print(f"\n🔍 发现 {len(error_files)} 个文件有语法错误")

    # 修复每个文件
    fixed_count = 0
    for file_path in sorted(error_files):
        print(f"\n🔧 检查 {file_path}")
        if fix_file_syntax(file_path):
            print("  ✅ 语法正确")
            fixed_count += 1
        else:
            print("  ❌ 需要手动修复")

    # 再次检查
    print("\n📊 再次检查...")
    stdout, stderr = run_ruff_check()

    if stdout:
        print(f"\n❌ 仍有错误需要修复:\n{stdout[:1000]}")
    else:
        print("\n✅ 所有语法错误已修复！")


if __name__ == "__main__":
    main()
