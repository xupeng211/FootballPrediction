#!/usr/bin/env python3
"""
批量修复MyPy类型错误
"""

import os
import re
from pathlib import Path
from datetime import datetime


def fix_redis_errors():
    """修复Redis相关错误"""
    print("\n🔧 修复Redis相关类型错误...")

    # 找到所有使用RedisError但没有导入的文件
    files_with_redis_errors = [
        "src/services/processing/caching/processing_cache.py",
        "src/cache/consistency_manager.py",
    ]

    for file_path in files_with_redis_errors:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否需要添加导入
        if (
            "RedisError" in content
            and "from redis.exceptions import RedisError" not in content
        ):
            # 查找导入位置
            import_pattern = r"(import redis\n|import redis\.asyncio)"
            if re.search(import_pattern, content):
                # 在redis导入后添加RedisError导入
                content = re.sub(
                    import_pattern,
                    r"\1from redis.exceptions import RedisError\n",
                    content,
                )

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"  ✅ 已修复: {file_path}")


def fix_sqlalchemy_errors():
    """修复SQLAlchemy相关错误"""
    print("\n🔧 修复SQLAlchemy相关类型错误...")

    # 找到所有数据库迁移文件
    migrations_dir = Path("src/database/migrations/versions")
    if not migrations_dir.exists():
        return

    for py_file in migrations_dir.glob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否需要添加导入
        if (
            "SQLAlchemyError" in content
            and "from sqlalchemy.exc import SQLAlchemyError" not in content
        ):
            # 在文件开头添加导入
            lines = content.split("\n")

            # 找到第一个导入位置
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("from sqlalchemy"):
                    insert_idx = i
                    break

            # 插入SQLAlchemy错误导入
            lines.insert(
                insert_idx,
                "from sqlalchemy.exc import SQLAlchemyError, DatabaseError\n",
            )

            with open(py_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"  ✅ 已修复: {py_file}")


def fix_http_errors():
    """修复HTTP相关错误"""
    print("\n🔧 修复HTTP相关类型错误...")

    # API文件列表
    api_files = [
        "src/api/app.py",
        "src/api/predictions_mod/prediction_handlers.py",
        "src/api/predictions_mod/history_handlers.py",
        "src/api/predictions_mod/batch_handlers.py",
    ]

    for file_path in api_files:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否需要添加导入
        if (
            "HTTPError" in content or "RequestException" in content
        ) and "from requests.exceptions import" not in content:
            # 查找导入位置
            import_pattern = r"(from fastapi import|import fastapi)"
            if re.search(import_pattern, content):
                # 在FastAPI导入前添加requests导入
                content = re.sub(
                    import_pattern,
                    "from requests.exceptions import HTTPError, RequestException\n\n\\1",
                    content,
                )

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"  ✅ 已修复: {file_path}")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 批量修复MyPy类型错误")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. 修复Redis错误
    fix_redis_errors()

    # 2. 修复SQLAlchemy错误
    fix_sqlalchemy_errors()

    # 3. 修复HTTP错误
    fix_http_errors()

    print("\n" + "=" * 80)
    print("✅ 批量修复完成！")
    print("=" * 80)

    print("\n📝 建议下一步:")
    print("1. 运行 'make mypy-check' 验证修复效果")
    print("2. 手动处理剩余的复杂类型错误")
    print("3. 考虑在mypy.ini中添加忽略规则")


if __name__ == "__main__":
    main()
