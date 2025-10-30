#!/usr/bin/env python3
"""
修复 tests/unit/ 目录下所有测试文件中的导入顺序问题
将文档字符串移到导入语句之前，确保正确的文件结构
"""

import ast
from pathlib import Path
from typing import Tuple, Set


def reorganize_file_structure(content: str) -> str:
    """重新组织文件结构：文档字符串 -> 导入语句 -> 其他内容"""
    lines = content.split("\n")

    # 提取文档字符串
    docstring = ""
    docstring_end = 0

    # 查找三引号文档字符串
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('"""') or line.startswith("'''"):
            # 找到文档字符串开始
            quote_type = '"""' if line.startswith('"""') else "'''"

            if line.count(quote_type) >= 2:
                # 单行文档字符串
                docstring = line
                docstring_end = i + 1
                break
            else:
                # 多行文档字符串
                docstring_lines = [line]
                i += 1
                while i < len(lines) and quote_type not in lines[i]:
                    docstring_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    docstring_lines.append(lines[i])
                    docstring = "\n".join(docstring_lines)
                    docstring_end = i + 1
                    break
        elif line == "":
            i += 1
            continue
        else:
            # 遇到非空行，停止查找文档字符串
            break

    # 提取导入语句（包括缩进的）
    imports = []
    imports_end = 0

    for i in range(docstring_end, len(lines)):
        line = lines[i].strip()

        # 跳过空行
        if line == "":
            continue

        # 如果是导入语句
        if line.startswith("import ") or line.startswith("from "):
            # 移除前导空格，添加到导入列表
            imports.append(line)
        else:
            # 遇到非导入语句，停止
            imports_end = i
            break

    # 如果没有找到其他内容，设置导入结束为文件末尾
    if imports_end == 0:
        imports_end = len(lines)

    # 提取剩余内容
    remaining_content = []
    for i in range(imports_end, len(lines)):
        remaining_content.append(lines[i])

    # 重新组织文件
    new_content = []

    # 添加文档字符串（如果有的话）
    if docstring:
        new_content.append(docstring)
        new_content.append("")

    # 添加导入语句（如果有的话）
    if imports:
        # 去重并保持顺序
        seen_imports = set()
        unique_imports = []
        for imp in imports:
            if imp not in seen_imports:
                unique_imports.append(imp)
                seen_imports.add(imp)

        for imp in unique_imports:
            new_content.append(imp)
        new_content.append("")

    # 添加剩余内容
    new_content.extend(remaining_content)

    return "\n".join(new_content)


def fix_import_file(filepath: str) -> bool:
    """修复单个文件的导入顺序问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 重新组织文件结构
        new_content = reorganize_file_structure(original_content)

        # 如果内容有变化，写回文件
        if new_content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

            # 验证修复后的文件语法是否正确
            try:
                ast.parse(new_content)
                return True
            except SyntaxError as e:
                print(f"  语法错误: {e}")
                # 如果修复后仍有语法错误，恢复原文件
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(original_content)
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
            except Exception:
        return False


def fix_all_import_order_files(directory: str) -> Tuple[int, int, Set[str]]:
    """修复目录下所有文件的导入顺序问题"""
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

            # 尝试修复导入顺序
            if fix_import_file(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 已修复: {py_file}")
            else:
                print(f"❌ 修复失败: {py_file}")
        else:
            # 即使没有语法错误，也检查并优化导入语句顺序
            if fix_import_file(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 优化导入格式: {py_file}")

    return total_files, fixed_files, fixed_files_list


def main():
    """主函数"""
    target_directory = "/home/user/projects/FootballPrediction/tests/unit"

    print(f"开始扫描和修复 {target_directory} 目录下的导入顺序问题...")
    print("=" * 80)

    total_files, fixed_files, fixed_files_list = fix_all_import_order_files(target_directory)

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
        for file_path in remaining_errors[:10]:  # 只显示前10个
            print(f"  - {file_path}")
        if len(remaining_errors) > 10:
            print(f"  ... 还有 {len(remaining_errors) - 10} 个文件")
    else:
        print("✅ 所有文件语法正确!")


if __name__ == "__main__":
    main()
