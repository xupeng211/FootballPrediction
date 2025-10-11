#!/usr/bin/env python3
"""
第二阶段：清理F401未使用导入错误
"""

import subprocess
import os
from pathlib import Path
import re


def get_f401_files():
    """获取所有有F401错误的文件"""
    print("🔍 正在扫描F401错误...")

    cmd = "ruff check --select F401 src/ --output-format=json"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ 扫描失败")
        return []

    # 解析JSON输出
    import json

    try:
        data = json.loads(result.stdout)
        files = {}
        for item in data:
            file_path = item["filename"]
            if file_path not in files:
                files[file_path] = []
            files[file_path].append(
                {"line": item["location"]["row"], "message": item["message"]}
            )
        return files
    except Exception:
        # 如果JSON解析失败，使用文本方式
        files = {}
        for line in result.stdout.split("\n"):
            if ":" in line and "F401" in line:
                parts = line.split(":")
                if len(parts) >= 3:
                    file_path = parts[0]
                    if file_path not in files:
                        files[file_path] = []
                    files[file_path].append({"line": parts[1], "message": line})
        return files


def clean_file_f401(file_path, dry_run=True):
    """清理单个文件的F401错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        new_lines = []
        removed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 检查是否是F401错误行
            if "# F401" in line or "F401" in line:
                # 查找导入语句
                import_line_idx = i
                while import_line_idx >= 0 and not (
                    lines[import_line_idx].strip().startswith("import ")
                    or lines[import_line_idx].strip().startswith("from ")
                ):
                    import_line_idx -= 1

                if import_line_idx >= 0:
                    # 检查是否是多行导入
                    if lines[import_line_idx].strip().endswith("("):
                        # 多行导入，找到匹配的)
                        j = import_line_idx + 1
                        while j < len(lines) and ")" not in lines[j]:
                            removed_lines.append(j)
                            j += 1
                        if j < len(lines):
                            removed_lines.append(j)
                        # 删除整个多行导入
                        for idx in sorted(removed_lines, reverse=True):
                            if idx < len(lines):
                                del lines[idx]
                        i = import_line_idx
                    else:
                        # 单行导入，直接删除
                        del lines[import_line_idx]
                        i = import_line_idx
                else:
                    new_lines.append(line)
                    i += 1
            else:
                new_lines.append(line)
                i += 1

        # 写入文件
        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))

        return len(removed_lines) > 0
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False


def batch_clean_f401(limit=50):
    """批量清理F401错误"""
    files = get_f401_files()
    total_files = len(files)
    total_errors = sum(len(errors) for errors in files.values())

    print(f"\n📊 发现 {total_files} 个文件有 F401 错误")
    print(f"📊 总计 {total_errors} 个错误")

    if total_files == 0:
        print("✅ 没有F401错误需要处理")
        return

    # 先自动修复一部分
    print(f"\n🔧 开始自动修复（限制 {limit} 个文件）...")

    fixed_count = 0
    for i, (file_path, errors) in enumerate(files.items()):
        if i >= limit:
            break

        print(f"\n处理 ({i+1}/{min(limit, total_files)}): {file_path}")
        print(f"  错误数: {len(errors)}")

        # 使用ruff自动修复
        cmd = f"ruff check --fix --select F401 {file_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True)

        if result.returncode == 0:
            fixed_count += 1
            print("  ✅ 已自动修复")
        else:
            print("  ⚠️ 自动修复失败，需要手动处理")

    print(f"\n✅ 自动修复了 {fixed_count} 个文件")

    # 显示剩余的文件
    remaining = total_files - fixed_count
    if remaining > 0:
        print(f"\n⚠️ 还有 {remaining} 个文件需要手动处理")
        print("\n建议：")
        print("1. 对简单文件，使用: ruff check --fix --select F401 <file>")
        print("2. 对复杂文件，手动检查并删除未使用的导入")
        print("3. 使用 'make fmt' 格式化代码")


def main():
    """主函数"""
    print("=" * 80)
    print("🧹 第二阶段：清理F401未使用导入错误")
    print("=" * 80)

    # 先检查当前状态
    print("\n📊 当前状态:")

    # 统计F401错误
    cmd = "ruff check --select F401 src/ | wc -l"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    f401_count = int(result.stdout.strip()) if result.stdout.strip() else 0
    print(f"   F401错误数: {f401_count}")

    if f401_count == 0:
        print("\n✅ 没有F401错误需要处理！")
        return

    # 询问用户
    print(f"\n⚠️ 发现 {f401_count} 个F401错误")
    print("\n选项:")
    print("1. 自动修复前50个文件")
    print("2. 自动修复前100个文件")
    print("3. 自动修复所有文件（可能较慢）")
    print("4. 仅查看错误详情")
    print("5. 退出")

    choice = input("\n请选择 (1-5): ").strip()

    if choice == "1":
        batch_clean_f401(50)
    elif choice == "2":
        batch_clean_f401(100)
    elif choice == "3":
        batch_clean_f401(10000)
    elif choice == "4":
        print("\n📋 错误详情:")
        subprocess.run("ruff check --select F401 src/ | head -50", shell=True)
    else:
        print("退出")


if __name__ == "__main__":
    main()
