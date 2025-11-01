#!/usr/bin/env python3
"""
批量修复数据库迁移文件的导入问题
"""

import os
import re
from pathlib import Path


def fix_migration_imports(file_path):
    """修复单个迁移文件的导入问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 检查是否需要添加各种导入
        needs_op = "op." in content and "from alembic import op" not in content
        needs_context = "context." in content and "from alembic import context" not in content
        needs_text = "text(" in content and "from sqlalchemy import text" not in content
        needs_logger = (
            "logger." in content
            and "logger = logging.getLogger" not in content
            and "import logging" not in content
        )

        # 在适当位置添加导入
        lines = content.split("\n")
        import_section_end = 0

        # 找到导入部分的结束位置
        for i, line in enumerate(lines):
            if (
                line.startswith("# revision identifiers")
                or line.startswith('"""')
                or line.startswith("revision =")
            ):
                import_section_end = i
                break

        # 构建需要添加的导入
        imports_to_add = []

        if needs_logger:
            if "import logging" not in content:
                imports_to_add.append("import logging")
            if "logger = logging.getLogger" not in content:
                imports_to_add.append("logger = logging.getLogger(__name__)")

        if needs_text and "from sqlalchemy import text" not in content:
            imports_to_add.append("from sqlalchemy import text")

        if needs_context:
            imports_to_add.append("from alembic import context")

        if needs_op:
            imports_to_add.append("from alembic import op")

        # 插入导入
        if imports_to_add:
            # 检查是否已经有 from alembic import 行，可以合并
            alembic_import_line = -1
            for i in range(import_section_end):
                if "from alembic import" in lines[i]:
                    alembic_import_line = i
                    break

            if alembic_import_line >= 0:
                # 合并到现有的alembic导入行
                existing_import = lines[alembic_import_line]
                parts = existing_import.split("import ")
                if len(parts) > 1:
                    current_imports = parts[1].split(", ")
                    new_imports = []

                    for imp in imports_to_add:
                        imp_name = imp.replace("from alembic import ", "").strip()
                        if imp_name not in current_imports:
                            new_imports.append(imp_name)

                    if new_imports:
                        lines[alembic_import_line] = (
                            f"{parts[0]}import {', '.join(current_imports + new_imports)}"
                        )
                        # 移除已添加的导入
                        imports_to_add = [
                            imp
                            for imp in imports_to_add
                            if not imp.startswith("from alembic import")
                        ]

            # 插入剩余的导入
            if imports_to_add:
                for imp in reversed(imports_to_add):
                    lines.insert(import_section_end, imp)

        # 重新组合内容
        fixed_content = "\n".join(lines)

        # 写回文件（如果有修改）
        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 修复了 {file_path.name}")
            return True
        else:
            print(f"⚪ 无需修复 {file_path.name}")
            return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path.name}: {e}")
        return False


def main():
    """主函数"""
    migrations_dir = Path("src/database/migrations/versions")

    if not migrations_dir.exists():
        print("❌ 迁移目录不存在")
        return

    migration_files = list(migrations_dir.glob("*.py"))
    print(f"🔍 检查 {len(migration_files)} 个迁移文件...")

    fixed_count = 0
    total_count = len(migration_files)

    for file_path in sorted(migration_files):
        if fix_migration_imports(file_path):
            fixed_count += 1

    print(f"\n📊 修复完成: {fixed_count}/{total_count} 个文件被修复")


if __name__ == "__main__":
    main()
