#!/usr/bin/env python3
"""
修复数据库模型文件的导入问题
"""

import re
from pathlib import Path

# 需要添加的常见SQLAlchemy导入
SQLALCHEMY_IMPORTS = {
    "Column": "from sqlalchemy import Column",
    "Integer": "from sqlalchemy import Integer",
    "String": "from sqlalchemy import String",
    "DateTime": "from sqlalchemy import DateTime",
    "Boolean": "from sqlalchemy import Boolean",
    "ForeignKey": "from sqlalchemy import ForeignKey",
    "Enum": "from sqlalchemy import Enum",
    "DECIMAL": "from sqlalchemy import DECIMAL",
    "Text": "from sqlalchemy import Text",
    "Float": "from sqlalchemy import Float",
    "Index": "from sqlalchemy import Index",
    "Mapped": "from sqlalchemy.orm import Mapped",
    "mapped_column": "from sqlalchemy.orm import mapped_column",
    "relationship": "from sqlalchemy.orm import relationship",
    "SQLEnum": "from sqlalchemy import Enum as SQLEnum",
}


def fix_file(file_path: Path):
    """修复单个文件的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    added_imports = set()

    # 查找文件中使用的SQLAlchemy类
    for class_name, import_stmt in SQLALCHEMY_IMPORTS.items():
        # 特殊处理 SQLEnum
        if class_name == "SQLEnum":
            pattern = r"\bSQLEnum\b"
        else:
            pattern = rf"\b{class_name}\b"

        if re.search(pattern, content) and import_stmt not in content:
            added_imports.add(import_stmt)

    # 如果需要添加导入
    if added_imports:
        # 找到导入部分
        lines = content.split("\n")
        import_end_idx = 0

        # 找到最后一个import语句的位置
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                import_end_idx = i

        # 在导入部分后添加新的导入
        if import_end_idx > 0:
            insert_idx = import_end_idx + 1
            # 插入新的导入
            for import_stmt in sorted(added_imports):
                lines.insert(insert_idx, import_stmt)
                insert_idx += 1
            lines.insert(insert_idx, "")  # 添加空行

        # 写回文件
        content = "\n".join(lines)
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 修复: {file_path.relative_to('.')}")
            return True

    return False


def main():
    """主函数"""
    print("修复数据库模型文件的导入问题...")

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
