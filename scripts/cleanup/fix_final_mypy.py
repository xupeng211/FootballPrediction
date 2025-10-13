#!/usr/bin/env python3
"""
最终修复所有MyPy错误
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent


def fix_final_errors():
    """修复最后的错误"""

    # 修复 maintenance_tasks.py
    maint_file = PROJECT_ROOT / "src/tasks/maintenance_tasks.py"
    content = maint_file.read_text(encoding="utf-8")

    # 修复无效的 type: ignore 注释
    content = re.sub(
        r"\(_result\.scalar\(\) or 0\)  # type: ignore or 0",
        r"(_result.scalar() or 0)  # type: ignore",
        content,
    )

    # 修复 result.rowcount 错误
    content = content.replace(
        "cleaned_sessions = result.rowcount  # type: ignore",
        "cleaned_sessions = _result.rowcount  # type: ignore",
    )

    # 修复 result.fetchall 错误
    content = content.replace(
        "rows = await result.fetchall()", "rows = _result.fetchall()"
    )

    maint_file.write_text(content, encoding="utf-8")
    print("✓ 修复 src/tasks/maintenance_tasks.py")

    # 修复 utils.py
    utils_file = PROJECT_ROOT / "src/tasks/utils.py"
    if utils_file.exists():
        content = utils_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # 查找第226行附近的语法错误
        for i, line in enumerate(lines):
            if i == 225:  # 第226行（0-based索引）
                if "def" in line and "(" in line and ")" in line and ":" not in line:
                    lines[i] = line + ":"

        content = "\n".join(lines)
        utils_file.write_text(content, encoding="utf-8")
        print("✓ 修复 src/tasks/utils.py")

    # 修复 maintenance_tasks.py 中的其他导入问题
    content = maint_file.read_text(encoding="utf-8")
    if "from sqlalchemy import text" not in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "from src.database.connection import DatabaseManager" in line:
                lines.insert(i + 1, "from sqlalchemy import text")
                break
        content = "\n".join(lines)
        maint_file.write_text(content, encoding="utf-8")
        print("✓ 添加 text 导入")

    # 修复 redis 导入
    if "import redis" not in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("import asyncio"):
                lines.insert(i + 1, "import redis")
                break
        content = "\n".join(lines)
        maint_file.write_text(content, encoding="utf-8")
        print("✓ 添加 redis 导入")

    # 修复 TaskErrorLogger 导入
    if "TaskErrorLogger" in content and "TaskErrorLogger" not in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "from src.tasks.celery_app import app" in line:
                lines.insert(
                    i + 1, "from src.tasks.error_logger import TaskErrorLogger"
                )
                break
        content = "\n".join(lines)
        maint_file.write_text(content, encoding="utf-8")
        print("✓ 添加 TaskErrorLogger 导入")


def main():
    print("🔧 最终修复所有 MyPy 错误")
    print("=" * 50)

    fix_final_errors()

    # 运行最终检查
    import subprocess

    print("\n运行 MyPy 最终检查...")
    result = subprocess.run(
        ["mypy", "src", "--no-error-summary"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("\n✅ 成功！MyPy 检查完全通过！")
        print("🎉 所有 MyPy 错误已修复！")
        return 0
    else:
        error_count = result.stdout.count("error:")
        print(f"\n⚠️  还有 {error_count} 个错误:")
        errors = result.stdout.split("\n")
        for error in errors:
            if "error:" in error:
                print(f"  • {error}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
