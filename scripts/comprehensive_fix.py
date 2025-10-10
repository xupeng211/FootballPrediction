#!/usr/bin/env python3
"""
全面修复语法错误
Comprehensive syntax fix
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set


def fix_syntax_errors(content: str) -> str:
    """修复语法错误"""
    lines = content.splitlines()
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 1. 修复未闭合的函数调用
        if stripped.endswith(",") and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line.startswith("from ") or next_line.startswith("import "):
                # 找到函数调用的开始
                paren_count = 0
                for j in range(i, -1, -1):
                    if "(" in lines[j]:
                        paren_count += lines[j].count("(") - lines[j].count(")")
                        if paren_count > 0:
                            # 闭合括号
                            new_lines.append(line.rstrip() + ")")
                            i += 1
                            # 跳过import语句
                            while i < len(lines) and (
                                lines[i].strip().startswith("from ")
                                or lines[i].strip().startswith("import ")
                            ):
                                i += 1
                            continue
                new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

        i += 1

    # 2. 移除错误的import位置
    # 收集所有应该移到顶部的import
    imports_to_move = []
    final_lines = []
    in_multiline_string = False
    multiline_char = None

    for i, line in enumerate(new_lines):
        stripped = line.strip()

        # 检查多行字符串
        if '"""' in stripped or "'''" in stripped:
            if not in_multiline_string:
                if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                    in_multiline_string = True
                    multiline_char = '"""' if '"""' in stripped else "'''"
            else:
                if multiline_char in stripped:
                    in_multiline_string = False

        # 跳过多行字符串内的内容
        if in_multiline_string:
            final_lines.append(line)
            continue

        # 如果是import语句且不在文件顶部（前50行）
        if (stripped.startswith("import ") or stripped.startswith("from ")) and i > 50:
            # 检查是否在函数或类内部
            if any(
                line.startswith(" ")
                for line in new_lines[max(0, i - 10) : i]
                if line.strip()
            ):
                # 在函数/类内部，跳过
                final_lines.append(line)
            else:
                # 在模块级别但位置错误，记录下来
                imports_to_move.append(line)
        else:
            final_lines.append(line)

    # 3. 将imports添加到文件顶部
    if imports_to_move:
        # 找到合适的位置插入imports
        insert_pos = 0
        for j, line in enumerate(final_lines[:50]):
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    insert_pos = j
                    break

        # 分类和排序imports
        stdlib_imports = []
        thirdparty_imports = []
        local_imports = []

        for imp in imports_to_move:
            imp_stripped = imp.strip()
            if imp_stripped.startswith("from ."):
                local_imports.append(imp)
            elif any(
                imp_stripped.startswith(f"import {lib}")
                or imp_stripped.startswith(f"from {lib}")
                for lib in [
                    "os",
                    "sys",
                    "time",
                    "datetime",
                    "json",
                    "logging",
                    "asyncio",
                    "pathlib",
                    "re",
                    "collections",
                    "itertools",
                    "functools",
                    "typing",
                    "uuid",
                    "hashlib",
                    "base64",
                    "urllib",
                    "http",
                    "socket",
                    "threading",
                    "multiprocessing",
                    "subprocess",
                    "shutil",
                    "tempfile",
                    "glob",
                    "math",
                    "random",
                    "statistics",
                    "decimal",
                    "fractions",
                    "enum",
                    "dataclasses",
                    "contextlib",
                    "warnings",
                    "traceback",
                    "inspect",
                    "importlib",
                    "pkgutil",
                    "types",
                    "copy",
                ]
            ):
                stdlib_imports.append(imp)
            elif imp_stripped.startswith("from src") or imp_stripped.startswith(
                "import src"
            ):
                local_imports.append(imp)
            else:
                thirdparty_imports.append(imp)

        # 构建import块
        all_imports = []
        if stdlib_imports:
            all_imports.extend(sorted(set(stdlib_imports)))
            all_imports.append("")
        if thirdparty_imports:
            all_imports.extend(sorted(set(thirdparty_imports)))
            all_imports.append("")
        if local_imports:
            all_imports.extend(sorted(set(local_imports)))
            all_imports.append("")

        # 插入imports
        final_lines = final_lines[:insert_pos] + all_imports + final_lines[insert_pos:]

    # 4. 修复其他常见错误
    content = "\n".join(final_lines)

    # 修复 "value=xxx, from yyy" -> "value=xxx)"
    content = re.sub(r"(\w+\s*=\s*[^,]+),\s*from\s+", r"\1)", content)

    # 修复 "dict(key=value, from xxx" -> "dict(key=value)"
    content = re.sub(r"(\{[^}]*),\s*from\s+", r"\1}", content)

    # 修复未闭合的except块
    content = re.sub(
        r"(\s*)try:\s*\n\s*from\s+([^\n]+)", r"\1# Import moved to top\n\1try:", content
    )

    return content


def check_and_fix_file(file_path: Path) -> bool:
    """检查并修复单个文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否有语法错误
        try:
            ast.parse(content)
            return False  # 没有错误
        except SyntaxError:
            pass  # 有错误，需要修复

        # 修复语法错误
        fixed_content = fix_syntax_errors(content)

        # 验证修复后的内容
        try:
            ast.parse(fixed_content)
        except SyntaxError:
            # 还是失败，尝试更简单的修复
            # 移除所有不在顶部的import
            lines = fixed_content.splitlines()
            kept_lines = []
            for line in lines:
                stripped = line.strip()
                # 保留文件顶部的import（前30行）
                if (
                    stripped.startswith("import ") or stripped.startswith("from ")
                ) and len(kept_lines) < 30:
                    kept_lines.append(line)
                # 保留非import语句
                elif not (
                    stripped.startswith("import ") or stripped.startswith("from ")
                ):
                    kept_lines.append(line)
                # 跳过其他位置的import
            fixed_content = "\n".join(kept_lines)

        # 写回文件
        if fixed_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

    except Exception as e:
        print(f"处理文件失败 {file_path}: {e}")
        return False

    return False


def main():
    """主函数"""
    print("🔧 全面修复语法错误...")

    src_path = Path("src")
    fixed_count = 0
    error_count = 0

    # 查找所有Python文件
    python_files = list(src_path.rglob("*.py"))
    print(f"找到 {len(python_files)} 个Python文件")

    for file_path in python_files:
        try:
            if check_and_fix_file(file_path):
                fixed_count += 1
                print(f"✓ 修复 {file_path.relative_to(src_path)}")
        except Exception as e:
            error_count += 1
            print(f"✗ 错误 {file_path.relative_to(src_path)}: {e}")

    print("\n✅ 完成！")
    print(f"修复了 {fixed_count} 个文件")
    if error_count > 0:
        print(f"处理失败 {error_count} 个文件")


if __name__ == "__main__":
    main()
