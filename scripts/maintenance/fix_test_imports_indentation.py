#!/usr/bin/env python3
"""
修复 tests/unit/ 目录下所有测试文件中的导入语句缩进问题
"""

import ast
from pathlib import Path
from typing import Tuple, Set


def fix_import_indentation(filepath: str) -> bool:
    """修复单个文件的导入语句缩进问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []
        changes_made = False

        for line in lines:
            # 检查是否是导入语句
            stripped_line = line.strip()
            if stripped_line.startswith("import ") or stripped_line.startswith("from "):
                # 如果有缩进，移除缩进
                if line != stripped_line:
                    fixed_lines.append(stripped_line)
                    changes_made = True
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        if changes_made:
            # 写回文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(fixed_lines))

            # 验证修复后的文件语法是否正确
            try:
                ast.parse("\n".join(fixed_lines))
                return True
            except SyntaxError:
                # 如果修复后仍有语法错误，恢复原文件
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return False

        return False

    except Exception as e:
        print(f"处理文件 {filepath} 时出错: {e}")
        return False


def check_file_syntax(filepath: str) -> bool:
    """检查文件语法是否正确"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        return True
            try:
                pass
def fix_all_import_indentations(directory: str) -> Tuple[int, int, Set[str]]:
    """修复目录下所有文件的导入语句缩进问题"""
    directory_path = Path(directory)
    total_files = 0
    fixed_files = 0
    fixed_files_list = set()

    for py_file in directory_path.rglob("*.py"):
        total_files += 1

        # 检查原始文件是否有语法错误
        has_syntax_error = not check_file_syntax(str(py_file))

        if has_syntax_error:
            print(f"发现语法错误文件: {py_file}")

            # 尝试修复导入语句缩进
            if fix_import_indentation(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 已修复: {py_file}")
            else:
                print(f"❌ 修复失败: {py_file}")
        else:
            # 即使没有语法错误，也检查并修复导入语句缩进
            if fix_import_indentation(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 优化导入格式: {py_file}")

    return total_files, fixed_files, fixed_files_list


def main():
    """主函数"""
    target_directory = "/home/user/projects/FootballPrediction/tests/unit"

    print(f"开始扫描和修复 {target_directory} 目录下的导入语句缩进问题...")
    print("=" * 80)

    total_files, fixed_files, fixed_files_list = fix_all_import_indentations(target_directory)

    print("=" * 80)
    print("扫描完成!")
    print(f"总共处理文件数: {total_files}")
    print(f"修复文件数: {fixed_files}")

    if fixed_files_list:
        print("\n修复的文件列表:")
        for file_path in sorted(fixed_files_list):
            print(f"  - {file_path}")
    else:
        print("没有需要修复的文件")

    # 再次检查是否还有语法错误的文件
    print("\n检查修复后的文件语法...")
    remaining_errors = []
    for py_file in Path(target_directory).rglob("*.py"):
        if not check_file_syntax(str(py_file)):
            remaining_errors.append(str(py_file))

    if remaining_errors:
        print(f"\n仍有语法错误的文件 ({len(remaining_errors)} 个):")
        for file_path in remaining_errors:
            print(f"  - {file_path}")
    else:
        print("✅ 所有文件语法正确!")


if __name__ == "__main__":
    main()
