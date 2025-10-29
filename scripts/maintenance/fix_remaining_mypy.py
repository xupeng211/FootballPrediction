#!/usr/bin/env python3
"""
修复剩余的MyPy类型错误
"""

import re
from pathlib import Path
from datetime import datetime


def fix_missing_imports():
    """修复缺失的导入"""
    print("\n🔧 修复缺失的导入...")

    # 修复文件列表
    fixes = [
        {
            "file": "src/services/processing/caching/processing_cache.py",
            "add_imports": [
                "import logging",
                "from typing import Dict, List, Optional, Any, Union",
                "from src.cache.redis import RedisManager, CacheKeyManager",
            ],
        },
        {
            "file": "src/cache/consistency_manager.py",
            "add_imports": [
                "import logging",
                "from typing import Dict, List, Optional, Any",
                "import asyncio",
                "from src.cache.redis import get_redis_manager",
            ],
        },
    ]

    for fix in fixes:
        path = Path(fix["file"])
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False
        for import_line in fix["add_imports"]:
            if import_line.split(" import ")[0] not in content:
                # 在文档字符串后添加
                if content.startswith('"""'):
                    lines = content.split("\n")
                    doc_end = 0
                    for i, line in enumerate(lines[1:], 1):
                        if line.strip() == '"""':
                            doc_end = i + 1
                            break
                    lines.insert(doc_end, import_line)
                    content = "\n".join(lines)
                else:
                    content = import_line + "\n\n" + content
                modified = True

        if modified:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ 已修复: {fix['file']}")


def fix_migration_file_imports():
    """修复迁移文件中的sa别名问题"""
    print("\n🔧 修复迁移文件sa别名...")

    migrations_dir = Path("src/database/migrations/versions")
    if not migrations_dir.exists:
        return

    for py_file in migrations_dir.glob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否使用了sa但没有定义
        if "sa." in content and "import sqlalchemy as sa" not in content:
            # 添加sa别名导入
            lines = content.split("\n")

            # 找到alembic导入位置
            insert_idx = 0
            for i, line in enumerate(lines):
                if "from alembic import" in line:
                    insert_idx = i + 1
                    break

            lines.insert(insert_idx, "import sqlalchemy as sa")

            with open(py_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"  ✅ 已修复sa别名: {py_file.name}")


def remove_unused_type_ignore():
    """移除未使用的type: ignore"""
    print("\n🔧 移除未使用的type: ignore...")

    src_dir = Path("src")
    count = 0

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            original = content

            # 移除特定的type: ignore
            patterns = [
                r"  # type: ignore\n",  # 独立的type: ignore
                r"(\w+\s*:\s*\w+)  # type: ignore\b",  # 类型注解后的type: ignore
            ]

            for pattern in patterns:
                content = re.sub(pattern, r"\1", content)

            if content != original:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)
                count += 1

        except Exception:
            pass

    print(f"  ✅ 已清理 {count} 个文件的 type: ignore")


def fix_pytest_plugins():
    """修复pytest_plugins类型注解"""
    print("\n🔧 修复pytest_plugins类型注解...")

    init_files = [
        "tests/unit/repositories/__init__.py",
        "tests/unit/domain/__init__.py",
        "tests/unit/core/__init__.py",
        "tests/integration/services/__init__.py",
    ]

    for file_path in init_files:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 添加类型注解
        if "pytest_plugins = [" in content and ":" not in content:
            content = content.replace("pytest_plugins = [", "pytest_plugins: list[str] = [")

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"  ✅ 已修复: {file_path}")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 修复剩余的MyPy类型错误")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 执行修复
    fix_missing_imports()
    fix_migration_file_imports()
    fix_pytest_plugins()
    remove_unused_type_ignore()

    print("\n" + "=" * 80)
    print("✅ 修复完成！")
    print("=" * 80)

    print("\n📊 运行检查:")
    print("mypy src/ --show-error-codes")


if __name__ == "__main__":
    main()
