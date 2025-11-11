#!/usr/bin/env python3
"""
批量修复migrations文件中的sa导入问题
"""

from pathlib import Path


def fix_migration_file(file_path):
    """修复单个migration文件的sa导入"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # 检查是否已经导入sa
        for line in lines:
            if 'from sqlalchemy import' in line and 'sa' in line:
                return False

        # 找到sqlalchemy导入的位置
        import_pos = -1
        for i, line in enumerate(lines):
            if 'from sqlalchemy' in line:
                import_pos = i + 1
                break

        if import_pos == -1:
            # 如果没有找到sqlalchemy导入，在其他导入后添加
            for i, line in enumerate(lines):
                if 'from alembic import op' in line:
                    import_pos = i + 1
                    break

        if import_pos == -1:
            return False

        # 添加sa导入
        lines.insert(import_pos, 'from sqlalchemy import text as sa')

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True

    except Exception:
        return False

def main():
    """主函数"""
    migrations_dir = Path("src/database/migrations/versions")

    if not migrations_dir.exists():
        return


    fixed_count = 0
    for py_file in migrations_dir.glob("*.py"):
        if py_file.name != "__init__.py":
            if fix_migration_file(py_file):
                fixed_count += 1


if __name__ == "__main__":
    main()
