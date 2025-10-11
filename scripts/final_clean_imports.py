#!/usr/bin/env python3
"""
最终清理重复导入
"""

from pathlib import Path


def clean_file_imports(file_path: Path):
    """彻底清理文件的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取所有导入
    imports_section = []
    class_section = []
    in_imports = True

    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()

        if in_imports and (
            stripped.startswith("from ")
            or stripped.startswith("import ")
            or stripped == ""
        ):
            if stripped.startswith("from ") or stripped.startswith("import "):
                imports_section.append(stripped)
            continue
        else:
            in_imports = False
            class_section.append(line)

    # 去重导入
    seen = set()
    unique_imports = []
    for imp in imports_section:
        if imp and imp not in seen:
            seen.add(imp)
            unique_imports.append(imp)

    # 分类导入
    base_imports = []
    sqlalchemy_imports = []
    sqlalchemy_orm_imports = []
    other_imports = []

    for imp in unique_imports:
        if imp.startswith("from ..base import"):
            base_imports.append(imp)
        elif imp.startswith("from sqlalchemy import"):
            sqlalchemy_imports.append(imp)
        elif imp.startswith("from sqlalchemy.orm import"):
            sqlalchemy_orm_imports.append(imp)
        elif imp.startswith("import sqlalchemy"):
            base_imports.append(imp)
        else:
            other_imports.append(imp)

    # 重新构建内容
    new_lines = []

    # 添加标准库导入
    for imp in other_imports:
        if not imp.startswith("from src.") and not imp.startswith("from .."):
            new_lines.append(imp)

    if other_imports and any(
        not imp.startswith("from src.") and not imp.startswith("from ..")
        for imp in other_imports
    ):
        new_lines.append("")

    # 添加第三方库导入
    for imp in sqlalchemy_imports:
        new_lines.append(imp)
    for imp in sqlalchemy_orm_imports:
        new_lines.append(imp)

    if sqlalchemy_imports or sqlalchemy_orm_imports:
        new_lines.append("")

    # 添加项目导入
    for imp in base_imports:
        new_lines.append(imp)
    for imp in other_imports:
        if imp.startswith("from src.") or imp.startswith("from .."):
            new_lines.append(imp)

    new_lines.append("")
    new_lines.extend(class_section)

    # 写回文件
    new_content = "\n".join(new_lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ 清理: {file_path.relative_to('.')}")


def main():
    """主函数"""
    files = [
        "src/database/models/league.py",
        "src/database/models/audit_log.py",
        "src/database/models/data_collection_log.py",
        "src/database/models/data_quality_log.py",
        "src/database/models/features.py",
        "src/database/models/odds.py",
        "src/database/models/user.py",
        "src/database/models/predictions.py",
        "src/database/models/team.py",
        "src/database/models/match.py",
        "src/database/models/raw_data.py",
    ]

    for file_path in files:
        path = Path(file_path)
        if path.exists():
            clean_file_imports(path)

    print("\n清理完成！")


if __name__ == "__main__":
    main()
