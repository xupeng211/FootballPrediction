#!/usr/bin/env python3
"""
批量修复特定模式的缩进错误
Batch fix specific pattern indentation errors
"""

import os
import re
from pathlib import Path


def fix_function_with_comment_pattern(file_path: str) -> bool:
    """修复函数定义和注释在同一行的模式"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        modified = False
        i = 0
        while i < len(lines):
            line = lines[i]

            # 查找模式: def name(...):    """comment"""
            if (
                "def " in line
                and ":" in line
                and '"""' in line
                and not line.strip().startswith("#")
            ):
                # 检查是否是函数定义和注释在同一行
                match = re.match(r'^(\s*)(def\s+[^:]+:)\s+(.+?)\s*"""([^"]*)"""', line)
                if match:
                    indent, func_def, middle, docstring = match.groups()

                    # 创建新行
                    if middle.strip():
                        new_lines = [
                            f"{indent}{func_def}",
                            f"{indent}    {middle}",
                            f'{indent}    """{docstring}"""',
                        ]
                    else:
                        new_lines = [f"{indent}{func_def}", f'{indent}    """{docstring}"""']

                    # 替换原行
                    lines[i : i + 1] = new_lines
                    modified = True
                    i += len(new_lines) - 1
                    print(f"✅ 修复函数定义: {file_path}:{i+1}")

            i += 1

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True

        return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False


def fix_assignment_with_comment_pattern(file_path: str) -> bool:
    """修复赋值语句和注释在同一行的模式"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        modified = False
        for i, line in enumerate(lines):
            # 查找模式: variable = value    """comment"""
            if "=" in line and '"""' in line and not line.strip().startswith("#"):
                match = re.match(r'^(\s*[^=]+=\s*)(.+?)\s*"""([^"]*)"""', line)
                if match:
                    indent, assignment, docstring = match.groups()

                    # 创建新行
                    new_line = f"{indent}{assignment}  # {docstring}"
                    lines[i] = new_line
                    modified = True
                    print(f"✅ 修复赋值注释: {file_path}:{i+1}")

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True

        return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False


def find_files_with_indentation_errors() -> list:
    """查找有缩进错误的文件"""
    files_with_errors = []

    for root, dirs, files in os.walk("src/"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 检查是否包含问题模式
                    if re.search(r'def\s+[^:]+:\s+"""', content):
                        files_with_errors.append(file_path)
                    elif re.search(r'=\s+.*?"""', content):
                        files_with_errors.append(file_path)

                except Exception:
                    continue

    return files_with_errors


def main():
    """主函数"""
    print("🔧 批量修复特定缩进模式")
    print("=" * 60)

    # 查找有问题的文件
    files_to_fix = find_files_with_indentation_errors()

    if not files_to_fix:
        print("✅ 没有发现需要修复的文件")
        return

    print(f"📊 发现 {len(files_to_fix)} 个文件需要修复")

    total_fixes = 0

    # 修复每个文件
    for file_path in files_to_fix:
        print(f"\n🔧 处理文件: {file_path}")

        if fix_function_with_comment_pattern(file_path):
            total_fixes += 1

        if fix_assignment_with_comment_pattern(file_path):
            total_fixes += 1

    print(f"\n{'='*60}")
    print("📊 修复统计")
    print(f"{'='*60}")
    print(f"   修复文件数: {total_fixes}")

    # 验证修复结果
    print("\n🔍 验证修复结果...")
    remaining_files = find_files_with_indentation_errors()

    if remaining_files:
        print(f"⚠️  仍有 {len(remaining_files)} 个文件需要手动修复:")
        for file_path in remaining_files[:5]:
            print(f"   {file_path}")
        if len(remaining_files) > 5:
            print(f"   ... 还有 {len(remaining_files) - 5} 个文件")
    else:
        print("✅ 所有已知模式已修复完成")


if __name__ == "__main__":
    main()
