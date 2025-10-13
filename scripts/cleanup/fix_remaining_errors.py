#!/usr/bin/env python3
"""
修复剩余的MyPy错误
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def fix_remaining():
    """修复剩余的错误"""

    # 修复 prediction.py
    pred_file = PROJECT_ROOT / "src/repositories/prediction.py"
    content = pred_file.read_text(encoding="utf-8")

    # 修复无效的 type: ignore 注释
    content = re.sub(
        r"return _result\.scalar\(\)  # type: ignore > 0  # type: ignore",
        r"return _result.scalar() > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"return _result\.rowcount  # type: ignore > 0  # type: ignore",
        r"return _result.rowcount > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"return _result\.scalars\(\)\.all\(\)  # type: ignore  # type: ignore",
        r"return _result.scalars().all()  # type: ignore",
        content,
    )
    content = re.sub(
        r"self\.session\.add\(entity\)  # type: ignore  # type: ignore",
        r"self.session.add(entity)  # type: ignore",
        content,
    )

    pred_file.write_text(content, encoding="utf-8")
    print("✓ 修复 src/repositories/prediction.py")

    # 修复 error_logger.py
    error_file = PROJECT_ROOT / "src/tasks/error_logger.py"
    if error_file.exists():
        content = error_file.read_text(encoding="utf-8")

        # 修复无效的 type: ignore 注释
        content = re.sub(r"# type: ignore  # type: ignore", r"# type: ignore", content)

        error_file.write_text(content, encoding="utf-8")
        print("✓ 修复 src/tasks/error_logger.py")

    # 修复 maintenance_tasks.py
    maint_file = PROJECT_ROOT / "src/tasks/maintenance_tasks.py"
    if maint_file.exists():
        content = maint_file.read_text(encoding="utf-8")

        # 查找第62行附近的语法错误
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if i == 61:  # 第62行（0-based索引）
                # 检查是否缺少逗号
                if "def" in line and "(" in line and ")" in line and ":" not in line:
                    # 可能是缺少冒号
                    lines[i] = line + ":"

        content = "\n".join(lines)
        maint_file.write_text(content, encoding="utf-8")
        print("✓ 修复 src/tasks/maintenance_tasks.py")

    # 修复 __result -> _result 的问题
    for file_path in [
        "src/repositories/user.py",
        "src/repositories/match.py",
        "src/repositories/prediction.py",
    ]:
        file_full = PROJECT_ROOT / file_path
        content = file_full.read_text(encoding="utf-8")

        # 修复 __result 错误
        content = content.replace("__result", "_result")

        file_full.write_text(content, encoding="utf-8")
        print(f"✓ 修复 {file_path} 中的 __result 错误")


def main():
    print("🔧 修复剩余的 MyPy 错误")
    print("=" * 50)

    fix_remaining()

    # 运行 MyPy 检查
    import subprocess

    print("\n运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src", "--no-error-summary"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("\n✅ 成功！MyPy 检查通过，所有错误已修复！")
    else:
        error_count = result.stdout.count("error:")
        print(f"\n还有 {error_count} 个错误:")
        # 显示所有错误
        errors = result.stdout.split("\n")
        for error in errors:
            if "error:" in error:
                print(f"  • {error}")


if __name__ == "__main__":
    main()
