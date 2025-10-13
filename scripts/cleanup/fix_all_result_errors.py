#!/usr/bin/env python3
"""
修复所有的 result -> _result 错误
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent


def fix_all_result_errors():
    """修复所有文件中的 result -> _result 错误"""

    # 需要修复的文件
    files_to_fix = ["src/tasks/maintenance_tasks.py", "src/tasks/error_logger.py"]

    total_fixes = 0

    for file_path in files_to_fix:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8")
        original_content = content

        # 修复 (await result.scalar() 模式
        content = re.sub(
            r"\(await result\.scalar\(\)  # type: ignore\)",
            r"(_result.scalar() or 0)  # type: ignore",
            content,
        )

        # 修复 (result.scalar() 模式
        content = re.sub(
            r"\(result\.scalar\(\)  # type: ignore\)",
            r"(_result.scalar() or 0)  # type: ignore",
            content,
        )

        # 修复 result.scalar() 模式（不在括号内的）
        content = re.sub(
            r"result\.scalar\(\)  # type: ignore",
            r"_result.scalar()  # type: ignore",
            content,
        )

        if content != original_content:
            full_path.write_text(content, encoding="utf-8")
            print(f"✓ 修复 {file_path}")
            total_fixes += 1

    return total_fixes


def main():
    print("🔧 修复所有 result -> _result 错误")
    print("=" * 50)

    fixes = fix_all_result_errors()
    print(f"\n总计修复了 {fixes} 个文件")

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
    else:
        error_count = result.stdout.count("error:")
        print(f"\n⚠️  还有 {error_count} 个错误需要手动修复:")
        errors = result.stdout.split("\n")
        for error in errors:
            if "error:" in error:
                print(f"  • {error}")


if __name__ == "__main__":
    main()
