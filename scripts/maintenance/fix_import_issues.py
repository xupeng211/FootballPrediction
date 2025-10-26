#!/usr/bin/env python3
"""
修复 tests/unit/ 目录下所有测试文件中的复杂导入问题
"""

import ast
from pathlib import Path
from typing import Tuple, Set


def fix_complex_imports(content: str) -> str:
    """修复复杂的导入问题"""
    lines = content.split("\n")
    fixed_lines = []
    in_import_block = False
    import_block_lines = []

    for line in lines:
        stripped_line = line.strip()

        # 检查是否是导入语句（包括缩进的）
        if stripped_line.startswith("import ") or stripped_line.startswith("from "):
            in_import_block = True
            import_block_lines.append(stripped_line)
        else:
            # 如果之前有导入块，先处理导入块
            if in_import_block and import_block_lines:
                # 过滤掉空行和无效的导入语句
                valid_imports = []
                for import_line in import_block_lines:
                    if (
                        import_line
                        and not import_line.startswith("from ")
                        and not import_line.startswith("import ")
                    ):
                        continue

                    # 检查是否是完整的导入语句
                    if (
                        import_line.startswith("from ")
                        and " import " not in import_line
                    ):
                        continue

                    if import_line.startswith("import ") and import_line == "import":
                        continue

                    valid_imports.append(import_line)

                # 添加有效的导入语句
                for import_line in valid_imports:
                    fixed_lines.append(import_line)

                import_block_lines = []
                in_import_block = False

            # 添加非导入行
            fixed_lines.append(line)

    # 处理最后剩余的导入块
    if in_import_block and import_block_lines:
        valid_imports = []
        for import_line in import_block_lines:
            if (
                import_line
                and not import_line.startswith("from ")
                and not import_line.startswith("import ")
            ):
                continue

            if import_line.startswith("from ") and " import " not in import_line:
                continue

            if import_line.startswith("import ") and import_line == "import":
                continue

            valid_imports.append(import_line)

        for import_line in valid_imports:
            fixed_lines.append(import_line)

    return "\n".join(fixed_lines)


def fix_incomplete_imports(content: str) -> str:
    """修复不完整的导入语句"""
    lines = content.split("\n")
    fixed_lines = []
    skip_next_line = False

    for i, line in enumerate(lines):
        if skip_next_line:
            skip_next_line = False
            continue

        stripped_line = line.strip()

        # 检查不完整的from导入
        if stripped_line.startswith("from ") and " import " not in stripped_line:
            # 查找下一行是否有import
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("import "):
                    # 合并两行
                    combined = f"{stripped_line} {next_line}"
                    fixed_lines.append(combined)
                    skip_next_line = True
                    continue
                else:
                    # 如果下一行没有import，跳过这个不完整的导入
                    continue
            else:
                # 最后一行，跳过不完整的导入
                continue

        # 检查不完整的import导入（只有import而没有后续内容）
        if stripped_line == "import":
            # 查找下一行是否有实际导入内容
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (
                    next_line
                    and not next_line.startswith("import ")
                    and not next_line.startswith("from ")
                ):
                    # 合并两行
                    combined = f"import {next_line}"
                    fixed_lines.append(combined)
                    skip_next_line = True
                    continue
                else:
                    # 跳过这个不完整的导入
                    continue
            else:
                # 最后一行，跳过不完整的导入
                continue

        # 检查只有'from'的情况
        if stripped_line == "from":
            # 跳过这种不完整的导入
            continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def remove_leading_spaces_from_imports(content: str) -> str:
    """移除导入语句前的前导空格"""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        stripped_line = line.strip()

        # 如果是导入语句且有前导空格，移除空格
        if (
            stripped_line.startswith("import ") or stripped_line.startswith("from ")
        ) and line != stripped_line:
            fixed_lines.append(stripped_line)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_import_file(filepath: str) -> bool:
    """修复单个文件的导入问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 应用所有修复
        content = original_content
        content = remove_leading_spaces_from_imports(content)
        content = fix_complex_imports(content)
        content = fix_incomplete_imports(content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            # 验证修复后的文件语法是否正确
            try:
                ast.parse(content)
                return True
            except SyntaxError:
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


def fix_all_import_files(directory: str) -> Tuple[int, int, Set[str]]:
    """修复目录下所有文件的导入问题"""
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

            # 尝试修复导入问题
            if fix_import_file(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 已修复: {py_file}")
            else:
                print(f"❌ 修复失败: {py_file}")
        else:
            # 即使没有语法错误，也检查并优化导入语句
            if fix_import_file(str(py_file)):
                fixed_files += 1
                fixed_files_list.add(str(py_file))
                print(f"✅ 优化导入格式: {py_file}")

    return total_files, fixed_files, fixed_files_list


def main():
    """主函数"""
    target_directory = "/home/user/projects/FootballPrediction/tests/unit"

    print(f"开始扫描和修复 {target_directory} 目录下的复杂导入问题...")
    print("=" * 80)

    total_files, fixed_files, fixed_files_list = fix_all_import_files(target_directory)

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
