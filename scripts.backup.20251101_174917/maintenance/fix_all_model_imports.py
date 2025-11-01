#!/usr/bin/env python3
"""
修复所有数据库模型文件的导入
"""

import re
from pathlib import Path
from typing import Dict, List


def analyze_file_needs(file_path: Path) -> Dict[str, List[str]]:
    """分析文件需要哪些导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    needs = {
        "Enum": [],
        "Column": [],
        "Integer": [],
        "String": [],
        "DateTime": [],
        "ForeignKey": [],
        "Boolean": [],
        "DECIMAL": [],
        "Text": [],
        "Float": [],
        "Index": [],
        "Mapped": [],
        "mapped_column": [],
        "relationship": [],
        "SQLEnum": [],
        "CheckConstraint": [],
        "JSON": [],
        "func": [],
    }

    # 检查使用了哪些类
    for class_name in needs:
        pattern = rf"\b{class_name}\b"
        if re.search(pattern, content):
            needs[class_name].append(class_name)

    return needs


def fix_file_imports(file_path: Path):
    """修复文件的导入"""
    needs = analyze_file_needs(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # 找到导入部分
    import_lines = []
    other_lines = []
    in_imports = True

    for line in lines:
        stripped = line.strip()
        if in_imports and (
            stripped.startswith("from ") or stripped.startswith("import ") or stripped == ""
        ):
            if stripped.startswith("from ") or stripped.startswith("import "):
                import_lines.append(line)
            continue
        else:
            in_imports = False
            other_lines.append(line)

    # 收集需要的导入
    new_imports = []

    # 标准库导入
    if needs["Enum"]:
        new_imports.append("from enum import Enum")

    # 第三方库导入
    sqlalchemy_core = []
    sqlalchemy_orm = []

    for class_name in needs["Column"]:
        sqlalchemy_core.append("Column")
    for class_name in needs["Integer"]:
        sqlalchemy_core.append("Integer")
    for class_name in needs["String"]:
        sqlalchemy_core.append("String")
    for class_name in needs["DateTime"]:
        sqlalchemy_core.append("DateTime")
    for class_name in needs["ForeignKey"]:
        sqlalchemy_core.append("ForeignKey")
    for class_name in needs["Boolean"]:
        sqlalchemy_core.append("Boolean")
    for class_name in needs["DECIMAL"]:
        sqlalchemy_core.append("DECIMAL")
    for class_name in needs["Text"]:
        sqlalchemy_core.append("Text")
    for class_name in needs["Float"]:
        sqlalchemy_core.append("Float")
    for class_name in needs["Index"]:
        sqlalchemy_core.append("Index")
    for class_name in needs["SQLEnum"]:
        sqlalchemy_core.append("Enum as SQLEnum")
    for class_name in needs["CheckConstraint"]:
        sqlalchemy_core.append("CheckConstraint")
    for class_name in needs["JSON"]:
        sqlalchemy_core.append("JSON")
    for class_name in needs["func"]:
        sqlalchemy_core.append("func")

    for class_name in needs["Mapped"]:
        sqlalchemy_orm.append("Mapped")
    for class_name in needs["mapped_column"]:
        sqlalchemy_orm.append("mapped_column")
    for class_name in needs["relationship"]:
        sqlalchemy_orm.append("relationship")

    # 去重
    sqlalchemy_core = list(set(sqlalchemy_core))
    sqlalchemy_orm = list(set(sqlalchemy_orm))

    # 添加导入
    if sqlalchemy_core:
        new_imports.append(f"from sqlalchemy import {', '.join(sorted(sqlalchemy_core))}")
    if sqlalchemy_orm:
        new_imports.append(f"from sqlalchemy.orm import {', '.join(sorted(sqlalchemy_orm))}")

    # 检查类型注解
    if any("Mapped[" in line for line in other_lines):
        if "from typing import" not in content and "import typing" not in content:
            new_imports.append("from typing import TYPE_CHECKING")

    # 构建新内容
    final_lines = []

    # 添加现有导入（保留非SQLAlchemy的）
    for imp in import_lines:
        if not imp.startswith("from sqlalchemy") and not imp.startswith("import sqlalchemy"):
            final_lines.append(imp)

    # 添加空行
    if final_lines and new_imports:
        final_lines.append("")

    # 添加新的SQLAlchemy导入
    final_lines.extend(new_imports)

    # 添加项目导入
    for imp in import_lines:
        if imp.startswith("from ..base import") or imp.startswith("from src.database.base"):
            final_lines.append(imp)

    # 添加剩余内容
    final_lines.append("")
    final_lines.extend(other_lines)

    # 写回文件
    new_content = "\n".join(final_lines)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✓ 修复: {file_path.relative_to('.')}")
        return True

    return False


def main():
    """主函数"""
    models_dir = Path("src/database/models")
    fixed_count = 0

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if fix_file_imports(py_file):
            fixed_count += 1

    print(f"\n修复完成！共修复 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
