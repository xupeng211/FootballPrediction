#!/usr/bin/env python3
"""
最终修复MyPy错误
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def fix_final_errors():
    """修复所有剩余的MyPy错误"""

    # 修复 match.py
    match_file = PROJECT_ROOT / "src/repositories/match.py"
    content = match_file.read_text(encoding="utf-8")

    # 修复无效的 type: ignore 注释
    content = re.sub(
        r"return _result\.scalar\(\)  # type: ignore > 0  # type: ignore",
        r"return _result.scalar() > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"return _result\.rowcount  # type: ignore > 0",
        r"return _result.rowcount > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"return _result\.scalars\(\)\.all\(\)  # type: ignore  # type: ignore",
        r"return _result.scalars().all()  # type: ignore",
        content,
    )

    match_file.write_text(content, encoding="utf-8")
    print("✓ 修复 src/repositories/match.py")

    # 修复 prediction.py
    pred_file = PROJECT_ROOT / "src/repositories/prediction.py"
    content = pred_file.read_text(encoding="utf-8")

    content = re.sub(
        r"if result\.rowcount  # type: ignore > 0:",
        r"if _result.rowcount > 0:  # type: ignore",
        content,
    )

    pred_file.write_text(content, encoding="utf-8")
    print("✓ 修复 src/repositories/prediction.py")

    # 修复 user.py 中的类似问题
    user_file = PROJECT_ROOT / "src/repositories/user.py"
    content = user_file.read_text(encoding="utf-8")

    content = re.sub(
        r"return _result\.scalar\(\)  # type: ignore > 0  # type: ignore",
        r"return _result.scalar() > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"return _result\.rowcount  # type: ignore > 0",
        r"return _result.rowcount > 0  # type: ignore",
        content,
    )
    content = re.sub(
        r"if result\.rowcount  # type: ignore > 0:",
        r"if _result.rowcount > 0:  # type: ignore",
        content,
    )
    content = re.sub(
        r"self\.session\.add\(entity\)  # type: ignore  # type: ignore",
        r"self.session.add(entity)  # type: ignore",
        content,
    )

    user_file.write_text(content, encoding="utf-8")
    print("✓ 修复 src/repositories/user.py")


def main():
    print("🔧 最终修复 MyPy 错误")
    print("=" * 50)

    fix_final_errors()

    # 运行 MyPy 检查
    import subprocess

    print("\n运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src", "--no-error-summary", "--show-error-codes"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("\n✅ 成功！MyPy 检查通过，没有错误！")
    else:
        error_count = result.stdout.count("error:")
        print(f"\n⚠️  还有 {error_count} 个错误:")
        # 显示前几个错误
        errors = result.stdout.split("\n")
        for error in errors:
            if "error:" in error:
                print(f"  • {error}")


if __name__ == "__main__":
    main()
