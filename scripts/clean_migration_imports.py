#!/usr/bin/env python3
"""
清理和修复数据库迁移文件的语法错误
"""

import os
import re
from pathlib import Path


def clean_migration_syntax(file_path):
    """清理单个迁移文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复常见的语法错误
        # 1. 修复 "from alembic import op, import logging" 这类错误
        content = re.sub(
            r"from alembic import op, import logging.*", "from alembic import op", content
        )

        # 2. 修复 "from alembic import op, from sqlalchemy import text" 这类错误
        content = re.sub(
            r"from alembic import op, from sqlalchemy import.*", "from alembic import op", content
        )

        # 3. 修复 "from alembic import op, import logging, logger = logging.getLogger" 这类错误
        content = re.sub(r"from alembic import op,.*", "from alembic import op", content)

        # 4. 确保必要的导入存在
        needs_logging = "logger." in content and "import logging" not in content
        needs_logger_def = "logger." in content and "logger = logging.getLogger" not in content
        needs_text = "text(" in content and "from sqlalchemy import text" not in content
        needs_context = "context." in content and "from alembic import context" not in content

        # 在适当位置添加导入
        lines = content.split("\n")

        # 找到合适的插入位置（在现有导入之后）
        insert_pos = 0
        for i, line in enumerate(lines):
            if (
                line.startswith("# revision identifiers")
                or line.startswith('"""')
                or line.startswith("revision =")
            ):
                insert_pos = i
                break

        # 添加必要的导入
        imports_to_add = []
        if needs_logging:
            imports_to_add.append("import logging")
        if needs_text and "from sqlalchemy import text" not in content:
            imports_to_add.append("from sqlalchemy import text")
        if needs_context and "from alembic import context" not in content:
            imports_to_add.append("from alembic import context")

        # 插入导入
        for imp in reversed(imports_to_add):
            lines.insert(insert_pos, imp)

        # 添加logger定义（如果需要）
        if needs_logger_def:
            lines.insert(insert_pos + len(imports_to_add), "logger = logging.getLogger(__name__)")

        # 重新组合内容
        fixed_content = "\n".join(lines)

        # 写回文件（如果有修改）
        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 清理了 {file_path.name}")
            return True
        else:
            print(f"⚪ 无需清理 {file_path.name}")
            return False

    except Exception as e:
        print(f"❌ 清理失败 {file_path.name}: {e}")
        return False


def main():
    """主函数"""
    migrations_dir = Path("src/database/migrations/versions")

    if not migrations_dir.exists():
        print("❌ 迁移目录不存在")
        return

    migration_files = list(migrations_dir.glob("*.py"))
    print(f"🧹 清理 {len(migration_files)} 个迁移文件...")

    cleaned_count = 0
    total_count = len(migration_files)

    for file_path in sorted(migration_files):
        if clean_migration_syntax(file_path):
            cleaned_count += 1

    print(f"\n📊 清理完成: {cleaned_count}/{total_count} 个文件被清理")


if __name__ == "__main__":
    main()
