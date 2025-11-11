#!/usr/bin/env python3
"""
SQLAlchemy导入修复脚本 - 专门处理sa未定义名称错误
SQLAlchemy import fix script - specifically handle sa undefined name errors
"""

from pathlib import Path


def add_sqlalchemy_import(file_path: Path) -> bool:
    """向文件添加SQLAlchemy导入"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经包含SQLAlchemy导入
        if ('import sqlalchemy' in content or 'from sqlalchemy' in content):
            return False

        # 检查是否使用了sa.模式
        if 'sa.' not in content:
            return False

        lines = content.split('\n')

        # 找到导入语句的位置
        import_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_line = i + 1

        # 插入SQLAlchemy导入
        if import_line > 0:
            lines.insert(import_line, 'import sqlalchemy as sa')
        else:
            # 如果没有现有导入，在文件开头添加
            lines.insert(0, 'import sqlalchemy as sa')

        # 写回文件
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception:
        return False

def fix_database_migrations():
    """修复数据库迁移文件中的SQLAlchemy导入"""

    migrations_path = Path("src/database/migrations/versions")
    if not migrations_path.exists():
        return 0

    fixed_count = 0
    total_files = 0

    for py_file in migrations_path.glob("*.py"):
        total_files += 1
        if add_sqlalchemy_import(py_file):
            fixed_count += 1

    return fixed_count

def fix_other_sqlalchemy_files():
    """修复其他文件中的SQLAlchemy导入"""

    src_path = Path("src")
    fixed_count = 0

    for py_file in src_path.rglob("*.py"):
        # 跳过迁移文件（已处理）和__init__.py文件
        if "migrations/versions" in str(py_file) or py_file.name == "__init__.py":
            continue

        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 检查是否需要SQLAlchemy导入但没有导入
            if 'sa.' in content and 'import sqlalchemy' not in content and 'from sqlalchemy' not in content:
                if add_sqlalchemy_import(py_file):
                    fixed_count += 1

        except Exception:
            pass

    return fixed_count

def main():
    """主函数"""

    # 修复数据库迁移文件
    migration_fixed = fix_database_migrations()

    # 修复其他文件
    other_fixed = fix_other_sqlalchemy_files()

    migration_fixed + other_fixed


if __name__ == "__main__":
    main()
