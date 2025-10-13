#!/usr/bin/env python3
"""
清理SQLAlchemy导入
"""

from pathlib import Path


def clean_file(file_path: Path):
    """清理单个文件的SQLAlchemy导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # 收集所有导入
    sqlalchemy_core_imports = set()
    sqlalchemy_orm_imports = set()
    other_imports = []
    class_body = []

    in_imports = True
    found_blank_after_imports = False

    for line in lines:
        stripped = line.strip()

        # 识别导入部分
        if in_imports:
            if stripped.startswith("from sqlalchemy import "):
                # 提取核心导入
                symbols = stripped.replace("from sqlalchemy import ", "").split(",")
                for symbol in symbols:
                    sqlalchemy_core_imports.add(symbol.strip())
            elif stripped.startswith("from sqlalchemy.orm import "):
                # 提取ORM导入
                symbols = stripped.replace("from sqlalchemy.orm import ", "").split(",")
                for symbol in symbols:
                    sqlalchemy_orm_imports.add(symbol.strip())
            elif stripped.startswith("import sqlalchemy"):
                other_imports.append(line)
            elif stripped.startswith("from ") or stripped.startswith("import "):
                other_imports.append(line)
            elif stripped == "":
                if found_blank_after_imports and other_imports:
                    in_imports = False
                    class_body.append(line)
                else:
                    found_blank_after_imports = True
                    other_imports.append(line)
            else:
                in_imports = False
                class_body.append(line)
        else:
            class_body.append(line)

    # 构建新的导入部分
    new_lines = []

    # 添加非SQLAlchemy导入
    for imp in other_imports:
        new_lines.append(imp)

    # 添加空行（如果需要）
    if other_imports and (sqlalchemy_core_imports or sqlalchemy_orm_imports):
        new_lines.append("")

    # 添加SQLAlchemy核心导入
    if sqlalchemy_core_imports:
        sorted_core = sorted(sqlalchemy_core_imports)
        new_lines.append(f"from sqlalchemy import {', '.join(sorted_core)}")

    # 添加SQLAlchemy ORM导入
    if sqlalchemy_orm_imports:
        sorted_orm = sorted(sqlalchemy_orm_imports)
        new_lines.append(f"from sqlalchemy.orm import {', '.join(sorted_orm)}")

    # 添加空行
    if sqlalchemy_core_imports or sqlalchemy_orm_imports:
        new_lines.append("")

    # 添加类定义部分
    new_lines.extend(class_body)

    # 写回文件
    new_content = "\n".join(new_lines)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✓ 清理: {file_path.relative_to('.')}")
        return True

    return False


def main():
    """主函数"""
    models_dir = Path("src/database/models")
    fixed_count = 0

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if clean_file(py_file):
            fixed_count += 1

    print(f"\n清理完成！共修复 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
