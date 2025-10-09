#!/usr/bin/env python3
"""
修复数据库模型中缺少的导入
"""

import ast
from pathlib import Path
from typing import Dict, List, Set


def find_used_types(content: str) -> Dict[str, Set[str]]:
    """查找文件中使用的类型"""
    tree = ast.parse(content)
    used_types = set()

    # 查找所有类型注解
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            # 查找类型注解
            if isinstance(node.annotation, ast.Name):
                used_types.add(node.annotation.id)
            elif isinstance(node.annotation, ast.Subscript):
                if isinstance(node.annotation.value, ast.Name):
                    base_type = node.annotation.value.id
                    if (
                        base_type == "Dict"
                        or base_type == "List"
                        or base_type == "Optional"
                    ):
                        used_types.add(base_type)
                    elif isinstance(node.annotation.slice, ast.Name):
                        used_types.add(node.annotation.slice.id)

        # 查找函数返回类型
        if isinstance(node, ast.FunctionDef):
            if node.returns:
                if isinstance(node.returns, ast.Name):
                    used_types.add(node.returns.id)
                elif isinstance(node.returns, ast.Subscript):
                    if isinstance(node.returns.value, ast.Name):
                        used_types.add(node.returns.value.id)

    # 查找 Mapped 注解中的类型
    import re

    mapped_pattern = r"Mapped\[([^\]]+)\]"
    for match in re.finditer(mapped_pattern, content):
        type_content = match.group(1)
        # 提取基础类型
        if "[" in type_content:
            base_type = type_content.split("[")[0]
        else:
            base_type = type_content
        used_types.add(base_type)

    # 查找其他常用类型
    common_types = [
        "Dict",
        "List",
        "Optional",
        "Any",
        "Union",
        "datetime",
        "Decimal",
        "timedelta",
    ]
    for type_name in common_types:
        if type_name in content:
            used_types.add(type_name)

    return {
        "typing": {
            t for t in used_types if t in ["Dict", "List", "Optional", "Any", "Union"]
        },
        "datetime": {t for t in used_types if t in ["datetime", "timedelta"]},
        "decimal": {t for t in used_types if t == "Decimal"},
    }


def fix_file(file_path: Path):
    """修复单个文件的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    used_types = find_used_types(content)
    lines = content.split("\n")

    # 查找导入部分
    import_lines = []
    other_lines = []
    in_imports = True

    for line in lines:
        stripped = line.strip()
        if in_imports and (
            stripped.startswith("from ")
            or stripped.startswith("import ")
            or stripped == ""
        ):
            import_lines.append(line)
        else:
            in_imports = False
            other_lines.append(line)

    # 检查需要添加的导入
    needs_typing = used_types["typing"] and not any(
        "typing" in imp for imp in import_lines
    )
    needs_datetime = used_types["datetime"] and not any(
        "datetime" in imp for imp in import_lines if "sqlalchemy" not in imp
    )
    needs_decimal = used_types["decimal"] and not any(
        "Decimal" in imp for imp in import_lines if "sqlalchemy" not in imp
    )

    if not (needs_typing or needs_datetime or needs_decimal):
        return False

    # 构建新的导入
    new_imports = []

    if needs_typing:
        types_str = ", ".join(sorted(used_types["typing"]))
        new_imports.append(f"from typing import {types_str}")

    if needs_datetime:
        new_imports.append("from datetime import datetime")
        if "timedelta" in used_types["datetime"]:
            new_imports.append("from datetime import timedelta")

    if needs_decimal:
        new_imports.append("from decimal import Decimal")

    # 插入导入
    if new_imports:
        # 找到插入位置
        insert_pos = 0
        for i, line in enumerate(import_lines):
            if line.startswith("from enum import") or line.startswith(
                "from datetime import"
            ):
                insert_pos = i
                break

        # 插入新导入
        for imp in new_imports:
            import_lines.insert(insert_pos, imp)
            insert_pos += 1

        # 重新构建内容
        new_lines = import_lines + [""] + other_lines
        new_content = "\n".join(new_lines)

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✓ 修复: {file_path.relative_to('.')} - 添加了 {', '.join(new_imports)}")
        return True

    return False


def main():
    """主函数"""
    models_dir = Path("src/database/models")
    fixed_count = 0

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if fix_file(py_file):
            fixed_count += 1

    print(f"\n修复完成！共修复 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
